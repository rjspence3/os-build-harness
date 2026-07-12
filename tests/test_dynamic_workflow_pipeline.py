"""Integration proof: dynamic_workflow domain_spec.json -> decompose -> expand_system -> plan_from_spec
auto-emits workflow-engine, dynamic-form, and library-import steps.

Helpers select specs by topology properties (engine block presence; dynamicForm screen presence),
NOT by hardcoded app names — so the tests are robust to name changes in the decomposition.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import decompose, expand, verify
from harness.prompt_recipes import _ENGINE_ACTIONS, plan_from_spec

DW_DOMAIN_PATH = Path(__file__).resolve().parent.parent / "examples" / "dynamic_workflow" / "domain_spec.json"


def _dw():
    """Load the fixture, run decompose + expand_system, return (result, domain)."""
    domain = json.loads(DW_DOMAIN_PATH.read_text())
    sysd = decompose.decompose(domain)
    # decompose returns {"system": {"specVersion": ..., "system": {"name":..., "apps":[...]}}, ...}
    inner = sysd["system"]
    result = expand.expand_system(inner, domain)
    return result, domain


def _core_spec(result: dict) -> dict:
    """Select the Core spec by owns-set membership: the spec that has an engine block
    (which is only stamped when the Core owns engine capabilities). NOT hardcoded by name."""
    for spec in result["specs"].values():
        if spec.get("engine"):
            return spec
    raise AssertionError("no Core spec with engine block found — detector did not fire")


def _worker_spec(result: dict) -> dict:
    """Select the enduser spec with at least one dynamicForm screen.
    NOT hardcoded by name — works for any actor whose screen has the dynamic form."""
    for spec in result["specs"].values():
        for s in spec.get("screens", []):
            if s.get("dynamicForm"):
                return spec
    raise AssertionError("no enduser spec with dynamicForm screen found — detector did not fire")


# ── domain decomposes as modular ─────────────────────────────────────────────
def test_domain_decomposes_modular():
    domain = json.loads(DW_DOMAIN_PATH.read_text())
    sysd = decompose.decompose(domain)
    assert sysd.get("modular") is True


# ── Core plan: workflow-engine + library-import fire, chunks ≤4 ──────────────
def test_core_plan_has_workflow_engine_steps():
    result, _ = _dw()
    core = _core_spec(result)
    steps = plan_from_spec(core)
    wf_steps = [s for s in steps if s["recipe"] == "workflow-engine"]
    assert len(wf_steps) >= 1, "expected >=1 workflow-engine steps"


def test_core_workflow_engine_chunks_le4():
    result, _ = _dw()
    core = _core_spec(result)
    steps = plan_from_spec(core)
    for s in [s for s in steps if s["recipe"] == "workflow-engine"]:
        assert len(s["params"]["actions"]) <= 4, (
            f"chunk too large: {s['params']['actions']}")


def test_core_workflow_engine_union_is_all_8_canonical():
    """The union of all workflow-engine step action lists equals all 8 canonical engine actions."""
    result, _ = _dw()
    core = _core_spec(result)
    steps = plan_from_spec(core)
    all_actions: list[str] = []
    for s in [s for s in steps if s["recipe"] == "workflow-engine"]:
        all_actions.extend(s["params"]["actions"])
    assert set(all_actions) == set(_ENGINE_ACTIONS), (
        f"expected {set(_ENGINE_ACTIONS)}, got {set(all_actions)}")


def test_core_plan_has_library_import_step():
    result, _ = _dw()
    core = _core_spec(result)
    steps = plan_from_spec(core)
    li = [s for s in steps if s["recipe"] == "library-import"]
    assert len(li) >= 1, "expected >=1 library-import steps"


# ── Worker plan: dynamic-form fires ──────────────────────────────────────────
def test_worker_plan_has_dynamic_form_step():
    result, _ = _dw()
    worker = _worker_spec(result)
    steps = plan_from_spec(worker)
    df = [s for s in steps if s["recipe"] == "dynamic-form"]
    assert len(df) >= 1, "expected >=1 dynamic-form steps in worker plan"


# ── D4: engine action names absent from service-action steps ─────────────────
def test_engine_actions_absent_from_service_action_steps():
    """D4: engine action names must not appear as service-action recipe steps in the Core plan."""
    result, _ = _dw()
    core = _core_spec(result)
    steps = plan_from_spec(core)
    sa_names = {s["params"].get("name") for s in steps if s["recipe"] == "service-action"}
    for action in _ENGINE_ACTIONS:
        assert action not in sa_names, (
            f"engine action {action!r} found as a service-action step (D4 dedupe broken)")


# ── All expanded specs validate and plan ─────────────────────────────────────
def test_all_expanded_specs_validate():
    """Every expanded spec passes harness-verify --phase spec (no spec-gap findings)."""
    result, _ = _dw()
    for name, spec in result["specs"].items():
        gaps = [f for f in verify.validate_spec(spec) if f.severity == "spec-gap"]
        assert not gaps, f"{name}: spec-gap findings: {[(g.summary, g.context) for g in gaps]}"


def test_all_expanded_specs_plan_non_empty():
    """Every expanded spec produces a non-empty plan without raising."""
    result, _ = _dw()
    for name, spec in result["specs"].items():
        steps = plan_from_spec(spec)
        assert steps, f"{name}: plan_from_spec returned empty steps"
