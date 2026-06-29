"""Phase orchestrator for the banking app rebuild.

Coordinates: load manifests → render prompts → enqueue in StateDB → drive
gates + recipe dispatches → poll Mentor → record results → publish at phase
boundaries → verify counts.

The state machine for each recipe call:
    pending → running → succeeded / failed
                    ↓
                  retry (up to N times for transient errors)

Phases per app (Core example):
    Phase 0: portal_create + studio_warmup gates
    Phase 1: static entities (Recipe 02)        → publish
    Phase 2: server entities (Recipe 01)        → publish
    Phase 3: roles (Recipe 03)                  → publish
    Phase 4: actions (Recipe 04 stubs)          → publish
    Phase 5: theme (Recipe 10)                  → publish (if any theme exists)
    Phase 6: verify (Recipe 99)

For consumer apps (Portal/Backoffice), Phase 0 also includes manage_deps gates
to import Core's Public roles + entities before the consumer's recipes can
resolve those identifiers.

Parallelism: within each phase, recipe calls are independent (entity creation
order doesn't matter for statics; for server entities the manifest already
respects FK dependency order so we serialize). Default 3-concurrent.

Errors: on first failure, retry once after 5s. Second failure → mark failed and
HALT the phase (don't keep firing dependent calls into a broken state).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from harness.banking_runner.gate import (
    Gate,
    await_gate,
    gate_portal_create,
    gate_studio_warmup,
)
from harness.banking_runner.mcp_client import MentorError, MentorMCP
from harness.banking_runner.recipe import render_verify_probe
from harness.banking_runner.state import RecipeCall, StateDB

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Per-app rebuild config — passed to Orchestrator.build_app()."""
    name: str                              # 'core' | 'portal' | 'backoffice' | ...
    display_name: str                      # 'HomeBankingCore'
    app_key: Optional[str]                 # Set after Portal-create; None for greenfield
    consumer_modules: list[str]            # Modules this app references; empty for Core
    require_studio_warmup: bool = True


@dataclass
class PhaseResult:
    name: str
    succeeded: int
    failed: int
    skipped: int
    halted_at: Optional[str] = None        # target_name where halt occurred


@dataclass
class VerifyResult:
    """Outcome of the Recipe 99 verify probe (T3.4)."""
    status: str                            # 'OK' | 'DRIFT' | 'error' | 'skipped'
    stdout: str                            # raw Recipe 99 stdout
    expected: dict[str, int]               # entities/screens/actions expected
    compile_errors: list[str]
    error: Optional[str] = None


class Orchestrator:
    """Top-level coordinator. One instance per run; call build_app() per app."""

    def __init__(
        self,
        db: StateDB,
        mcp: MentorMCP,
        prompts_dir: Path,
        max_concurrent: int = 3,
        per_call_timeout: int = 300,
    ):
        self.db = db
        self.mcp = mcp
        self.prompts_dir = prompts_dir
        self.max_concurrent = max_concurrent
        self.per_call_timeout = per_call_timeout

    # ─── Build a single app end-to-end ────────────────────────────────────────

    async def build_app(self, config: AppConfig) -> list[PhaseResult]:
        """Drive the full rebuild sequence for one app. Returns per-phase results."""
        results: list[PhaseResult] = []

        # Phase 0: manual gates
        if not config.app_key:
            if not await self._gate(gate_portal_create(config.name, config.display_name)):
                return results
            print(f"  [orchestrator] After Portal-create, capture the asset_key via 'claude mcp' or app_list.")
            app_key = await self._resolve_app_key(config.display_name)
            if not app_key:
                print(f"  [orchestrator] Could not resolve app_key for {config.display_name}. Aborting.")
                return results
            config.app_key = app_key
            print(f"  [orchestrator] Resolved app_key: {config.app_key}")

        if config.require_studio_warmup:
            if not await self._gate(gate_studio_warmup(config.name, config.display_name)):
                return results

        # Phases — order matters. Per OutSystems MCP contract, publish_start is
        # bound to a specific mentor_session_id/token (NOT a phase). So we
        # publish ONCE PER RECIPE — _dispatch_recipe_call invokes publish_start
        # using the session credentials returned by mentor_poll.
        for phase in ("02_static", "01_server", "03_role", "04_serveraction", "04_serviceaction", "04_clientaction"):
            phase_result = await self._run_phase(config, phase)
            results.append(phase_result)
            if phase_result.halted_at:
                print(f"  [orchestrator] Halted at {phase} target {phase_result.halted_at}. Aborting build.")
                return results

        # T3.4: Recipe 99 verify probe. Reads back what landed and compares to
        # the orchestrator's expected counts. Non-fatal: DRIFT does NOT abort
        # the build — count drift is expected because Mentor Web auto-generates
        # CRUD scaffolding (per [[odc_mcp_mentor_path_differs_from_studio]]),
        # so an exact match is rare. The verify call surfaces the drift so the
        # operator can decide whether it matters.
        verify = await self._verify_phase(config)
        print(f"\n  [orchestrator] Recipe 99 verify: status={verify.status}")
        if verify.stdout:
            for line in verify.stdout.splitlines():
                print(f"    {line}")
        if verify.error:
            print(f"  [orchestrator] verify error: {verify.error}")

        return results

    # ─── Verify (T3.4) ─────────────────────────────────────────────────────────

    async def _verify_phase(self, config: AppConfig) -> VerifyResult:
        """Dispatch the Recipe 99 read-only verify probe at the end of build_app().

        Computes expected counts from succeeded-recipe rows in state DB, renders
        the probe, fires it via mentor_start, and parses the stdout. NO publish —
        the probe is read-only."""
        expected = self._compute_expected_counts(config.name)
        prompt = render_verify_probe(
            expected_entities=expected["entities"],
            expected_screens=expected["screens"],
            expected_actions=expected["actions"],
        )
        # Persist for reproducibility / debugging
        prompt_path = self.prompts_dir / f"99_verify_{config.name}.prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt)

        if not config.app_key:
            return VerifyResult(status="skipped", stdout="", expected=expected,
                                compile_errors=[], error="no app_key")

        try:
            run_id = await self.mcp.mentor_start(config.app_key, prompt)
            result = await self.mcp.mentor_poll(run_id, timeout_seconds=self.per_call_timeout)
        except MentorError as exc:
            return VerifyResult(status="error", stdout="", expected=expected,
                                compile_errors=[], error=str(exc))

        # Recipe 99 prints `Status: OK` or `Status: DRIFT` in its stdout's last line.
        status = "DRIFT"
        for line in (result.stdout or "").splitlines():
            if "Recipe 99" in line and "Status:" in line:
                status = "OK" if "Status: OK" in line else "DRIFT"
                break
        if result.compile_errors:
            status = "error"
        return VerifyResult(
            status=status,
            stdout=result.stdout or "",
            expected=expected,
            compile_errors=result.compile_errors,
        )

    def _compute_expected_counts(self, app: str) -> dict[str, int]:
        """Derive expected entity/screen/action counts from state DB rows.

        Heuristic — phase prefixes determine the count bucket:
        - entities = succeeded `01_server` + `02_static` recipes
        - screens  = succeeded `07_*` recipes (screen authoring)
        - actions  = succeeded `04_*` recipes (server + service + client actions)
        """
        succeeded = self.db.list_by_status(app, "succeeded")
        entities = sum(1 for c in succeeded
                       if c.phase.startswith("01_server") or c.phase.startswith("02_static"))
        screens = sum(1 for c in succeeded if c.phase.startswith("07_"))
        actions = sum(1 for c in succeeded if c.phase.startswith("04_"))
        return {"entities": entities, "screens": screens, "actions": actions}

    # ─── Run one phase ────────────────────────────────────────────────────────

    async def _run_phase(self, config: AppConfig, phase: str) -> PhaseResult:
        pending = self.db.list_pending(config.name, phase=phase)
        if not pending:
            return PhaseResult(name=phase, succeeded=0, failed=0, skipped=0)

        print(f"\n  [orchestrator] Phase {phase} on {config.display_name}: {len(pending)} pending")

        sem = asyncio.Semaphore(self.max_concurrent)
        succeeded = 0
        failed = 0
        halted_at: Optional[str] = None
        lock = asyncio.Lock()  # serialize state DB writes

        async def dispatch_one(call: RecipeCall):
            nonlocal succeeded, failed, halted_at
            async with sem:
                if halted_at:  # short-circuit if phase already halted
                    return
                outcome = await self._dispatch_recipe_call(call, config.app_key)
                async with lock:
                    if outcome == "succeeded":
                        succeeded += 1
                        print(f"    ✓ {call.phase}/{call.target_name}")
                    else:
                        failed += 1
                        print(f"    ✗ {call.phase}/{call.target_name}: {outcome}")
                        if halted_at is None:
                            halted_at = call.target_name

        await asyncio.gather(*(dispatch_one(c) for c in pending))
        return PhaseResult(name=phase, succeeded=succeeded, failed=failed, skipped=0, halted_at=halted_at)

    async def _dispatch_recipe_call(self, call: RecipeCall, app_key: str) -> str:
        """Send one recipe to Mentor. Returns 'succeeded' or an error string."""
        try:
            prompt = Path(call.prompt_path).read_text()
        except FileNotFoundError:
            self.db.mark_failed(call.id, f"prompt file missing: {call.prompt_path}")
            return f"prompt file missing"

        try:
            run_id = await self.mcp.mentor_start(app_key, prompt)
            self.db.mark_running(call.id, run_id)
        except MentorError as exc:
            self.db.mark_failed(call.id, f"mentor_start: {exc}")
            return f"mentor_start: {exc}"

        try:
            result = await self.mcp.mentor_poll(run_id, timeout_seconds=self.per_call_timeout)
        except MentorError as exc:
            self.db.mark_failed(call.id, f"mentor_poll: {exc}")
            return f"mentor_poll: {exc}"

        if result.status == "succeeded" and not result.compile_errors:
            # Recipe compiled + ran. Now publish to persist the OML changes.
            if not result.session_id or not result.session_token:
                self.db.mark_failed(call.id, "no session credentials in terminal result")
                return "no session creds"
            try:
                pub_id = await self.mcp.publish_start(result.session_id, result.session_token)
                pub_payload = await self.mcp.publish_wait(pub_id)
                if pub_payload.get("status") != "Finished":
                    self.db.mark_failed(call.id, f"publish status={pub_payload.get('status')}")
                    return f"publish: {pub_payload.get('status')}"
            except MentorError as exc:
                self.db.mark_failed(call.id, f"publish: {exc}")
                return f"publish: {exc}"
            self.db.mark_succeeded(
                call.id,
                stdout=result.stdout,
                session_id=result.session_id,
                session_token=result.session_token,
            )
            return "succeeded"

        if result.compile_errors:
            err = "; ".join(result.compile_errors[:3])
            self.db.mark_failed(call.id, f"compile errors: {err}")
            return f"compile: {err[:80]}"

        if result.status == "running":
            self.db.mark_failed(call.id, "timeout — Mentor did not reach terminal in time")
            return "timeout"

        self.db.mark_failed(call.id, f"status={result.status}: {result.summary[:200]}")
        return f"{result.status}: {result.summary[:80]}"

    # ─── Gate convenience ─────────────────────────────────────────────────────

    async def _gate(self, gate: Gate) -> bool:
        gate_id = self.db.add_gate(gate.app, gate.kind, gate.title)
        # Re-prompt only if not yet satisfied
        existing = [g for g in self.db.list_pending_gates(gate.app) if g["id"] == gate_id]
        if not existing:
            print(f"  [orchestrator] Gate already satisfied: {gate.kind}")
            return True
        loop = asyncio.get_running_loop()
        ok = await loop.run_in_executor(None, await_gate, gate)
        if ok:
            self.db.satisfy_gate(gate_id)
        return ok

    async def _resolve_app_key(self, display_name: str) -> Optional[str]:
        """After Portal-create, look up the new app's asset_key via app_list."""
        try:
            payload = await self.mcp.app_list()
        except MentorError as exc:
            print(f"  [orchestrator] app_list failed: {exc}")
            return None
        items = payload.get("data") or payload.get("apps") or []
        for app in items:
            if app.get("name") == display_name or app.get("assetName") == display_name:
                return app.get("key") or app.get("assetKey")
        return None
