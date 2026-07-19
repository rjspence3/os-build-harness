"""Rolling recipe reconciliation (WALL-006) — the live-state 'evolving recipes' layer."""
from harness import reconcile as rc
from harness import prompt_recipes as pr


# ── LiveModel ────────────────────────────────────────────────────────────────────
def test_livemodel_defensive_shapes():
    live = rc.LiveModel.from_payloads(
        entities={"items": [{"name": "Req", "attributes": [{"name": "Id"}, {"name": "Title"}]}]},
        screens={"data": [{"name": "reqDetail", "components": [{"id": "saveBtn"}, {"dataSpecId": "titleInput"}],
                           "inputParameters": [{"name": "Id", "references": "Req"}]}]},
        actions={"results": [{"name": "SaveReqRecord"}]})
    assert live.has_entity("Req") and not live.has_entity("Ghost")
    assert {a["name"] for a in live.entity_attrs("Req")} == {"Id", "Title"}
    assert live.entity_attrs("Ghost") is None                     # unknown -> None, not []
    assert live.screen_component_ids("reqDetail") >= {"saveBtn", "titleInput"}
    assert live.screen_component_ids("nope") is None
    assert live.screen_takes_id("reqDetail") is True
    assert live.has_action("SaveReqRecord") and not live.has_action("Other")


# ── conditional self-heal (the flagship WALL-003 fix) ─────────────────────────────
_MOC_SPEC = {"screens": [{"id": "reqCreate", "components": [
    {"id": "descriptioninput", "type": "Input", "boundTo": "MaintenanceRequest.Description"},
    {"id": "MOCRequired", "type": "Dropdown", "boundTo": "MaintenanceRequest.MOCRequired"},
    {"id": "MOCTracking", "type": "Input", "boundTo": "MaintenanceRequest.MOCTrackingNumber",
     "visibleWhen": "MOCRequired = True"}]}]}


def test_conditional_selfheals_absent_widgets():
    """The create-form only authored `descriptioninput`; the conditional targets MOCTracking and reads
    MOCRequired, neither of which is live. The reconciler must emit ensure_widgets for both, bound to
    the form record New<entity>."""
    live = rc.LiveModel.from_payloads(
        screens={"items": [{"name": "reqCreate", "components": [{"id": "descriptioninput"}]}]})
    params = {"screen": "reqCreate", "component_id": "MOCTracking", "visible_when": "MOCRequired = True"}
    out, notes = rc.reconcile_params("conditional", params, live, _MOC_SPEC)
    ens = {w["id"]: w for w in out["ensure_widgets"]}
    assert set(ens) == {"MOCTracking", "MOCRequired"}
    assert ens["MOCTracking"]["attr"] == "MOCTrackingNumber"      # boundTo tail, not the id
    assert ens["MOCRequired"]["type"] == "Dropdown"
    assert out["record"] == "NewMaintenanceRequest"
    assert notes


def test_conditional_noop_when_widget_present():
    live = rc.LiveModel.from_payloads(
        screens={"items": [{"name": "reqCreate",
                            "components": [{"id": "MOCTracking"}, {"id": "MOCRequired"}]}]})
    params = {"screen": "reqCreate", "component_id": "MOCTracking", "visible_when": "MOCRequired = True"}
    out, _ = rc.reconcile_params("conditional", params, live, _MOC_SPEC)
    assert "ensure_widgets" not in out                            # both present -> nothing to heal


def test_conditional_recipe_renders_ensure_widgets():
    """The recipe must actually emit the create-if-absent instruction the reconciler asks for."""
    p = pr.render("conditional", {"screen": "reqCreate", "component_id": "MOCTracking",
                                  "visible_when": "MaintenanceRequest.MOCRequired = True",
                                  "record": "NewMaintenanceRequest",
                                  "ensure_widgets": [{"id": "MOCTracking", "attr": "MOCTrackingNumber", "type": "Input"}]})
    assert "ENSURE these inputs exist" in p and 'data-spec-id="MOCTracking"' in p
    assert "NewMaintenanceRequest.MOCTrackingNumber" in p


# ── list-screen detail-id + column resolution ─────────────────────────────────────
def test_list_screen_resolves_placeholder_columns_and_detail_id():
    spec = {"dataModel": {"entities": [
        {"name": "Cfg", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
            {"name": "HeaderText", "dataType": "Text"}, {"name": "Notice", "dataType": "Text"},
            {"name": "OwnerId", "dataType": "Identifier", "references": "Member"}]}]},
        "screens": [{"id": "cfgDetail", "inputParameters": []}]}
    live = rc.LiveModel.from_payloads(
        entities={"items": [{"name": "Cfg", "attributes": [
            {"name": "Id", "isIdentifier": True}, {"name": "HeaderText"}, {"name": "Notice"}]}]},
        screens={"items": [{"name": "cfgDetail", "inputParameters": []}]})
    params = {"screen": "cfgList", "entity": "Cfg", "columns": ["(entity display fields)"],
              "detail_screen": "cfgDetail"}
    out, notes = rc.reconcile_params("list-screen", params, live, spec)
    assert [c["field"] for c in out["columns"]] == ["HeaderText", "Notice"]   # FK/Id dropped
    assert out["detail_takes_id"] is False                                    # cfgDetail has no Id param
    assert any("no Id input" in n for n in notes)


def test_list_screen_detail_takes_id_true():
    spec = {"screens": [{"id": "d", "inputParameters": [{"name": "Id", "references": "X"}]}]}
    live = rc.LiveModel.from_payloads(screens={"items": [{"name": "d",
                                     "inputParameters": [{"name": "Id"}]}]})
    out, _ = rc.reconcile_params("list-screen", {"screen": "l", "entity": "X", "detail_screen": "d",
                                                 "columns": [{"field": "A", "kind": "text"}]}, live, spec)
    assert out["detail_takes_id"] is True


# ── create-form live refresh ──────────────────────────────────────────────────────
def test_create_form_refreshes_mandatory_defaults_from_live():
    spec = {"dataModel": {"entities": [
        {"name": "St", "isStatic": True, "records": [{"Record": "Open", "Order": 1}]}]}}
    live = rc.LiveModel.from_payloads(entities={"items": [{"name": "Req", "attributes": [
        {"name": "Id", "isIdentifier": True, "mandatory": True},
        {"name": "Title", "mandatory": True},
        {"name": "Status", "references": "St", "mandatory": True}]}]})
    out, notes = rc.reconcile_params("create-form", {"entity": "Req", "fields": ["Title"]}, live, spec)
    mdef = {d["field"]: d for d in out["mandatory_defaults"]}
    assert mdef["Status"]["value"] == "Entities.St.Open"
    assert notes


# ── safety: unknown recipe / no live / errors are no-ops ──────────────────────────
def test_reconcile_is_safe_noop():
    params = {"a": 1}
    assert rc.reconcile_params("nav-block", params, rc.LiveModel())[0] == params   # no reconciler
    assert rc.reconcile_params("conditional", params, None)[0] == params           # no live model
    # a reconciler that blows up must return the ORIGINAL params + a note, never raise
    out, notes = rc.reconcile_params("conditional", {"screen": "x", "visible_when": "y"},
                                     rc.LiveModel.from_payloads(screens={"items": [{"name": "x"}]}), None)
    assert out is not None
