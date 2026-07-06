"""Tests for harness/gate.py — the consolidated DEFINITION OF DONE runner (Phase 5).

Browser-free: the live gates (behavioral/role/render/pixel/structural) each own a Playwright sweep
proven elsewhere. Here we monkeypatch those out and pin the COMPOSITION LOGIC — the part that decides
what "done" means: which dimensions are mandatory vs omitted, that a spec-gap short-circuits, that ANY
gate failure flips the overall verdict, and that the process exit code enforces it (0 iff DONE).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import capture, gate, verify


# ── specs of varying shape ──────────────────────────────────────────────────
def _spec_minimal() -> dict:
    """One screen, no write-paths, no gated screens, no charts/theme — only spec + structural apply."""
    return {
        "specVersion": "0.2",
        "app": {"name": "t", "roles": ["User"]},
        "dataModel": {"entities": [{"name": "Item", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
        "screens": [{"id": "list", "name": "List", "route": "/list", "roles": ["User"],
                     "components": [{"id": "t", "type": "Table", "boundTo": "Item"}],
                     "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "t"}]}}],
    }


def _spec_full() -> dict:
    """Write-path + gated screen + theme — behavioral, role, and render all become mandatory."""
    s = _spec_minimal()
    s["screens"][0]["actions"] = [{"does": ["CreateEntity"], "entity": "Item"}]
    s["screens"].append({"id": "admin", "name": "Admin", "route": "/admin", "roles": ["Admin"],
                         "access": {"adminOnly": True, "redirectTo": "list"},
                         "components": [], "acceptance": {"assertions": []}})
    s["design"] = {"theme": {"palette": {"primary": "#123456"}}}
    return s


# ── stub the live gates so composition is deterministic ─────────────────────
def _stub_live(monkeypatch, *, structural_fail=0, behavioral_ok=True, role_ok=True,
               render_ok=True, pixel_ok=True):
    monkeypatch.setattr(verify, "validate_spec", lambda spec: [])
    monkeypatch.setattr(capture, "build_runtime_snapshot",
                        lambda *a, **k: {"screens": []})
    monkeypatch.setattr(capture, "_assert_capture_channel",
                        lambda spec, snap: ([], 3, structural_fail))
    monkeypatch.setattr(capture, "run_behavioral", lambda *a, **k: [
        {"screen": "list", "entity": "Item", "op": "create",
         "verdict": "PERSISTS" if behavioral_ok else "NO_PERSIST (row absent after reload)"}])
    monkeypatch.setattr(capture, "run_role", lambda *a, **k: [
        {"screen": "admin", "check": "anon", "verdict": "BLOCKS_ANON" if role_ok else "LEAKS_TO_ANON"},
        {"screen": "admin", "check": "member", "verdict": "ALLOWS_MEMBER"}])
    monkeypatch.setattr(capture, "run_render", lambda *a, **k: [
        {"kind": "theme", "target": "design.theme", "verdict": "APPLIED" if render_ok else "NOT_APPLIED"}])
    monkeypatch.setattr(capture, "run_pixel", lambda *a, **k: [
        {"kind": "pixel", "screen": "list", "match_pct": 100.0 if pixel_ok else 40.0,
         "verdict": "MATCH" if pixel_ok else "DRIFT"}])


def _rows(spec, **live):
    return {r["gate"]: r for r in gate.run_all_gates(
        spec, "http://x", {}, pixel_ref=None, pixel_threshold=99.0, pixel_tol=16,
        pixel_mask=[], nav_mode="href", out_dir=None)}


# ── applicability predicates (pure) ─────────────────────────────────────────
def test_has_write_paths_detects_declared_crud():
    assert gate._has_write_paths(_spec_full()) is True
    assert gate._has_write_paths(_spec_minimal()) is False


def test_has_render_targets_detects_theme_and_charts():
    assert gate._has_render_targets(_spec_full()) is True
    assert gate._has_render_targets(_spec_minimal()) is False
    withchart = _spec_minimal()
    withchart["screens"][0]["charts"] = [{"id": "c1"}]
    assert gate._has_render_targets(withchart) is True


# ── composition: undeclared dimensions are OMITTED, not failed ──────────────
def test_minimal_spec_omits_undeclared_dimensions_and_is_done(monkeypatch):
    _stub_live(monkeypatch)
    rows = _rows(_spec_minimal())
    assert rows["spec"]["status"] == "PASS"
    assert rows["structural"]["status"] == "PASS"
    for g in ("behavioral", "role", "render", "pixel"):
        assert rows[g]["status"] == "OMIT", g


def test_full_spec_makes_declared_dimensions_mandatory(monkeypatch):
    _stub_live(monkeypatch)
    rows = _rows(_spec_full())
    for g in ("behavioral", "role", "render"):
        assert rows[g]["status"] == "PASS", g
    assert rows["pixel"]["status"] == "OMIT"   # no reference supplied → fidelity opt-in


# ── enforcement: any failure flips the verdict + exit code ──────────────────
def _exit_code(monkeypatch, tmp_path, spec, argv_extra=()):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return gate.main([str(p), "--base-url", "http://x", *argv_extra])


def test_all_green_exits_zero_done(monkeypatch, tmp_path):
    _stub_live(monkeypatch)
    assert _exit_code(monkeypatch, tmp_path, _spec_full()) == 0


def test_behavioral_failure_is_not_done_exit_one(monkeypatch, tmp_path):
    _stub_live(monkeypatch, behavioral_ok=False)
    assert _exit_code(monkeypatch, tmp_path, _spec_full()) == 1


def test_structural_failure_is_not_done_exit_one(monkeypatch, tmp_path):
    _stub_live(monkeypatch, structural_fail=2)
    assert _exit_code(monkeypatch, tmp_path, _spec_minimal()) == 1


def test_spec_gap_short_circuits_before_live_gates(monkeypatch, tmp_path):
    monkeypatch.setattr(verify, "validate_spec",
                        lambda spec: [verify.Finding("spec-gap", "bad", "ctx")])
    # build_runtime_snapshot must NOT be called once the spec gate fails
    called = {"snap": False}
    monkeypatch.setattr(capture, "build_runtime_snapshot",
                        lambda *a, **k: called.__setitem__("snap", True) or {})
    rc = _exit_code(monkeypatch, tmp_path, _spec_full())
    assert rc == 1
    assert called["snap"] is False


def test_pixel_gate_runs_when_reference_supplied(monkeypatch, tmp_path):
    _stub_live(monkeypatch, pixel_ok=False)
    rc = _exit_code(monkeypatch, tmp_path, _spec_full(), ("--pixel", "/some/ref"))
    assert rc == 1   # pixel DRIFT now counts against done
