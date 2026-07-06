"""Tests for harness/prompt_recipes.py + harness/prompt_step.py.

Recipes are pure `params -> str`; each test asserts the rendered prompt bakes in
the live-build CORRECTIONS that keep the retry-factor near zero — so a regression
that drops a correction fails here, offline, without an MCP.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import prompt_recipes as pr
from harness import prompt_step


# ── shared preamble corrections apply to every recipe ────────────────────────
@pytest.mark.parametrize("name,params", [
    ("nav-block", {"items": [{"label": "Inbox", "toScreen": "inbox"}]}),
    ("list-screen", {"screen": "documents", "entity": "Document", "columns": ["Title"]}),
    ("role-gate", {"screen": "settings"}),
    ("seed-entity", {"entity": "Document", "rows": [{"Title": "Q3 Plan"}]}),
])
def test_every_recipe_carries_the_preamble_corrections(name, params):
    prompt = pr.render(name, params)
    assert "data-spec-id" in prompt                      # runtime-resolution contract
    assert "do not publish" in prompt.lower()            # orchestrator owns publish
    # no stray platform role (keep Anonymous) — every recipe must say so
    assert "role" in prompt.lower() and "anonymous" in prompt.lower()


def test_nav_block_kills_the_link_default_text_defect():
    prompt = pr.render("nav-block", {"items": [
        {"label": "Inbox", "toScreen": "inbox"}, {"label": "Board", "toScreen": "board"}]})
    # the whole point: one shared block, not per-screen; and delete the literal "link" text
    assert "reusable Web Block" in prompt
    assert "do not fan this nav out per screen" in prompt.lower()
    assert 'literal "link"' in prompt.lower() or 'literal \"link\"' in prompt
    assert "Inbox" in prompt and "Board" in prompt


def test_list_screen_binds_entity_and_forbids_empty():
    prompt = pr.render("list-screen", {
        "screen": "documents", "entity": "Document",
        "columns": ["Title", "Author", "UpdatedAt"], "detail_screen": "documentDetail"})
    assert "aggregate over the Document entity" in prompt
    assert 'data-entity="Document"' in prompt
    assert "Title, Author, UpdatedAt" in prompt
    assert "documentDetail" in prompt                    # row -> detail nav
    assert "do not leave an empty table" in prompt.lower()


def test_role_gate_refuses_platform_role():
    prompt = pr.render("role-gate", {"screen": "settings", "home": "Issues"})
    assert "do NOT add any platform Role" in prompt
    assert "ln_current_user" in prompt
    assert "IsAdmin" in prompt and "Issues" in prompt


def test_seed_entity_uses_existing_loader_and_warns_run_once():
    prompt = pr.render("seed-entity", {"entity": "Document", "rows": [
        {"Title": "Q3 Product Planning"}, {"Title": "Onboarding Guide"}]})
    assert "LoadSampleDataForDocument" in prompt
    assert "runs once" in prompt.lower() and "guard" in prompt.lower()
    assert "DATA-ONLY" in prompt
    assert "Q3 Product Planning" in prompt


def test_missing_required_param_raises():
    with pytest.raises(ValueError):
        pr.render("list-screen", {"screen": "x"})        # missing entity + columns


def test_unknown_recipe_raises():
    with pytest.raises(KeyError):
        pr.render("nope", {})


# ── CLI ──────────────────────────────────────────────────────────────────────
def test_cli_list(capsys):
    rc = prompt_step.main(["--list"])
    out = capsys.readouterr().out
    assert rc == 0
    for name in ("nav-block", "list-screen", "role-gate", "seed-entity"):
        assert name in out


def test_cli_render(capsys):
    rc = prompt_step.main(["role-gate", "--params", '{"screen":"members"}'])
    out = capsys.readouterr().out
    assert rc == 0
    assert "members" in out and "do NOT add any platform Role" in out


def test_cli_bad_params(capsys):
    rc = prompt_step.main(["role-gate", "--params", "{not json}"])
    assert rc == 1


def test_cli_execute_is_honest_not_implemented(capsys):
    rc = prompt_step.main(["--execute", "role-gate", "--params", '{"screen":"members"}'])
    assert rc == 3   # never a false success


# ── spec -> build plan (the loop-closer) ─────────────────────────────────────
def _spec_with_first_class_fields():
    return {
        "specVersion": "0.2",
        "app": {"name": "t", "roles": ["User", "Admin"]},
        "dataModel": {"entities": [
            {"name": "Member", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "IsAdmin", "dataType": "Boolean"}]},
            {"name": "Doc", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Title", "dataType": "Text"}]}]},
        "navigation": {"block": "SidebarNav", "workspaceLabel": "Acme",
                       "items": [{"label": "Docs", "toScreen": "docs"}]},
        "auth": {"provider": "app-local", "userEntity": "Member", "adminAttribute": "IsAdmin",
                 "loginScreen": "login",
                 "testUsers": [{"role": "Admin", "label": "Rob", "isAdmin": True},
                               {"role": "User", "label": "Kira"}]},
        "screens": [
            {"id": "docs", "name": "Docs", "route": "/docs",
             "components": [{"id": "docsTable", "type": "Table", "boundTo": "Doc",
                             "columns": [{"field": "Title", "kind": "text"}]}],
             "navigation": [{"fromComponent": "docsTable", "event": "onClick", "toScreen": "docDetail"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "docsTable"}]}},
            {"id": "settings", "name": "Settings", "route": "/settings",
             "access": {"adminOnly": True, "redirectTo": "docs"},
             "components": [{"id": "cfg", "type": "Container"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "cfg"}]}},
            {"id": "docDetail", "name": "Doc Detail", "route": "/doc",
             "components": [{"id": "body", "type": "Container"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "body"}]}},
            {"id": "login", "name": "Login", "route": "/login",
             "components": [{"id": "form", "type": "Form"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "form"}]}},
        ],
    }


def test_plan_derives_expected_ordered_steps():
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    recipes = [s["recipe"] for s in steps]
    # scaffold first (data model, then all screens with Anonymous baked — seam 3d), then nav-block,
    # seed the user entity, the docs list, and the settings gate
    assert recipes[0] == "data-model" and recipes[1] == "screen"
    assert "nav-block" in recipes and "seed-entity" in recipes and "list-screen" in recipes and "role-gate" in recipes
    nav = next(s for s in steps if s["recipe"] == "nav-block")["params"]
    assert nav["block_name"] == "SidebarNav" and nav["logout_to"] == "login"
    assert nav["items"][0] == {"label": "Docs", "toScreen": "docs"}


def test_plan_seed_uses_testusers_with_admin_flag():
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    seed = next(s for s in steps if s["recipe"] == "seed-entity")
    assert seed["params"]["entity"] == "Member"
    rows = seed["params"]["rows"]
    assert {"label": "Rob", "IsAdmin": True} in rows and {"label": "Kira", "IsAdmin": False} in rows


def test_plan_list_screen_carries_columns_and_detail_nav():
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    ls = next(s for s in steps if s["recipe"] == "list-screen")
    assert ls["params"]["entity"] == "Doc"
    assert ls["params"]["columns"] == ["Title"]
    assert ls["params"]["detail_screen"] == "docDetail"


def test_plan_role_gate_pulls_auth_and_redirect():
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    gate = next(s for s in steps if s["recipe"] == "role-gate")
    assert gate["params"]["screen"] == "settings"
    assert gate["params"]["user_entity"] == "Member" and gate["params"]["admin_attr"] == "IsAdmin"
    assert gate["params"]["home"] == "docs" and gate["params"]["login"] == "login"


def test_plan_steps_all_render():
    for step in pr.plan_from_spec(_spec_with_first_class_fields()):
        prompt = pr.render(step["recipe"], step["params"])
        assert "data-spec-id" in prompt and "do not publish" in prompt.lower()


def test_cli_plan(capsys, tmp_path):
    import json as _json
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(_json.dumps(_spec_with_first_class_fields()))
    rc = prompt_step.main(["--plan", str(spec_file)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "build plan" in out and "nav-block" in out and "role-gate" in out


def test_create_form_recipe_encodes_the_write_path_corrections():
    p = pr.render("create-form", {"screen": "documentDetail", "entity": "Document",
                                  "fields": ["Title", "Content"], "id_param": "DocumentId",
                                  "creator_attr": "CreatorId", "return_screen": "documents"})
    assert "Public=FALSE" in p and "OS-BLD-40409" in p          # non-public server action
    assert "NullIdentifier()" in p                              # create-vs-update branch
    assert "inline record literal" in p                         # typed-local + per-attr, no inline
    assert 'data-spec-id="titleinput"' in p and 'data-spec-id="savedocumentbtn"' in p
    assert "ln_current_user" in p                               # identity for CreatorId


def test_plan_emits_write_path_step_from_actions_does():
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [
                {"name": "Doc", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Title", "dataType": "Text"},
                    {"name": "CreatorId", "dataType": "Identifier", "references": "Member"},
                    {"name": "CreatedAt", "dataType": "DateTime"}]},
                {"name": "Member", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
            "auth": {"provider": "app-local", "userEntity": "Member"},
            "screens": [
                {"id": "docs", "name": "D", "components": [{"id": "l", "type": "List", "boundTo": "Doc"}],
                 "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "l"}]}},
                {"id": "docDetail", "name": "DD",
                 "inputParameters": [{"name": "DocId", "dataType": "Identifier", "references": "Doc"}],
                 "components": [{"id": "b", "type": "Button", "label": "Save"}],
                 "actions": [{"name": "SaveDoc", "trigger": {"onComponent": "b", "event": "onClick"},
                              "does": ["CreateEntity", "UpdateEntity"]}],
                 "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "b"}]}}]}
    wp = [s for s in pr.plan_from_spec(spec) if s["recipe"] == "create-form"]
    # seam 3f: one write-path emits three thrash-free sub-steps (action -> widgets -> wire)
    assert [s["params"]["phase"] for s in wp] == ["action", "widgets", "wire"]
    p = wp[0]["params"]
    assert p["entity"] == "Doc" and "Title" in p["fields"]
    assert "CreatorId" not in p["fields"] and "CreatedAt" not in p["fields"]   # FK + audit dropped
    assert p["id_param"] == "DocId" and p["creator_attr"] == "CreatorId" and p["return_screen"] == "docs"


def test_write_path_entity_is_the_data_bound_one_not_the_context_input():
    """Iteration-2 seam: a list screen that creates its listed entity while carrying a
    parent-context input param. `tasks` lists Tasks (boundTo) inside a TaskList (ListId input);
    CreateTask makes a Task, NOT a TaskList. The data-bound entity must win over the context
    input — else the write-path recipe targets the wrong entity."""
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [
                {"name": "TaskList", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Name", "dataType": "Text"}]},
                {"name": "Task", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Title", "dataType": "Text"},
                    {"name": "ListId", "dataType": "Identifier", "mandatory": True, "references": "TaskList"}]}]},
            "screens": [
                {"id": "tasks", "name": "Tasks",
                 "inputParameters": [{"name": "ListId", "dataType": "Identifier", "references": "TaskList"}],
                 "components": [{"id": "tbl", "type": "Table", "boundTo": "Task"}],
                 "actions": [{"name": "CreateTask", "trigger": {"onComponent": "tbl", "event": "onClick"},
                              "does": ["CreateEntity"]}],
                 "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tbl"}]}}]}
    wp = [s for s in pr.plan_from_spec(spec) if s["recipe"] == "create-form"]
    assert [s["params"]["phase"] for s in wp] == ["action", "widgets", "wire"]   # seam 3f
    p = wp[0]["params"]
    assert p["entity"] == "Task"                        # boundTo wins; NOT the TaskList context input
    # seam 3a: the mandatory parent FK Task.ListId must be wired from the screen's ListId input param
    assert p["context_fk"] == {"attr": "ListId", "from_param": "ListId"}
    # seam 3b: no input param references Task itself -> create-only, id_param omitted (not a phantom "TaskId")
    assert "id_param" not in p
    # the WIRE phase instructs the mandatory parent-FK assignment; the ACTION phase the server action
    wire = pr.render("create-form", {**p, "phase": "wire"})
    assert "NewTask.ListId = the screen's ListId input parameter" in wire
    assert "MANDATORY parent reference" in wire
    action = pr.render("create-form", {**p, "phase": "action"})
    assert "SaveTaskRecord" in action and "Public=FALSE" in action
    # the combined (phase=None) prompt still carries the create-only Id instruction (backward-compatible)
    combined = pr.render("create-form", {k: v for k, v in p.items() if k != "phase"})
    assert "NullIdentifier() (always create)" in combined


def test_data_model_recipe_authors_all_entities_one_turn_with_fks():
    p = pr.render("data-model", {"entities": [
        {"name": "TaskList", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
            {"name": "Title", "dataType": "Text", "mandatory": True, "length": 100}]},
        {"name": "Task", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
            {"name": "IsDone", "dataType": "Boolean", "mandatory": True, "default": False},
            {"name": "ListId", "dataType": "Identifier", "mandatory": True, "references": "TaskList"}]}]})
    assert "ALL of these entities in THIS ONE turn" in p              # seam 3d: interdependent -> one turn
    assert "Title: Text, mandatory, length 100" in p
    assert "IsDone: Boolean, mandatory, default False" in p
    assert "ListId: a mandatory foreign-key reference to TaskList" in p
    assert "- TaskList: Title: Text" in p and "- Task: IsDone: Boolean" in p   # auto-number Id skipped (not re-authored)


def test_screen_recipe_bakes_anonymous_and_input_params():
    p = pr.render("screen", {"screens": [
        {"id": "lists", "name": "Lists", "route": "/lists", "default": True},
        {"id": "tasks", "name": "Tasks", "route": "/tasks",
         "input_params": [{"name": "ListId", "references": "TaskList", "isRequired": True}]}]})
    assert "BAKE Anonymous access at creation" in p and "clear all platform Roles" in p   # seam 3d-anon
    assert "change_applied MUST be true" in p                          # seam 3d-phantom gate
    assert '"Lists" at route /lists' in p and "default (home) screen" in p
    assert "ListId (TaskList Identifier, mandatory)" in p             # input param w/ FK type


def test_plan_scaffold_screens_carry_input_params_and_default():
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    scr = next(s for s in steps if s["recipe"] == "screen")["params"]["screens"]
    ids = [s["id"] for s in scr]
    assert "docs" in ids and scr[0]["default"] is True               # first screen defaults to home


def test_plan_scaffolds_but_no_list_or_write_for_bare_spec():
    """Scaffold steps (data-model + screens) are ALWAYS emitted — every app needs its entities
    and screens. But a bare screen with a Container (no data component) and no actions gets no
    list-screen / create-form / role-gate."""
    bare = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [{"name": "E", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
            "screens": [{"id": "s", "name": "S", "components": [{"id": "c", "type": "Container"}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]}}]}
    assert [s["recipe"] for s in pr.plan_from_spec(bare)] == ["data-model", "screen"]
