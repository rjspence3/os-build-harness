"""harness prompt-recipe catalog — fully-formed, pre-corrected Mentor prompts.

Each recipe turns a small param dict into ONE complete NL prompt that authors a
common build unit correctly the FIRST time — every known correction from live
builds is pre-applied, so the retry-factor stays near zero (harness doctrine
"Throughput": fix the PROMPT, not the artifact). Recipes are pure `params -> str`
functions (deterministic, unit-testable without an MCP), rendered by
`harness-prompt-step` and fed to `mentor_start`.

Cross-cutting corrections baked into EVERY recipe (via `_preamble`):
  * one concern per turn; author, then a SEPARATE cleanup turn (combined
    create+cleanup instructions cascade-hang) — so each recipe is one unit.
  * emit `data-spec-id="<componentId>"` (+ `data-entity`, `data-row-id`) on
    rendered widgets so `harness-capture` resolves them EXACTLY at runtime.
  * never add a platform Role unless explicitly building auth; keep screens
    Anonymous (a stray role breaks localStorage-auth apps).
  * validate before publish; verify at runtime, not by Mentor's self-report.
"""
from __future__ import annotations

_PREAMBLE = (
    "You are authoring ONE build unit into an OutSystems app via the Model API. Do exactly this unit and "
    "nothing else; do not refactor unrelated screens. On every rendered widget you create, set an HTML "
    "attribute data-spec-id=\"<the component id below>\" (OutSystems widget Attributes: Name=data-spec-id, "
    "Value=the id) so runtime verification can resolve it exactly; for a data table/list also set "
    "data-entity=\"<EntityName>\" on the container and data-row-id on each row. Do NOT add any platform Role "
    "to a screen unless this unit is explicitly about auth — keep screens Anonymous. After authoring, run the "
    "model validation and report errors/warnings; do NOT publish (the orchestrator publishes)."
)


def _p(params: dict, key: str, default=None, required: bool = False):
    if required and key not in params:
        raise ValueError(f"recipe missing required param: {key!r}")
    return params.get(key, default)


# ── recipes ──────────────────────────────────────────────────────────────────
def nav_block(params: dict) -> str:
    """Author the app's persistent navigation ONCE as a reusable Web Block.
    params: block_name, items:[{label,toScreen}], logout_to(login screen), workspace_label?"""
    block = _p(params, "block_name", "SidebarNav")
    items = _p(params, "items", [], required=True)
    logout_to = _p(params, "logout_to", "Login")
    workspace = _p(params, "workspace_label", "")
    lines = "\n".join(f"   - a link labelled exactly \"{i['label']}\" navigating to the {i['toScreen']} screen"
                      for i in items)
    ws = f" a workspace header showing \"{workspace}\"," if workspace else ""
    return (
        f"{_PREAMBLE}\n\n"
        f"Create ONE reusable Web Block named {block} that renders the app's persistent left navigation, so "
        f"every screen references this single block instead of re-authoring the nav. The block contains, in order:"
        f"{ws}\n{lines}\n"
        f"   - a \"Log out\" link that clears the session (localStorage keys ln_current_user + ln_current_name) "
        f"and navigates to the {logout_to} screen.\n"
        f"CRITICAL: each link must be a single link whose displayed text is EXACTLY its label and nothing else — "
        f"OutSystems gives a new Link widget a default literal \"link\" Text widget; DELETE that literal \"link\" "
        f"ITextWidget from each link so it does not render \"linkInbox\"-style prefixes (a scan of Expression "
        f"children alone looks clean and misses it — find and remove the literal-text widget). Set "
        f"data-spec-id on each link = its toScreen id. Do not fan this nav out per screen; this block IS the nav."
    )


def list_screen(params: dict) -> str:
    """Bind a screen's data list/table to an entity so it renders real rows.
    params: screen, entity, columns:[str], sort_by?, join?, detail_screen?, component_id?"""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    columns = _p(params, "columns", [], required=True)
    cid = _p(params, "component_id", f"{entity.lower()}Table")
    sort_by = _p(params, "sort_by")
    join = _p(params, "join")
    detail = _p(params, "detail_screen")
    cols = ", ".join(columns)
    sort_txt = f" sorted by {sort_by}" if sort_by else ""
    join_txt = (f" Join to {join} so its display fields resolve (use an explicit join in the aggregate, "
                f"never a second data source).") if join else ""
    detail_txt = (f" Each row links to the {detail} screen passing the record's Id.") if detail else ""
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {screen} screen, add a screen aggregate over the {entity} entity{sort_txt} (pin the aggregate "
        f"name so it is not auto-renamed).{join_txt} Add a Table with component id {cid} (set data-spec-id="
        f"\"{cid}\" and data-entity=\"{entity}\" on it) bound to that aggregate, with columns: {cols}. Put it in "
        f"the screen's content area (to the right of the nav).{detail_txt} The table must render the real rows — "
        f"if it comes up empty, the aggregate binding is wrong; fix it, do not leave an empty table."
    )


def role_gate(params: dict) -> str:
    """App-local Admin gate for a screen (no platform role / no end-user IdP).
    params: screen, user_entity(default Member), admin_attr(default IsAdmin), home(default Issues), login(default Login)"""
    screen = _p(params, "screen", required=True)
    user_entity = _p(params, "user_entity", "Member")
    admin_attr = _p(params, "admin_attr", "IsAdmin")
    home = _p(params, "home", "Issues")
    login = _p(params, "login", "Login")
    return (
        f"{_PREAMBLE}\n\n"
        f"Add app-local access control to the {screen} screen so only Admin users can view it. IMPORTANT: do NOT "
        f"add any platform Role to the screen — keep it Anonymous exactly like the other screens; a platform role "
        f"breaks this app's localStorage-based identity. Add an On Ready screen action that runs in order:\n"
        f"1. A JavaScript node reading localStorage: OutUserId = localStorage.getItem('ln_current_user')||''; "
        f"OutName = localStorage.getItem('ln_current_name')||''.\n"
        f"2. An Assign copying those into Text locals CurrentUserId, CurrentUserName.\n"
        f"3. An If: when CurrentUserId = \"\" -> Destination {login}.\n"
        f"4. An Aggregate fetching the single {user_entity} where Id = the parsed CurrentUserId "
        f"(cast Text->identifier), refreshed after CurrentUserId is set.\n"
        f"5. An If: when that {user_entity}'s {admin_attr} is False -> Destination {home}.\n"
        f"So: logged-out -> {login}, non-admin -> {home}, admin -> through. Seed at least one Admin and one "
        f"non-admin test user so the gate is exercisable. Verify all three paths at runtime."
    )


def seed_entity(params: dict) -> str:
    """Seed sample rows for an entity via the app's LoadSampleData orchestrator.
    params: entity, rows:[{...}] (or count+describe), fk_notes?"""
    entity = _p(params, "entity", required=True)
    rows = _p(params, "rows", [], required=True)
    fk_notes = _p(params, "fk_notes", "")
    rows_txt = "\n".join(f"   - {json_1line(r)}" for r in rows)
    fk_txt = f" {fk_notes}" if fk_notes else ""
    return (
        f"{_PREAMBLE}\n\n"
        f"Populate the {entity} entity with sample data using the app's EXISTING sample-data mechanism — find the "
        f"loader that seeds the other entities (a LoadSampleData orchestrator calling per-entity "
        f"LoadSampleDataFor<X> actions, run by a timer on publish) and add a LoadSampleDataFor{entity} action in "
        f"the same Assign->Create<Entity> style, wired into the orchestrator. Create these rows (set FKs to "
        f"existing referenced rows so they resolve):{fk_txt}\n{rows_txt}\n"
        f"This is a DATA-ONLY unit — do not touch any screen UI. Note: LoadSampleData often runs once on first "
        f"publish; if the rows do not appear after publish, the run-once guard blocked it — clear the guard or "
        f"delete+re-run so the {entity} rows actually insert. Verify the rows exist at runtime."
    )


def json_1line(obj) -> str:
    import json
    return json.dumps(obj, separators=(", ", "="))


RECIPES = {
    "nav-block": nav_block,
    "list-screen": list_screen,
    "role-gate": role_gate,
    "seed-entity": seed_entity,
}


def render(name: str, params: dict) -> str:
    if name not in RECIPES:
        raise KeyError(f"unknown recipe {name!r}; known: {', '.join(sorted(RECIPES))}")
    return RECIPES[name](params or {})
