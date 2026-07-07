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


def test_seed_entity_creates_mechanism_from_scratch_on_fresh_app():
    """Phase-0.1 fix: the seed recipe must NOT assume an existing loader (fresh apps have none —
    it forced a hand-step). It creates LoadSampleData + a WhenPublished timer, empty-guarded."""
    prompt = pr.render("seed-entity", {"entity": "Document", "rows": [
        {"Title": "Q3 Product Planning"}, {"Title": "Onboarding Guide"}]})
    assert "Do NOT assume a sample-data mechanism already exists" in prompt
    assert "server action LoadSampleData" in prompt and "WhenPublished" in prompt
    assert "zero rows" in prompt and "ONLY if empty" in prompt        # empty-guard
    assert "Q3 Product Planning" in prompt
    assert "DETERMINISTIC BOOTSTRAP" not in prompt                    # no bootstrap_screens -> timer only


def test_seed_entity_bootstrap_wires_onready(the=None):
    """Seam B fix: when bootstrap_screens are given, the seed ALSO calls LoadSampleData from those
    screens' OnReady, so seeding does not depend on the flaky WhenPublished timer."""
    prompt = pr.render("seed-entity", {"entity": "Member", "rows": [{"Name": "Rob"}],
                                       "bootstrap_screens": ["login"]})
    assert "DETERMINISTIC BOOTSTRAP" in prompt and "OnReady" in prompt and "login" in prompt


def test_role_gate_looks_up_by_identity_not_id_and_forbids_identifier_change():
    """Seam E: role-gate must look the user up by the identity attr (what login stores), NOT by Id
    (a Text->Id cast makes Mentor 'reconcile' by changing the entity identifier — irreversible)."""
    p = pr.render("role-gate", {"screen": "admin", "user_entity": "Member", "admin_attr": "IsAdmin",
                                "home": "home", "login": "login", "identity_attr": "Name"})
    assert "Member.Name = CurrentUser" in p and "NO cast to the Id" in p
    assert "do NOT change its identifier" in p           # forbid the poison
    assert "ln_current_user" in p


def test_login_and_role_gate_agree_on_identity_session_key():
    """login stores the identity attr in the session key; role-gate reads it — consistent, no Id cast."""
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    lg = next(s for s in steps if s["recipe"] == "login")["params"]
    rg = next(s for s in steps if s["recipe"] == "role-gate")["params"]
    assert lg["identity_attr"] == rg["identity_attr"] == "Name"   # same key both sides
    login_p = pr.render("login", lg)
    assert "do NOT use or change the entity's Id/identifier" in login_p


def test_plan_auth_seed_bootstraps_on_login_screen():
    seed = next(s for s in pr.plan_from_spec(_spec_with_first_class_fields())
                if s["recipe"] == "seed-entity" and s["params"]["entity"] == "Member")
    assert seed["params"].get("bootstrap_screens") == ["login"]      # entry screen for an authed app


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
                {"name": "Name", "dataType": "Text", "mandatory": True},
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
    # seeds the userEntity's identity attr (Name), not a literal "label", so login can match on it
    assert {"Name": "Rob", "IsAdmin": True} in rows and {"Name": "Kira", "IsAdmin": False} in rows


def test_plan_emits_login_step_for_app_local_auth():
    steps = pr.plan_from_spec(_spec_with_first_class_fields())
    lg = next(s for s in steps if s["recipe"] == "login")
    assert lg["params"]["screen"] == "login" and lg["params"]["user_entity"] == "Member"
    assert lg["params"]["identity_attr"] == "Name"
    prompt = pr.render("login", lg["params"])
    assert 'data-spec-id="loginidentityinput"' in prompt and 'data-spec-id="loginbtn"' in prompt
    assert "ln_current_user" in prompt and "ln_current_name" in prompt


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


def test_agent_recipe_binds_trial_model_and_gates_publish():
    p = pr.render("agent", {"agent_name": "HelperAgent", "system_prompt": "You are terse.",
                            "tools": ["LookupOrder"]})
    assert "kind=AIAgent" in p and "BuildMessages" in p and "ICallAgentNode" in p
    assert "You are terse." in p and "AIModelConnection named \"TrialClaudeHaiku4_5\"" in p
    assert "OS-APPS-40028" in p and "ServerRequestTimeout=120" in p
    assert "CreateActionHandler()" in p and "LookupOrder" in p           # tool wiring
    assert "CallHelperAgent" in p                                        # public contract
    assert "AgentAPI" in p and "/rest/AgentAPI/ask" in p                 # invocable REST trigger (gate hits this)


def test_chart_recipe_avoids_listappend_and_uses_aggregate():
    p = pr.render("chart", {"screen": "dashboard", "chart_type": "Column", "category_field": "Week",
                            "series": [{"name": "Income", "value_field": "Income"},
                                       {"name": "Expenses", "value_field": "Expenses"}]})
    assert "OutSystemsCharts" in p and "Charts\\ColumnChart" in p
    assert "NEVER (System).ListAppend" in p and "aggregate" in p.lower()
    assert "OutSystems.Model.Logic.Aggregates" in p                      # ns qualification note


def test_theme_recipe_activates_and_warns_import_stripped():
    p = pr.render("theme", {"css": ".x{color:red}", "font_faces": "@font-face{font-family:Sora}"})
    assert "ACTIVATE" in p and "DefaultMobileTheme" in p                 # inert-until-activated
    assert "@import" in p and "stripped at publish" in p
    assert "same-call read is stale" in p and "@font-face" in p


def test_create_form_recipe_encodes_the_write_path_corrections():
    p = pr.render("create-form", {"screen": "documentDetail", "entity": "Document",
                                  "fields": ["Title", "Content"], "id_param": "DocumentId",
                                  "creator_attr": "CreatorId", "return_screen": "documents"})
    assert "Public=FALSE" in p and "OS-BLD-40409" in p          # non-public server action
    assert "NullIdentifier()" in p                              # create-vs-update branch
    assert "inline record literal" in p                         # typed-local + per-attr, no inline
    assert 'data-spec-id="titleinput"' in p and 'data-spec-id="savedocumentbtn"' in p
    assert "ln_current_user" in p                               # identity for CreatorId


def test_create_form_action_phase_forbids_identifier_change():
    """The action turn (Save<Entity>Record) references the entity heavily; without a guard Mentor
    'reconciles' by re-keying the entity identifier ''->'ID' -> OS-DPL-RDBS-40020, an irreversible
    deploy block. gate_demo (2026-07-06) hit exactly this. Both the action phase and the combined
    prompt must forbid touching the entity identifier (mirrors the Seam E login/role-gate fix)."""
    for params in (
        {"screen": "tasks", "entity": "Task", "fields": ["Title", "Done"], "phase": "action"},
        {"screen": "tasks", "entity": "Task", "fields": ["Title", "Done"]},  # combined
    ):
        p = pr.render("create-form", params)
        assert "OS-DPL-RDBS-40020" in p
        assert "do NOT rename, re-key, add, or change" in p
        assert "touch no entity schema" in p


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
    # seam 3f (revised): action FIRST, then Form+widgets+wire in ONE combined turn (proven-persist shape)
    assert [s["params"]["phase"] for s in wp] == ["action", "combined"]
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
    assert [s["params"]["phase"] for s in wp] == ["action", "combined"]   # seam 3f (revised)
    p = wp[0]["params"]
    assert p["entity"] == "Task"                        # boundTo wins; NOT the TaskList context input
    # seam 3a: the mandatory parent FK Task.ListId must be wired from the screen's ListId input param
    assert p["context_fk"] == {"attr": "ListId", "from_param": "ListId"}
    # seam 3b: no input param references Task itself -> create-only, id_param omitted (not a phantom "TaskId")
    assert "id_param" not in p
    # the COMBINED phase instructs the mandatory parent-FK assignment; the ACTION phase the server action
    combined = pr.render("create-form", {**p, "phase": "combined"})
    assert "NewTask.ListId = the screen's ListId input parameter" in combined
    assert "MANDATORY parent reference" in combined
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
    # R9 / gate_demo2: the identifier must be settled + CONFIRMED this turn (a data-model turn can
    # report success yet silently drop the Id, detonating only at the first write-path).
    assert "CONFIRM it has an Id identifier" in p
    assert "OS-DPL-RDBS-40020" in p
    assert "report each entity's identifier attribute by name" in p


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


def _master_detail_spec():
    return {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [
                {"name": "TaskList", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Title", "dataType": "Text", "mandatory": True}]},
                {"name": "Task", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Title", "dataType": "Text"},
                    {"name": "ListId", "dataType": "Identifier", "mandatory": True, "references": "TaskList"}]}]},
            "screens": [
                {"id": "lists", "name": "Lists",
                 "components": [{"id": "listsTable", "type": "Table", "boundTo": "TaskList"},
                                {"id": "openBtn", "type": "Button", "label": "Open"}],
                 "navigation": [{"fromComponent": "openBtn", "event": "onClick", "toScreen": "tasks",
                                 "params": ["ListId"]}],
                 "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "listsTable"}]}},
                {"id": "tasks", "name": "Tasks",
                 "inputParameters": [{"name": "ListId", "dataType": "Identifier", "references": "TaskList"}],
                 "components": [{"id": "tasksTable", "type": "Table", "boundTo": "Task"}],
                 "actions": [{"name": "CreateTask", "trigger": {"onComponent": "tasksTable", "event": "onClick"},
                              "does": ["CreateEntity"]}],
                 "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tasksTable"}]}}]}


def test_list_screen_emits_spec_nav_component_label(the=None):
    """Seam 3e: the lists list-screen must carry the spec's declared nav button ("Open"/openBtn)
    so the runtime gate's parent-nav finds it, and the rendered prompt authors that labeled link."""
    ls = next(s for s in pr.plan_from_spec(_master_detail_spec())
              if s["recipe"] == "list-screen" and s["params"]["entity"] == "TaskList")
    assert ls["params"]["nav_label"] == "Open" and ls["params"]["nav_component_id"] == "openBtn"
    prompt = pr.render("list-screen", ls["params"])
    assert 'Link with the text "Open"' in prompt and 'data-spec-id="openbtn"' in prompt


def test_plan_seeds_listed_entity_with_no_create_ui():
    """Seam 3g: TaskList is rendered in a list but has no create UI (only Task does), so it can
    never be populated at runtime — the plan must emit a seed-entity step for it."""
    steps = pr.plan_from_spec(_master_detail_spec())
    seeds = [s for s in steps if s["recipe"] == "seed-entity"]
    assert any(s["params"]["entity"] == "TaskList" and s["params"]["rows"] for s in seeds)
    # Task HAS a create write-path -> it is NOT auto-seeded
    assert not any(s["params"]["entity"] == "Task" for s in seeds)


def test_plan_emits_v03_agent_chart_theme_and_sampledata_seed():
    """Phase 1: the v0.3 additive spec fields (agents/charts/design.theme/sampleData) must reach
    their recipes — plan_from_spec emits chart/theme/agent steps and seeds from spec sampleData."""
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["Member"]},
            "dataModel": {"entities": [
                {"name": "Project", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Name", "dataType": "Text", "mandatory": True},
                    {"name": "Priority", "dataType": "Integer", "mandatory": True}],
                 "sampleData": [{"Name": "Website", "Priority": 3}]}]},
            "screens": [{"id": "projects", "name": "Projects",
                         "components": [{"id": "projectsTable", "type": "Table", "boundTo": "Project"}],
                         "charts": [{"id": "priorityChart", "chartType": "Column", "entity": "Project",
                                     "categoryField": "Name", "series": [{"name": "Priority", "valueField": "Priority"}]}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "projectsTable"}]}}],
            "design": {"theme": {"palette": {"primary": "#5E6AD2"}, "css": ".x{}"}},
            "agents": [{"name": "TaskHelperAgent", "systemPrompt": "You help.",
                        "modelConnection": "TrialClaudeHaiku4_5"}]}
    steps = pr.plan_from_spec(spec)
    recipes = [s["recipe"] for s in steps]
    assert "chart" in recipes and "theme" in recipes and "agent" in recipes
    chart = next(s for s in steps if s["recipe"] == "chart")["params"]
    assert chart["chart_type"] == "Column" and chart["category_field"] == "Name" and chart["screen"] == "projects"
    ag = next(s for s in steps if s["recipe"] == "agent")["params"]
    assert ag["agent_name"] == "TaskHelperAgent" and ag["model_connection"] == "TrialClaudeHaiku4_5"
    theme = next(s for s in steps if s["recipe"] == "theme")["params"]
    assert "--primary: #5E6AD2" in theme["css"]
    seed = next(s for s in steps if s["recipe"] == "seed-entity")["params"]
    assert {"Name": "Website", "Priority": 3} in seed["rows"]        # uses spec sampleData, not placeholders


def test_plan_emits_row_actions_for_update_and_delete():
    """Phase 2: a list screen whose action does Update/Delete gets row-actions (Edit/Delete) steps
    in addition to the create-form; the recipe emits the drivable data-spec-ids."""
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [
                {"name": "Task", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Title", "dataType": "Text"}]}]},
            "screens": [{"id": "tasks", "name": "Tasks",
                         "components": [{"id": "tbl", "type": "Table", "boundTo": "Task"}],
                         "actions": [{"name": "SaveTask", "trigger": {"onComponent": "tbl", "event": "onClick"},
                                      "does": ["CreateEntity", "UpdateEntity", "DeleteEntity"]}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tbl"}]}}]}
    steps = pr.plan_from_spec(spec)
    ra = [s for s in steps if s["recipe"] == "row-actions"]
    phases = sorted(s["params"]["phase"] for s in ra)
    assert phases == ["delete", "edit"]                         # both affordances, separate steps
    assert [s for s in steps if s["recipe"] == "create-form"]   # create-form still emitted
    edit = pr.render("row-actions", {"screen": "tasks", "entity": "Task", "phase": "edit"})
    assert 'data-spec-id="edittaskbtn"' in edit and "UpdateAction" in edit
    dele = pr.render("row-actions", {"screen": "tasks", "entity": "Task", "phase": "delete"})
    assert 'data-spec-id="deletetaskbtn"' in dele and "DeleteAction" in dele


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


# ── Phase 4 Batch A: static entity / structure / input validation / exception handling ──

def test_static_entity_recipe_manual_pk_and_explicit_record_ids():
    p = pr.render("static-entity", {"name": "AccountStatus",
                                    "records": [{"Label": "Active"}, {"Label": "Closed", "SortOrder": 2}]})
    assert "CreateStaticEntity" in p and "Public=TRUE" in p
    assert "MANUAL identifier" in p and "auto-number is unsupported for static" in p
    assert "Id=1, Label='Active'" in p and "Id=2, Label='Closed', SortOrder=2" in p
    assert "already exists THROWS" in p          # create-once guard


def test_structure_recipe_has_no_identifier():
    p = pr.render("structure", {"name": "GeocodeResult",
                                "attributes": [{"name": "Lat", "dataType": "Decimal"},
                                               {"name": "Lng", "dataType": "Decimal"}]})
    assert "non-persistent Structure" in p and "has NO identifier" in p
    assert "Lat: Decimal" in p and "Lng: Decimal" in p
    assert "Do NOT create an entity, screen, or UI" in p


def test_input_validation_recipe_short_circuits_before_save():
    p = pr.render("input-validation", {"screen": "signup", "entity": "Member",
                                       "fields": [{"name": "Email", "mandatory": True, "format": "Email"},
                                                  {"name": "Name", "mandatory": True}]})
    assert "BEFORE SaveMemberRecord is called" in p
    assert "SHORT-CIRCUITS" in p and "NEVER persists a row" in p
    assert "NewMember.Email is non-empty" in p and "valid Email" in p
    assert "Valid=False" in p and "mandatory flag" in p


def test_exception_handler_recipe_resolves_warning_by_scope():
    server = pr.render("exception-handler", {"action": "SaveOrderRecord", "scope": "server"})
    assert "AllExceptions" in server and 'No Exception Handling' in server
    assert "Success=False" in server                       # server scope -> output, not feedback
    screen = pr.render("exception-handler", {"action": "DoCheckout", "scope": "screen",
                                             "message": "Checkout failed."})
    assert "'Checkout failed.'" in screen                  # screen scope -> feedback message


def test_plan_emits_batch_a_chain_in_order():
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["User"]},
            "structures": [{"name": "ResultDTO", "attributes": [{"name": "Ok", "dataType": "Boolean"}]}],
            "dataModel": {"entities": [
                {"name": "Status", "isStatic": True,
                 "attributes": [{"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                                {"name": "Label", "dataType": "Text"}],
                 "records": [{"Label": "Active"}, {"Label": "Closed"}]},
                {"name": "Account", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Email", "dataType": "Email", "mandatory": True}]}]},
            "screens": [{"id": "accounts", "name": "Accounts", "route": "/accounts", "isDefault": True,
                         "components": [{"id": "tbl", "type": "Table", "boundTo": "Account"}],
                         "actions": [{"name": "AddAccount",
                                      "trigger": {"onComponent": "tbl", "event": "onClick"},
                                      "does": ["CreateEntity"], "validate": True, "guardExceptions": True}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tbl"}]}}]}
    recipes = [s["recipe"] for s in pr.plan_from_spec(spec)]
    # structures + static entities BEFORE the data model; validation + exception AFTER the create-form
    assert recipes == ["structure", "static-entity", "data-model", "screen", "list-screen",
                       "create-form", "create-form", "input-validation", "exception-handler"]


def test_static_entity_excluded_from_data_model_step():
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [
                {"name": "Status", "isStatic": True, "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True}],
                 "records": [{"Label": "A"}]},
                {"name": "Account", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
            "screens": [{"id": "s", "name": "S", "components": [{"id": "c", "type": "Container"}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]}}]}
    steps = pr.plan_from_spec(spec)
    dm = next(s for s in steps if s["recipe"] == "data-model")
    names = [e["name"] for e in dm["params"]["entities"]]
    assert names == ["Account"]                            # static Status is NOT in the data-model turn
    assert any(s["recipe"] == "static-entity" and s["params"]["name"] == "Status" for s in steps)


def test_validation_and_exception_are_opt_in():
    # a CreateEntity action WITHOUT validate/guardExceptions emits neither extra step
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": [{"name": "Task", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Title", "dataType": "Text"}]}]},
            "screens": [{"id": "tasks", "name": "T", "route": "/tasks",
                         "components": [{"id": "tbl", "type": "Table", "boundTo": "Task"}],
                         "actions": [{"name": "Add", "trigger": {"onComponent": "tbl", "event": "onClick"},
                                      "does": ["CreateEntity"]}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tbl"}]}}]}
    recipes = [s["recipe"] for s in pr.plan_from_spec(spec)]
    assert "input-validation" not in recipes and "exception-handler" not in recipes


def test_create_form_widgets_wrap_in_form_and_carry_phantom_check():
    """batcha wall fix: bare Inputs added directly to the screen phantomed 4×; the persisted shape
    wraps inputs in a Form widget. The widgets phase also carries the positive phantom detector
    (absent 'On Click must be set' error == phantom -> re-author fresh)."""
    p = {"screen": "contacts", "entity": "Contact", "fields": ["Name", "Email"]}
    widgets = pr.render("create-form", {**p, "phase": "widgets"})
    assert 'data-spec-id="contactform"' in widgets            # Form container
    assert "Form container widget" in widgets and "Source record is NewContact" in widgets
    assert "did NOT persist (a phantom" in widgets            # phantom self-check
    assert 'data-spec-id="nameinput"' in widgets and 'data-spec-id="savecontactbtn"' in widgets


def test_create_form_combined_phase_builds_form_and_wires_in_one_turn():
    """The proven-persist recovery shape: Form + inputs + button + OnClick wiring in ONE turn,
    AFTER the server action exists. This is the plan's default second phase now."""
    p = {"screen": "contacts", "entity": "Contact", "fields": ["Name", "Email"]}
    combined = pr.render("create-form", {**p, "phase": "combined"})
    assert "Save ContactRecord".replace(" ", "") in combined.replace(" ", "")  # SaveContactRecord referenced
    assert "ALREADY exists" in combined                       # does NOT re-author the action
    assert 'data-spec-id="contactform"' in combined and 'data-spec-id="savecontactbtn"' in combined
    assert "NewContact.Id = NullIdentifier()" in combined and "RefreshData" in combined


# ── Phase 4 Batch B: service/client/SQL actions, aggregate join, global event, index ──

def test_service_action_is_public_unlike_server_action():
    p = pr.render("service-action", {"name": "GetTotal", "wraps": "ComputeTotal",
                                     "inputs": [{"name": "OrderId", "dataType": "Identifier"}],
                                     "outputs": [{"name": "Total", "dataType": "Decimal"}]})
    assert "Public=TRUE" in p and "OS-BLD-40409" in p          # service action IS the exposed unit
    assert "calls the existing Server Action ComputeTotal" in p
    assert "OrderId (Identifier)" in p and "Total (Decimal)" in p


def test_client_action_is_browser_side():
    p = pr.render("client-action", {"name": "FormatMoney", "purpose": "format a decimal as currency",
                                    "inputs": [{"name": "Amount", "dataType": "Decimal"}]})
    assert "CLIENT-side" in p and "do not touch the database" in p
    assert "format a decimal as currency" in p


def test_sql_action_uses_odc_sql_dialect_and_binds_params():
    p = pr.render("sql-action", {"name": "Recent", "returns": "Order",
                                 "statement": "SELECT {Order}.[Id] FROM {Order} WHERE {Order}.[CustomerId] = @Customer",
                                 "inputs": [{"name": "Customer", "dataType": "Identifier"}]})
    assert "ISQLNode" in p and "{Order}" in p and "[Id]" in p and "@Customer" in p
    assert "CreateInputParameter" in p and "LongIntegerToIdentifier" in p
    assert "output List of Order" in p


def test_aggregate_join_uses_correct_namespace_and_is_additive():
    p = pr.render("aggregate-join", {"screen": "orders", "primary_entity": "Order",
                                     "join_entity": "Customer", "join_attr": "CustomerId",
                                     "display_fields": [{"entity": "Customer", "field": "Name"}]})
    assert "CreateJoin" in p and "CS0234" in p                 # wrong-namespace foot-gun
    assert "Order.CustomerId = Customer.Id" in p and "Customer.Name" in p
    assert "Do NOT rebuild the aggregate" in p


def test_global_event_forbidden_in_workflow_app():
    p = pr.render("global-event", {"name": "OrderPlaced", "payload": [{"name": "OrderId", "dataType": "Identifier"}]})
    assert "CreateGlobalEvent" in p and "THROWS" in p and "OrderId (Identifier)" in p


def test_entity_index_unique_and_add_only():
    uniq = pr.render("entity-index", {"entity": "Order", "attributes": ["Code"], "unique": True})
    assert "UNIQUE index" in uniq and "Order" in uniq and "Code" in uniq
    assert "ONLY add the index" in uniq
    plain = pr.render("entity-index", {"entity": "Order", "attributes": ["CustomerId"]})
    assert "UNIQUE" not in plain


def test_plan_emits_batch_b_constructs_in_order():
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "logic": [{"kind": "serviceAction", "name": "GetX", "outputs": [{"name": "X", "dataType": "Text"}]},
                      {"kind": "sqlAction", "name": "Q1", "statement": "SELECT 1", "inputs": []},
                      {"kind": "globalEvent", "name": "Ev1", "payload": []}],
            "dataModel": {"entities": [
                {"name": "Customer", "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Name", "dataType": "Text"}]},
                {"name": "Order", "indexes": [{"attributes": ["CustomerId"]}],
                 "attributes": [
                     {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                     {"name": "CustomerId", "dataType": "Identifier", "references": "Customer"}]}]},
            "screens": [{"id": "orders", "name": "Orders", "route": "/orders", "isDefault": True,
                         "components": [{"id": "tbl", "type": "Table", "boundTo": "Order"}],
                         "aggregateJoin": {"joinEntity": "Customer", "joinAttr": "CustomerId",
                                           "displayFields": [{"entity": "Customer", "field": "Name"}]},
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tbl"}]}}]}
    recipes = [s["recipe"] for s in pr.plan_from_spec(spec)]
    # entity index emitted right after the data model; aggregate-join right after its list-screen
    assert recipes[0] == "data-model" and recipes[1] == "entity-index"
    assert recipes.index("aggregate-join") == recipes.index("list-screen") + 1
    # logic units emitted last, one per unit
    assert recipes[-3:] == ["service-action", "sql-action", "global-event"]


def test_unknown_logic_kind_is_skipped_not_crashed():
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "logic": [{"kind": "bogusKind", "name": "X"}],
            "dataModel": {"entities": [{"name": "E", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
            "screens": [{"id": "s", "name": "S", "components": [{"id": "c", "type": "Container"}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]}}]}
    recipes = [s["recipe"] for s in pr.plan_from_spec(spec)]
    assert "service-action" not in recipes and recipes == ["data-model", "screen"]


# ── Phase 4 Batch C: workflow (BPT), app-reference (multi-app), external-library ──

def test_workflow_recipe_bakes_one_turn_and_public_service_action():
    p = pr.render("workflow", {"name": "Fulfillment", "trigger_event": "OrderPlaced",
                               "activities": [{"name": "Notify", "calls_service_action": "SendNotice"}]})
    assert "CreateBusinessProcess" in p
    assert "corrupts its verify cache" in p and "before that publish" in p   # the 0-process landmine
    assert "StartProcessOn = the Global Event OrderPlaced" in p and "TriggerMode = Event" in p
    assert "ActionToTrigger is the PUBLIC Service Action SendNotice" in p
    assert "orchestrator publishes the process together with its references" in p


def test_app_reference_recipe_imports_static_and_handles_hidden_stub():
    p = pr.render("app-reference", {"producer_app": "CoreData",
                                    "elements": [{"kind": "Entity", "name": "Customer"},
                                                 {"kind": "StaticEntity", "name": "Status"}]})
    assert "addReferenceToElements" in p and "AddDependency(ParseGlobalKey" in p and "RefreshDependencies" in p
    assert "INCLUDING any STATIC entity" in p                # the hidden-stub cause
    assert "OS-APPS-40028" in p and "TryParseGlobalKey" in p  # the in-session recovery
    assert "Customer (Entity)" in p and "Status (StaticEntity)" in p


def test_external_library_recipe_is_lifecycle_not_a_mentor_turn():
    p = pr.render("external-library", {"name": "PdfUtils", "source": "a .NET 8 helper"})
    assert "NOT a mentor_start turn" in p and "extlib_upload" in p
    assert "GenerationError is TERMINAL" in p and ".NET 8" in p
    assert "ReadyForReview" in p and "HTTP 500" in p          # publish-status gotcha


def test_plan_emits_batch_c_in_order():
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "externalLibraries": [{"name": "PdfUtils"}],
            "appReferences": [{"producerApp": "CoreData", "elements": [{"name": "Customer"}]}],
            "logic": [{"kind": "serviceAction", "name": "SendNotice", "outputs": [{"name": "Ok", "dataType": "Boolean"}]},
                      {"kind": "globalEvent", "name": "OrderPlaced", "payload": []}],
            "processes": [{"name": "Fulfillment", "triggerEvent": "OrderPlaced",
                           "activities": [{"name": "Notify", "callsServiceAction": "SendNotice"}]}],
            "dataModel": {"entities": [{"name": "Order", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
            "screens": [{"id": "s", "name": "S", "components": [{"id": "c", "type": "Container"}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]}}]}
    recipes = [s["recipe"] for s in pr.plan_from_spec(spec)]
    # foundational plumbing FIRST, the process LAST (after its event + service action)
    assert recipes[0] == "external-library" and recipes[1] == "app-reference"
    assert recipes[-1] == "workflow"
    assert recipes.index("workflow") > recipes.index("service-action")
    assert recipes.index("workflow") > recipes.index("global-event")
