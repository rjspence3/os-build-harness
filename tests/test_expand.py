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
    # a Core exposes its entities so consumer apps can reference + READ them (else portals render empty)
    assert oc["dataModel"].get("public") is True


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


def test_agent_grounds_on_consumed_entities():
    # The #1 agent failure is no grounding — an agent that consumes producer entities MUST retrieve them.
    # expand derives grounding from `consumes.entities` so the built agent reasons over real data.
    a = _specs()["ScoreOrderRiskAgent"]["agents"][0]
    assert set(a["grounding"]) == {"Order", "OrderLine"}       # both consumed entities
    assert "Ground every answer" in a["systemPrompt"]          # grounded prompt, not a bare reasoner
    assert "Order" in a["systemPrompt"]


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


# ── dynamic-workflow detector unit tests (from real fixture) ─────────────────

DW_DOMAIN = Path(__file__).resolve().parent.parent / "examples" / "dynamic_workflow" / "domain_spec.json"


def _dw_domain() -> dict:
    return json.loads(DW_DOMAIN.read_text())


def _dw_pipeline():
    """Run the full pipeline on the dynamic_workflow fixture; return (result, domain)."""
    domain = _dw_domain()
    sysd = decompose.decompose(domain)
    inner = sysd["system"]
    result = expand.expand_system(inner, domain)
    return result, domain


def _dw_core_spec(result: dict) -> dict:
    """Select the Core spec by checking which spec has an engine block (owns engine caps)."""
    for spec in result["specs"].values():
        if spec.get("engine"):
            return spec
    raise AssertionError("no Core spec with engine block found")


def _dw_worker_spec(result: dict) -> dict:
    """Select the worker enduser spec by presence of a dynamicForm screen."""
    for spec in result["specs"].values():
        for s in spec.get("screens", []):
            if s.get("dynamicForm"):
                return spec
    raise AssertionError("no enduser spec with dynamicForm screen found")


def test_dw_decompose_is_modular():
    """The dynamic_workflow domain decomposes as modular."""
    domain = _dw_domain()
    sysd = decompose.decompose(domain)
    assert sysd.get("modular") is True


def test_dw_engine_block_on_workflow_core():
    """WorkflowCore gets an engine block with the 8 canonical actions in canonical order."""
    from harness.prompt_recipes import _ENGINE_ACTIONS
    result, _ = _dw_pipeline()
    core = _dw_core_spec(result)
    eng = core.get("engine")
    assert eng is not None
    assert eng["coreApp"] == "WorkflowCore"
    assert set(eng["actions"]) == set(_ENGINE_ACTIONS)
    assert eng["actions"] == _ENGINE_ACTIONS   # canonical order
    # entity map has task_template
    assert eng["entities"].get("task_template") == "TaskTemplate"


def test_engine_actions_do_not_leak_onto_non_engine_core():
    """FIX-001: orchestration-referenced engine actions (InstantiateWorkflow/EscalateOverdue, via
    callsService / cap-name) must attach ONLY to the Core that owns engine service caps — never leak
    onto an unrelated Core in a multi-Core domain. A Core owning none of the engine entities gets []."""
    caps = _dw_domain()["domain"]["capabilities"]
    # An unrelated Core (owns retail-ish entities) sees the SAME capability list but owns no engine entity.
    assert expand._engine_actions_for_core(["Order", "OrderLine"], caps) == []
    # The engine Core (owns the workflow entities) still collects all 8, incl. the orchestration refs.
    engine_owns = ["TaskTemplate", "Scenario", "ScenarioStep", "TransitionRule", "DecisionRow",
                   "WorkflowInstance", "TaskInstance", "AuditEvent"]
    from harness.prompt_recipes import _ENGINE_ACTIONS
    assert expand._engine_actions_for_core(engine_owns, caps) == _ENGINE_ACTIONS


def test_dw_engine_actions_removed_from_logic():
    """Engine action names must NOT appear in the Core's logic serviceActions (D4)."""
    from harness.prompt_recipes import _ENGINE_ACTIONS
    result, _ = _dw_pipeline()
    core = _dw_core_spec(result)
    logic_sa_names = {u["name"] for u in core.get("logic", []) if u.get("kind") == "serviceAction"}
    for action in _ENGINE_ACTIONS:
        assert action not in logic_sa_names, f"engine action {action!r} still in logic"
    # Non-engine SAs must still be in logic
    assert "SaveLibraryElement" in logic_sa_names
    assert "SubmitIntake" in logic_sa_names


def test_dw_library_import_block_on_workflow_core():
    """WorkflowCore gets a libraryImport block with mode=seed and the 5 FK-ordered entities."""
    result, _ = _dw_pipeline()
    core = _dw_core_spec(result)
    lib = core.get("libraryImport")
    assert lib is not None
    assert lib["mode"] == "seed"
    assert lib["libraryEntities"] == ["TaskTemplate", "Scenario", "ScenarioStep",
                                      "TransitionRule", "DecisionRow"]


def test_dw_dynamic_form_on_exactly_one_worker_screen():
    """Exactly one worker screen (MyWork) gets a dynamicForm block; no admin screen does."""
    result, _ = _dw_pipeline()
    worker = _dw_worker_spec(result)
    df_screens = [s for s in worker.get("screens", []) if s.get("dynamicForm")]
    assert len(df_screens) == 1
    df = df_screens[0]["dynamicForm"]
    assert df["taskInstance"] == "TaskInstance"
    assert df["taskTemplate"] == "TaskTemplate"
    assert df.get("completeAction", "CompleteTask") == "CompleteTask"
    # Admin specs must NOT have a dynamicForm
    for name, spec in result["specs"].items():
        if spec is worker:
            continue
        for s in spec.get("screens", []):
            assert not s.get("dynamicForm"), f"unexpected dynamicForm in {name}: {s['id']}"


def test_dw_retail_core_unaffected():
    """The retail domain's OrderingCore has no engine/libraryImport; logic still has PlaceOrder/OrderPlaced."""
    retail_specs = _specs()
    oc = retail_specs["OrderingCore"]
    assert oc.get("engine") is None
    assert oc.get("libraryImport") is None
    logic = {(u["kind"], u["name"]) for u in oc.get("logic", [])}
    assert ("serviceAction", "PlaceOrder") in logic
    assert ("globalEvent", "OrderPlaced") in logic
    for s in oc.get("screens", []):
        assert not s.get("dynamicForm")


def test_dw_expand_system_none_domain_adds_no_new_fields():
    """expand_system(system, domain=None) produces no engine/libraryImport/dynamicForm fields."""
    domain = _dw_domain()
    sysd = decompose.decompose(domain)
    inner = sysd["system"]
    result = expand.expand_system(inner, domain=None)
    for spec in result["specs"].values():
        assert spec.get("engine") is None
        assert spec.get("libraryImport") is None
        for s in spec.get("screens", []):
            assert not s.get("dynamicForm")


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
