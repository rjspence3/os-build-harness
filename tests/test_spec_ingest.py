"""Tests for harness/spec_ingest.py — the two-stage spec-document ingestion subsystem.

Style mirrors test_prompt_step.py + test_verify.py: offline, deterministic,
no MCP, pure unit + integration tests. The fixture at
tests/fixtures/basf_trimmed_spec.md drives e2e tests.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.spec_ingest import (
    MarkdownTable,
    ParseReport,
    Section,
    blocking_gaps,
    build_draft_spec,
    extract_entities,
    extract_integrations,
    extract_roles,
    extract_screens,
    extract_static_entities,
    extract_workflow_note,
    infer_component_type,
    ingest,
    map_attribute_type,
    parse_markdown_tables,
    parse_sections,
    parse_text_length,
    plan_gaps_with_fidelity,
    render_fill_prompt,
)
from harness.prompt_recipes import plan_gaps_from_spec
from harness.verify import _schema_findings

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "basf_trimmed_spec.md"


def _fixture_md() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def _fixture_draft() -> dict:
    return build_draft_spec(_fixture_md())


# ── Primitives ────────────────────────────────────────────────────────────────

def test_parse_tables_basic():
    text = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    tables = parse_markdown_tables(text)
    assert len(tables) == 1
    t = tables[0]
    assert t.headers == ["A", "B"]
    assert t.rows == [["1", "2"], ["3", "4"]]


def test_parse_tables_ragged_rows_padded_and_truncated():
    text = "| A | B | C |\n|---|---|---|\n| 1 |\n| x | y | z | extra |"
    tables = parse_markdown_tables(text)
    assert len(tables) == 1
    t = tables[0]
    # Short row should be padded to 3 columns.
    assert t.rows[0] == ["1", "", ""]
    # Long row should be truncated to 3 columns.
    assert t.rows[1] == ["x", "y", "z"]


def test_parse_tables_escaped_pipe_preserved():
    text = r"| A | B |" + "\n|---|---|\n" + r"| a \| b | c |"
    tables = parse_markdown_tables(text)
    assert len(tables) == 1
    # The escaped pipe should be a literal pipe in the cell value.
    assert tables[0].rows[0][0] == "a | b"


def test_parse_tables_none_returns_empty():
    assert parse_markdown_tables("") == []
    assert parse_markdown_tables("No tables here\nJust plain text.") == []


def test_parse_sections_flat_by_heading():
    text = "# A\npara\n## B\n### C ignored body\n#### D"
    secs = parse_sections(text)
    titles = [s.title for s in secs]
    levels = [s.level for s in secs]
    assert titles == ["A", "B", "C ignored body", "D"]
    assert levels == [1, 2, 3, 4]


# ── Type mapper ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected_type,expected_ref,expected_id", [
    ("Auto Number", "Identifier", None, True),
    ("User Id", "Text", None, False),
    ("Building Id", "Identifier", "Building", False),
    ("RequestStatus Id", "Identifier", "RequestStatus", False),
    ("CostCenterApproval Id", "Identifier", "CostCenterApproval", False),
    ("Text (200)", "Text", None, False),
    ("Text (unlimited)", "Text", None, False),
    ("Text", "Text", None, False),
    ("Date Time", "DateTime", None, False),
    ("Date", "Date", None, False),
    ("Time", "Time", None, False),
    ("Boolean", "Boolean", None, False),
    ("Integer", "Integer", None, False),
    ("Long Integer", "LongInteger", None, False),
    ("LongInteger", "LongInteger", None, False),
    ("Decimal", "Decimal", None, False),
    ("Currency", "Currency", None, False),
    ("Email", "Email", None, False),
    ("Phone Number", "PhoneNumber", None, False),
    ("PhoneNumber", "PhoneNumber", None, False),
    ("SomethingWeird", "Text", None, False),
    ("", "Text", None, False),
])
def test_map_attribute_type_table(raw, expected_type, expected_ref, expected_id):
    dtype, ref, is_id = map_attribute_type(raw)
    assert dtype == expected_type, f"raw={raw!r}: expected dataType {expected_type!r}, got {dtype!r}"
    assert ref == expected_ref, f"raw={raw!r}: expected references {expected_ref!r}, got {ref!r}"
    assert is_id == expected_id, f"raw={raw!r}: expected isIdentifier {expected_id!r}, got {is_id!r}"


def test_parse_text_length():
    assert parse_text_length("Text (200)") == 200
    assert parse_text_length("Text (unlimited)") is None
    assert parse_text_length("Text") is None
    assert parse_text_length("Date") is None


def test_user_id_is_text_not_fk():
    dtype, ref, is_id = map_attribute_type("User Id")
    assert dtype == "Text"
    assert ref is None
    assert is_id is False


# ── Entities ─────────────────────────────────────────────────────────────────

def test_extract_entities_from_fixture():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    entities = extract_entities(secs, report)
    names = [e["name"] for e in entities]
    assert "MaintenanceRequest" in names
    assert "Building" in names

    mr = next(e for e in entities if e["name"] == "MaintenanceRequest")
    # Status should be Identifier referencing RequestStatus.
    status = next(a for a in mr["attributes"] if a["name"] == "Status")
    assert status["dataType"] == "Identifier"
    assert status.get("references") == "RequestStatus"
    assert not status.get("isIdentifier", False)

    # Id should be isIdentifier=True.
    id_attr = next(a for a in mr["attributes"] if a["name"] == "Id")
    assert id_attr["isIdentifier"] is True
    assert id_attr["dataType"] == "Identifier"

    # Description should have length 2000.
    desc = next(a for a in mr["attributes"] if a["name"] == "Description")
    assert desc["dataType"] == "Text"
    assert desc.get("length") == 2000


def test_extract_entities_skips_row_missing_type():
    md = "#### Entities\n##### SomeEntity\n| Attribute | Type | Required |\n|---|---|---|\n| Foo | | No |\n| Bar | Text | Yes |"
    secs = parse_sections(md)
    report = ParseReport()
    entities = extract_entities(secs, report)
    # Foo is skipped (no Type), Bar is kept.
    assert len(entities) == 1
    assert entities[0]["name"] == "SomeEntity"
    assert len(entities[0]["attributes"]) == 1
    assert entities[0]["attributes"][0]["name"] == "Bar"
    assert any("Foo" in n and "missing Type" in n for n in report.notes)


def test_extract_entities_drops_empty_entity():
    md = "#### Entities\n##### EmptyEntity\n| Attribute | Type | Required |\n|---|---|---|\n| | | |"
    secs = parse_sections(md)
    report = ParseReport()
    entities = extract_entities(secs, report)
    assert all(e["name"] != "EmptyEntity" for e in entities)
    assert any("EmptyEntity" in s for s in report.skipped)


# ── Static entities ───────────────────────────────────────────────────────────

def test_extract_static_entities_with_records():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    static_entities = extract_static_entities(secs, report)
    names = [e["name"] for e in static_entities]
    assert "RequestStatus" in names
    assert "RequestType" in names

    rs = next(e for e in static_entities if e["name"] == "RequestStatus")
    assert rs.get("isStatic") is True
    assert len(rs.get("records", [])) == 6
    # Check specific record.
    draft = rs["records"][0]
    assert draft["Record"] == "Draft"
    assert draft["Label"] == "Draft"
    assert draft.get("Order") == 1
    # RequestStatus has an Order attribute.
    assert any(a["name"] == "Order" for a in rs["attributes"])

    # RequestType has no Order column — should have no Order attribute.
    rt = next(e for e in static_entities if e["name"] == "RequestType")
    assert not any(a["name"] == "Order" for a in rt["attributes"])


def test_extract_static_entity_bad_order_kept_raw():
    md = (
        "#### Static Entities\n"
        "##### StatusX\n"
        "| Record | Label | Order |\n"
        "|--------|-------|-------|\n"
        "| Draft | Draft | one |\n"
    )
    secs = parse_sections(md)
    report = ParseReport()
    static_entities = extract_static_entities(secs, report)
    assert len(static_entities) == 1
    rec = static_entities[0]["records"][0]
    # Non-integer Order is kept raw (as a string).
    assert rec["Order"] == "one"
    assert any("not an integer" in n for n in report.notes)


# ── Roles ─────────────────────────────────────────────────────────────────────

def test_extract_roles_strips_emphasis_and_reads_matrix():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    roles, permissions = extract_roles(secs, report)
    # Bold markers should be stripped.
    assert "Requester" in roles
    assert "Maintenance Planner" in roles
    assert "Maintenance Scheduler" in roles
    assert "Administrator" in roles
    # No raw bold markers in role names.
    assert not any("**" in r for r in roles)

    # 'Accept request' should only be permitted for Maintenance Planner.
    accept = next((p for p in permissions if p["action"] == "Accept request"), None)
    assert accept is not None
    assert "Maintenance Planner" in accept["roles"]
    assert "Requester" not in accept["roles"]


# ── Screens ───────────────────────────────────────────────────────────────────

def test_extract_screens_infers_components_from_data_table():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    screens = extract_screens(secs, report)
    assert len(screens) >= 1
    create_screen = next((s for s in screens if "MaintenanceRequestCreate" in s["id"]), None)
    assert create_screen is not None

    comp_map = {c["id"]: c for c in create_screen["components"]}
    # Dropdown input type.
    assert comp_map.get("requestType", {}).get("type") == "Dropdown"
    # Date picker -> DatePicker.
    assert comp_map.get("dateNeeded", {}).get("type") == "DatePicker"
    # Multi-line text -> Input.
    assert comp_map.get("description", {}).get("type") == "Input"
    # No component has a boundTo (Stage B gap).
    assert not any(c.get("boundTo") for c in create_screen["components"])


def test_extract_screens_actions_have_no_does():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    screens = extract_screens(secs, report)
    create_screen = next((s for s in screens if "MaintenanceRequestCreate" in s["id"]), None)
    assert create_screen is not None
    for action in create_screen.get("actions", []):
        assert "does" not in action, f"action {action['name']!r} should not have 'does'"


def test_extract_screens_synthesizes_valid_acceptance():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    screens = extract_screens(secs, report)
    for s in screens:
        assertions = s.get("acceptance", {}).get("assertions", [])
        assert len(assertions) >= 1, f"screen {s['id']!r} has no acceptance assertions"


# ── Integrations ──────────────────────────────────────────────────────────────

def test_extract_integrations_sap_and_excel():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    integrations, logic_units = extract_integrations(secs, report)
    # Should find at least one RestApi consume (SAP mentioned in prose).
    rest_integ = [i for i in integrations if i.get("kind") == "RestApi"
                  and i.get("direction") == "consume"]
    assert len(rest_integ) >= 1, "Expected at least one RestApi consume integration"
    # Should find at least one excelImport logic unit.
    excel_logic = [l for l in logic_units if l.get("kind") == "excelImport"]
    assert len(excel_logic) >= 1, "Expected at least one excelImport logic unit"


# ── Workflow note ─────────────────────────────────────────────────────────────

def test_extract_workflow_note_is_note_not_process():
    secs = parse_sections(_fixture_md())
    report = ParseReport()
    note = extract_workflow_note(secs, report)
    # Returns a string (from the transition rules table or workflow heading).
    assert isinstance(note, str)
    # The draft must NOT have a processes key.
    draft = build_draft_spec(_fixture_md())
    assert "processes" not in draft


# ── Stage A e2e ───────────────────────────────────────────────────────────────

def test_ingest_fixture_produces_schema_valid_draft():
    draft = _fixture_draft()
    assert _schema_findings(draft) == []
    assert draft["specVersion"] == "0.2"
    # Roles must be non-empty.
    assert len(draft["app"]["roles"]) >= 1
    # Every entity must have at least one attribute.
    for entity in draft["dataModel"]["entities"]:
        assert len(entity["attributes"]) >= 1, f"entity {entity['name']!r} has no attributes"
    # Every screen must have acceptance.assertions.
    for screen in draft["screens"]:
        assert len(screen["acceptance"]["assertions"]) >= 1, (
            f"screen {screen['id']!r} has empty acceptance.assertions"
        )


def test_ingest_fixture_draft_only_missing_semantic_wiring():
    from harness.verify import validate_spec
    draft = _fixture_draft()
    findings = validate_spec(draft)
    # No schema-violation findings.
    schema_violations = [f for f in findings if "schema violation" in f.summary.lower()]
    assert schema_violations == [], f"Unexpected schema violations: {schema_violations}"
    # Any remaining spec-gaps concern semantic concerns (binding, nav, auth) — not schema.
    # The fixture produces a clean draft with 0 spec-gap findings.
    spec_gaps = [f for f in findings if f.severity == "spec-gap"]
    # If there are spec-gaps, they must NOT be schema violations.
    for gap in spec_gaps:
        assert "schema violation" not in gap.summary.lower()


# ── Stage B gap shape ─────────────────────────────────────────────────────────

def test_stage_b_gap_report_shape():
    result = ingest(_fixture_md(), "demo")
    required_keys = {"kind", "capability", "detail", "where", "resolution", "blocking"}
    for gap in result.gaps:
        missing = required_keys - set(gap.keys())
        assert not missing, f"Gap missing keys {missing}: {gap}"
    # There should be at least one spec-wiring or platform-native gap.
    assert any(g["kind"] in ("spec-wiring", "platform-native") for g in result.gaps)


def test_stage_b_data_component_without_boundto_is_spec_wiring():
    """A Table component with no boundTo must emit a spec-wiring data-binding gap."""
    spec = {
        "specVersion": "0.2",
        "app": {"name": "Test", "roles": ["User"]},
        "dataModel": {"entities": [
            {"name": "Item", "attributes": [{"name": "Id", "dataType": "Identifier"}]},
        ]},
        "screens": [{
            "id": "itemList",
            "name": "Item List",
            "components": [{"id": "itemTable", "type": "Table"}],  # no boundTo
            "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "itemTable"}]},
        }],
    }
    gaps = plan_gaps_with_fidelity(spec, "demo")
    wiring_gaps = [g for g in gaps if g["kind"] == "spec-wiring" and g["capability"] == "data-binding"]
    assert wiring_gaps, "Expected at least one spec-wiring data-binding gap for unbound Table"


# ── Fidelity (crux tests) ─────────────────────────────────────────────────────

def _app_local_spec() -> dict:
    """Minimal spec with app-local auth to exercise auth:app-local gap."""
    return {
        "specVersion": "0.2",
        "app": {"name": "AuthApp", "roles": ["User"]},
        "dataModel": {"entities": [
            {"name": "Item", "attributes": [{"name": "Id", "dataType": "Identifier"}]},
        ]},
        "screens": [{
            "id": "home",
            "name": "Home",
            "components": [{"id": "c1", "type": "Container"}],
            "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c1"}]},
        }],
        "auth": {"provider": "app-local"},
    }


def _rest_spec(auth_value: str | None = None) -> dict:
    """Minimal spec with a REST consume integration."""
    integ: dict = {"name": "SomeApi", "kind": "RestApi", "direction": "consume"}
    if auth_value is not None:
        integ["auth"] = auth_value
    return {
        "specVersion": "0.2",
        "app": {"name": "RestApp", "roles": ["User"]},
        "dataModel": {"entities": [
            {"name": "Item", "attributes": [{"name": "Id", "dataType": "Identifier"}]},
        ]},
        "screens": [{
            "id": "home",
            "name": "Home",
            "components": [{"id": "c1", "type": "Container"}],
            "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c1"}]},
        }],
        "integrations": [integ],
    }


def test_fidelity_demo_app_local_auth_advisory():
    """In demo mode, auth:app-local gap must be blocking=False."""
    gaps = plan_gaps_with_fidelity(_app_local_spec(), "demo")
    auth_gaps = [g for g in gaps if g["capability"] == "auth:app-local"]
    assert auth_gaps, "Expected auth:app-local gap"
    assert all(not g["blocking"] for g in auth_gaps)


def test_fidelity_production_app_local_auth_blocking():
    """In production mode, auth:app-local gap must be blocking=True."""
    gaps = plan_gaps_with_fidelity(_app_local_spec(), "production")
    auth_gaps = [g for g in gaps if g["capability"] == "auth:app-local"]
    assert auth_gaps, "Expected auth:app-local gap"
    assert all(g["blocking"] for g in auth_gaps)
    assert blocking_gaps(gaps), "blocking_gaps() must be non-empty"


def test_fidelity_production_unhardened_rest_blocking():
    """In production mode, a rest-consume integration with no auth is blocking."""
    gaps = plan_gaps_with_fidelity(_rest_spec(auth_value=None), "production")
    rest_gaps = [g for g in gaps if g["capability"] == "rest-consume"]
    assert rest_gaps, "Expected rest-consume gap"
    assert any(g["blocking"] for g in rest_gaps), "Unhardened REST should be blocking in production"


def test_fidelity_production_hardened_rest_not_blocking():
    """In production mode, a rest-consume integration with OAuth auth is NOT blocking."""
    gaps = plan_gaps_with_fidelity(_rest_spec(auth_value="OAuth"), "production")
    rest_gaps = [g for g in gaps if g["capability"] == "rest-consume"]
    assert rest_gaps, "Expected rest-consume gap"
    # A hardened (auth='OAuth') integration should NOT be blocking.
    assert not any(g["blocking"] for g in rest_gaps), (
        "Hardened REST (auth=OAuth) should not be blocking in production"
    )


def test_plan_gaps_from_spec_unchanged_by_demo():
    """demo fidelity must equal plan_gaps_from_spec(spec) + blocking=False on each gap."""
    spec = _fixture_draft()
    raw = plan_gaps_from_spec(spec)
    demo = plan_gaps_with_fidelity(spec, "demo")
    assert len(raw) == len(demo)
    for r, d in zip(raw, demo):
        expected = dict(r)
        expected["blocking"] = False
        assert d == expected, f"Demo gap mismatch: expected {expected}, got {d}"


def test_invalid_fidelity_raises():
    with pytest.raises(ValueError):
        plan_gaps_with_fidelity({}, "staging")


# ── Fill-prompt ───────────────────────────────────────────────────────────────

def test_fill_prompt_mirrors_preamble_and_lists_gaps():
    result = ingest(_fixture_md(), "demo")
    prompt = result.fill_prompt
    # Must contain the ingest preamble marker.
    assert "app_spec.json" in prompt
    assert "harness-verify" in prompt
    # Must contain at least one gap's capability and resolution.
    for gap in result.gaps:
        assert gap["capability"] in prompt
        assert gap["resolution"] in prompt
    # Must be a pure string.
    assert isinstance(prompt, str)


# ── CLI ───────────────────────────────────────────────────────────────────────

def test_cli_writes_out_and_returns_zero_demo(tmp_path):
    from harness.spec_ingest import main as ingest_main
    out_path = tmp_path / "draft.json"
    rc = ingest_main([str(_FIXTURE), "--out", str(out_path), "--fidelity", "demo"])
    assert rc == 0
    assert out_path.exists()
    draft = json.loads(out_path.read_text())
    assert draft["specVersion"] == "0.2"


def test_cli_production_blocking_exits_nonzero(tmp_path):
    """production mode with a blocking gap exits 1.

    The fixture's REST integration is unhardened (no auth), so production
    fidelity flags it as a blocking gap and the CLI exits 1.
    """
    from harness.spec_ingest import main as ingest_main
    out_path = tmp_path / "prod.json"
    rc = ingest_main([str(_FIXTURE), "--out", str(out_path), "--fidelity", "production"])
    assert rc == 1


def test_production_rest_hardening_is_per_integration():
    """FIX-001: a hardened integration (auth set) must NOT be flagged blocking
    just because a sibling REST integration is unhardened."""
    from harness.spec_ingest import plan_gaps_with_fidelity, blocking_gaps
    spec = {
        "specVersion": "0.2",
        "app": {"name": "MultiInteg", "roles": ["User"]},
        "dataModel": {"entities": [{"name": "E", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
        "screens": [{"id": "s", "name": "S", "route": "/s",
                     "components": [{"id": "c", "type": "Container"}],
                     "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]}}],
        "integrations": [
            {"name": "SAPHardened", "kind": "RestApi", "direction": "consume",
             "auth": "OAuth", "methods": [{"name": "m", "http": "GET"}]},
            {"name": "SAPBare", "kind": "RestApi", "direction": "consume",
             "methods": [{"name": "n", "http": "GET"}]},
        ],
    }
    gaps = plan_gaps_with_fidelity(spec, "production")
    rest_gaps = {g["detail"]: g["blocking"] for g in gaps if g.get("capability") == "rest-consume"}
    assert rest_gaps["integration 'SAPHardened'"] is False
    assert rest_gaps["integration 'SAPBare'"] is True
    assert len(blocking_gaps(gaps)) == 1


def test_json_production_blocking_exits_nonzero(tmp_path):
    """FIX-002: the --json branch honors the production blocking gate."""
    from harness.spec_ingest import main as ingest_main
    rc = ingest_main([str(_FIXTURE), "--json", "--fidelity", "production"])
    assert rc == 1


def test_cli_demo_blocking_exits_zero(tmp_path):
    """demo mode always exits 0 even when there are gaps."""
    from harness.spec_ingest import main as ingest_main
    out_path = tmp_path / "demo.json"
    rc = ingest_main([str(_FIXTURE), "--out", str(out_path), "--fidelity", "demo"])
    assert rc == 0


def test_cli_missing_file_exits_two():
    from harness.spec_ingest import main as ingest_main
    rc = ingest_main(["/no/such/file.md"])
    assert rc == 2


def test_cli_report_and_emit_prompt_flags(capsys, tmp_path):
    """--report and --emit-prompt both appear in stdout."""
    from harness.spec_ingest import main as ingest_main
    out_path = tmp_path / "out.json"
    rc = ingest_main([str(_FIXTURE), "--out", str(out_path),
                      "--report", "--emit-prompt"])
    assert rc == 0
    captured = capsys.readouterr().out
    # Worklist presence.
    assert "GAP WORKLIST" in captured or "capability" in captured.lower()
    # Fill-prompt preamble.
    assert "app_spec.json" in captured
