"""Spec-driven autonomous build driver — the harness as BRAIN *and* HANDS.

`plan_from_spec(spec)` decides the ordered build steps; each is rendered to a
pre-corrected Mentor prompt; this driver fires it through the harness's own
`MentorMCP` client (mcp-remote → OutSystems MCP), polls to terminal, publishes
per unit, and halts on failure — with ZERO turn-by-turn human authoring. A
Claude Code session's only job is to launch this and watch; the harness does the
build. This is the spec-driven counterpart to `banking_runner.orchestrator`
(which is wired to the home_banking manifest + hardcoded phases instead).

Design decisions:
  * SERIAL execution in plan order. Unlike the banking phase-runner (concurrent
    within a phase), spec steps have hard ordering deps (data-model → screens →
    list bindings → seed) and `plan_from_spec` already emits them topologically.
  * PUBLISH PER UNIT, using the session credentials returned by mentor_poll —
    the proven orchestrator shape (publish is bound to the Mentor session, not a
    phase). Recipes tell Mentor NOT to self-publish; the driver publishes.
  * RETRY ONCE on a transient failure, then HALT (don't fire dependent steps
    into a broken model). Resumable: StateDB skips already-succeeded steps.
  * The step logic is MCP-agnostic (any object with mentor_start/mentor_poll/
    publish_start/publish_wait) so it unit-tests against a fake client.

CLI:
    python -m harness.run_build SPEC.json --app-key KEY      # build into an existing app
    python -m harness.run_build SPEC.json --create --kind CrossDevice
    python -m harness.run_build SPEC.json --plan-only        # print the plan, no MCP (safe preview)
    python -m harness.run_build SPEC.json --app-key KEY --max-steps 1   # canary: fire only step 1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness.prompt_recipes import plan_from_spec, render


@dataclass
class StepResult:
    index: int
    recipe: str
    target: str
    outcome: str                     # 'succeeded' | 'skipped' | an error string
    run_id: Optional[str] = None


@dataclass
class BuildReport:
    app_key: Optional[str]
    total: int
    succeeded: int
    failed: int
    skipped: int
    halted_at: Optional[str] = None
    steps: list[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.halted_at is None


def _slug(text: str, fallback: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-").lower()
    return s or fallback


def _step_target(step: dict, index: int) -> str:
    """A stable, human-readable label for a plan step (StateDB target_name, prompt filename)."""
    p = step.get("params", {})
    primary = (p.get("entity") or p.get("screen") or p.get("name") or p.get("agent_name")
               or p.get("block_name") or p.get("producer_app") or "")
    phase = p.get("phase")           # create-form/row-actions sub-phase disambiguator
    base = f"{step['recipe']}:{_slug(primary, str(index))}"
    # per-button action-button steps share an entity — disambiguate by the button label
    buttons = p.get("buttons")
    if buttons and isinstance(buttons, list) and buttons[0].get("label"):
        base = f"{base}:{_slug(buttons[0]['label'], 'btn')}"
    return f"{base}:{phase}" if phase else base


# ── §Recovery — codified symptom ⇒ action (BUILD_LOOP §Recovery, made deterministic) ──
# This is the synthesis: the autonomous driver reacts to Mentor/publish symptoms the way a
# build-root session would per BUILD_LOOP §Recovery — but reproducibly, with no agent judgment in
# the loop. Three actions cover the rules the driver can act on from a terminal result:
RETRY = "retry"     # transient / hang / wedged / phantom ⇒ re-author in a FRESH session (R1/R7/R9/R12)
HALT = "halt"       # deterministic build-rule failure ⇒ stop with a diagnosis (R11, compile errors)
VERIFY = "verify"   # Mentor+publish say it landed ⇒ CONFIRM via an independent read before trusting

_DPL_50205 = "OS-DPL-50205"

# Errors a RETRY cannot fix — and where a fresh-session retry makes it WORSE (each retry opens
# another Mentor session, so retrying a session-cap failure deepens the exhaustion). Halt fast.
_NONRETRYABLE = ("per_tenant_cap", "session cap", "session_cap", "capacity", "quota",
                 "rate limit", "rate_limit", "too many requests", "unauthorized", "forbidden")


def _nonretryable_reason(result) -> Optional[str]:
    blob = f"{getattr(result, 'error', '') or ''} {result.summary or ''}".lower()
    return next((sig for sig in _NONRETRYABLE if sig in blob), None)


# The subset of non-retryable signals that are TRANSIENT resource contention, not a permanent block:
# a per-tenant session slot may free within seconds (our own publish releasing, or ambient 24h reap).
# Unlike auth/quota/forbidden, these are worth a brief in-build wait-and-retry so the build CASCADES
# through freed slots instead of dropping to the slow external poller. A capped mentor_start is rejected
# pre-admission (no session opened), so retrying it does NOT deepen exhaustion.
_CAP_SIGNALS = ("per_tenant_cap", "session cap", "session_cap", "capacity")


def _is_cap_halt(detail: str) -> bool:
    d = (detail or "").lower()
    return any(sig in d for sig in _CAP_SIGNALS)


def classify_terminal(result) -> tuple[str, str]:
    """A terminal MentorRunResult ⇒ (action, reason). HALT on compile errors (deterministic — a
    recipe gap a re-fire won't fix); RETRY on hang/timeout/cancel (fresh-session re-author, R1/R7);
    VERIFY on a clean success (never trusted until the independent read confirms it, §Turn step 5)."""
    if result.compile_errors:
        return HALT, "compile errors: " + "; ".join(result.compile_errors[:3])
    nr = _nonretryable_reason(result)
    if nr:                              # session-cap / auth / quota — retrying opens MORE sessions
        return HALT, (f"non-retryable ({nr}): {result.error or result.summary}. Stop opening turns and let "
                      f"Mentor session slots release (or raise the tenant cap); resume from the StateDB after.")
    if result.status == "running":
        return RETRY, "hang/timeout past budget — cancel + fresh session (R1)"
    if result.status == "cancelled":
        return RETRY, "cancelled session is unpublishable — re-author fresh (R7)"
    if result.status != "succeeded":
        return RETRY, f"non-terminal-success status={result.status}" + (f": {result.error}" if result.error else "")
    if not result.session_id or not result.session_token:
        return RETRY, "no session credentials at terminal — cannot publish this unit"
    return VERIFY, "succeeded"


def classify_publish(payload: dict) -> tuple[str, str]:
    """A terminal publish_wait payload ⇒ (action, reason). Live ODC contract (canary 2026-07-08):
    success is `state == "succeeded"` (legacy `status == "Finished"` accepted too), failure is
    `state == "failed"` carrying a build-engine `code`. HALT on a deterministic OS-DPL-* code (R11 —
    the server already exhausted transient retries; a re-publish won't fix it); RETRY (bounded,
    fresh re-author) on other failures / non-terminal-success; VERIFY on success — including
    no_changes_detected, which is NOT proof of anything (§Turn 5); the step's own read decides."""
    blob = json.dumps(payload)
    state = (payload.get("state") or "").lower()
    status = payload.get("status") or ""
    succeeded = state == "succeeded" or status == "Finished"
    failed = state in ("failed", "cancelled") or status in ("Failed", "Cancelled")
    if failed or _DPL_50205 in blob:
        code = (payload.get("code") or "").upper()
        detail = (payload.get("detail") or payload.get("message") or "").strip()
        detail_txt = f" — {detail[:400]}" if detail else ""
        if code.startswith("OS-DPL") or _DPL_50205 in blob:
            return HALT, (f"publish failed {code or _DPL_50205}{detail_txt} (R11 — deterministic "
                          f"build-rule; common causes: a public/exposed action that writes entities or "
                          f"carries an Entity Record/Identifier signature; a public action that raises a "
                          f"Global Event; a local FK to a cross-app entity; or a PUBLIC Web Block whose "
                          f"internal action navigates (DestinationNode). Diagnose the element; do NOT re-publish.)")
        return RETRY, f"publish failed {code or state or status}{detail_txt} — fresh re-author"
    if not succeeded:
        return RETRY, f"publish not terminal-success (state={state or status})"
    if payload.get("no_changes_detected"):
        return VERIFY, "no_changes_detected — nothing deployed; the independent read decides if the unit is present"
    return VERIFY, "published"


def _names_from(payload: dict, keys=("items", "data", "entities", "screens", "results")) -> list[str]:
    """Defensively pull element names out of a context_* payload across ODC response shapes.
    Returns [] when nothing parseable — the caller treats that as 'cannot verify', never a defect."""
    rows = None
    for k in keys:
        v = payload.get(k)
        if isinstance(v, list):
            rows = v
            break
    if rows is None and isinstance(payload.get("data"), dict):
        for k in keys:
            v = payload["data"].get(k)
            if isinstance(v, list):
                rows = v
                break
    names = []
    for r in rows or []:
        if isinstance(r, dict):
            n = r.get("name") or r.get("Name") or r.get("label")
            if n:
                names.append(n)
        elif isinstance(r, str):
            names.append(r)
    return names


def _entities_missing_identifier(payload: dict, want: list[str]) -> list[str]:
    """R9: entities present in the read but with NO identifier attribute (the silent phantom that
    detonates at the first write-path). Best-effort — only flags when the payload exposes the field."""
    rows = None
    for k in ("items", "data", "entities"):
        v = payload.get(k)
        if isinstance(v, list):
            rows = v
            break
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or r.get("Name")
        if name not in want:
            continue
        has_id = r.get("hasIdentifier")
        if has_id is None:
            ident = r.get("identifier") or r.get("identifierAttribute") or r.get("keyAttribute")
            attrs = r.get("attributes") or r.get("Attributes") or []
            if ident:
                has_id = True
            elif isinstance(attrs, list) and attrs:
                has_id = any((isinstance(a, dict) and (a.get("isIdentifier") or a.get("name") == "Id"))
                             for a in attrs)
            else:
                has_id = None            # unknown → do not flag (can't verify)
        if has_id is False:
            out.append(name)
    return out


class SpecDriver:
    """Runs a plan_from_spec build end-to-end through an MCP client — the harness as brain AND hands.

    Autonomous like a pure runner, adaptive like a build-root session: it fires each harness-rendered
    step, then reacts to the terminal + publish symptoms per the codified §Recovery rules
    (classify_terminal/classify_publish) and CONFIRMS each unit landed via an independent context read
    (_verify_step) before trusting it — up to `max_attempts` fresh-session re-authors, then halts.

    The MCP client needs mentor_start / mentor_poll / publish_start / publish_wait; optionally
    mentor_cancel (R1/R7 hang recovery) and context_entities / context_screens (honest verification).
    Missing optional methods degrade gracefully — verification is skipped, never faked green."""

    def __init__(self, mcp, prompts_dir: Path, *, per_call_timeout: int = 400,
                 publish_timeout: int = 600, db=None, env_key: str = "", max_attempts: int = 3,
                 cap_wait_seconds: float = 8.0, cap_retries: int = 6, reuse_session: bool = True):
        self.mcp = mcp
        self.prompts_dir = Path(prompts_dir)
        self.per_call_timeout = per_call_timeout
        self.publish_timeout = publish_timeout
        self.db = db                 # optional StateDB for resumable runs
        self.env_key = env_key       # ODC Dev environment key for publishes (resolved via env_list)
        self.max_attempts = max(1, max_attempts)   # fresh-session re-authors before halting (§Recovery)
        # Cap-cascade: on a per-tenant-cap hit, wait this long and re-fire the SAME step (up to
        # cap_retries) before halting to the external poller — lets a build ride freed slots and flow
        # through consecutive steps in one invocation instead of one-step-per-poller-tick.
        self.cap_wait_seconds = max(0.0, cap_wait_seconds)
        self.cap_retries = max(0, cap_retries)
        # SESSION ECONOMY: reuse ONE Mentor session (one per-tenant slot) across a build's steps via
        # fresh_context resume turns, instead of opening a new session per step (greedy — saturates the
        # 100-cap on a big build). `_session` holds the live (id, token) for the current build; it is
        # DROPPED on any step failure so a write-wedged session self-heals into a fresh one, and the
        # per-step independent _verify_step catches a silent rollback. Cancelled once at build end.
        self.reuse_session = reuse_session
        self._session: Optional[tuple[str, str]] = None
        self._last_run_id: Optional[str] = None

    async def build(self, spec: dict, app_key: str, *, app_name: str = "app",
                    max_steps: Optional[int] = None) -> BuildReport:
        steps = plan_from_spec(spec)
        if max_steps is not None:
            steps = steps[:max_steps]
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # Targets that repeat in THIS plan (e.g. two list-screens bound to the same entity on
        # different screens both render as `list-screen:<entity>`). Only these need position-aware
        # skip-matching; unique targets match by name alone, so inserting/removing steps elsewhere
        # doesn't shift their identity and needlessly re-fire them on resume.
        from collections import Counter
        counts = Counter(_step_target(s, i) for i, s in enumerate(steps))
        self._dup_targets = {t for t, c in counts.items() if c > 1}

        report = BuildReport(app_key=app_key, total=len(steps),
                             succeeded=0, failed=0, skipped=0)
        for i, step in enumerate(steps):
            target = _step_target(step, i)
            if self.db is not None and self._already_succeeded(app_name, i, target):
                report.skipped += 1
                report.steps.append(StepResult(i, step["recipe"], target, "skipped"))
                print(f"  [{i+1}/{len(steps)}] ⏭  {target} (already succeeded)")
                continue

            print(f"  [{i+1}/{len(steps)}] ▶  {step['recipe']} — {step.get('why', target)}")
            res = await self._drive_step(step, i, target, app_key, app_name)
            report.steps.append(res)
            if res.outcome == "succeeded":
                report.succeeded += 1
                print(f"          ✓ {target}")
            else:
                report.failed += 1
                report.halted_at = target
                print(f"          ✗ {target}: {res.outcome} — HALT")
                break
        # Release the ONE session this build held (best-effort; if cancel is a no-op on a terminal run
        # the single session still reaps in 24h — but we spent 1 slot for the whole build, not N).
        if self._session is not None and self._last_run_id is not None:
            await self._safe_cancel(self._last_run_id)
            self._session = None
        return report

    def _already_succeeded(self, app: str, index: int, target: str) -> bool:
        # A step is "already done" if a succeeded row matches its target. For targets that repeat in
        # the plan (duplicates), also require the plan position (phase=index) to match — else the
        # second occurrence is silently skipped as a dup of the first (the intake-table bug,
        # 2026-07-09: two `list-screen:supplier` on different screens). Unique targets match by name
        # alone, so they survive index shifts from edits elsewhere without a needless re-fire.
        want_phase = f"{index:03d}" if target in getattr(self, "_dup_targets", set()) else None
        for call in self.db.list_by_status(app, "succeeded"):
            if call.target_name == target and (want_phase is None or call.phase == want_phase):
                return True
        return False

    async def _drive_step(self, step: dict, index: int, target: str, app_key: str,
                          app_name: str) -> StepResult:
        """Fire one plan step and drive it to a VERIFIED success, applying §Recovery: HALT on a
        deterministic build-rule failure, else up to `max_attempts` FRESH-session re-authors on a
        transient/hang/phantom, confirming via an independent read each success. This is the adaptive
        core — the reproducible version of what a build-root session does by hand."""
        recipe = step["recipe"]
        try:
            prompt = render(recipe, step.get("params", {}))
        except Exception as exc:  # a bad param dict is a plan bug, not a Mentor failure
            return StepResult(index, recipe, target, f"render error: {exc}")
        prompt_path = self.prompts_dir / f"{index:03d}_{_slug(target, str(index))}.prompt.txt"
        prompt_path.write_text(prompt)
        row_id = self.db.upsert_pending(app_name, f"{index:03d}", target, str(prompt_path)) if self.db else None

        last = "not attempted"
        last_run_id = None
        cap_waits = 0
        attempt = 0
        while attempt < self.max_attempts:
            attempt += 1
            action, detail, result = await self._attempt_step(prompt, app_key, row_id)
            last = detail
            last_run_id = result.run_id if result else last_run_id
            if action == HALT:
                # Cap contention is transient: wait briefly and re-fire the SAME step so the build
                # cascades through slots as they free, rather than halting to the 10-min poller. A
                # busy slot is not a failed author attempt, so it doesn't burn one. Bounded, then halt.
                if _is_cap_halt(detail) and cap_waits < self.cap_retries:
                    cap_waits += 1
                    attempt -= 1
                    print(f"          ⏳ cap wait {cap_waits}/{self.cap_retries}: session slot busy — "
                          f"retry in {self.cap_wait_seconds:g}s")
                    await asyncio.sleep(self.cap_wait_seconds)
                    continue
                if row_id is not None:
                    self.db.mark_failed(row_id, detail)
                return StepResult(index, recipe, target, f"halt: {detail}", run_id=last_run_id)
            if action == RETRY:
                print(f"          ↻ attempt {attempt}/{self.max_attempts}: {detail}")
                continue
            # action == VERIFY: confirm the unit actually LANDED before trusting it (§Turn 5, R9)
            defect = await self._verify_step(step, app_key)
            if defect is None:
                if row_id is not None:
                    self.db.mark_succeeded(row_id, stdout=(result.stdout if result else ""),
                                           session_id=result.session_id, session_token=result.session_token)
                return StepResult(index, recipe, target, "succeeded", run_id=last_run_id)
            last = defect
            self._session = None        # verify failed (possible silent rollback) — re-author fresh
            print(f"          ↻ attempt {attempt}/{self.max_attempts}: verification failed — {defect}")
        if row_id is not None:
            self.db.mark_failed(row_id, f"exhausted {self.max_attempts} attempts: {last}")
        return StepResult(index, recipe, target, f"halt: exhausted {self.max_attempts} attempts — {last}",
                          run_id=last_run_id)

    async def _attempt_step(self, prompt: str, app_key: str, row_id):
        """One fire→poll→(publish) cycle. Returns (action, reason, result|None) per §Recovery.
        Reuses the build's live session (fresh_context resume — one slot for many steps) when we have
        one; else opens a fresh session on app_key. On ANY non-VERIFY outcome the session is DROPPED so
        the next attempt re-authors clean (self-heals a write-wedge). One slot, not one-per-step."""
        from harness.mcp_client import MentorError
        reuse = self.reuse_session and self._session is not None
        try:
            if reuse:
                sid, tok = self._session
                run_id = await self.mcp.mentor_start(prompt=prompt, session_id=sid,
                                                     session_token=tok, fresh_context=True)
            else:
                run_id = await self.mcp.mentor_start(app_key, prompt)
            self._last_run_id = run_id
            if row_id is not None:
                self.db.mark_running(row_id, run_id)
            result = await self.mcp.mentor_poll(run_id, timeout_seconds=self.per_call_timeout)
        except MentorError as exc:
            self._session = None            # a start/poll error may have wedged the session — drop it
            return RETRY, f"mentor error: {exc}", None

        action, reason = classify_terminal(result)
        if action != VERIFY:
            if result.status == "running":       # R1: cancel the hung run before a fresh re-author
                await self._safe_cancel(result.run_id)
            self._session = None            # non-terminal-success ⇒ abandon this session, re-author fresh
            return action, reason, result
        try:
            pub_id = await self.mcp.publish_start(result.session_id, result.session_token,
                                                  env_key=self.env_key)
            payload = await self.mcp.publish_wait(pub_id, timeout_seconds=self.publish_timeout)
            paction, preason = classify_publish(payload)
            # On a publish FAILURE, fetch the build-engine messages so the REAL per-element compile
            # error (behind a generic OS-BEW/OS-DPL code) is surfaced + printed — not just the code.
            if paction != VERIFY:
                pk = payload.get("publication_key") or payload.get("publicationKey") or pub_id
                msgs = await self._publish_failure_detail(pk)
                if msgs:
                    preason = f"{preason} :: {msgs}"
                    print(f"          ⓘ build-engine messages: {msgs}")
        except MentorError as exc:
            paction, preason = RETRY, f"publish error: {exc}"
        # Session economy: KEEP this session's slot for the next step (capture its refreshed creds) —
        # do NOT cancel per-step. The token rotates each turn, so store the fresh pair. On a publish
        # RETRY, drop the session so the re-author is clean; the build cancels the one live session at
        # the end (build()) to release its single slot.
        if paction == VERIFY and result.session_id and result.session_token:
            self._session = (result.session_id, result.session_token)
        else:
            self._session = None
        return paction, preason, result

    async def _publish_failure_detail(self, pub_key) -> str:
        """Extract the human-readable build-engine messages behind a failed publish (the actual
        per-element compile errors). Best-effort; '' when unavailable."""
        fn = getattr(self.mcp, "publish_logs", None)
        if fn is None or not pub_key:
            return ""
        try:
            payload = await fn(pub_key)
        except Exception:
            return ""
        msgs = []
        rows = payload if isinstance(payload, list) else (
            payload.get("messages") or payload.get("results") or payload.get("data") or [])
        for m in (rows or [])[:8]:
            if isinstance(m, dict):
                txt = m.get("message") or m.get("text") or m.get("detail") or ""
                el = m.get("element") or m.get("elementName") or m.get("target") or ""
                sev = m.get("severity") or m.get("level") or ""
                line = " ".join(str(x) for x in (sev, el, txt) if x).strip()
                if line:
                    msgs.append(line)
            elif isinstance(m, str):
                msgs.append(m)
        return " | ".join(msgs)[:600]

    async def _safe_cancel(self, run_id) -> None:
        cancel = getattr(self.mcp, "mentor_cancel", None)
        if cancel is None:
            return
        try:
            await cancel(run_id)
        except Exception:
            pass

    async def _verify_step(self, step: dict, app_key: str) -> Optional[str]:
        """Independent read confirming the step actually LANDED (§Turn 5 + R9). Returns a defect
        string, or None if it landed OR cannot be checked. NEVER fakes a pass — an unreadable/absent
        context method is 'cannot verify' (None), a parseable read with the element MISSING is a defect."""
        recipe = step["recipe"]
        params = step.get("params", {})
        try:
            if recipe == "data-model":
                fn = getattr(self.mcp, "context_entities", None)
                if fn is None:
                    return None
                want = [e["name"] for e in params.get("entities", []) if not e.get("isStatic")]
                if not want:
                    return None
                payload = await fn(app_key)
                got = _names_from(payload)
                if not got:
                    return None                                  # cannot verify (empty/unparseable)
                missing = [n for n in want if n not in got]
                if missing:
                    return f"data-model phantom (R9): entities absent after publish: {', '.join(missing)}"
                no_id = _entities_missing_identifier(payload, want)
                if no_id:
                    return (f"missing identifier (R9): {', '.join(no_id)} — re-author data-model FRESH "
                            f"before the next publish (post-publish identifier change is irreversible)")
            elif recipe == "screen":
                fn = getattr(self.mcp, "context_screens", None)
                if fn is None:
                    return None
                want = [s["id"] for s in params.get("screens", [])]
                if not want:
                    return None
                payload = await fn(app_key)
                got = {g.lower() for g in _names_from(payload)}
                if not got:
                    return None
                missing = [n for n in want if n.lower() not in got]
                if missing:
                    return f"screen phantom: screens absent after publish: {', '.join(missing)}"
        except Exception as exc:
            print(f"          (verify note: could not confirm {recipe} — {exc}; not treated as a defect)")
            return None
        return None


async def resolve_or_create_app(mcp, *, app_key: Optional[str], create: bool,
                                name: str, kind: str) -> Optional[str]:
    """Return the app key to build into: the given key, or a freshly created app's key."""
    if app_key:
        return app_key
    if not create:
        return None
    payload = await mcp.app_create(name, kind)
    key = (payload.get("key") or payload.get("assetKey") or payload.get("application_key")
           or (payload.get("data") or {}).get("key"))
    if key:
        return key
    # Fall back to resolving by name via app_list. ODC shape: {results:[{name, assetKey, ...}]}.
    listing = await mcp.app_list()
    for app in _rows(listing):
        if app.get("name") == name or app.get("assetName") == name:
            return app.get("assetKey") or app.get("key")
    return None


def _rows(payload: dict) -> list:
    """The row list out of a paginated ODC list payload (results/data/apps/items/environments)."""
    for k in ("results", "data", "apps", "environments", "items"):
        v = payload.get(k)
        if isinstance(v, list):
            return v
    return []


async def resolve_env_key(mcp, override: Optional[str]) -> str:
    """The ODC environment key to publish into: an explicit override, else the Development-purpose
    env from env_list, else the first, else '' (let the MCP default). Never raises. ODC shape:
    {results:[{key, name, purpose:'Development', order}]}."""
    if override:
        return override
    try:
        payload = await mcp.env_list()
    except Exception:
        return ""
    envs = _rows(payload)

    def key_of(e):
        return e.get("key") or e.get("environmentKey") or e.get("assetKey") or ""
    for e in envs:
        tag = f"{e.get('purpose', '')} {e.get('name', '')} {e.get('stage', '')}".lower()
        if "development" in tag or "dev" in tag:
            return key_of(e)
    return key_of(envs[0]) if envs else ""


def _print_plan(spec: dict) -> None:
    steps = plan_from_spec(spec)
    warn = [s for s in steps if s.get("atomicity_warning")]
    note = [s for s in steps if s.get("atomicity_note")]
    summary = []
    if warn:
        summary.append(f"{len(warn)} splittable-heavy ⚠")
    if note:
        summary.append(f"{len(note)} one-turn-heavy ·")
    print(f"Plan: {len(steps)} steps" + (f"  ({', '.join(summary)})" if summary else "  (all atomic)") + "\n")
    for i, s in enumerate(steps):
        w = s.get("weight", "")
        tail = ("  ⚠ " + s["atomicity_warning"] if s.get("atomicity_warning")
                else "  · " + s["atomicity_note"] if s.get("atomicity_note") else "")
        print(f"  {i+1:>3}. [{w:>2}] {s['recipe']:<16} {_step_target(s, i):<38} — {s.get('why','')}{tail}")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="run_build",
        description="Autonomously build an app_spec through OutSystems Mentor MCP (harness = brain + hands).")
    ap.add_argument("spec", type=Path, help="app_spec.json")
    ap.add_argument("--app-key", default=None, help="Build into this existing ODC app key.")
    ap.add_argument("--create", action="store_true", help="Create a new app first (needs --kind).")
    ap.add_argument("--kind", default="CrossDevice",
                    help="app_create kind when --create (CrossDevice|BusinessProcess|AIAgent|MCPConnection).")
    ap.add_argument("--name", default=None, help="App name for --create (default: spec app.name).")
    ap.add_argument("--plan-only", action="store_true", help="Print the plan and exit (no MCP).")
    ap.add_argument("--max-steps", type=int, default=None, help="Fire only the first N steps (canary).")
    ap.add_argument("--state", type=Path, default=None, help="StateDB path for resumable runs.")
    ap.add_argument("--prompts-dir", type=Path, default=None, help="Where to write rendered prompts.")
    ap.add_argument("--tenant", default=None, help="Override the ODC tenant hostname.")
    ap.add_argument("--env-key", default=None,
                    help="ODC environment key to publish into (default: auto-resolve Dev via env_list).")
    ap.add_argument("--timeout", type=int, default=400, help="Per-step Mentor poll timeout (s).")
    args = ap.parse_args(argv)

    spec = json.loads(args.spec.read_text())
    app_name = args.name or (spec.get("app") or {}).get("name") or args.spec.stem

    if args.plan_only:
        _print_plan(spec)
        return 0

    if not args.app_key and not args.create:
        print("error: pass --app-key <key> or --create (with --kind).")
        return 2

    prompts_dir = args.prompts_dir or (args.spec.parent / "_prompts")
    return asyncio.run(_run(args, spec, app_name, prompts_dir))


async def _run(args, spec: dict, app_name: str, prompts_dir: Path) -> int:
    from harness.mcp_client import MentorMCP
    from harness.build_state import StateDB

    db = StateDB(args.state) if args.state else None
    mcp_kwargs = {"tenant": args.tenant} if args.tenant else {}
    try:
        async with MentorMCP(**mcp_kwargs) as mcp:
            app_key = await resolve_or_create_app(
                mcp, app_key=args.app_key, create=args.create, name=app_name, kind=args.kind)
            if not app_key:
                print("error: could not resolve or create the app key.")
                return 2
            env_key = await resolve_env_key(mcp, args.env_key)
            print(f"Building '{app_name}' into app_key={app_key} (publish env_key={env_key or '<default>'})\n")
            driver = SpecDriver(mcp, prompts_dir, per_call_timeout=args.timeout, db=db, env_key=env_key)
            report = await driver.build(spec, app_key, app_name=app_name, max_steps=args.max_steps)
    finally:
        if db is not None:
            db.close()

    print(f"\nBuild {'OK' if report.ok else 'HALTED'} — "
          f"{report.succeeded} succeeded, {report.failed} failed, {report.skipped} skipped "
          f"of {report.total}.")
    if report.halted_at:
        print(f"Halted at: {report.halted_at}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
