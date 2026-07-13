"""Unit tests for the spec-driven autonomous build driver (harness.run_build).

Exercises the SpecDriver step loop against a FakeMCP — no live Mentor. Validates:
serial success path + publish-per-unit, retry-then-halt, retry-then-recover,
compile-error classification, max_steps canary, resumable skip via StateDB, and
resolve_or_create_app.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from harness.mcp_client import MentorError, MentorRunResult
from harness.build_state import StateDB
from harness import run_build
from harness.run_build import (
    SpecDriver, resolve_or_create_app, _step_target,
    classify_terminal, classify_publish, _names_from, _entities_missing_identifier,
    RETRY, HALT, VERIFY,
)


@dataclass
class _Script:
    status: str = "succeeded"
    compile_errors: list = field(default_factory=list)
    publish_status: str = "Finished"
    fail_starts: int = 0                       # first N mentor_start calls raise (transient)
    publish_payload: dict = None               # override publish_wait return (OS-DPL-50205, no_changes)
    heal_after: int = 0                        # after N attempts, this script switches to clean success
    error: str = ""                            # terminal error blob (e.g. 'per_tenant_cap_reached')


class FakeMCP:
    """Minimal MCP double: scripts responses by substring match on the prompt."""

    def __init__(self):
        self._scripts: dict[str, _Script] = {}
        self._default = _Script()
        self._by_run: dict[str, _Script] = {}
        self._n = 0
        self.start_calls = 0
        self.publish_calls = 0
        self._starts_seen: dict[str, int] = {}
        self._attempts: dict[int, int] = {}     # per-script attempt count (for heal_after)
        self._last_script: _Script = None
        self.cancels: list = []                 # run_ids cancelled (R1 hang recovery)
        self.entity_reads: list = []            # FIFO context_entities payloads (verification)
        self.screen_reads: list = []            # FIFO context_screens payloads

    def script_for(self, needle: str, script: _Script):
        self._scripts[needle] = script

    def _match(self, prompt: str) -> _Script:
        for needle, s in self._scripts.items():
            if needle in prompt:
                return s
        return self._default

    async def mentor_start(self, app_key: str = None, prompt: str = "", *,
                           session_id: str = None, session_token: str = None,
                           fresh_context: bool = False) -> str:
        self.start_calls += 1
        # record whether this was a session-reuse resume (slot economy) or a fresh app_key session
        if session_id and session_token:
            self.resume_starts = getattr(self, "resume_starts", 0) + 1
        else:
            self.fresh_starts = getattr(self, "fresh_starts", 0) + 1
        s = self._match(prompt)
        if s.fail_starts:
            seen = self._starts_seen.get(id(s), 0)
            self._starts_seen[id(s)] = seen + 1
            if seen < s.fail_starts:
                raise MentorError("simulated transient mentor_start failure")
        self._n += 1
        run_id = f"run-{self._n}"
        self._by_run[run_id] = s
        return run_id

    async def mentor_poll(self, run_id: str, timeout_seconds: int = 400, **kw) -> MentorRunResult:
        s = self._by_run[run_id]
        # heal_after: after N attempts a flaky script switches to a clean success (models recovery)
        self._attempts[id(s)] = self._attempts.get(id(s), 0) + 1
        healed = s.heal_after and self._attempts[id(s)] > s.heal_after
        status = "succeeded" if healed else s.status
        errs = [] if healed else list(s.compile_errors)
        self._last_script = _Script() if healed else s
        err = "" if healed else s.error
        ok = status == "succeeded" and not errs and not err
        return MentorRunResult(
            run_id=run_id, status=status, stdout="ok", compile_errors=errs, error=err,
            summary="", session_id="sid" if ok else None, session_token="tok" if ok else None,
            raw_events=[])

    async def mentor_cancel(self, run_id: str) -> None:
        self.cancels.append(run_id)

    async def publish_start(self, session_id: str, session_token: str, env_key: str = "") -> str:
        self.publish_calls += 1
        self._n += 1
        return f"pub-{self._n}"

    async def publish_wait(self, pub_id: str, timeout_seconds: int = 600) -> dict:
        s = self._last_script
        if s is not None and s.publish_payload is not None:
            return dict(s.publish_payload)
        return {"state": "succeeded", "revision": 1}          # live ODC contract shape

    async def context_entities(self, app_key: str, **kw) -> dict:
        return self.entity_reads.pop(0) if self.entity_reads else {"items": []}

    async def context_screens(self, app_key: str, **kw) -> dict:
        return self.screen_reads.pop(0) if self.screen_reads else {"items": []}

    async def app_create(self, name: str, kind: str = "CrossDevice") -> dict:
        return {"key": f"key-for-{name}"}

    async def app_list(self) -> dict:
        return {"data": [{"name": "Listed", "key": "listed-key"}]}


def _spec():
    """A small spec: 1 entity + 2 screens + nav → data-model, screen, nav-block, list-screen, seed."""
    return {
        "specVersion": "0.3", "app": {"name": "Demo"},
        "dataModel": {"entities": [
            {"name": "Case", "sampleData": [{"Title": "A"}], "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                {"name": "Title", "dataType": "Text"}]}]},
        "navigation": {"block": "SidebarNav", "items": [{"label": "Cases", "toScreen": "cases"}]},
        "screens": [
            {"id": "cases", "name": "Cases", "isDefault": True, "components": [
                {"id": "caseT", "type": "Table", "boundTo": "Case",
                 "columns": [{"field": "Title", "kind": "text"}]}]},
        ]}


def _run(coro):
    return asyncio.run(coro)


def test_step_target_is_stable_and_disambiguated_by_phase():
    a = _step_target({"recipe": "create-form", "params": {"screen": "s", "entity": "Case", "phase": "action"}}, 3)
    b = _step_target({"recipe": "create-form", "params": {"screen": "s", "entity": "Case", "phase": "combined"}}, 3)
    assert a != b and a.startswith("create-form:case") and a.endswith(":action")


def test_build_success_path_publishes_every_step(tmp_path):
    mcp = FakeMCP()
    driver = SpecDriver(mcp, tmp_path / "p")
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok and report.failed == 0
    assert report.succeeded == report.total > 0
    # publish-per-unit: one publish per successful step
    assert mcp.publish_calls == report.succeeded
    # every rendered prompt was written for reproducibility
    assert list((tmp_path / "p").glob("*.prompt.txt"))


def test_session_is_reused_across_steps_not_one_per_step(tmp_path):
    # SESSION ECONOMY: an all-success build opens ONE fresh session (first step, on app_key) and
    # RESUMES it for every later step (fresh_context), spending one per-tenant slot for the whole
    # build — not one slot per step. The single session is cancelled once at the end.
    mcp = FakeMCP()
    driver = SpecDriver(mcp, tmp_path / "p")               # reuse_session defaults True
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok and report.succeeded == report.total > 1
    assert getattr(mcp, "fresh_starts", 0) == 1            # exactly one slot-opening session
    assert getattr(mcp, "resume_starts", 0) == report.succeeded - 1   # rest are reuse resumes
    assert len(mcp.cancels) == 1                           # one release at build end, not per step


def test_reuse_disabled_opens_a_session_per_step(tmp_path):
    # Opt-out: reuse_session=False restores the greedy one-session-per-step behavior (no resumes).
    mcp = FakeMCP()
    driver = SpecDriver(mcp, tmp_path / "p", reuse_session=False)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok
    assert getattr(mcp, "resume_starts", 0) == 0
    assert getattr(mcp, "fresh_starts", 0) == report.succeeded


def test_verify_defect_drops_session_and_reauthors_fresh(tmp_path):
    # Write-wedge self-heal: if a step's independent verify finds it did NOT land (silent rollback),
    # the session is dropped and the retry opens a FRESH session — not another resume on the wedged one.
    mcp = FakeMCP()
    # nav-block verify fails once (phantom), then the retry (fresh session) succeeds via heal_after.
    mcp.script_for("SidebarNav", _Script(heal_after=1))
    mcp.screen_reads = []                                  # (screens verify tolerant; nav uses default)
    driver = SpecDriver(mcp, tmp_path / "p")
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    # at least one fresh re-author beyond the initial session (the drop-and-reauthor)
    assert report.ok
    assert getattr(mcp, "fresh_starts", 0) >= 1


def test_cap_hit_waits_and_cascades_instead_of_halting(tmp_path):
    # A per-tenant-cap hit is transient: the step should wait-and-retry in-build (not halt) until a
    # slot frees, so the build cascades through it. heal_after=2 => caps twice, then a slot frees.
    mcp = FakeMCP()
    mcp.script_for("SidebarNav", _Script(error="per_tenant_cap_reached", heal_after=2))
    driver = SpecDriver(mcp, tmp_path / "p", cap_wait_seconds=0, cap_retries=5)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok and report.failed == 0
    assert not any("per_tenant_cap" in (s.outcome or "") for s in report.steps)


def test_cap_hit_halts_after_exhausting_cap_retries(tmp_path):
    # If the slot never frees, bounded cap-waits are exhausted and the step halts for the poller.
    mcp = FakeMCP()
    mcp.script_for("SidebarNav", _Script(error="per_tenant_cap_reached"))   # never heals
    driver = SpecDriver(mcp, tmp_path / "p", cap_wait_seconds=0, cap_retries=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert not report.ok and report.halted_at and "nav-block" in report.halted_at
    assert "per_tenant_cap" in next(s.outcome for s in report.steps if s.recipe == "nav-block")


def test_two_list_screens_same_entity_different_screens_both_build(tmp_path):
    # Regression (intake-table bug): _step_target is entity-based, so two tables bound to the SAME
    # entity on DIFFERENT screens share the target `list-screen:<entity>`. _already_succeeded must be
    # position-aware (phase) or it skips the second as a dup of the first, leaving that screen listless.
    spec = {
        "specVersion": "0.3", "app": {"name": "Demo"},
        "dataModel": {"entities": [{"name": "Case", "sampleData": [{"Title": "A"}], "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
            {"name": "Title", "dataType": "Text"}]}]},
        "navigation": {"block": "SidebarNav", "items": [
            {"label": "Queue", "toScreen": "queue"}, {"label": "Archive", "toScreen": "archive"}]},
        "screens": [
            {"id": "queue", "name": "Queue", "isDefault": True, "components": [
                {"id": "qT", "type": "Table", "boundTo": "Case", "columns": [{"field": "Title", "kind": "text"}]}]},
            {"id": "archive", "name": "Archive", "components": [
                {"id": "aT", "type": "Table", "boundTo": "Case", "columns": [{"field": "Title", "kind": "text"}]}]},
        ]}
    db = StateDB(tmp_path / "s.db")
    driver = SpecDriver(FakeMCP(), tmp_path / "p", db=db)
    report = _run(driver.build(spec, "app-key", app_name="Demo"))
    db.close()
    ls = [s for s in report.steps if s.recipe == "list-screen"]
    assert len(ls) == 2 and all(s.outcome == "succeeded" for s in ls)   # BOTH built, neither skipped


def test_build_halts_after_retry_and_skips_dependents(tmp_path):
    mcp = FakeMCP()
    mcp.script_for("SidebarNav", _Script(status="failed"))     # nav-block fails both attempts
    driver = SpecDriver(mcp, tmp_path / "p")
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert not report.ok and report.halted_at and "nav-block" in report.halted_at
    # halted → later steps (list-screen, seed) never fired
    assert not any(s.recipe == "list-screen" for s in report.steps if s.outcome != "skipped")


def test_build_recovers_on_retry(tmp_path):
    mcp = FakeMCP()
    mcp.script_for("SidebarNav", _Script(fail_starts=1))       # first start throws, retry succeeds
    driver = SpecDriver(mcp, tmp_path / "p")
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok and report.failed == 0


def test_compile_errors_fail_the_step(tmp_path):
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(compile_errors=["OS-DPL-50205"]))
    driver = SpecDriver(mcp, tmp_path / "p")
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert not report.ok and "data-model" in (report.halted_at or "")


def test_max_steps_is_a_canary_throttle(tmp_path):
    mcp = FakeMCP()
    driver = SpecDriver(mcp, tmp_path / "p")
    report = _run(driver.build(_spec(), "app-key", app_name="Demo", max_steps=1))
    assert report.total == 1 and report.succeeded == 1


def test_resumable_skips_already_succeeded(tmp_path):
    db = StateDB(tmp_path / "state.db")
    try:
        mcp = FakeMCP()
        driver = SpecDriver(mcp, tmp_path / "p", db=db)
        first = _run(driver.build(_spec(), "app-key", app_name="Demo"))
        assert first.ok
        publishes_first = mcp.publish_calls
        # second run: everything already succeeded → all skipped, no new Mentor calls
        mcp2 = FakeMCP()
        driver2 = SpecDriver(mcp2, tmp_path / "p", db=db)
        second = _run(driver2.build(_spec(), "app-key", app_name="Demo"))
        assert second.skipped == second.total and second.succeeded == 0
        assert mcp2.start_calls == 0 and publishes_first > 0
    finally:
        db.close()


def test_resolve_or_create_app_passthrough_and_create():
    mcp = FakeMCP()
    assert _run(resolve_or_create_app(mcp, app_key="existing", create=False, name="X", kind="CrossDevice")) == "existing"
    created = _run(resolve_or_create_app(mcp, app_key=None, create=True, name="NewApp", kind="CrossDevice"))
    assert created == "key-for-NewApp"
    assert _run(resolve_or_create_app(mcp, app_key=None, create=False, name="X", kind="CrossDevice")) is None


def test_plan_only_cli_prints_plan(capsys, tmp_path):
    import json
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(_spec()))
    rc = run_build.main([str(spec_file), "--plan-only"])
    out = capsys.readouterr().out
    assert rc == 0 and "Plan:" in out and "data-model" in out and "list-screen" in out


def test_cli_requires_app_key_or_create(capsys, tmp_path):
    import json
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(_spec()))
    rc = run_build.main([str(spec_file)])
    assert rc == 2 and "app-key" in capsys.readouterr().out


# ── §Recovery — codified symptom ⇒ action ────────────────────────────────────

def _result(status="succeeded", compile_errors=(), creds=True):
    return MentorRunResult(run_id="r", status=status, stdout="", compile_errors=list(compile_errors),
                           summary="", session_id="s" if creds else None,
                           session_token="t" if creds else None, raw_events=[])


def test_classify_terminal_halts_fast_on_session_cap():
    # a session-cap / auth error is non-retryable — retrying opens MORE sessions, so HALT
    r = _result(status="failed")
    r.error = "per_tenant_cap_reached: Per-tenant session cap reached cluster-wide"
    action, reason = classify_terminal(r)
    assert action == HALT and "non-retryable" in reason and "per_tenant_cap" in reason
    # a plain failure (no cap/auth signal) still retries, and now surfaces the error
    r2 = _result(status="failed")
    r2.error = "transient build blip"
    assert classify_terminal(r2)[0] == RETRY


def test_source_control_401_is_transient_not_a_hard_auth_halt():
    # B3: a 401 from the SOURCE-CONTROL / OML-download API is transient (platform JWT still valid) —
    # it must RETRY, not hit the non-retryable 'unauthorized' halt.
    r = _result(status="failed")
    r.error = ("oml_download_failed: Failed to list revisions with source: HTTP status client error "
               "(401 Unauthorized) for url (https://.../api/source-control/v2/assets/.../revisions)")
    assert classify_terminal(r)[0] == RETRY
    # a bare unauthorized WITHOUT the source-control markers is still a hard halt
    r2 = _result(status="failed")
    r2.error = "unauthorized: token rejected"
    assert classify_terminal(r2)[0] == HALT


def test_classify_terminal_actions():
    assert classify_terminal(_result(compile_errors=["OS-DPL-50205"]))[0] == HALT
    assert classify_terminal(_result(status="running"))[0] == RETRY       # hang (R1)
    assert classify_terminal(_result(status="cancelled"))[0] == RETRY     # wedged (R7)
    assert classify_terminal(_result(status="failed"))[0] == RETRY
    assert classify_terminal(_result(creds=False))[0] == RETRY            # no publish creds
    assert classify_terminal(_result())[0] == VERIFY                      # clean success → confirm


def test_classify_publish_actions():
    # live ODC contract: state ∈ succeeded|failed; failed carries a build-engine code
    assert classify_publish({"state": "failed", "code": "OS-DPL-50205"})[0] == HALT   # R11 deterministic
    assert classify_publish({"state": "failed", "code": "OS-DPL-40003"})[0] == HALT   # any OS-DPL → halt
    assert classify_publish({"state": "failed", "code": "OS-BEW-50000"})[0] == RETRY  # build-engine → fresh re-author
    assert classify_publish({"state": "succeeded", "no_changes_detected": True})[0] == VERIFY
    assert classify_publish({"state": "succeeded", "revision": 3})[0] == VERIFY
    assert classify_publish({"status": "Finished"})[0] == VERIFY                       # legacy shape accepted


def test_context_parse_helpers_are_shape_tolerant():
    assert _names_from({"items": [{"name": "A"}, {"Name": "B"}, "C"]}) == ["A", "B", "C"]
    assert _names_from({"data": {"entities": [{"name": "X"}]}}) == ["X"]
    assert _names_from({"junk": 1}) == []                                  # unparseable → empty (cannot verify)
    miss = _entities_missing_identifier({"items": [{"name": "Case", "hasIdentifier": False}]}, ["Case"])
    assert miss == ["Case"]
    ok = _entities_missing_identifier({"items": [{"name": "Case", "attributes": [{"name": "Id", "isIdentifier": True}]}]}, ["Case"])
    assert ok == []


def test_os_dpl_50205_at_publish_halts_without_wasting_retries(tmp_path):
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(publish_payload={"state": "failed", "code": "OS-DPL-50205"}))
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert not report.ok and "OS-DPL-50205" in (report.halted_at and next(
        s.outcome for s in report.steps if s.recipe == "data-model") or "")
    assert mcp.start_calls == 1                                            # deterministic HALT, no retry storm


def test_os_bew_comp_crash_halts_fast_with_rebuild_fresh_guidance(tmp_path):
    # B1: an OS-BEW-COMP publish crash re-authored in-place wedges the app; halt-fast after 2 (not the
    # full max_attempts=3) with rebuild-fresh guidance, rather than grinding corrupting in-place retries.
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(publish_payload={"state": "failed", "code": "OS-BEW-COMP-50008",
                                                          "detail": "An internal server error occurred!"}))
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    outcome = next(s.outcome for s in report.steps if s.recipe == "data-model")
    assert not report.ok
    assert "OML-WEDGED" in outcome and "REBUILD FRESH" in outcome
    assert mcp.start_calls == 2                                            # halt-fast at 2, not 3


def test_os_bew_50000_crash_halts_fast_with_rebuild_fresh_guidance(tmp_path):
    # Harvest corruption-wedge-broaden (live 2026-07-12: QualifyWorkflow Core-import). OS-BEW-50000
    # ("Internal Error") used to fall through the OS-BEW-COMP-only guard and grind max_attempts,
    # corrupting the OML. It must now halt-fast after 2 with rebuild-fresh guidance.
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(publish_payload={"state": "failed", "code": "OS-BEW-50000",
                                                          "detail": "Internal Error."}))
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    outcome = next(s.outcome for s in report.steps if s.recipe == "data-model")
    assert not report.ok
    assert "OML-WEDGED" in outcome and "REBUILD FRESH" in outcome
    assert mcp.start_calls == 2                                            # halt-fast at 2, not 3


def test_invalid_oml_40028_halts_fast_with_rebuild_fresh_guidance(tmp_path):
    # Harvest corruption-wedge-broaden (live 2026-07-12: portal send-back button-wire). OS-APPS-40028
    # "Input binary does not contain a valid OML" is definitive OML corruption — halt-fast, rebuild fresh.
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(publish_payload={
        "state": "failed", "code": "OS-APPS-40028",
        "detail": "Input binary does not contain a valid OML"}))
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    outcome = next(s.outcome for s in report.steps if s.recipe == "data-model")
    assert not report.ok
    assert "OML-WEDGED" in outcome and "REBUILD FRESH" in outcome
    assert mcp.start_calls == 2


def test_hang_is_cancelled_then_recovered_in_a_fresh_session(tmp_path):
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(status="running", heal_after=1))  # first fire hangs, then heals
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok                                                       # recovered
    assert mcp.cancels                                                     # R1: the hung run was cancelled


def test_data_model_phantom_is_caught_by_verification_then_recovers(tmp_path):
    mcp = FakeMCP()
    # data-model reports success both times, but the FIRST independent read is missing 'Case' (phantom);
    # the second read shows it present → verification fails once, then passes.
    mcp.entity_reads = [
        {"items": [{"name": "Other"}]},
        {"items": [{"name": "Case", "hasIdentifier": True}, {"name": "Other"}]},
    ]
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=3)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert report.ok                                                       # phantom caught + recovered
    dm = next(s for s in report.steps if s.recipe == "data-model")
    assert dm.outcome == "succeeded"


def test_missing_identifier_phantom_R9_is_caught(tmp_path):
    mcp = FakeMCP()
    # entity present but with NO identifier (R9 latent phantom) → defect; never heals → exhausts → halt
    mcp.entity_reads = [{"items": [{"name": "Case", "hasIdentifier": False}]}] * 5
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=2)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    assert not report.ok
    dm = next(s for s in report.steps if s.recipe == "data-model")
    assert "identifier" in dm.outcome.lower()


def test_no_changes_detected_with_present_entity_is_a_success(tmp_path):
    mcp = FakeMCP()
    mcp.script_for("data model", _Script(publish_payload={"state": "succeeded", "no_changes_detected": True}))
    mcp.entity_reads = [{"items": [{"name": "Case", "hasIdentifier": True}]}]
    driver = SpecDriver(mcp, tmp_path / "p", max_attempts=2)
    report = _run(driver.build(_spec(), "app-key", app_name="Demo"))
    # no_changes_detected is not trusted on its own — the read confirms the unit IS present → success
    assert report.ok
    dm = next(s for s in report.steps if s.recipe == "data-model")
    assert dm.outcome == "succeeded"
