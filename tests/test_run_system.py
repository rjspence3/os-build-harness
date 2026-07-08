"""Tests for harness/run_system.py — the multi-app orchestration planner.

Pins the properties a driving session relies on: the plan is topologically ordered (every producer
before every consumer, even same-layer Core->Core and even when the consumer sorts alphabetically
first), each phase carries the right app_create kind + create->author->publish lifecycle (with the BPT
special case), cross-app gates (dependsOn) are correct, and a MONOLITH is refused outright.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import run_system

FIX = Path(__file__).resolve().parent / "fixtures"


def _retail_plan() -> dict:
    return run_system.plan_from_domain(json.loads((FIX / "domain_retail.json").read_text()))


def _pos(plan: dict) -> dict:
    return {ph["app"]: i for i, ph in enumerate(plan["phases"])}


# ── the whole plan ───────────────────────────────────────────────────────────
def test_retail_plans_all_apps_modular():
    plan = _retail_plan()
    assert plan["modular"] is True
    assert {ph["app"] for ph in plan["phases"]} == {
        "DesignSystem", "CatalogCore", "OrderingCore", "PaymentsCore",
        "ScoreOrderRiskAgent", "FulfillWorkflow", "MerchantApp", "ShopperApp"}


def test_every_producer_before_every_consumer():
    plan = _retail_plan()
    pos = _pos(plan)
    for ph in plan["phases"]:
        for producer in ph["dependsOn"]:
            assert pos[producer] < pos[ph["app"]], f"{producer} must build before {ph['app']}"


def test_core_to_core_dependency_ordered():
    pos = _pos(_retail_plan())
    assert pos["CatalogCore"] < pos["OrderingCore"]  # OrderingCore consumes CatalogCore


def test_topological_order_beats_alphabetical():
    """ACore consumes BCore (both core). Alphabetically ACore < BCore, but the producer BCore
    MUST come first — proving a real topo sort, not a name sort."""
    system = {"system": {"name": "t", "apps": [
        {"name": "BCore", "layer": "core", "kind": "WebApplication", "context": "b", "owns": ["B"]},
        {"name": "ACore", "layer": "core", "kind": "WebApplication", "context": "a", "owns": ["A"],
         "consumes": [{"app": "BCore", "entities": ["B"]}]},
    ]}}
    order = run_system.topo_order(system)
    assert order.index("BCore") < order.index("ACore")


# ── per-phase shape ──────────────────────────────────────────────────────────
def test_kinds_and_lifecycles():
    phases = {ph["app"]: ph for ph in _retail_plan()["phases"]}
    assert phases["DesignSystem"]["kind"] == "Library"
    assert phases["CatalogCore"]["kind"] == "WebApplication"
    assert phases["ScoreOrderRiskAgent"]["kind"] == "AIAgent"
    wf = phases["FulfillWorkflow"]
    assert wf["kind"] == "BusinessProcess"
    # the BPT lifecycle encodes the proven publish-once-with-process sequencing
    joined = " ".join(wf["lifecycle"]).lower()
    assert "no auto-publish" in joined and "process present" in joined


def test_library_phase_has_no_authoring_steps():
    phases = {ph["app"]: ph for ph in _retail_plan()["phases"]}
    assert phases["DesignSystem"]["stepCount"] == 0
    assert phases["CatalogCore"]["stepCount"] > 0


def test_depends_on_matches_consumes():
    phases = {ph["app"]: ph for ph in _retail_plan()["phases"]}
    assert phases["FulfillWorkflow"]["dependsOn"]  # non-empty
    assert set(phases["ShopperApp"]["dependsOn"]) >= {"CatalogCore", "OrderingCore", "PaymentsCore"}


# ── monolith refusal ─────────────────────────────────────────────────────────
def test_monolith_is_refused():
    plan = run_system.plan_system(json.loads((FIX / "system_monolith.json").read_text()))
    assert plan["modular"] is False
    assert plan["phases"] == []
    assert any(r["status"] == "FAIL" for r in plan["invariants"])


def test_plan_from_prebuilt_system_topology():
    """plan_system also works from a hand-written system topology (no flat domain)."""
    plan = run_system.plan_system(json.loads((FIX / "system_retail.json").read_text()))
    assert plan["modular"] is True and len(plan["phases"]) == 8


# ── CLI ──────────────────────────────────────────────────────────────────────
def test_cli_domain_exit_zero_and_emits_plan(tmp_path, capsys):
    out = tmp_path / "plan.json"
    rc = run_system.main([str(FIX / "domain_retail.json"), "--domain", "--emit-plan", str(out)])
    assert rc == 0
    assert "MODULAR" in capsys.readouterr().out
    plan = json.loads(out.read_text())
    assert plan["modular"] is True and plan["phases"]


def test_cli_monolith_exit_one(capsys):
    rc = run_system.main([str(FIX / "system_monolith.json")])
    assert rc == 1
    assert "MONOLITH" in capsys.readouterr().out
