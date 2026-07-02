"""Tests for harness-verify's spec-validation phase (offline, deterministic)."""
from __future__ import annotations

import copy
import json

import pytest

from harness.verify import SCHEMA_PATH, _schema_findings, validate_spec


def _example() -> dict:
    """The reference spec embedded in the schema (a single-screen excerpt)."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["examples"][0]


def _completed_example() -> dict:
    """The example plus the 'transfer' screen its navigation references — a
    complete, internally-consistent spec."""
    spec = _example()
    spec["screens"].append({
        "id": "transfer",
        "name": "Transfer",
        "components": [{"id": "amountInput", "type": "Input"}],
        "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "amountInput"}]},
    })
    return spec


def test_example_passes_json_schema_layer() -> None:
    # The embedded example is schema-valid even though it is an excerpt.
    assert _schema_findings(_example()) == []


def test_example_excerpt_flagged_by_crossref_for_dangling_transfer() -> None:
    # Cross-ref catches what JSON Schema cannot: navigation/assertion -> 'transfer'
    # which the excerpt never defines.
    findings = validate_spec(_example())
    gaps = [f for f in findings if f.severity == "spec-gap"]
    assert gaps, "expected the dangling 'transfer' reference to be flagged"
    assert all("transfer" in f.context for f in gaps)


def test_completed_example_is_clean() -> None:
    findings = validate_spec(_completed_example())
    assert [f for f in findings if f.severity == "spec-gap"] == []


def test_bad_datatype_is_schema_gap() -> None:
    spec = _completed_example()
    spec["dataModel"]["entities"][0]["attributes"][1]["dataType"] = "Money"  # not in allow-list
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("schema violation" in f.summary for f in gaps)


def test_screen_role_not_in_app_roles_is_crossref_gap() -> None:
    spec = _completed_example()
    spec["screens"][0]["roles"] = ["Manager"]  # app.roles is just ["Customer"]
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("role" in f.summary for f in gaps)


def test_assertion_datatype_contradicting_model_is_gap() -> None:
    spec = _completed_example()
    # Balance is Currency in the model; assert it's Decimal.
    for a in spec["screens"][0]["acceptance"]["assertions"]:
        if a["kind"] == "attribute":
            a["dataType"] = "Decimal"
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("contradicts the data model" in f.summary for f in gaps)


def test_dangling_relationship_target_is_gap() -> None:
    spec = _completed_example()
    spec["dataModel"]["entities"][0]["relationships"] = [{"to": "Ghost", "kind": "manyToOne"}]
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("unknown entity" in f.summary for f in gaps)


def test_binding_to_unknown_attribute_is_gap() -> None:
    spec = _completed_example()
    spec["screens"][0]["components"][0]["boundTo"] = "Account.Ghost"
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("unknown attribute" in f.summary for f in gaps)


# ── live phase: channel dispatch (findings-grounded) ────────────────────────
from harness.verify import LIVE_CHANNELS, _LIVE_HANDLERS, run_live_phase, _live_exit_code  # noqa: E402

ASSERTION_KINDS = {"entityExists", "attribute", "componentPresent", "binding", "navigates", "integrationExists"}


def test_every_kind_has_a_handler_and_channel() -> None:
    assert set(_LIVE_HANDLERS) == ASSERTION_KINDS
    assert set(LIVE_CHANNELS) == ASSERTION_KINDS


def test_channel_mapping_matches_findings() -> None:
    expected = {
        "entityExists": "mcp",
        "attribute": "mcp",
        "componentPresent": "mcp",
        "binding": "mcp",
        "navigates": "mcp",
        "integrationExists": "unverifiable",
    }
    assert {k: v[0] for k, v in LIVE_CHANNELS.items()} == expected
    # every channel decision must carry a (citing) rationale
    assert all(len(v[1]) > 20 for v in LIVE_CHANNELS.values())


def test_live_no_mcp_config_is_inconclusive_never_pass() -> None:
    results = run_live_phase(_completed_example(), mcp_config=None)
    by = {r.kind: r.status for r in results}
    assert by["entityExists"] == "unconfigured"      # mcp channel, no config
    assert by["componentPresent"] == "unconfigured"  # mcp (screen-walk), no config/snapshot
    assert by["binding"] == "unconfigured"           # mcp (screen-walk) now, not unverifiable
    assert _live_exit_code(results) == 3
    assert not any(r.status == "pass" for r in results)


def test_live_with_mcp_config_gates_to_not_implemented(tmp_path) -> None:
    cfg = tmp_path / ".mcp.json"
    cfg.write_text('{"mcpServers": {"outsystems": {"command": "x"}}}')
    results = run_live_phase(_completed_example(), mcp_config=cfg)
    by = {r.kind: r.status for r in results}
    assert by["entityExists"] == "not-implemented"   # configured but no snapshot supplied
    assert by["navigates"] == "not-implemented"      # mcp (screen-walk), config but no --screens
    assert by["binding"] == "not-implemented"        # mcp now, not unverifiable
    assert _live_exit_code(results) == 3             # still never a fake pass


# ── v0.2 schema fields (from P1.5 live calibration) ─────────────────────────
def test_specversion_must_be_0_2() -> None:
    spec = _completed_example()
    spec["specVersion"] = "0.1"  # old version
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("schema violation" in f.summary for f in gaps)


def test_v0_2_attribute_fields_validate() -> None:
    spec = _completed_example()
    a = spec["dataModel"]["entities"][0]["attributes"][1]  # Nickname (Text)
    a.update({"length": 50, "description": "account nickname"})
    spec["dataModel"]["entities"][0]["attributes"][2].update({"decimals": 2})  # Balance (Currency)
    assert [f for f in validate_spec(spec) if f.severity == "spec-gap"] == []


def test_static_entity_with_records_validates() -> None:
    spec = _completed_example()
    spec["dataModel"]["entities"].append({
        "name": "Goal", "isStatic": True, "description": "lookup",
        "attributes": [{"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                       {"name": "Label", "dataType": "Text", "length": 50}],
        "records": [{"Id": "1", "Label": "Home"}, {"Id": "2", "Label": "Holiday"}],
    })
    assert [f for f in validate_spec(spec) if f.severity == "spec-gap"] == []


def test_fk_references_resolves_and_dangling_is_gap() -> None:
    spec = _completed_example()
    # add a second entity whose attr references Account (FK)
    spec["dataModel"]["entities"].append({
        "name": "Transaction",
        "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
            {"name": "AccountId", "dataType": "Identifier", "references": "Account"},
        ],
    })
    assert [f for f in validate_spec(spec) if f.severity == "spec-gap"] == []
    # now break it
    spec["dataModel"]["entities"][-1]["attributes"][1]["references"] = "Ghost"
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("FK references unknown entity" in f.summary for f in gaps)


def test_screen_input_parameters_validate() -> None:
    spec = _completed_example()
    spec["screens"][1].update({  # the transfer screen
        "uiFlow": "MainFlow",
        "inputParameters": [{"name": "AccountId", "dataType": "Identifier", "references": "Account"}],
    })
    assert [f for f in validate_spec(spec) if f.severity == "spec-gap"] == []


def test_integrations_block_validates_and_assertion_resolves() -> None:
    spec = _completed_example()
    spec["integrations"] = [{"name": "RatesApi", "kind": "RestApi", "baseUrl": "https://x"}]
    spec["screens"][0]["acceptance"]["assertions"].append(
        {"kind": "integrationExists", "integration": "RatesApi"})
    assert [f for f in validate_spec(spec) if f.severity == "spec-gap"] == []
    # dangling integration assertion → gap
    spec["screens"][0]["acceptance"]["assertions"][-1]["integration"] = "Ghost"
    gaps = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    assert any("integrationExists references unknown integration" in f.summary for f in gaps)


def test_integration_assertion_routes_unverifiable() -> None:
    spec = _completed_example()
    spec["integrations"] = [{"name": "RatesApi", "kind": "RestApi"}]
    spec["screens"][0]["acceptance"]["assertions"].append(
        {"kind": "integrationExists", "integration": "RatesApi"})
    results = run_live_phase(spec, mcp_config=None)
    ie = [r for r in results if r.kind == "integrationExists"]
    assert ie and all(r.status == "unverifiable" for r in ie)


# ── P3: mcp-channel executor against a real context_entities snapshot ───────
from pathlib import Path  # noqa: E402
from harness.verify import load_entities_snapshot, _normalize_datatype  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "home_banking_core_entities.snapshot.json"


def _snap() -> dict:
    return load_entities_snapshot(FIXTURE)


def _live_spec(assertions: list) -> dict:
    return {"specVersion": "0.2", "app": {"name": "x", "roles": ["R"]},
            "dataModel": {"entities": [{"name": "E", "attributes": [{"name": "a", "dataType": "Text"}]}]},
            "screens": [{"id": "s", "name": "S", "components": [],
                         "acceptance": {"assertions": assertions}}]}


def test_normalize_datatype() -> None:
    assert _normalize_datatype("Long Integer") == "LongInteger"
    assert _normalize_datatype("Date Time") == "DateTime"
    assert _normalize_datatype("HBCustomer Identifier") == "Identifier"  # FK
    assert _normalize_datatype("Currency") == "Currency"


def test_snapshot_loads_real_fixture() -> None:
    snap = _snap()
    assert "HBCustomer" in snap and "HBAccount" in snap
    assert snap["HBCustomer"]["attributes"]["Id"]["dataType"] == "LongInteger"  # normalized from "Long Integer"


def test_entity_exists_pass_fail_against_live() -> None:
    snap = _snap()
    r = run_live_phase(_live_spec([{"kind": "entityExists", "entity": "HBCustomer"}]), None, snap)
    assert r[0].status == "pass" and r[0].channel == "mcp"
    r = run_live_phase(_live_spec([{"kind": "entityExists", "entity": "Ghost"}]), None, snap)
    assert r[0].status == "fail"


def test_attribute_pass_with_normalization_and_fk() -> None:
    snap = _snap()
    # live "Long Integer" must match spec "LongInteger"; live mandatory True
    r = run_live_phase(_live_spec([{"kind": "attribute", "entity": "HBCustomer", "attribute": "Id",
                                    "dataType": "LongInteger", "mandatory": True}]), None, snap)
    assert r[0].status == "pass"
    # FK: live "HBCustomer Identifier" -> "Identifier"
    r = run_live_phase(_live_spec([{"kind": "attribute", "entity": "HBAccount", "attribute": "CustomerId",
                                    "dataType": "Identifier"}]), None, snap)
    assert r[0].status == "pass"


def test_attribute_fail_modes() -> None:
    snap = _snap()
    wrong = run_live_phase(_live_spec([{"kind": "attribute", "entity": "HBCustomer", "attribute": "Id",
                                        "dataType": "Currency"}]), None, snap)
    missing = run_live_phase(_live_spec([{"kind": "attribute", "entity": "HBCustomer", "attribute": "Ghost",
                                          "dataType": "Text"}]), None, snap)
    bad_mand = run_live_phase(_live_spec([{"kind": "attribute", "entity": "HBCustomer", "attribute": "Name",
                                           "dataType": "Text", "mandatory": False}]), None, snap)  # live True
    assert wrong[0].status == "fail" and missing[0].status == "fail" and bad_mand[0].status == "fail"


def test_live_exit_code_pass_and_fail() -> None:
    snap = _snap()
    assert _live_exit_code(run_live_phase(_live_spec([{"kind": "entityExists", "entity": "HBCustomer"}]), None, snap)) == 0
    assert _live_exit_code(run_live_phase(_live_spec([{"kind": "entityExists", "entity": "Ghost"}]), None, snap)) == 1


def test_mcp_kinds_inconclusive_without_snapshot() -> None:
    # behavior preserved: no snapshot -> mcp kinds unconfigured, never pass
    r = run_live_phase(_live_spec([{"kind": "entityExists", "entity": "HBCustomer"}]), None, None)
    assert r[0].status == "unconfigured"


# ── NO-HOLES capability/connectivity check (HD D11) ─────────────────────────
def _caps_spec() -> dict:
    """A minimal but COMPLETE spec with a capabilities layer: entity bound + covered,
    screen covered, role covered, action declared on the capability's screen."""
    return {
        "specVersion": "0.2",
        "app": {"name": "x", "roles": ["Member"]},
        "dataModel": {"entities": [
            {"name": "Item", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Name", "dataType": "Text", "length": 50, "mandatory": True},
            ]},
        ]},
        "screens": [{
            "id": "items", "name": "Items",
            "components": [{"id": "itemsTable", "type": "Table", "boundTo": "Item"},
                           {"id": "saveBtn", "type": "Button", "label": "Save"}],
            "actions": [{"name": "SaveItem", "trigger": {"onComponent": "saveBtn", "event": "onClick"},
                         "does": ["CreateEntity"]}],
            "acceptance": {"assertions": [{"kind": "entityExists", "entity": "Item"}]},
        }],
        "capabilities": [{
            "name": "Manage items", "roles": ["Member"], "screens": ["items"],
            "entities": ["Item"], "actions": ["SaveItem"],
            "steps": [{"description": "save an item", "screen": "items", "action": "SaveItem"}],
        }],
    }


def _gaps(spec: dict) -> list:
    return [f for f in validate_spec(spec) if f.severity == "spec-gap"]


def _advisories(spec: dict) -> list:
    return [f for f in validate_spec(spec) if f.severity == "advisory"]


def test_complete_capabilities_spec_is_clean() -> None:
    assert _gaps(_caps_spec()) == []


def test_structure_only_spec_gets_advisory_not_gap() -> None:
    # No capabilities layer -> one advisory nudge, never a gap (backward compat).
    spec = _completed_example()
    assert "capabilities" not in spec
    assert _gaps(spec) == []
    assert any("no capabilities layer" in f.summary for f in _advisories(spec))


def test_entity_not_covered_by_capability_is_hole() -> None:
    spec = _caps_spec()
    spec["dataModel"]["entities"].append(
        {"name": "Extra", "attributes": [{"name": "Id", "dataType": "Identifier", "isIdentifier": True}]})
    assert any("entity 'Extra'" in f.context and "no capability" in f.context for f in _gaps(spec))


def test_screen_not_covered_by_capability_is_hole() -> None:
    spec = _caps_spec()
    spec["screens"].append({
        "id": "extra", "name": "Extra", "components": [{"id": "x", "type": "Container"}],
        "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "x"}]}})
    assert any("screen 'extra'" in f.context and "no capability" in f.context for f in _gaps(spec))


def test_role_not_covered_by_capability_is_hole() -> None:
    spec = _caps_spec()
    spec["app"]["roles"].append("Admin")
    assert any("role 'Admin'" in f.context and "no capability" in f.context for f in _gaps(spec))


def test_capability_referencing_unknown_screen_is_gap() -> None:
    spec = _caps_spec()
    spec["capabilities"][0]["screens"] = ["ghost"]
    assert any("capability references unknown screen" in f.summary for f in _gaps(spec))


def test_capability_referencing_unknown_entity_is_gap() -> None:
    spec = _caps_spec()
    spec["capabilities"][0]["entities"] = ["Ghost"]
    assert any("capability references unknown entity" in f.summary for f in _gaps(spec))


def test_capability_action_not_on_its_screens_is_gap() -> None:
    spec = _caps_spec()
    spec["capabilities"][0]["actions"] = ["GhostAction"]
    assert any("capability action not declared on any of its screens" in f.summary for f in _gaps(spec))


def test_capability_role_not_in_app_roles_is_gap() -> None:
    spec = _caps_spec()
    spec["capabilities"][0]["roles"] = ["Ghost"]
    assert any("capability role not declared in app.roles" in f.summary for f in _gaps(spec))


# ── PRODUCT-UI primitives (groupBy / columns / Board / Sidebar) ──────────────
def _pui_spec() -> dict:
    return {
        "specVersion": "0.2",
        "app": {"name": "x", "roles": ["Member"]},
        "dataModel": {"entities": [
            {"name": "State", "isStatic": True, "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Label", "dataType": "Text", "length": 50}]},
            {"name": "Item", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Title", "dataType": "Text", "length": 100, "mandatory": True},
                {"name": "Priority", "dataType": "Integer"},
                {"name": "StateId", "dataType": "Identifier", "references": "State"}]},
        ]},
        "screens": [
            {"id": "list", "name": "List", "components": [
                {"id": "itemsList", "type": "List", "boundTo": "Item", "groupBy": "StateId", "columns": [
                    {"field": "Priority", "kind": "glyph", "glyphSet": "priority"},
                    {"field": "Title", "kind": "text"},
                    {"field": "Item.StateId", "kind": "glyph", "glyphSet": "workflowState"}]},
                {"id": "sidebar", "type": "Sidebar", "nav": [{"label": "Board", "toScreen": "board", "section": "Main"}]}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "itemsList"}]}},
            {"id": "board", "name": "Board", "components": [
                {"id": "kanban", "type": "Board", "boundTo": "Item",
                 "board": {"columnsBy": "StateId", "card": {"title": "Title", "badges": ["Priority"]}}}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "kanban"}]}},
        ],
    }


def test_product_ui_primitives_validate_clean() -> None:
    assert _gaps(_pui_spec()) == []


def test_sidebar_nav_unknown_screen_is_gap() -> None:
    spec = _pui_spec()
    spec["screens"][0]["components"][1]["nav"][0]["toScreen"] = "ghost"
    assert any("sidebar nav targets unknown screen" in f.summary for f in _gaps(spec))


def test_board_dotted_field_unknown_attribute_is_gap() -> None:
    spec = _pui_spec()
    spec["screens"][1]["components"][0]["board"]["card"]["title"] = "Item.Ghost"
    assert any("product-ui field references unknown attribute" in f.summary for f in _gaps(spec))


# ── screen-walk executor (componentPresent / binding / navigates) — D12 ──────
from harness.verify import load_screens_snapshot  # noqa: E402


def _walk_spec() -> dict:
    return {"specVersion": "0.2", "app": {"name": "x", "roles": ["R"]},
            "dataModel": {"entities": [{"name": "Issue", "attributes": [{"name": "Title", "dataType": "Text"}]}]},
            "screens": [{"id": "issues", "name": "Issues", "components": [
                {"id": "issuesTable", "type": "Table", "boundTo": "Issue"},
                {"id": "newBtn", "type": "Button"}],
                "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "issues"}],
                "acceptance": {"assertions": [
                    {"kind": "componentPresent", "componentId": "issuesTable"},
                    {"kind": "binding", "componentId": "issuesTable", "boundTo": "Issue"},
                    {"kind": "navigates", "fromComponent": "newBtn", "event": "onClick", "toScreen": "issues"}]}}]}


_GOOD_WALK = {"screens": [{"id": "issues", "components": [
    {"id": "issuesTable", "boundTo": "Issue"}, {"id": "newBtn"}],
    "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "issues"}]}]}


def test_screen_walk_all_pass() -> None:
    snap = load_screens_snapshot(_GOOD_WALK)
    results = run_live_phase(_walk_spec(), None, None, snap)
    assert {r.kind: r.status for r in results} == {
        "componentPresent": "pass", "binding": "pass", "navigates": "pass"}
    assert all(r.channel == "mcp" for r in results)
    assert _live_exit_code(results) == 0


def test_screen_walk_component_missing_fails() -> None:
    walk = {"screens": [{"id": "issues", "components": [{"id": "newBtn"}],
            "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "issues"}]}]}
    results = run_live_phase(_walk_spec(), None, None, load_screens_snapshot(walk))
    by = {r.kind: r.status for r in results}
    assert by["componentPresent"] == "fail" and by["binding"] == "fail"  # table absent → both fail
    assert _live_exit_code(results) == 1


def test_screen_walk_binding_mismatch_fails() -> None:
    walk = {"screens": [{"id": "issues", "components": [
        {"id": "issuesTable", "boundTo": "Project"}, {"id": "newBtn"}],
        "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "issues"}]}]}
    results = run_live_phase(_walk_spec(), None, None, load_screens_snapshot(walk))
    by = {r.kind: r.status for r in results}
    assert by["componentPresent"] == "pass" and by["binding"] == "fail"


def test_screen_walk_navigates_missing_fails() -> None:
    walk = {"screens": [{"id": "issues", "components": [
        {"id": "issuesTable", "boundTo": "Issue"}, {"id": "newBtn"}], "navigation": []}]}
    results = run_live_phase(_walk_spec(), None, None, load_screens_snapshot(walk))
    assert {r.kind: r.status for r in results}["navigates"] == "fail"


def test_screen_walk_matches_by_name_when_no_id() -> None:
    walk = {"screens": [{"name": "Issues", "components": [
        {"id": "issuesTable", "boundTo": "Issue"}, {"id": "newBtn"}],
        "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "issues"}]}]}
    results = run_live_phase(_walk_spec(), None, None, load_screens_snapshot(walk))
    assert all(r.status == "pass" for r in results)


# ── worked live example (examples/task_tracker) ─────────────────────────────
def test_example_live_snapshots_all_pass() -> None:
    """The shipped live snapshots match the example spec → every live assertion passes."""
    from pathlib import Path
    from harness.verify import (
        run_live_phase, _live_exit_code, load_entities_snapshot, load_screens_snapshot,
    )
    ex = Path(__file__).resolve().parents[1] / "examples" / "task_tracker"
    spec = json.loads((ex / "app_spec.json").read_text(encoding="utf-8"))
    ents = load_entities_snapshot(ex / "live_entities.json")
    scrn = load_screens_snapshot(ex / "live_screens.json")
    results = run_live_phase(spec, mcp_config=None, entities_snapshot=ents, screens_snapshot=scrn)
    assert all(r.status == "pass" for r in results), [r.render() for r in results if r.status != "pass"]
    assert _live_exit_code(results) == 0
    assert len(results) == 9


def test_navigates_matches_when_walk_emits_screen_name() -> None:
    """A screen-walk may emit the screen NAME while the spec asserts by id;
    run_live_phase normalizes nav toScreen to the id so `navigates` still matches."""
    from harness.verify import run_live_phase, load_screens_snapshot
    spec = {"screens": [
        {"id": "home", "name": "Home", "acceptance": {"assertions": [
            {"kind": "navigates", "fromComponent": "goBtn", "event": "onClick", "toScreen": "detail"}]}},
        {"id": "detail", "name": "Detail", "acceptance": {"assertions": []}},
    ]}
    walk = {"screens": [{"id": "Home", "components": [{"id": "goBtn"}],
            "navigation": [{"fromComponent": "goBtn", "event": "onClick", "toScreen": "Detail"}]}]}
    scrn = load_screens_snapshot(walk)
    results = run_live_phase(spec, mcp_config=None, screens_snapshot=scrn)
    nav = next(r for r in results if r.kind == "navigates")
    assert nav.status == "pass", nav.detail    # "Detail" (name) resolved to id "detail"
