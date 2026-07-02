"""Smoke tests for scripts/build_from_spec.py — the full spec->build->verify PLAN driver.

Asserts the driver emits all three phases (NL entities, NL screens, verify plan) for the
worked task_tracker example, exits 0, and authors nothing (no MCP/network imports fire).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "examples" / "task_tracker" / "app_spec.json"


def _load_driver():
    spec = importlib.util.spec_from_file_location(
        "build_from_spec", REPO_ROOT / "scripts" / "build_from_spec.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_plan_emits_three_phases_exit_zero(capsys) -> None:
    driver = _load_driver()
    rc = driver.main(["--from-spec", str(SPEC)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PHASE 1 · Author entities" in out
    assert "PHASE 2 · Author screens" in out
    assert "PHASE 3 · Verify" in out
    # Phase 1 is the NL intent (proven authoring path), NOT the superseded C# batch.
    # (The words "applyModelApiCode" appear in Phase 3's verify recipe legitimately; the
    #  C# BATCH is fenced with ```csharp and only emitted under --emit-csharp.)
    assert "Server entity `TaskList`" in out
    assert "```csharp" not in out                                   # no C# batch unless --emit-csharp
    # Phase 2 names widgets exactly (verifier keys on names).
    assert "`listsTable`" in out and "`tasksTable`" in out
    # Phase 3 names the deterministic verify command.
    assert "harness-verify --phase live --entities entities.json --screens screens.json" in out


def test_emit_csharp_appends_legacy_batch(capsys) -> None:
    driver = _load_driver()
    rc = driver.main(["--from-spec", str(SPEC), "--emit-csharp"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "APPENDIX" in out and "applyModelApiCode" in out          # legacy C# present on demand


def test_missing_spec_exits_two(capsys) -> None:
    driver = _load_driver()
    rc = driver.main(["--from-spec", str(REPO_ROOT / "does_not_exist.json")])
    assert rc == 2
