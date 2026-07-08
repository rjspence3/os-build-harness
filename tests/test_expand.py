"""Tests for harness/expand.py — system topology -> one app_spec.v0 per app.

The contract this pins: every emitted spec is app_spec.v0.2-valid (0 spec-gaps) AND plannable by the
existing plan_from_spec, and the cross-app wiring lands on the right fields — a Core exposes its
service actions/events as logic and owns its entities (intra-context FK only), a consumer gets
appReferences (never a cross-app FK), a Workflow gets a process block, an Agent gets an agents block.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import decompose, expand, verify
from harness.prompt_recipes import plan_from_spec

FIX = Path(__file__).resolve().parent / "fixtures"


def _pipeline() -> tuple[dict, dict]:
    domain = json.loads((FIX / "domain_retail.json").read_text())
    system = decompose.decompose(domain)["system"]
    return expand.expand_system(system, domain), domain


def _specs() -> dict:
    return _pipeline()[0]["specs"]


# ── the whole set is valid + plannable ───────────────────────────────────────
def test_every_emitted_spec_validates_and_plans():
    specs = _specs()
    assert set(specs) == {"CatalogCore", "OrderingCore", "PaymentsCore",
                          "FulfillWorkflow", "ScoreOrderRiskAgent", "MerchantApp", "ShopperApp"}
    for name, spec in specs.items():
        gaps = [f for f in verify.validate_spec(spec) if f.severity == "spec-gap"]
        assert not gaps, (name, [(g.summary, g.context) for g in gaps])
        assert plan_from_spec(spec)  # non-empty, no exception


def test_library_is_not_an_app_spec():
    result, _ = _pipeline()
    assert result["libraries"] == ["DesignSystem"]
    assert "DesignSystem" not in result["specs"]


# ── Core (service) wiring ────────────────────────────────────────────────────
def test_core_owns_entities_exposes_logic_no_screens():
    oc = _specs()["OrderingCore"]
    assert oc["screens"] == []
    owned = {e["name"] for e in oc["dataModel"]["entities"]}
    assert owned == {"Order", "OrderLine", "Cart"}
    logic = {(u["kind"], u["name"]) for u in oc["logic"]}
    assert ("serviceAction", "PlaceOrder") in logic
    assert ("globalEvent", "OrderPlaced") in logic


def test_domain_attributes_flow_into_core_entities():
    oc = _specs()["OrderingCore"]
    order = next(e for e in oc["dataModel"]["entities"] if e["name"] == "Order")
    attrs = {a["name"]: a["dataType"] for a in order["attributes"]}
    assert attrs.get("Id") == "Identifier"
    assert attrs.get("PlacedAt") == "DateTime"
    assert attrs.get("Total") == "Currency"


def test_intra_context_fk_present_cross_context_is_appref_not_fk():
    oc = _specs()["OrderingCore"]
    ents = {e["name"]: e for e in oc["dataModel"]["entities"]}
    # OrderLine -> Order is intra-context: a real FK attribute
    ol_refs = {a.get("references") for a in ents["OrderLine"]["attributes"]}
    assert "Order" in ol_refs
    # Order -> Product is cross-context: NOT a local FK anywhere in OrderingCore...
    for e in oc["dataModel"]["entities"]:
        assert all(a.get("references") != "Product" for a in e["attributes"])
    # ...it is an appReference instead
    refs = {r["producerApp"]: r for r in oc["appReferences"]}
    assert "CatalogCore" in refs
    assert any(el["name"] == "Product" and el["kind"] == "Entity"
               for el in refs["CatalogCore"]["elements"])


# ── Workflow wiring ──────────────────────────────────────────────────────────
def test_workflow_gets_process_and_service_action_refs():
    wf = _specs()["FulfillWorkflow"]
    assert wf["dataModel"]["entities"] == [] and wf["screens"] == []
    proc = wf["processes"][0]
    assert proc["producerApp"] == "OrderingCore"
    assert proc["triggerEvent"] == "OrderPlaced"
    called = {a["callsServiceAction"] for a in proc["activities"]}
    assert called == {"ScoreOrderRisk", "CapturePayment", "AdjustInventory"}
    # each called SA is imported via an appReference (ServiceAction kind)
    ref_sas = {el["name"] for r in wf["appReferences"] for el in r["elements"]
               if el["kind"] == "ServiceAction"}
    assert {"ScoreOrderRisk", "CapturePayment", "AdjustInventory"} <= ref_sas


# ── Agent wiring ─────────────────────────────────────────────────────────────
def test_agent_gets_agents_block_and_refs():
    ag = _specs()["ScoreOrderRiskAgent"]
    assert ag["agents"][0]["name"] == "ScoreOrderRisk"
    assert ag["agents"][0]["modelConnection"] == "TrialClaudeHaiku4_5"
    assert any(r["producerApp"] == "OrderingCore" for r in ag["appReferences"])


# ── End-user wiring ──────────────────────────────────────────────────────────
def test_enduser_owns_no_entities_has_refs_and_screens():
    sa = _specs()["ShopperApp"]
    assert sa["dataModel"]["entities"] == []
    assert sa["screens"] and any(s.get("isDefault") for s in sa["screens"])
    assert sa["app"]["roles"] == ["Shopper"]
    producers = {r["producerApp"] for r in sa["appReferences"]}
    assert {"CatalogCore", "OrderingCore", "PaymentsCore"} <= producers


# ── build order ──────────────────────────────────────────────────────────────
def test_build_order_is_layered_producers_first():
    domain = json.loads((FIX / "domain_retail.json").read_text())
    system = decompose.decompose(domain)["system"]
    order = expand.build_order(system)
    # foundation before any core; every core before every enduser
    assert order.index("DesignSystem") < order.index("CatalogCore")
    last_core = max(order.index(c) for c in ("CatalogCore", "OrderingCore", "PaymentsCore"))
    assert last_core < order.index("ShopperApp")
    assert last_core < order.index("MerchantApp")


# ── CLI writes per-app spec files that each validate ─────────────────────────
def test_cli_writes_valid_spec_files(tmp_path):
    sys_path = tmp_path / "sys.json"
    decompose.main([str(FIX / "domain_retail.json"), "--emit-system", str(sys_path)])
    rc = expand.main([str(sys_path), "--domain", str(FIX / "domain_retail.json"),
                      "--out-dir", str(tmp_path / "apps")])
    assert rc == 0
    files = list((tmp_path / "apps").glob("*.app_spec.json"))
    assert len(files) == 7
    for f in files:
        spec = json.loads(f.read_text())
        assert not [x for x in verify.validate_spec(spec) if x.severity == "spec-gap"]
