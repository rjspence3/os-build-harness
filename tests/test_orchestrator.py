"""Tier 3 orchestrator integration tests — with a FakeMentorMCP.

Simulates the multi-recipe flows from TEST_PLAN.md (T3.1, T3.2, T3.4) without
live Mentor dispatch. Validates:
- T3.1: 5-recipe sequence all succeed → state DB shows 5 succeeded rows
- T3.1.fail: middle recipe fails → orchestrator halts phase + leaves remaining pending
- T3.2: resume after interrupt — pre-marked succeeded rows are skipped
- T3.4: verify phase wiring — expected counts computed from state DB,
  Recipe 99 prompt dispatched, status surfaced

Live Mentor dispatch (the real T3.1/T3.2/T3.3) is deferred to Tier 4, where the
full rebuild will exercise the same paths against the real MCP.
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.banking_runner.mcp_client import MentorError, MentorRunResult
from harness.banking_runner.orchestrator import (
    AppConfig,
    Orchestrator,
    VerifyResult,
)
from harness.banking_runner.state import StateDB


# ─── Fake MCP client ───────────────────────────────────────────────────────────

@dataclass
class _Script:
    """Per-prompt scripted response for FakeMentorMCP."""
    status: str = "succeeded"                 # 'succeeded' | 'failed' | 'cancelled' | 'running'
    stdout: str = "Recipe XX: ... | Status: OK"
    compile_errors: list[str] = field(default_factory=list)
    summary: str = ""
    session_id: str = "fake-session-id"
    session_token: str = "fake-session-token"
    publish_status: str = "Finished"          # 'Finished' | 'Failed'
    raise_on_start: bool = False              # simulate mentor_start failure


class FakeMentorMCP:
    """In-memory MCP client. Returns scripted responses per target_name.

    Default behavior: every call succeeds with `Status: OK`. Override per-target
    via `script_for(target_name, _Script(...))`. Records every call for
    inspection."""

    def __init__(self):
        self._scripts: dict[str, _Script] = {}
        self._default = _Script()
        self.mentor_start_calls: list[tuple[str, str]] = []      # (app_key, prompt)
        self.mentor_poll_calls: list[str] = []                   # run_ids
        self.publish_start_calls: list[tuple[str, str]] = []     # (session_id, token)
        self.publish_wait_calls: list[str] = []                  # pub_ids
        self._next_run_id = 0

    def script_for(self, target_name: str, script: _Script):
        """Match by substring on the prompt text (target_name is in the prompt)."""
        self._scripts[target_name] = script

    def _match_script(self, prompt: str) -> _Script:
        for target_name, script in self._scripts.items():
            if target_name in prompt:
                return script
        return self._default

    async def mentor_start(self, app_key: str, prompt: str) -> str:
        self.mentor_start_calls.append((app_key, prompt))
        script = self._match_script(prompt)
        if script.raise_on_start:
            raise MentorError("simulated mentor_start failure")
        self._next_run_id += 1
        run_id = f"run-{self._next_run_id}"
        # Stash prompt → script lookup keyed on run_id
        self._scripts_by_run = getattr(self, "_scripts_by_run", {})
        self._scripts_by_run[run_id] = script
        return run_id

    async def mentor_poll(self, run_id: str, timeout_seconds: int = 60, **kwargs) -> MentorRunResult:
        self.mentor_poll_calls.append(run_id)
        script = self._scripts_by_run.get(run_id, self._default)
        return MentorRunResult(
            run_id=run_id,
            status=script.status,
            stdout=script.stdout,
            compile_errors=list(script.compile_errors),
            summary=script.summary,
            session_id=script.session_id if script.status == "succeeded" else None,
            session_token=script.session_token if script.status == "succeeded" else None,
            raw_events=[],
        )

    async def publish_start(self, session_id: str, session_token: str, env_key: str = "") -> str:
        self.publish_start_calls.append((session_id, session_token))
        self._next_run_id += 1
        return f"pub-{self._next_run_id}"

    async def publish_wait(self, publication_id: str, timeout_seconds: int = 60) -> dict:
        self.publish_wait_calls.append(publication_id)
        # Mirror the script for whichever publish was started
        # (For simplicity: assume the same script that produced the session)
        return {"status": "Finished", "publication_id": publication_id}


# ─── Test fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_state(tmp_path) -> StateDB:
    db = StateDB(tmp_path / "state.db")
    yield db
    db.close()


@pytest.fixture
def tmp_prompts(tmp_path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    return d


def _seed_recipes(db: StateDB, prompts_dir: Path, app: str, phase: str,
                  targets: list[str]) -> list[int]:
    """Create a .prompt.txt + state-DB row for each target. Returns row ids."""
    ids = []
    for t in targets:
        p = prompts_dir / f"{phase}_{t}.prompt.txt"
        # Embed the target name in the prompt body so FakeMentorMCP can match it
        p.write_text(f"Recipe XX target={t}\n```csharp\neSpace => {{}}\n```\n")
        ids.append(db.upsert_pending(app, phase, t, str(p)))
    return ids


def _make_orchestrator(db: StateDB, mcp: FakeMentorMCP, prompts_dir: Path) -> Orchestrator:
    return Orchestrator(db=db, mcp=mcp, prompts_dir=prompts_dir, max_concurrent=1)


# ─── T3.1 simulation — 5 recipes, all succeed ──────────────────────────────────

def test_t31_multi_recipe_all_succeed(tmp_state, tmp_prompts):
    mcp = FakeMentorMCP()
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)

    targets = ["ChartDataOption", "HBAgentType", "DataSettings", "HBBranch", "HomeBankingCore"]
    _seed_recipes(tmp_state, tmp_prompts, "core", "02_static", targets)

    result = asyncio.run(orch._run_phase(config, "02_static"))

    assert result.succeeded == 5
    assert result.failed == 0
    assert result.halted_at is None
    # State DB confirms all 5 succeeded
    succeeded = tmp_state.list_by_status("core", "succeeded", "02_static")
    assert len(succeeded) == 5
    assert {c.target_name for c in succeeded} == set(targets)
    # MCP was called 5 times for mentor_start + 5 for mentor_poll + 5 for publish_start
    assert len(mcp.mentor_start_calls) == 5
    assert len(mcp.mentor_poll_calls) == 5
    assert len(mcp.publish_start_calls) == 5


# ─── T3.1.fail simulation — middle recipe fails, phase halts ───────────────────

def test_t31_halt_on_middle_failure(tmp_state, tmp_prompts):
    mcp = FakeMentorMCP()
    mcp.script_for("DataSettings", _Script(
        status="succeeded",
        compile_errors=["CS1061: missing API method"],
        stdout="failed compile",
    ))
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)

    targets = ["ChartDataOption", "HBAgentType", "DataSettings", "HBBranch", "HomeBankingCore"]
    _seed_recipes(tmp_state, tmp_prompts, "core", "02_static", targets)

    result = asyncio.run(orch._run_phase(config, "02_static"))

    # Halt should fire at DataSettings — its compile_errors trigger mark_failed.
    # With max_concurrent=1, the orchestrator iterates in pending order, so
    # ChartDataOption + HBAgentType land succeeded, DataSettings lands failed,
    # then the halt short-circuits HBBranch + HomeBankingCore.
    assert result.failed == 1
    assert result.halted_at == "DataSettings"
    # Failed row recorded
    failed = tmp_state.list_by_status("core", "failed", "02_static")
    assert len(failed) == 1
    assert failed[0].target_name == "DataSettings"
    assert "CS1061" in (failed[0].error or "")


def test_t31_mentor_start_error_propagates_to_state(tmp_state, tmp_prompts):
    """If mentor_start raises, the row is marked failed with the error."""
    mcp = FakeMentorMCP()
    mcp.script_for("HBBranch", _Script(raise_on_start=True))
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)

    _seed_recipes(tmp_state, tmp_prompts, "core", "02_static", ["HBBranch"])
    result = asyncio.run(orch._run_phase(config, "02_static"))

    assert result.failed == 1
    failed = tmp_state.list_by_status("core", "failed", "02_static")
    assert len(failed) == 1
    assert "simulated mentor_start failure" in (failed[0].error or "")


# ─── T3.2 simulation — resume after interrupt skips succeeded rows ────────────

def test_t32_resume_skips_succeeded(tmp_state, tmp_prompts):
    """After a partial run, re-dispatching the same phase should only
    process recipes still in 'pending' status."""
    mcp = FakeMentorMCP()
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)

    targets = ["ChartDataOption", "HBAgentType", "DataSettings", "HBBranch", "HomeBankingCore"]
    ids = _seed_recipes(tmp_state, tmp_prompts, "core", "02_static", targets)
    # Pre-mark the first 3 as succeeded (simulating an interrupted run)
    for rid in ids[:3]:
        tmp_state.mark_succeeded(rid, stdout="OK", session_id="s", session_token="t")

    # Second run — only the last 2 should dispatch
    result = asyncio.run(orch._run_phase(config, "02_static"))

    assert result.succeeded == 2
    assert result.failed == 0
    # Only 2 mentor_start calls in this run (the first 3 were skipped)
    assert len(mcp.mentor_start_calls) == 2
    # Final state DB: all 5 succeeded
    all_succeeded = tmp_state.list_by_status("core", "succeeded", "02_static")
    assert len(all_succeeded) == 5


# ─── T3.4 simulation — verify phase wiring ─────────────────────────────────────

def test_t34_verify_phase_skipped_without_app_key(tmp_state, tmp_prompts):
    """Verify probe needs an app_key. Without one (greenfield + portal-create
    didn't resolve), the probe is skipped."""
    mcp = FakeMentorMCP()
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key=None, consumer_modules=[],
                       require_studio_warmup=False)
    verify = asyncio.run(orch._verify_phase(config))
    assert verify.status == "skipped"
    assert verify.error == "no app_key"
    assert mcp.mentor_start_calls == []


def test_t34_verify_phase_dispatches_when_app_key_present(tmp_state, tmp_prompts):
    """With an app_key, verify dispatches Recipe 99 via mentor_start (no publish)."""
    mcp = FakeMentorMCP()
    # Default script returns "Recipe XX: ... | Status: OK" — but verify reads
    # for "Recipe 99: ... Status: OK". Override.
    mcp._default = _Script(stdout="Recipe 99 — Post-publish verification:\n"
                                  "  Entities: 5 ...\nRecipe 99: VerifyBuild | Status: OK")
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)

    verify = asyncio.run(orch._verify_phase(config))
    assert verify.status == "OK"
    assert "Recipe 99: VerifyBuild | Status: OK" in verify.stdout
    # mentor_start fired once, no publish (verify is read-only)
    assert len(mcp.mentor_start_calls) == 1
    assert len(mcp.publish_start_calls) == 0


def test_t34_verify_phase_drift_detected(tmp_state, tmp_prompts):
    """Recipe 99 stdout with Status: DRIFT marks the verify as drift."""
    mcp = FakeMentorMCP()
    mcp._default = _Script(stdout="Recipe 99: VerifyBuild | Status: DRIFT")
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)
    verify = asyncio.run(orch._verify_phase(config))
    assert verify.status == "DRIFT"


def test_t34_verify_phase_compile_error(tmp_state, tmp_prompts):
    mcp = FakeMentorMCP()
    mcp._default = _Script(compile_errors=["CS9999: bad C#"], stdout="")
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)
    verify = asyncio.run(orch._verify_phase(config))
    assert verify.status == "error"
    assert verify.compile_errors == ["CS9999: bad C#"]


def test_t34_expected_counts_from_state_db(tmp_state, tmp_prompts):
    """Verify computes expected counts by summing succeeded rows by phase prefix."""
    mcp = FakeMentorMCP()
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    # Seed succeeded rows across phases
    for t in ("E1", "E2"):
        rid = tmp_state.upsert_pending("core", "01_server", t, "/dev/null")
        tmp_state.mark_succeeded(rid, "ok")
    for t in ("S1",):
        rid = tmp_state.upsert_pending("core", "02_static", t, "/dev/null")
        tmp_state.mark_succeeded(rid, "ok")
    for t in ("A1", "A2", "A3"):
        rid = tmp_state.upsert_pending("core", "04_serveraction", t, "/dev/null")
        tmp_state.mark_succeeded(rid, "ok")

    counts = orch._compute_expected_counts("core")
    assert counts["entities"] == 3  # 01_server + 02_static
    assert counts["actions"] == 3   # 04_*
    assert counts["screens"] == 0


def test_t34_verify_prompt_persisted_to_disk(tmp_state, tmp_prompts):
    """The rendered verify prompt is written to prompts_dir for debugging."""
    mcp = FakeMentorMCP()
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)
    asyncio.run(orch._verify_phase(config))
    assert (tmp_prompts / "99_verify_core.prompt.txt").exists()
    content = (tmp_prompts / "99_verify_core.prompt.txt").read_text()
    assert "Recipe 99" in content


# ─── Cross-cutting — state DB lifecycle ────────────────────────────────────────

def test_succeeded_row_carries_session_credentials(tmp_state, tmp_prompts):
    """After dispatch, the state row must have session_id + session_token from
    the terminal Mentor result. Required for publish_start binding."""
    mcp = FakeMentorMCP()
    mcp._default = _Script(session_id="sid-123", session_token="tok-abc")
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)
    _seed_recipes(tmp_state, tmp_prompts, "core", "02_static", ["T1"])
    asyncio.run(orch._run_phase(config, "02_static"))

    succeeded = tmp_state.list_by_status("core", "succeeded", "02_static")
    assert len(succeeded) == 1
    assert succeeded[0].session_id == "sid-123"
    assert succeeded[0].session_token == "tok-abc"


def test_failed_row_does_not_dispatch_publish(tmp_state, tmp_prompts):
    """On compile error, orchestrator must NOT call publish_start."""
    mcp = FakeMentorMCP()
    mcp.script_for("T1", _Script(compile_errors=["CS0001"]))
    orch = _make_orchestrator(tmp_state, mcp, tmp_prompts)
    config = AppConfig(name="core", display_name="HomeBankingCore",
                       app_key="fake-app-key", consumer_modules=[],
                       require_studio_warmup=False)
    _seed_recipes(tmp_state, tmp_prompts, "core", "02_static", ["T1"])
    asyncio.run(orch._run_phase(config, "02_static"))

    assert len(mcp.publish_start_calls) == 0
    failed = tmp_state.list_by_status("core", "failed", "02_static")
    assert len(failed) == 1
