"""Tests for harness/decompose.py — the architect pass (flat domain spec -> modular topology).

Pins the rubric mechanics: one Core per bounded context, one End-User app per actor, orchestration/AI
externalized, and — the crux — intra-context references become FKs while cross-context references
become read-only consumes (never a cross-app FK). Every produced topology must pass its own gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import architecture as arch
from harness import decompose

FIX = Path(__file__).resolve().parent / "fixtures"


def _apps(result: dict) -> dict:
    return {a["name"]: a for a in result["system"]["system"]["apps"]}


def _retail() -> dict:
    return decompose.decompose(json.loads((FIX / "domain_retail.json").read_text()))


# ── the golden flat case ─────────────────────────────────────────────────────
def test_retail_decomposes_to_modular():
    result = _retail()
    assert result["modular"] is True, [r for r in result["invariants"] if r["status"] == "FAIL"]
    # and the produced topology independently passes the gate
    assert arch.verdict(arch.check_system(result["system"])) is True


def test_one_core_per_context():
    apps = _apps(_retail())
    cores = {n for n, a in apps.items() if a["layer"] == "core"}
    assert cores == {"CatalogCore", "OrderingCore", "PaymentsCore"}
    for c in cores:
        assert isinstance(apps[c]["context"], str) and apps[c]["context"]


def test_one_enduser_app_per_actor():
    apps = _apps(_retail())
    enduser = {n for n, a in apps.items() if a["layer"] == "enduser"}
    assert enduser == {"ShopperApp", "MerchantApp"}
    for e in enduser:
        assert apps[e]["owns"] == [] if apps[e].get("owns") is not None else True


def test_orchestration_and_agent_externalized():
    apps = _apps(_retail())
    assert apps["FulfillWorkflow"]["layer"] == "orchestration"
    assert apps["FulfillWorkflow"]["kind"] == "BusinessProcess"
    assert apps["ScoreOrderRiskAgent"]["kind"] == "AIAgent"


def test_intra_context_ref_is_fk_cross_context_is_consume():
    apps = _apps(_retail())
    oc = apps["OrderingCore"]
    # OrderLine -> Order is intra-context: a real FK
    assert {"from": "OrderLine", "target": "Order"} in oc["foreignKeys"]
    # Order -> Product is cross-context: a read-only consume of CatalogCore, NOT an FK
    assert all(fk["target"] != "Product" for fk in oc["foreignKeys"])
    assert any(c["app"] == "CatalogCore" and "Product" in c.get("entities", []) for c in oc["consumes"])


def test_writing_capability_exposes_service_and_event_on_core():
    apps = _apps(_retail())
    oc_ex = apps["OrderingCore"]["exposes"]
    assert "PlaceOrder" in oc_ex["serviceActions"]
    assert "OrderPlaced" in oc_ex["events"]


def test_workflow_consumes_trigger_event_and_step_services():
    consumes = {c["app"]: c for c in _apps(_retail())["FulfillWorkflow"]["consumes"]}
    assert "OrderPlaced" in consumes["OrderingCore"].get("events", [])
    assert "ScoreOrderRisk" in consumes["ScoreOrderRiskAgent"].get("serviceActions", [])
    assert "CapturePayment" in consumes["PaymentsCore"].get("serviceActions", [])


# ── untagged entities cluster by reference graph ─────────────────────────────
def test_untagged_entities_cluster_by_references():
    """No explicit context tags: two disjoint reference clusters -> two Core apps."""
    flat = {"domain": {"name": "d",
            "entities": [
                {"name": "Author", "references": []},
                {"name": "Book", "references": ["Author"]},
                {"name": "Ticket", "references": []},
                {"name": "Comment", "references": ["Ticket"]}],
            "actors": [], "capabilities": []}}
    result = decompose.decompose(flat)
    cores = [a for a in result["system"]["system"]["apps"] if a["layer"] == "core"]
    assert len(cores) == 2  # {Author,Book} and {Ticket,Comment}
    assert result["modular"] is True
    # each entity landed in exactly one core
    owned = [e for c in cores for e in c["owns"]]
    assert sorted(owned) == ["Author", "Book", "Comment", "Ticket"]


# ── in-app agent call (Call Agent pattern) ───────────────────────────────────
def test_enduser_consumes_agent_for_in_app_ai_step():
    """A NON-orchestrating capability with an AI step is the in-app Call Agent pattern: the actor's
    end-user app must consume the agent's service action (not only the workflow)."""
    flat = {"domain": {"name": "d",
            "entities": [{"name": "Case", "context": "c", "attributes": [{"name": "Note", "dataType": "Text"}]}],
            "actors": ["agent-user"],
            "capabilities": [
                {"name": "Assistant", "actor": "agent-user", "reads": ["Case"],
                 "steps": [{"name": "Reason", "ai": "Helper", "reads": ["Case"]}]}]}}
    result = decompose.decompose(flat)
    apps = {a["name"]: a for a in result["system"]["system"]["apps"]}
    assert "HelperAgent" in apps and apps["HelperAgent"]["kind"] == "AIAgent"
    user_app = apps["AgentUserApp"]
    assert any(c["app"] == "HelperAgent" and "Helper" in c.get("serviceActions", [])
               for c in user_app["consumes"]), user_app["consumes"]
    assert result["modular"] is True


def test_orchestrating_ai_step_does_not_wire_to_enduser():
    """An AI step inside an ORCHESTRATING capability is driven by the Workflow, not the actor's app."""
    flat = {"domain": {"name": "d",
            "entities": [{"name": "Order", "context": "o", "attributes": [{"name": "Total", "dataType": "Currency"}]}],
            "actors": ["buyer"],
            "capabilities": [
                {"name": "Buy", "actor": "buyer", "writes": ["Order"], "service": "PlaceOrder",
                 "raisesEvent": "OrderPlaced"},
                {"name": "Fulfill", "orchestrates": True, "triggerEvent": "OrderPlaced",
                 "steps": [{"ai": "RiskScore", "reads": ["Order"]}]}]}}
    result = decompose.decompose(flat)
    apps = {a["name"]: a for a in result["system"]["system"]["apps"]}
    buyer = apps["BuyerApp"]
    assert all(c["app"] != "RiskScoreAgent" for c in buyer.get("consumes", []))


# ── the decomposer SURFACES an un-decomposable input, never hides it ─────────
def test_mutual_cross_context_refs_surface_as_non_modular():
    """Two contexts referencing each other -> a Core<->Core consume cycle the gate must catch."""
    flat = {"domain": {"name": "knot",
            "entities": [
                {"name": "A", "context": "alpha", "references": ["B"]},
                {"name": "B", "context": "beta", "references": ["A"]}],
            "actors": [], "capabilities": []}}
    result = decompose.decompose(flat)
    assert result["modular"] is False
    assert any(r["gate"] == "acyclic-downward" and r["status"] == "FAIL" for r in result["invariants"])


# ── CLI ──────────────────────────────────────────────────────────────────────
def test_cli_emits_gate_passing_system(tmp_path, capsys):
    out = tmp_path / "sys.json"
    rc = decompose.main([str(FIX / "domain_retail.json"), "--emit-system", str(out)])
    assert rc == 0
    assert "MODULAR" in capsys.readouterr().out
    emitted = json.loads(out.read_text())
    assert arch.verdict(arch.check_system(emitted)) is True
