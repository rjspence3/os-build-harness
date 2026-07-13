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


def test_nav_block_authors_app_shell_with_tags_badges_sections():
    prompt = pr.render("nav-block", {
        "block_name": "SidebarNav", "brand": "RIVIAN", "subtitle": "Supplier Onboarding",
        "user_label": "R. Spence", "user_role": "Compliance",
        "items": [
            {"label": "Dashboard", "toScreen": "dashboard", "tag": "DSH", "section": "OPERATIONS"},
            {"label": "Case Queue", "toScreen": "queue", "tag": "QUE", "badge": "47", "section": "OPERATIONS"},
            {"label": "Supplier Intake", "toScreen": "intake", "tag": "INT", "section": "SUPPLIER"},
        ]})
    assert '"app-sidebar"' in prompt                       # the dark shell hook
    assert "RIVIAN" in prompt and "Supplier Onboarding" in prompt
    assert '"nav-tag"' in prompt and '"DSH"' in prompt     # mono tag chip
    assert '"nav-badge"' in prompt and '"47"' in prompt    # count badge
    assert '"OPERATIONS"' in prompt and '"SUPPLIER"' in prompt   # section headers
    assert "is-active" in prompt                           # active-item highlight
    assert '"sidebar-user"' in prompt and "Compliance" in prompt


def test_action_button_splits_action_from_wire_atomically():
    """Atomicity: action-button authors ONE button, split into an action turn + a wire turn."""
    act = pr.render("action-button", {"screen": "caseDetail", "entity": "Case", "id_param": "CaseId",
                                       "buttons": [{"label": "Approve Case", "set": {"Status": "APPROVED"}}],
                                       "phase": "action"})
    assert "NON-PUBLIC server action ApplyApproveCase" in act and "UpdateAction" in act
    assert "OS-DPL-50205" in act and 'Button labelled' not in act   # action-only turn, no button here
    wire = pr.render("action-button", {"screen": "caseDetail", "entity": "Case", "id_param": "CaseId",
                                        "buttons": [{"label": "Approve Case", "set": {"Status": "APPROVED"}}],
                                        "phase": "wire"})
    assert 'Button labelled "Approve Case"' in wire and "already exists" in wire and "RefreshData" in wire


def test_plan_action_buttons_are_two_atomic_steps_each():
    spec = _spec_with_first_class_fields()
    spec["screens"][2]["inputParameters"] = [{"name": "DocId", "dataType": "Identifier", "references": "Doc"}]
    spec["screens"][2]["detail"] = {"stages": ["Draft", "Final"],
                                    "stateActions": [{"label": "Publish", "set": {"State": "PUBLISHED"}}]}
    steps = pr.plan_from_spec(spec)
    ab = [s for s in steps if s["recipe"] == "action-button"]
    phases = [s["params"]["phase"] for s in ab]
    assert phases == ["action", "wire"]                       # one button -> action then wire
    assert all(s["weight"] <= pr.MAX_STEP_WEIGHT for s in ab)  # atomic


def test_step_weight_flags_heavy_split_vs_exempt():
    # a splittable heavy step warns; data-model/seed-graph (exempt) get a softer note, never a split warning
    steps = pr.annotate_weights([
        {"recipe": "nav-block", "params": {"items": [{"label": f"n{i}"} for i in range(20)]}},
        {"recipe": "data-model", "params": {"entities": [{"attributes": [{"name": f"a{i}"} for i in range(9)]}
                                                         for _ in range(6)]}},
    ])
    assert steps[0].get("atomicity_warning") and steps[0]["weight"] > pr.MAX_STEP_WEIGHT
    assert steps[1].get("atomicity_note") and not steps[1].get("atomicity_warning")   # exempt: note, not warn


def test_nav_block_is_non_public_and_logout_is_auth_conditional():
    """R11(d): a PUBLIC block with an internal navigation trips OS-DPL-50205 at publish. The app-shell
    nav is internal → author Public=false. A logout link (which navigates) is emitted ONLY when the app
    has a login screen (logout_to) — a no-auth app gets no logout link (no nav to a non-existent Login)."""
    no_auth = pr.render("nav-block", {"items": [{"label": "Home", "toScreen": "home"}]})
    assert "Public=false" in no_auth and "OS-DPL-50205" in no_auth
    assert "Log out" not in no_auth and "localStorage" not in no_auth   # no auth → no logout, no session read
    with_auth = pr.render("nav-block", {"items": [{"label": "Home", "toScreen": "home"}], "logout_to": "login"})
    assert "Log out" in with_auth and "navigates to the login screen" in with_auth
    assert "Public=false" in with_auth                                  # still internal even with auth


def test_list_screen_binds_entity_and_forbids_empty():
    prompt = pr.render("list-screen", {
        "screen": "documents", "entity": "Document",
        "columns": ["Title", "Author", "UpdatedAt"], "detail_screen": "documentDetail"})
    assert "aggregate over the Document entity" in prompt
    assert 'data-entity="Document"' in prompt
    # plain string columns render as per-column text cells (back-compat)
    for field in ("Title", "Author", "UpdatedAt"):
        assert f"`{field}`: a plain text cell showing Document.{field}." in prompt
    assert "documentDetail" in prompt                    # row -> detail nav
    assert "do not leave an empty table" in prompt.lower()


def test_list_screen_authors_styled_product_ui_cells():
    prompt = pr.render("list-screen", {
        "screen": "queue", "entity": "Case", "component_id": "caseTable",
        "columns": [
            {"field": "CaseId", "kind": "identifier"},
            {"field": "Status", "kind": "chip"},
            {"field": "Tier", "kind": "tag"},
            {"field": "Owner", "kind": "avatar"},
            {"field": "State", "kind": "glyph", "glyphSet": "workflow"},
        ]})
    # a status chip is tinted by an EXPRESSION off the row value, not a hardcoded class
    assert '"chip chip-" + ToLower(Case.Status)' in prompt
    assert '"tag tag-" + ToLower(Case.Tier)' in prompt
    assert '"cell-id"' in prompt                         # mono identifier cell
    assert "avatar" in prompt and "Substr(Case.Owner, 0, 2)" in prompt
    assert "glyph glyph-workflow" in prompt and "data-value" in prompt


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
    assert "INDEPENDENT PER-ENTITY GUARD" in prompt                   # not nested under the first entity's guard
    assert "do NOT nest it inside another entity" in prompt
    assert "Q3 Product Planning" in prompt
    assert "DETERMINISTIC BOOTSTRAP" not in prompt                    # no bootstrap_screens -> timer only


def test_seed_entity_bootstrap_wires_onready(the=None):
    """Seam B fix: when bootstrap_screens are given, the seed ALSO calls LoadSampleData from those
    screens' OnReady, so seeding does not depend on the flaky WhenPublished timer."""
    prompt = pr.render("seed-entity", {"entity": "Member", "rows": [{"Name": "Rob"}],
                                       "bootstrap_screens": ["login"]})
    assert "DETERMINISTIC BOOTSTRAP" in prompt and "OnReady" in prompt and "login" in prompt


def test_seed_entity_resolves_fk_refs_by_natural_key(the=None):
    """SEED-A: an FK-heavy child seeds by resolving each parent natural-key reference to a real Id
    (parents seeded first), never writing a dangling FK."""
    prompt = pr.render("seed-entity", {"entity": "Contact", "rows": [{"FullName": "Ada", "SupplierId": "acme"}],
                                        "fk_refs": [{"attr": "SupplierId", "parent": "Supplier", "parent_key": "Code"}]})
    assert "FOREIGN KEYS" in prompt and "PARENTS BEFORE CHILDREN" in prompt
    assert "SupplierId → a Supplier matched on Supplier.Code" in prompt
    assert "NATURAL-KEY reference" in prompt and "take" in prompt and "Id" in prompt
    assert "SKIP that row" in prompt                                   # no dangling FK


def test_plan_seeds_fk_set_as_one_graph_parents_first():
    """SEED-A wiring: an FK-linked seed set becomes ONE seed-graph step (capture-Id-from-create),
    entities in dependency order (parents first), each carrying its natural_key + fk_refs."""
    spec = {
        "specVersion": "0.3", "app": {"name": "fk"},
        "dataModel": {"entities": [
            {"name": "Supplier", "sampleData": [{"Code": "acme", "Name": "Acme"}], "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                {"name": "Code", "dataType": "Text", "naturalKey": True},
                {"name": "Name", "dataType": "Text"}]},
            {"name": "Part", "sampleData": [{"Sku": "p1", "SupplierId": "acme"}], "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                {"name": "Sku", "dataType": "Text"},
                {"name": "SupplierId", "dataType": "Identifier", "references": "Supplier"}]}]},
        "screens": [
            {"id": "parts", "name": "Parts", "isDefault": True, "components": [
                {"id": "partT", "type": "Table", "boundTo": "Part", "columns": [{"field": "Sku", "kind": "text"}]}]},
            {"id": "suppliers", "name": "Suppliers", "components": [
                {"id": "supT", "type": "Table", "boundTo": "Supplier", "columns": [{"field": "Code", "kind": "text"}]}]},
        ]}
    steps = pr.plan_from_spec(spec)
    graph = next(s for s in steps if s["recipe"] == "seed-graph")
    ents = graph["params"]["entities"]
    order = [e["name"] for e in ents]
    assert order.index("Supplier") < order.index("Part")              # parent before child
    part = next(e for e in ents if e["name"] == "Part")
    assert part["fk_refs"] == [{"attr": "SupplierId", "parent": "Supplier", "parent_key": "Code"}]
    supplier = next(e for e in ents if e["name"] == "Supplier")
    assert supplier["fk_refs"] == [] and supplier["natural_key"] == "Code"
    # the rendered prompt captures parent Ids from CreateAction return (no aggregate lookup)
    prompt = pr.render("seed-graph", graph["params"])
    assert "CAPTURE" in prompt and "Supplier_acme_Id" in prompt and "aggregate does not return rows" in prompt.lower()


def test_seed_topo_order_breaks_cycles_deterministically():
    spec = {"dataModel": {"entities": [
        {"name": "A", "attributes": [{"name": "BId", "references": "B"}]},
        {"name": "B", "attributes": [{"name": "AId", "references": "A"}]}]}}
    # a real FK cycle still returns both names (alphabetical remainder), never raises
    assert pr._seed_topo_order(["B", "A"], spec) == ["A", "B"]


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
    # columns now carry their render `kind` (structured) so list_screen authors styled cells
    assert ls["params"]["columns"] == [{"field": "Title", "kind": "text"}]
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


def test_agent_recipe_authors_the_six_action_boilerplate():
    # Ground truth = the stock ABC agent: LoadMemory -> GetGroundingData -> BuildMessages ->
    # [Call Agent widget] -> StoreMemory -> Response, wrapped by a public Call<Name>. All 6 present.
    p = pr.render("agent", {"agent_name": "HelperAgent", "system_prompt": "You are terse.",
                            "grounding": ["Order"], "tools": ["LookupOrder"]})
    assert "kind=AIAgent" in p
    for action in ("LoadMemory", "GetGroundingData", "BuildMessages", "AgentFlow", "StoreMemory"):
        assert action in p
    assert "You are terse." in p and 'AIModelConnection "TrialClaudeHaiku4_5"' in p
    assert "OS-APPS-40028" in p and "ServerRequestTimeout=120" in p
    assert "CallHelperAgent" in p                                        # public consumption contract
    # The LLM is invoked by the native Call Agent widget, NOT a hand-written model call.
    assert "Call Agent" in p and "IS the model invocation" in p
    # REST verification endpoint is ON by default (the gate invokes through it) but labeled dev/strip-for-prod
    assert "AgentAPI" in p and ("AUTH-GATE OR STRIP for production" in p or "VERIFICATION endpoint" in p)


def test_agent_recipe_tools_use_native_action_calling_not_a_manual_loop():
    # The mechanism correction (ABC ground truth): the reasoning loop is NATIVE to the agent runtime,
    # bounded by a Call Condition. The recipe must NOT tell the caller to append tool output and re-call.
    p = pr.render("agent", {"agent_name": "ScreeningAgent", "system_prompt": "Screen suppliers.",
                            "max_loops": 6, "tools": [
                                {"name": "GetScreeningResult",
                                 "description": "Look up denied-party screening for a supplier code.",
                                 "parameters": "SupplierCode (Text)"}]})
    assert "native Action calling" in p
    assert "Do NOT hand-orchestrate" in p                               # the anti-pattern is called out
    assert "Call Condition" in p and "LoopCount >= 6" in p              # native break-when-true bound, false at start
    assert "`<= N` form" in p                                           # the live-proven wrong form is warned against
    assert "Look up denied-party screening" in p                        # tool DESCRIPTION (model chooses by it)
    # the OLD manual-loop language must be gone
    assert "APPEND its output to ChatMessages" not in p and "ToolSelection" not in p


def test_agent_no_tools_has_no_action_calling_block():
    p = pr.render("agent", {"agent_name": "Summarizer", "system_prompt": "Summarize.", "tools": []})
    assert "native Action calling" not in p and "Do NOT hand-orchestrate" not in p  # no tools -> no loop
    assert "Call Agent" in p                                            # still invokes the model natively
    assert "CallSummarizer" in p


def test_agent_rest_endpoint_can_be_stripped_for_production():
    # default: verification REST present (the gate needs it) but flagged for prod hardening
    on = pr.render("agent", {"agent_name": "A", "system_prompt": "x", "tools": ["T"]})
    assert "AgentAPI" in on and "/rest/AgentAPI/ask" in on and "STRIP for production" in on
    # a production build sets expose_rest=False -> no anonymous endpoint
    off = pr.render("agent", {"agent_name": "A", "system_prompt": "x", "tools": ["T"], "expose_rest": False})
    assert "AgentAPI" not in off


def test_chart_recipe_avoids_listappend_and_uses_aggregate():
    p = pr.render("chart", {"screen": "dashboard", "chart_type": "Column", "category_field": "Week",
                            "series": [{"name": "Income", "value_field": "Income"},
                                       {"name": "Expenses", "value_field": "Expenses"}]})
    assert "NEVER (System).ListAppend" in p and "aggregate" in p.lower()
    assert "OutSystems.Model.Logic.Aggregates" in p                      # ns qualification note


def test_chart_recipe_is_native_widget_not_a_reference_block():
    """Harvest chart-native-widget: ODC charts are native toolbox widgets, NOT a referenced
    OutSystemsCharts block (the recipe used the O11 framing). The prompt must forbid the reference."""
    p = pr.render("chart", {"screen": "dashboard", "chart_type": "Column", "category_field": "Week",
                            "series": [{"name": "Income", "value_field": "Income"}]})
    assert "native" in p.lower() and "toolbox" in p.lower()
    assert "do NOT addReferenceToElements" in p
    assert "Charts\\ColumnChart" not in p                                # the O11 framing is gone


def test_chart_recipe_supports_all_seven_odc_types():
    """ODC has exactly 7 chart widgets; the recipe renders each with its per-type note."""
    for t in ("Area", "Bar", "Column", "Line", "Pie", "Donut", "Radar"):
        p = pr.render("chart", {"screen": "s", "chart_type": t, "category_field": "C",
                                "series": [{"name": "V", "value_field": "V"}]})
        assert f"NATIVE {t} Chart" in p
    # single-series types don't set SeriesName; multi-series do
    pie = pr.render("chart", {"screen": "s", "chart_type": "Pie", "category_field": "C",
                              "series": [{"name": "V", "value_field": "V"}]})
    assert "single series" in pie.lower() and "InnerSize" not in pie
    donut = pr.render("chart", {"screen": "s", "chart_type": "Donut", "category_field": "C",
                                "series": [{"name": "V", "value_field": "V"}]})
    assert "InnerSize" in donut
    with pytest.raises(ValueError):
        pr.render("chart", {"screen": "s", "chart_type": "Gauge", "category_field": "C", "series": []})


def test_chart_recipe_advanced_escape_hatch():
    """A non-widget need (gauge/scatter/tooltip) routes through SetHighcharts*Configs."""
    p = pr.render("chart", {"screen": "s", "chart_type": "Line", "category_field": "C",
                            "series": [{"name": "V", "value_field": "V"}],
                            "advanced": "custom tooltip with unit suffix"})
    assert "SetHighcharts" in p and "custom tooltip with unit suffix" in p


def test_top_bar_authors_shell_header_as_shared_block():
    """P0: the app-shell top bar (breadcrumb + env chip + CTA) as a shared block with a Crumb input."""
    p = pr.render("top-bar", {"app_label": "Rivian Onboarding", "env_label": "ODC · PROD",
                              "cta_label": "New request", "cta_screen": "IntakeScreen",
                              "screens": ["CaseQueue", "Dashboard"]})
    assert "app-topbar" in p and "breadcrumb" in p and "env-chip" in p
    assert "Crumb" in p                                   # per-screen breadcrumb input
    assert "Rivian Onboarding" in p and "ODC · PROD" in p
    assert "btn-primary" in p and "New request" in p and "IntakeScreen" in p
    assert "reusable Web Block" in p or "shared" in p.lower()


def test_page_header_composes_title_tag_and_action_row():
    """P0: page header = title + status/tier tag + a right-aligned action-button row (primary/secondary)."""
    p = pr.render("page-header", {"screen": "CaseDetail", "title": "GetCase.Name",
                                  "tag": {"text": "T1 · CRITICAL", "kind": "t1"},
                                  "actions": [{"label": "Approve Case", "action": "ApproveCase", "primary": True},
                                              {"label": "Send Back", "action": "SendBack"}]})
    assert "page-header" in p and "page-title" in p and "header-actions" in p
    assert "tag tag-t1" in p and "T1 · CRITICAL" in p
    assert "btn-primary" in p and "Approve Case" in p and "ApproveCase" in p
    assert "btn-secondary" in p and "Send Back" in p


def test_top_bar_and_page_header_registered():
    assert "top-bar" in pr.RECIPES and "page-header" in pr.RECIPES


def test_theme_recipe_activates_and_warns_import_stripped():
    p = pr.render("theme", {"css": ".x{color:red}", "font_faces": "@font-face{font-family:Sora}"})
    assert "ACTIVATE" in p and "DefaultMobileTheme" in p                 # inert-until-activated
    assert "@import" in p and "stripped at publish" in p
    assert "same-call read is stale" in p and "@font-face" in p


def test_dashboard_recipe_authors_kpi_cards_with_live_counts():
    p = pr.render("dashboard", {"screen": "dash", "columns": 3, "cards": [
        {"label": "Open Cases", "icon": "folder", "entity": "QualificationCase"},
        {"label": "Overdue", "icon": "clock", "entity": "ReviewTask", "filter": "IsOverdue", "trend": "+3"},
        {"label": "Suppliers", "value": "128"}]})
    assert '"kpi-card"' in p and '"kpi-value"' in p and '"kpi-label"' in p
    assert "COUNT of QualificationCase" in p                             # live count, not placeholder
    assert "filtered where IsOverdue" in p and '"kpi-trend"' in p
    assert '"kpi-icon glyph-folder"' in p


def test_detail_recipe_authors_stepper_reviews_and_timeline():
    p = pr.render("detail", {"screen": "caseDetail",
        "stages": [{"label": "Intake", "state": "done"}, {"label": "Screening", "state": "active"}, "Approval"],
        "review_teams": ["Procurement", "Quality", "Engineering"],
        "review_entity": "ReviewTask", "review_state_field": "State",
        "timeline_entity": "AuditEvent", "timeline_fields": ["Description", "CreatedAt"]})
    assert '"stepper"' in p and "step is-done" in p and "step is-active" in p and "step is-pending" in p
    assert '"review-grid"' in p and '"review-card"' in p and "Procurement" in p
    assert '"review-status chip chip-" + ToLower(ReviewTask.State)' in p
    assert '"timeline"' in p and '"timeline-item"' in p and "AuditEvent" in p


def test_plan_emits_dashboard_and_detail_from_screen_fields():
    spec = _spec_with_first_class_fields()
    spec["screens"][0]["dashboard"] = {"cards": [{"label": "Docs", "entity": "Doc"}]}
    spec["screens"][2]["detail"] = {"stages": ["Intake", "Approval"],
                                    "timeline_entity": "AuditEvent"}
    spec["screens"][2]["detail"] = {"stages": ["Intake", "Approval"], "timelineEntity": "AuditEvent"}
    steps = pr.plan_from_spec(spec)
    recipes = [s["recipe"] for s in steps]
    assert "dashboard" in recipes and "detail" in recipes
    det = next(s for s in steps if s["recipe"] == "detail")["params"]
    assert det["timeline_entity"] == "AuditEvent"                        # camelCase -> snake mapping


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
    # default (non-producer): entities stay private — no exposure instruction
    assert "Public property = Yes" not in p


def test_data_model_public_exposes_entities_for_cross_app_read():
    # A producer/Core marks dataModel.public -> entities are exposed Public so consumers can reference
    # + READ them (else the modular producer->consumer data flow is silently empty).
    ents = [{"name": "Supplier", "attributes": [
        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
        {"name": "Code", "dataType": "Text", "mandatory": True}]}]
    pub = pr.render("data-model", {"entities": ents, "public": True})
    assert "Public property = Yes" in pub and "read its data" in pub.lower()
    priv = pr.render("data-model", {"entities": ents})
    assert "Public property = Yes" not in priv                # default stays private (back-compat)


def test_plan_marks_core_datamodel_public():
    # plan_from_spec passes public=True to the data-model step when the spec marks the app a producer.
    from harness.prompt_recipes import plan_from_spec
    spec = {"specVersion": "0.2", "app": {"name": "Core"},
            "dataModel": {"public": True, "entities": [{"name": "Supplier", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Code", "dataType": "Text", "mandatory": True}]}]},
            "screens": []}
    dm = next(s for s in plan_from_spec(spec) if s["recipe"] == "data-model")
    assert dm["params"]["public"] is True


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


def test_headless_core_with_sampledata_gets_bootstrap_screen_and_seed():
    # B2a: a data-owning app (sampleData) with NO screens must get a synthetic bootstrap screen so the
    # seed's OnReady fires — else a headless Core silently ships un-seeded (consumers render empty).
    core = {"specVersion": "0.2", "app": {"name": "Core"},
            "dataModel": {"public": True, "entities": [{"name": "Supplier", "naturalKey": "Code",
                "sampleData": [{"Code": "A", "Name": "X"}], "attributes": [
                    {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    {"name": "Code", "dataType": "Text", "mandatory": True},
                    {"name": "Name", "dataType": "Text", "mandatory": True}]}]},
            "screens": []}
    recipes = [s["recipe"] for s in pr.plan_from_spec(core)]
    assert "screen" in recipes and any("seed" in r for r in recipes)
    # a headless app with NO sampleData stays screenless (safeguard only fires when there's data to seed)
    core_nodata = {"specVersion": "0.2", "app": {"name": "Core"},
                   "dataModel": {"entities": [{"name": "E", "attributes": [
                       {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
                   "screens": []}
    assert "screen" not in [s["recipe"] for s in pr.plan_from_spec(core_nodata)]


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


def test_create_form_edit_screen_prefills_and_updates_in_place():
    """An edit screen (id_param) must PREFILL the form from the existing record and set Id FROM the
    param so Save UpdateActions in place — NOT force NullIdentifier (which opens a blank form and the
    save blanks every field: the partEdit no-prefill defect)."""
    combined = pr.render("create-form", {"screen": "partEdit", "entity": "Part",
                                         "fields": ["Sku", "Name"], "id_param": "PartId", "phase": "combined"})
    assert "GetPartById" in combined and "List.Current" in combined     # prefill aggregate + assign
    assert "NewPart.Id = PartId" in combined and "UpdateAction" in combined  # edit in place
    assert "Assign NewPart.Id = NullIdentifier()" not in combined       # NOT force-create
    # create-only stays force-create with no prefill aggregate (byte-compatible)
    create_only = pr.render("create-form", {"screen": "intake", "entity": "Supplier",
                                            "fields": ["Code"], "phase": "combined"})
    assert "Assign NewSupplier.Id = NullIdentifier()" in create_only
    assert "GetSupplierById" not in create_only


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

def test_workflow_recipe_refs_and_process_in_one_turn():
    # runtime-proven (wfprobe): reference the producer's event + PUBLIC SA AND author the process in ONE turn
    p = pr.render("workflow", {"name": "Fulfillment", "producer_app": "batchb",
                               "trigger_event": "OrderPlaced",
                               "activities": [{"name": "Notify", "calls_service_action": "SendNotice"}]})
    assert "CreateBusinessProcess" in p
    assert "corrupts its verify cache" in p and "NEVER been published" in p   # the 0-process landmine
    assert "Reference the producer app 'batchb'" in p                         # cross-app refs in this turn
    assert "Global Event OrderPlaced" in p and "Service Action(s) SendNotice" in p
    assert "StartProcessOn = the referenced OrderPlaced Global Event" in p and "TriggerMode = Event" in p
    assert "ActionToTrigger is the referenced PUBLIC Service Action SendNotice" in p
    assert "KEEP THE PROCESS MINIMAL" in p                                    # the push-logic-to-Core doctrine
    assert "900s" in p                                                        # the one-turn timeout warning


def test_workflow_recipe_hitl_decision_and_human_activity():
    # HITL shape (live-proven need): one decision on a process variable + one human activity, with the
    # end-and-defer fallback, and the "no nested gateways — branch in a Core action" rule.
    p = pr.render("workflow", {"name": "TicketResolution", "producer_app": "SupportCore",
                               "trigger_event": "TicketSubmitted",
                               "activities": [{"name": "RunTriage", "calls_service_action": "CallTriageAgent"},
                                              {"name": "Handle", "calls_service_action": "PersistProposal"}],
                               "decision": {"on": "RiskTier", "then_activity": "ApproveTask", "else_activity": "End"},
                               "human_activity": {"name": "ApproveTask", "role": "SupportAgent"}})
    assert "Decision node on the process variable 'RiskTier'" in p
    assert "Do NOT add nested/second gateways" in p                          # multi-way branching goes in a Core action
    assert "Human activity 'ApproveTask'" in p and "role 'SupportAgent'" in p
    assert "end-and-defer" in p.lower() or "END that branch" in p            # the fallback when human activity unauthored


def test_workflow_recipe_no_decision_stays_linear():
    p = pr.render("workflow", {"name": "Simple", "producer_app": "Core", "trigger_event": "Ev",
                               "activities": [{"name": "A", "calls_service_action": "DoIt"}]})
    assert "Decision node" not in p and "Human activity" not in p            # linear when no HITL params


def test_workflow_skeleton_is_refs_plus_start_end_only():
    # the non-greedy first turn: refs + Start->End, NO activities (added later, one small turn each)
    p = pr.render("workflow", {"name": "Wf", "producer_app": "Core", "trigger_event": "Ev",
                               "activities": [{"name": "A", "calls_service_action": "DoIt"}], "skeleton": True})
    assert "SKELETON" in p and "wired directly to an End node" in p
    assert "NO activities yet" in p
    assert "an Automatic Activity node 'A'" not in p                         # activities are NOT in the skeleton turn


def test_workflow_add_inserts_one_node_before_end():
    a = pr.render("workflow-add", {"process": "Wf", "kind": "activity", "calls_service_action": "CallAgent"})
    assert "one node" in a.lower() and "immediately BEFORE the End node" in a and "CallAgent" in a
    d = pr.render("workflow-add", {"process": "Wf", "kind": "decision", "on": "RiskTier",
                                   "then_activity": "Approve", "else_activity": "End"})
    assert "Decision node on the process variable 'RiskTier'" in d and "nested/second gateways" in d
    h = pr.render("workflow-add", {"process": "Wf", "kind": "human", "name": "Approve", "role": "Agent"})
    assert "Human activity 'Approve'" in h and "END that branch" in h        # defer fallback


def test_plan_stages_complex_process_into_small_turns():
    # a process with a decision + human is STAGED: skeleton + one workflow-add per activity + decision + human
    spec = {"app": {"name": "Wf"}, "dataModel": {"entities": []}, "screens": [],
            "processes": [{"name": "Res", "producerApp": "Core", "triggerEvent": "Sub",
                           "activities": [{"name": "T", "callsServiceAction": "CallAgent"},
                                          {"name": "H", "callsServiceAction": "Handle"}],
                           "decision": {"on": "NeedsApproval", "then_activity": "Ap", "else_activity": "End"},
                           "humanActivity": {"name": "Ap", "role": "Agent"}}]}
    steps = pr.plan_from_spec(spec)
    wf = [s for s in steps if s["recipe"] in ("workflow", "workflow-add")]
    assert wf[0]["recipe"] == "workflow" and wf[0]["params"].get("skeleton") is True
    adds = [s for s in wf if s["recipe"] == "workflow-add"]
    kinds = [s["params"]["kind"] for s in adds]
    assert kinds == ["activity", "activity", "decision", "human"]           # every node its own small turn


def test_plan_simple_process_stays_one_turn():
    spec = {"app": {"name": "Wf"}, "dataModel": {"entities": []}, "screens": [],
            "processes": [{"name": "Simple", "producerApp": "Core", "triggerEvent": "Sub",
                           "activities": [{"name": "N", "callsServiceAction": "Notify"}]}]}
    steps = pr.plan_from_spec(spec)
    wf = [s for s in steps if s["recipe"].startswith("workflow")]
    assert len(wf) == 1 and wf[0]["recipe"] == "workflow" and not wf[0]["params"].get("skeleton")


def test_app_reference_recipe_imports_static_and_handles_hidden_stub():
    p = pr.render("app-reference", {"producer_app": "CoreData",
                                    "elements": [{"kind": "Entity", "name": "Customer"},
                                                 {"kind": "StaticEntity", "name": "Status"}]})
    assert "addReferenceToElements" in p and "RefreshDependencies" in p
    assert "producerKey*elementKey with an ASTERISK" in p    # ParseGlobalKey colon form is rejected
    assert "do NOT create a local entity with a FOREIGN KEY to a cross-app referenced entity" in p  # OS-DPL-50205 cause
    assert "OS-DPL-50205" in p
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
            "processes": [{"name": "Fulfillment", "producerApp": "batchb", "triggerEvent": "OrderPlaced",
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


# ── T-W4: button fidelity ─────────────────────────────────────────────────────
def _spec_with_declared_button() -> dict:
    """A spec where the CreateSupplier action has trigger.onComponent pointing at
    addSupplierBtn whose label is '+ New Supplier'."""
    return {
        "specVersion": "0.3", "app": {"name": "r", "roles": ["User"]},
        "dataModel": {"entities": [{"name": "Supplier", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
            {"name": "Name", "dataType": "Text", "mandatory": True}]}]},
        "screens": [
            {"id": "intake", "name": "Intake", "route": "/intake",
             "components": [
                 {"id": "addSupplierBtn", "type": "Button", "label": "+ New Supplier"},
                 {"id": "intakeTable", "type": "Table", "boundTo": "Supplier"},
             ],
             "actions": [{"name": "CreateSupplier",
                          "trigger": {"onComponent": "addSupplierBtn", "event": "onClick"},
                          "does": ["CreateEntity"]}]},
        ],
    }


def test_create_form_honors_declared_button():
    """T-W4: create_form with button_id/button_label emits the declared id + label verbatim,
    not the legacy 'Add Supplier' / 'savesupplierBtn'."""
    prompt = pr.render("create-form", {
        "screen": "intake", "entity": "Supplier", "fields": ["Name"],
        "button_id": "addSupplierBtn", "button_label": "+ New Supplier",
        "phase": "combined",
    })
    assert '"addSupplierBtn"' in prompt
    assert '"+ New Supplier"' in prompt
    # Must NOT contain the legacy generated label
    assert "Add Supplier" not in prompt


def test_plan_resolves_button_from_trigger():
    """T-W4 wiring: plan_from_spec resolves the declared button via trigger.onComponent and
    wires button_id + button_label into the create-form params."""
    spec = _spec_with_declared_button()
    steps = pr.plan_from_spec(spec)
    cf_steps = [s for s in steps if s["recipe"] == "create-form"]
    assert cf_steps, "expected create-form steps"
    # All create-form steps for this entity should carry the declared button
    for cf in cf_steps:
        if cf["params"].get("phase") in ("combined", "widgets", "wire", None):
            assert cf["params"].get("button_id") == "addSupplierBtn"
            assert cf["params"].get("button_label") == "+ New Supplier"


def test_create_form_legacy_button_unchanged():
    """T-W4 regression: create_form WITHOUT button_id/button_label falls back to the legacy
    generated id (save<entity>btn) and label (Add <Entity>) — byte-identical to pre-W4."""
    prompt = pr.render("create-form", {
        "screen": "intake", "entity": "Supplier", "fields": ["Name"],
        "phase": "combined",
    })
    assert 'savesupplierBtn' in prompt or 'savesupplier' in prompt
    assert "Add Supplier" in prompt


# ── T-W5b: dashboard split ───────────────────────────────────────────────────
def _spec_with_dashboard_count_cards() -> dict:
    return {
        "specVersion": "0.3", "app": {"name": "d", "roles": ["User"]},
        "dataModel": {"entities": [
            {"name": "Supplier", "sampleData": [{"Name": "A"}, {"Name": "B"}, {"Name": "C"}, {"Name": "D"}],
             "attributes": [{"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                            {"name": "Name", "dataType": "Text"}]},
        ]},
        "screens": [
            {"id": "dashboard", "name": "Dashboard", "route": "/dashboard",
             "dashboard": {"cards": [
                 {"label": "Suppliers", "entity": "Supplier", "icon": "users"},
                 {"label": "Status", "value": "Active"},  # literal-only card
             ]}},
        ],
    }


def test_plan_splits_dashboard_count_into_structure_aggregate_then_bind():
    """T-W5b/W5d: plan_from_spec on a spec with a COUNT card emits THREE dashboard steps —
    structure (author the .kpi-card containers) BEFORE aggregate BEFORE bind. The structure
    phase is the W5d fix: without it the bind turn ('do not add widgets') left the value bare
    (live-proven — DOM had .kpi-value but zero .kpi-card)."""
    spec = _spec_with_dashboard_count_cards()
    steps = pr.plan_from_spec(spec)
    dash_steps = [s for s in steps if s["recipe"] == "dashboard"]
    assert len(dash_steps) == 3, f"expected 3 dashboard steps, got {len(dash_steps)}"
    phases = [s["params"]["phase"] for s in dash_steps]
    assert phases == ["structure", "aggregate", "bind"], phases


def test_theme_includes_outsystemsui_reset():
    """Harvest theme-outsystemsui-reset: every theme stylesheet must PREPEND the reset so the
    UI class contract wins over OutSystemsUI link defaults (live-proven: nav-item's inner <a>
    rendered blue+underline because nothing reset `.nav-item a`)."""
    p = pr.render("theme", {"css": ".x{color:red}"})
    assert ".nav-item a" in p
    assert "color:inherit" in p
    assert "text-decoration:none" in p
    # the design CSS is still present (reset does not replace it)
    assert ".x{color:red}" in p


def test_dashboard_structure_phase_authors_kpi_card_container():
    """Harvest dashboard-kpi-card-structure: the structure phase authors the .kpi-card CONTAINER
    (not a bare value) with a placeholder, so the bind phase has a card to point at."""
    p = pr.render("dashboard", {"screen": "dash", "phase": "structure", "cards": [
        {"label": "Open Cases", "entity": "QualificationCase"},
        {"label": "Suppliers", "entity": "Supplier"}]})
    assert "kpi-card" in p
    assert "kpi-value" in p
    assert "STRUCTURE" in p                 # authors structure only
    assert "no real values" in p.lower() or 'placeholder' in p.lower()
    # explicit: each card MUST be a Container (the live gap was a missing container)
    assert "Container" in p and "without this container" in p.lower()


def test_plan_single_dashboard_step_for_literal_cards():
    """T-W5b regression: a dashboard with ONLY literal cards (no entity/aggregate) keeps the
    legacy single step (no split, no phase key)."""
    spec = {
        "specVersion": "0.3", "app": {"name": "d", "roles": ["User"]},
        "dataModel": {"entities": []},
        "screens": [
            {"id": "dashboard", "name": "Dashboard", "route": "/dashboard",
             "dashboard": {"cards": [
                 {"label": "Version", "value": "2.0"},
                 {"label": "Status", "value": "Active"},
             ]}},
        ],
    }
    steps = pr.plan_from_spec(spec)
    dash_steps = [s for s in steps if s["recipe"] == "dashboard"]
    assert len(dash_steps) == 1
    assert dash_steps[0]["params"].get("phase") is None


# ── T-W5c: kpi_rebind flag ───────────────────────────────────────────────────
def test_kpi_rebind_flag_gates_model_api_step():
    """T-W5c: kpi-rebind is NOT emitted by default; emitted once when
    kpi_model_api_fallback=True, positioned after the bind step."""
    spec = _spec_with_dashboard_count_cards()
    # Default: kpi-rebind absent
    steps_default = pr.plan_from_spec(spec)
    assert not any(s["recipe"] == "kpi-rebind" for s in steps_default)

    # Flag on: kpi-rebind present, AFTER the bind step
    steps_flag = pr.plan_from_spec(spec, kpi_model_api_fallback=True)
    recipes = [s["recipe"] for s in steps_flag]
    assert "kpi-rebind" in recipes
    bind_idx = next(i for i, s in enumerate(steps_flag) if s["recipe"] == "dashboard"
                    and s["params"].get("phase") == "bind")
    rebind_idx = next(i for i, s in enumerate(steps_flag) if s["recipe"] == "kpi-rebind")
    assert rebind_idx > bind_idx

    # kpi-rebind renders a valid prompt
    rebind_step = next(s for s in steps_flag if s["recipe"] == "kpi-rebind")
    prompt = pr.render("kpi-rebind", rebind_step["params"])
    assert "applyModelApiCode" in prompt
    assert "CountSuppliers.Count" in prompt          # per-card name (Count + PascalCase(label))
    assert "data-spec-id" in prompt


def test_dashboard_aggregates_are_uniquely_named_per_card():
    # Regression (OS-BEW-COMP-50008): two cards over the SAME entity must get DISTINCT aggregate names
    # (else two same-named screen aggregates on one screen fail compilation). Name by card label.
    import re
    agg = pr.render("dashboard", {"screen": "dash", "phase": "aggregate", "cards": [
        {"label": "Open Cases", "entity": "QualificationCase"},
        {"label": "Overdue", "entity": "QualificationCase", "filter": 'SlaState = "OVERDUE"'},
        {"label": "Suppliers", "entity": "Supplier"}]})
    names = re.findall(r"aggregate named (\w+)", agg)
    assert len(names) == 3 and len(set(names)) == 3     # all distinct — no CountQualificationCase collision
    # the bind phase must reference the SAME per-card names
    bind = pr.render("dashboard", {"screen": "dash", "phase": "bind", "cards": [
        {"label": "Open Cases", "entity": "QualificationCase"},
        {"label": "Overdue", "entity": "QualificationCase", "filter": 'SlaState = "OVERDUE"'}]})
    assert "CountOpenCases.Count" in bind and "CountOverdue.Count" in bind


# ── G1: workflow-engine ───────────────────────────────────────────────────────

def test_G1a_workflow_engine_defaults():
    """T-G1a: render with no params; check all default-action names + doctrine substrings."""
    p = pr.render("workflow-engine", {})
    assert "WorkflowEngineCore" in p
    # Default 4 actions
    for name in ["ResolveScenario", "InstantiateWorkflow", "AdvanceInstance", "CompleteTask"]:
        assert name in p
    assert "OS-DPL-50205" in p
    assert "AdvanceInstance->AdvanceInternal" in p
    assert "N-invariant" in p
    assert "off-by-one" in p
    assert "co-locate" in p
    assert "do not publish" in p.lower()


def test_G1b_workflow_engine_custom_entities():
    """T-G1b: custom entities override; defaults fill in the rest."""
    p = pr.render("workflow-engine", {
        "entities": {"scenario": "Flow", "transition_rule": "Rule", "task_instance": "Unit"}
    })
    assert "Flow" in p
    assert "Rule" in p
    assert "Unit" in p
    # These roles weren't overridden — defaults apply
    assert "TaskTemplate" in p
    assert "AuditEvent" in p


def test_G1c_workflow_engine_subset_and_chunk():
    """T-G1c: ClaimTask only; chunk warning when full set; Bogus filtered; empty no crash."""
    # ClaimTask only: present + wipes-unset-columns + fetch; off-by-one NOT needed
    p_claim = pr.render("workflow-engine", {"actions": ["ClaimTask"]})
    assert "ClaimTask" in p_claim
    assert "wipes unset columns" in p_claim
    assert "fetch" in p_claim.lower()
    assert "off-by-one" not in p_claim
    assert "OS-DPL-50205" in p_claim
    assert "co-locate" in p_claim

    # Full set: all 8 names + 900s chunk warning + doctrine substrings
    p_full = pr.render("workflow-engine", {"actions": pr._ENGINE_ACTIONS})
    for name in pr._ENGINE_ACTIONS:
        assert name in p_full
    assert "900s" in p_full
    assert "no orphan" in p_full
    assert "never invents a task" in p_full
    assert "nothing runs unvalidated" in p_full

    # Unknown action filtered; known one present
    p_mixed = pr.render("workflow-engine", {"actions": ["ClaimTask", "Bogus"]})
    assert "ClaimTask" in p_mixed
    assert "Bogus" not in p_mixed

    # Empty list: OS-DPL-50205 still emitted, no crash
    p_empty = pr.render("workflow-engine", {"actions": []})
    assert "OS-DPL-50205" in p_empty


# ── G2: dynamic-form ─────────────────────────────────────────────────────────

def test_G2a_dynamic_form_defaults():
    """T-G2a: render with no params; all doctrine substrings present."""
    p = pr.render("dynamic-form", {})
    assert "SPIKE" in p
    assert "FieldDefinition" in p
    assert "no dynamic widget" in p
    assert "Switch" in p
    for ft in ["text", "textarea", "number", "date", "select", "checkbox"]:
        assert ft in p
    assert "InputData" in p
    assert "OutputData" in p
    assert "CompleteTask" in p
    assert "TransitionRule.Condition" in p
    assert "Structure" in p
    assert "cannot live in a BPT app" in p
    assert "first '{'" in p
    assert "last '}'" in p
    assert "data-spec-id" in p
    assert "Anonymous" in p
    assert "do not publish" in p.lower()


def test_G2b_dynamic_form_custom_entities_and_types():
    """T-G2b: custom entities, field_types subset, custom complete_action."""
    p = pr.render("dynamic-form", {
        "entities": {"task_template": "WorkTemplate", "task_instance": "WorkItem"},
        "field_types": ["text", "select"],
        "complete_action": "FinishTask",
    })
    assert "WorkTemplate" in p
    assert "FieldDefinition" in p   # attribute name stays constant
    assert "WorkItem" in p
    assert "FinishTask" in p
    assert "text" in p
    assert "select" in p
    assert "textarea" not in p
    assert "checkbox" not in p


def test_G2c_dynamic_form_live_proven_parse_gotchas():
    """The dynamic-form recipe must carry the ODC parse mechanics learned by hand-building the live
    demo: reserved-word FType, case-sensitive JSONDeserialize + key normalization, the FormField
    structure shape, and the select->text fallback. Omitting any reproduces a live bug."""
    p = pr.render("dynamic-form", {})
    # reserved word + structure shape
    assert "FType" in p and "'Type' is a reserved word" in p
    assert "FormField" in p
    assert "Required (Boolean)" in p and "Options (List of Text)" in p
    # case-sensitive deserialize + normalization of the JSON property names
    assert "CASE-SENSITIVE" in p
    assert "normali" in p.lower()          # NORMALIZED / normalize
    assert "Replace()" in p
    assert '-> "Label":' in p              # the concrete key-normalization mapping
    assert "empty-label" in p
    # select fallback limitation
    assert "SELECT LIMITATION" in p and "text Input" in p
    # the parse driver + submit serialization
    assert "LoadActiveForm" in p and "JSONSerialize" in p
    # serialization false-positive: Options leak into OutputData -> match "Value":"X", not bare token
    assert "SERIALIZATION CAVEAT" in p
    assert '"Value":"Reject"' in p


def test_G1d_workflow_engine_frontier_not_a_count():
    """The workflow-engine recipe must warn NEVER to advance by counting completed tasks (the live
    over-advance bug on a rework/loop-back), and must describe the reject->rework routing."""
    p = pr.render("workflow-engine", {"actions": ["AdvanceInstance", "CompleteTask"]})
    assert "FRONTIER" in p
    assert "over-advance" in p
    assert "COUNTING" in p                 # never pick the next step by counting done tasks
    assert "rework" in p and "loop-back" in p
    # CompleteTask carries the approval-reject routing
    assert "Reject" in p and "does NOT mark the instance Completed" in p
    # reject detection must match the VALUE, not a bare token (Options leak "Reject" into OutputData)
    assert "DETECT THE VALUE" in p and '"Value":"Reject"' in p
    assert "Sequence+1" in p               # concrete linear frontier fallback


def test_agent_recipe_carries_cold_start_timeout_caveat():
    """The agent recipe must warn about the 10s client-side cold-start timeout when a screen invokes
    an agent synchronously (live-proven OS-CLRT-60900)."""
    p = pr.render("agent", {"agent_name": "TriageAgent", "system_prompt": "You triage tickets."})
    assert "OS-CLRT-60900" in p
    assert "10s" in p
    assert "cold" in p.lower()


def test_G2c_dynamic_form_role_gate():
    """T-G2c: role_gate default -> ln_current_user present; False -> absent, Anonymous still present."""
    p_default = pr.render("dynamic-form", {})
    assert "ln_current_user" in p_default

    p_no_gate = pr.render("dynamic-form", {"role_gate": False})
    assert "ln_current_user" not in p_no_gate
    assert "Anonymous" in p_no_gate


# ── G3: library-import ────────────────────────────────────────────────────────

def test_G3a_library_import_seed_defaults():
    """T-G3a: seed mode defaults — all doctrine substrings present."""
    p = pr.render("library-import", {})
    assert "LoadLibrary" in p
    assert "NON-PUBLIC" in p
    assert "OS-DPL-50205" in p
    assert "FK order" in p
    # All 5 default entities present in FK order
    entities = ["TaskTemplate", "Scenario", "ScenarioStep", "TransitionRule", "DecisionRow"]
    for e in entities:
        assert e in p
    # FK order: each entity appears before the next in the string
    positions = [p.index(e) for e in entities]
    assert positions == sorted(positions)
    assert "DELETE-then-INSERT" in p
    # ODC has NO IsInDevStage(): the recipe must gate on a Confirm input param and warn
    # against the phantom stage built-in (live-proven publish failure OS-DPL-50205).
    assert "Confirm" in p
    assert "IsInDevStage" in p  # present only as the negative caveat
    assert "OnReady" in p
    assert "headless" in p.lower()
    assert "do not publish" in p.lower()


def test_G3b_library_import_etl():
    """T-G3b: etl mode doctrine substrings."""
    p = pr.render("library-import", {"mode": "etl"})
    assert "REST" in p
    assert "natural-key upsert" in p
    assert "Code" in p
    assert "fetch" in p.lower()
    assert "wipes unset columns" in p
    assert "FK order" in p
    assert "DELETE-then-INSERT" not in p


def test_G3c_library_import_etl_custom():
    """T-G3c: etl with custom natural_key and library_entities subset."""
    p = pr.render("library-import", {
        "mode": "etl",
        "natural_key": "ExternalId",
        "library_entities": ["Scenario", "DecisionRow"],
    })
    assert "ExternalId" in p
    assert "Scenario" in p
    assert "DecisionRow" in p
    assert "TaskTemplate" not in p


def test_G3d_library_import_bogus_mode_raises():
    """T-G3d: unknown mode raises ValueError."""
    import pytest
    with pytest.raises(ValueError):
        pr.render("library-import", {"mode": "bogus"})


# ── emitter unit tests (plan_from_spec -> workflow-engine / dynamic-form / library-import) ──────

def _engine_spec(actions, entities=None, core_app="WorkflowCore", extra_logic=None):
    """Helper: build a minimal spec with an engine block and optional logic units."""
    spec = {
        "specVersion": "0.2",
        "app": {"name": core_app, "roles": ["User"]},
        "dataModel": {"entities": []},
        "screens": [],
        "engine": {"coreApp": core_app, "actions": actions,
                   "entities": entities or {"task_template": "TaskTemplate",
                                            "task_instance": "TaskInstance"}},
    }
    if extra_logic:
        spec["logic"] = extra_logic
    return spec


def test_emitter_workflow_engine_chunks_le_4_and_cover_all():
    """The full engine action set chunks into ceil(N/4) steps, each len<=4, concatenating back
    to _ENGINE_ACTIONS in canonical order (turn-size doctrine D6)."""
    import math
    from harness.prompt_recipes import _ENGINE_ACTIONS
    spec = _engine_spec(_ENGINE_ACTIONS)
    steps = pr.plan_from_spec(spec)
    wf = [s for s in steps if s["recipe"] == "workflow-engine"]
    expected_chunks = math.ceil(len(_ENGINE_ACTIONS) / 4)
    assert len(wf) == expected_chunks, f"expected {expected_chunks} chunks, got {len(wf)}"
    for s in wf:
        assert len(s["params"]["actions"]) <= 4
    concatenated = [a for s in wf for a in s["params"]["actions"]]
    assert concatenated == _ENGINE_ACTIONS
    assert wf[0]["params"]["actions"] == _ENGINE_ACTIONS[:4]


def test_emitter_workflow_engine_core_app_and_entities_passthrough():
    """core_app and entities are passed to each chunk unchanged."""
    from harness.prompt_recipes import _ENGINE_ACTIONS
    entities = {"task_template": "TaskTemplate", "task_instance": "TaskInstance"}
    spec = _engine_spec(_ENGINE_ACTIONS, entities=entities, core_app="MyCore")
    steps = pr.plan_from_spec(spec)
    for s in [s for s in steps if s["recipe"] == "workflow-engine"]:
        assert s["params"]["core_app"] == "MyCore"
        assert s["params"]["entities"] == entities


def test_emitter_workflow_engine_renders_each_chunk():
    """Each chunk renders (no exception) and mentions the core_app."""
    from harness.prompt_recipes import _ENGINE_ACTIONS
    spec = _engine_spec(_ENGINE_ACTIONS, core_app="WorkflowCore")
    for s in [s for s in pr.plan_from_spec(spec) if s["recipe"] == "workflow-engine"]:
        prompt = pr.render("workflow-engine", s["params"])
        assert "WorkflowCore" in prompt


def test_emitter_no_engine_block_produces_no_workflow_engine_step():
    """A spec without an engine block produces no workflow-engine step."""
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": []}, "screens": []}
    assert not [s for s in pr.plan_from_spec(spec) if s["recipe"] == "workflow-engine"]


def test_emitter_engine_dedupe_removes_engine_names_from_logic():
    """D4: a serviceAction in logic whose name is in engine.actions is skipped; non-engine SAs stay."""
    from harness.prompt_recipes import _ENGINE_ACTIONS
    spec = _engine_spec(
        [_ENGINE_ACTIONS[0]],  # e.g. "ResolveScenario"
        extra_logic=[
            {"kind": "serviceAction", "name": _ENGINE_ACTIONS[0]},   # same name -> dedupe
            {"kind": "serviceAction", "name": "SaveLibraryElement"},  # non-engine -> keep
            {"kind": "serviceAction", "name": "SubmitIntake"},        # non-engine -> keep
        ]
    )
    steps = pr.plan_from_spec(spec)
    service_actions = [s["params"]["name"] for s in steps if s["recipe"] == "service-action"]
    assert _ENGINE_ACTIONS[0] not in service_actions, "engine action should be deduped from logic"
    assert "SaveLibraryElement" in service_actions
    assert "SubmitIntake" in service_actions
    assert len([s for s in steps if s["recipe"] == "workflow-engine"]) == 1


def test_emitter_non_engine_core_logic_unchanged():
    """A non-engine Core's logic serviceActions are emitted unchanged (no engine block)."""
    spec = {"specVersion": "0.2", "app": {"name": "OrderingCore", "roles": ["User"]},
            "dataModel": {"entities": []}, "screens": [],
            "logic": [{"kind": "serviceAction", "name": "PlaceOrder"},
                      {"kind": "globalEvent", "name": "OrderPlaced"}]}
    steps = pr.plan_from_spec(spec)
    sa_names = [s["params"]["name"] for s in steps if s["recipe"] == "service-action"]
    assert "PlaceOrder" in sa_names
    ev_names = [s["params"]["name"] for s in steps if s["recipe"] == "global-event"]
    assert "OrderPlaced" in ev_names


def test_emitter_dynamic_form_from_screen_field():
    """A screen with dynamicForm -> 1 dynamic-form step with correct entities/complete_action."""
    spec = {"specVersion": "0.2", "app": {"name": "WorkerApp", "roles": ["Worker"]},
            "dataModel": {"entities": []},
            "screens": [{
                "id": "mywork", "name": "MyWork",
                "components": [{"id": "c1", "type": "Label", "label": "x"}],
                "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c1"}]},
                "dynamicForm": {"taskInstance": "TaskInstance", "taskTemplate": "TaskTemplate",
                                "completeAction": "CompleteTask"}
            }]}
    steps = pr.plan_from_spec(spec)
    df = [s for s in steps if s["recipe"] == "dynamic-form"]
    assert len(df) == 1
    p = df[0]["params"]
    assert p["entities"] == {"task_template": "TaskTemplate", "task_instance": "TaskInstance"}
    assert p["complete_action"] == "CompleteTask"
    assert p["screen"] == "MyWork"


def test_emitter_dynamic_form_renders():
    """dynamic-form step renders without exception."""
    params = {"block_name": "DynamicTaskForm", "screen": "MyWork",
              "entities": {"task_template": "TaskTemplate", "task_instance": "TaskInstance"},
              "complete_action": "CompleteTask"}
    prompt = pr.render("dynamic-form", params)
    assert "DynamicTaskForm" in prompt and "TaskTemplate" in prompt


def test_emitter_no_dynamic_form_field_produces_no_step():
    """A screen without dynamicForm produces no dynamic-form step."""
    spec = {"specVersion": "0.2", "app": {"name": "WorkerApp", "roles": ["W"]},
            "dataModel": {"entities": []},
            "screens": [{"id": "home", "name": "Home",
                         "components": [{"id": "c", "type": "Label", "label": "x"}],
                         "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]}}]}
    assert not [s for s in pr.plan_from_spec(spec) if s["recipe"] == "dynamic-form"]


def test_emitter_library_import_seed_default():
    """libraryImport block -> 1 library-import step, mode seed, FK-ordered entities, renders."""
    lib_ents = ["TaskTemplate", "Scenario", "ScenarioStep", "TransitionRule", "DecisionRow"]
    spec = {"specVersion": "0.2", "app": {"name": "WorkflowCore", "roles": ["User"]},
            "dataModel": {"entities": []}, "screens": [],
            "libraryImport": {"mode": "seed", "libraryEntities": lib_ents}}
    steps = pr.plan_from_spec(spec)
    li = [s for s in steps if s["recipe"] == "library-import"]
    assert len(li) == 1
    p = li[0]["params"]
    assert p["mode"] == "seed"
    assert p["library_entities"] == lib_ents
    prompt = pr.render("library-import", p)
    assert "seed" in prompt.lower() and "TaskTemplate" in prompt


def test_emitter_no_library_import_produces_no_step():
    """A spec without libraryImport produces no library-import step."""
    spec = {"specVersion": "0.2", "app": {"name": "t", "roles": ["U"]},
            "dataModel": {"entities": []}, "screens": []}
    assert not [s for s in pr.plan_from_spec(spec) if s["recipe"] == "library-import"]


# ── T-REG: registry checks ────────────────────────────────────────────────────

def test_REG_new_recipes_in_registry(capsys):
    """T-REG: all three new names in RECIPES; each renders with 'do not publish'; --list shows all."""
    for name in ("workflow-engine", "dynamic-form", "library-import"):
        assert name in pr.RECIPES, f"{name!r} missing from RECIPES"
        p = pr.render(name, {})
        assert "do not publish" in p.lower(), f"{name!r} missing 'do not publish'"

    prompt_step.main(["--list"])
    out = capsys.readouterr().out
    for name in ("workflow-engine", "dynamic-form", "library-import"):
        assert name in out, f"{name!r} missing from --list output"


def test_list_and_detail_cells_forbid_structure_drop():
    """P0 harden (harvest #2 class): chip cells and review cards must FORCE the Container, or the
    value renders bare. The recipe prompts must say so explicitly."""
    ls = pr.render("list-screen", {"screen": "queue", "entity": "Case", "component_id": "casetbl",
                                   "columns": [{"field": "Status", "kind": "chip"}]})
    assert "Container is REQUIRED" in ls and "structure-drop" in ls
    det = pr.render("detail", {"screen": "CaseDetail", "stages": ["Intake", "Review"],
                               "review_teams": ["Procurement", "Quality"]})
    assert "MUST be its own Container" in det and "review-card" in det
