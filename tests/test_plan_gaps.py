"""Tests for harness.prompt_recipes.plan_gaps_from_spec — the production-coverage
gap surfacer, four-verdict taxonomy (ODC-only; never O11).

The failure it guards against: a spec that asks for behavior the harness can't build
used to be SILENTLY DROPPED, yielding a hollow plan with no warning (a rich prose-capabilities spec (the
case: eight screens, zero data bindings, no forms).

Each gap carries one of four verdicts so the fix is unambiguous:
  - spec-wiring     — fix the spec so a build step is generated
  - platform-native — ODC covers it; configure/author (portal prereq + hardening)
  - demo-stub       — demo-only shortcut; must be replaced for production
  - recipe-missing  — buildable on ODC but no recipe yet / needs external component
A fully-wired spec whose every feature is buildable produces an empty gap list.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import prompt_recipes as pr


def _by_cap(gaps, capability):
    return next(g for g in gaps if g["capability"] == capability)


def _caps(gaps):
    return {g["capability"] for g in gaps}


# ── spec-wiring: the spec under-specifies a buildable feature ─────────────────
def test_fully_wired_buildable_spec_has_no_gaps():
    spec = {
        "app": {"name": "T"},
        "dataModel": {"entities": [{"name": "Task", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
            {"name": "Title", "dataType": "Text"}]}]},
        "screens": [{
            "id": "tasks", "name": "Tasks",
            "components": [{"id": "t", "type": "Table", "boundTo": "Task"},
                           {"id": "add", "type": "Button", "label": "New Task"}],
            "actions": [{"name": "CreateTask", "does": ["CreateEntity"]}],
        }],
    }
    assert pr.plan_gaps_from_spec(spec) == []


def test_unbound_data_component_is_spec_wiring():
    spec = {"screens": [{"id": "list", "components": [
        {"id": "grid", "type": "Table", "label": "Rows"}]}]}
    gaps = pr.plan_gaps_from_spec(spec)
    g = _by_cap(gaps, "data-binding")
    assert g["kind"] == "spec-wiring" and "boundTo" in g["resolution"]


def test_form_affordance_without_write_action_is_spec_wiring():
    spec = {"screens": [{"id": "create", "components": [
        {"id": "saveBtn", "type": "Button", "label": "Save"}]}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "write-path")["kind"] == "spec-wiring"


def test_capabilities_only_flags_hollow_plan_as_spec_wiring():
    """A prose-capabilities signature: rich capabilities[] prose, no screen component boundTo anything."""
    spec = {"capabilities": [{"name": "Browse"}, {"name": "Create"}],
            "screens": [{"id": "list", "components": [{"id": "t", "type": "Table", "label": "Rows"}]}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "capabilities-only")["kind"] == "spec-wiring"


def test_capabilities_alongside_wired_screens_not_flagged():
    spec = {"capabilities": [{"name": "Browse"}],
            "screens": [{"id": "list", "components": [{"id": "t", "type": "Table", "boundTo": "Task"}]}]}
    assert "capabilities-only" not in _caps(pr.plan_gaps_from_spec(spec))


# ── platform-native: ODC covers it (NOT a wall) ──────────────────────────────
def test_email_verb_is_platform_native_with_smtp_prereq():
    spec = {"screens": [{"id": "d", "actions": [{"name": "Notify", "does": ["SendEmail"]}]}]}
    g = _by_cap(pr.plan_gaps_from_spec(spec), "email")
    assert g["kind"] == "platform-native" and "SMTP" in g["resolution"]


def test_rest_integration_is_platform_native_with_hardening_note():
    spec = {"integrations": [{"name": "Salesforce", "kind": "RestApi",
                              "description": "CRM customer data"}], "screens": []}
    g = _by_cap(pr.plan_gaps_from_spec(spec), "rest-consume")
    assert g["kind"] == "platform-native" and "harden" in g["resolution"].lower()


def test_external_database_integration_is_platform_native():
    spec = {"integrations": [{"name": "Camp", "kind": "RestApi",
                              "description": "Oracle external database, real-time reads"}], "screens": []}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "external-database")["kind"] == "platform-native"


def test_platform_idp_auth_is_platform_native():
    spec = {"auth": {"provider": "platform-idp"}, "screens": []}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "auth:platform-idp")["kind"] == "platform-native"


def test_non_admin_roles_with_platform_idp_are_platform_native():
    spec = {"auth": {"provider": "platform-idp"},
            "screens": [{"id": "q", "access": {"requiresRole": "Planner"}}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "role-model")["kind"] == "platform-native"


# ── demo-stub: shipped for demo, must be replaced for production ──────────────
def test_app_local_auth_is_a_demo_stub():
    spec = {"auth": {"provider": "app-local"}, "screens": []}
    g = _by_cap(pr.plan_gaps_from_spec(spec), "auth:app-local")
    assert g["kind"] == "demo-stub" and "platform-idp" in g["resolution"]


def test_role_gates_without_auth_block_imply_app_local_demo_stub():
    spec = {"screens": [{"id": "cfg", "access": {"requiresRole": "Admin"}}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "auth:app-local")["kind"] == "demo-stub"


def test_non_admin_roles_under_app_local_are_demo_stub():
    spec = {"auth": {"provider": "app-local"},
            "screens": [{"id": "q", "access": {"requiresRole": "Planner"}}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "role-model")["kind"] == "demo-stub"


# ── recipe-missing: buildable on ODC but no recipe yet / needs external component ─
def test_soap_integration_is_recipe_missing():
    spec = {"integrations": [{"name": "CampSoap", "kind": "RestApi",
                              "description": "SOAP WSDL endpoint"}], "screens": []}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "soap-consume")["kind"] == "recipe-missing"


def test_payment_integration_is_recipe_missing():
    spec = {"integrations": [{"name": "Pay", "kind": "RestApi",
                              "description": "payment gateway card processing"}], "screens": []}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "payment-gateway")["kind"] == "recipe-missing"


def test_document_generation_verb_is_recipe_missing():
    spec = {"screens": [{"id": "r", "actions": [{"name": "Export", "does": ["GeneratePdf"]}]}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "document-generation")["kind"] == "recipe-missing"


def test_transition_verb_is_recipe_missing_workflow():
    spec = {"screens": [{"id": "d", "actions": [{"name": "Accept", "does": ["Approve"]}]}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "workflow-transition")["kind"] == "recipe-missing"


def test_unknown_verb_falls_back_to_recipe_missing():
    spec = {"screens": [{"id": "d", "actions": [{"name": "Frobnicate", "does": ["Frobnicate"]}]}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "action:Frobnicate")["kind"] == "recipe-missing"


def test_upload_verb_is_platform_native_file_storage():
    spec = {"screens": [{"id": "d", "actions": [{"name": "Attach", "does": ["Upload"]}]}]}
    assert _by_cap(pr.plan_gaps_from_spec(spec), "file-storage")["kind"] == "platform-native"
