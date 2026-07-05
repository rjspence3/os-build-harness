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


def create_form(params: dict) -> str:
    """Wire a WORKING create/edit form for an entity — the write-path (Phase 6, the
    definition of done). Encodes every correction a hand-authored create turn needs
    (extracted from the linear Documents write-path seam report).
    params: screen, entity, fields:[attr], return_screen?, id_param?, creator_attr?"""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    fields = _p(params, "fields", [], required=True)
    ret = _p(params, "return_screen")
    id_param = _p(params, "id_param")              # None => create-only screen (no own-record id input)
    ctx = _p(params, "context_fk")                 # {"attr","from_param"} mandatory parent FK from a screen param
    creator = _p(params, "creator_attr")           # e.g. CreatorId — set from session identity
    flist = ", ".join(fields)
    inputs = "; ".join(f'an Input bound to {entity}.{f} (data-spec-id="{f.lower()}input")' for f in fields)
    creator_txt = (
        f" Set {entity}.{creator} from the logged-in user: read localStorage 'ln_current_user' via a JavaScript "
        f"node and Assign {creator} = LongIntegerToIdentifier(TextToLongInteger(thatValue))."
        if creator else "")
    context_txt = (
        f" Set {entity}.{ctx['attr']} = the screen's {ctx['from_param']} input parameter — a MANDATORY parent "
        f"reference the record CANNOT be saved without; it arrives via navigation from the parent list "
        f"(cast with LongIntegerToIdentifier(TextToLongInteger(...)) if needed)."
        if ctx else "")
    if id_param:
        recv_txt = (f"The screen receives a {id_param} input ({id_param} = a null/empty identifier means CREATE "
                    f"a new record; a real id means EDIT that one).")
        id_set_txt = f"sets its Id from {id_param} (use LongIntegerToIdentifier(TextToLongInteger(...)) if a cast is needed)"
    else:
        recv_txt = ("This is a CREATE-ONLY form: the screen has no own-record id input, so every save creates a "
                    "new record (Id = NullIdentifier()).")
        id_set_txt = "sets its Id = NullIdentifier() (always create)"
    ret_txt = f" After saving, Destination back to the {ret} screen." if ret else " After saving, RefreshData the screen."
    return (
        f"{_PREAMBLE}\n\n"
        f"Make the {screen} screen a WORKING create/edit form for the {entity} entity that PERSISTS — a write-path, "
        f"not a display. {recv_txt}\n"
        f"1. Author a server action Save{entity}Record with Public=FALSE (a Public server action fails to publish, "
        f"OS-BLD-40409). Input: a {entity} record. Inside: an If on the record's Id = NullIdentifier() — True branch "
        f"calls {entity}.CreateAction, False branch calls {entity}.UpdateAction — return the id. Build the record "
        f"with a TYPED LOCAL variable + one Assign PER attribute; NEVER an inline record literal (they fail on fresh apps).\n"
        f"2. On the screen, add editable inputs: {inputs} (fields: {flist}), and a Save button "
        f'(data-spec-id="save{entity.lower()}btn").{creator_txt}{context_txt}\n'
        f"3. Wire Save OnClick to a screen action that reads the form values into a typed {entity} local, {id_set_txt}, "
        f"calls Save{entity}Record, then RefreshData.{ret_txt}\n"
        f"The result MUST persist to the database and survive a page reload. If a 'New {entity}' entry point navigates "
        f"here with an empty id, this screen IS the create form — do not leave it read-only."
    )


def json_1line(obj) -> str:
    import json
    return json.dumps(obj, separators=(", ", "="))


RECIPES = {
    "nav-block": nav_block,
    "list-screen": list_screen,
    "role-gate": role_gate,
    "seed-entity": seed_entity,
    "create-form": create_form,
}


def render(name: str, params: dict) -> str:
    if name not in RECIPES:
        raise KeyError(f"unknown recipe {name!r}; known: {', '.join(sorted(RECIPES))}")
    return RECIPES[name](params or {})


# ── spec -> ordered build plan (the loop-closer) ─────────────────────────────
_DATA_COMPONENT_TYPES = {"Table", "List", "Card", "Board"}


def _columns_of(comp: dict) -> list:
    cols = []
    for col in comp.get("columns", []) or []:
        cols.append(col.get("field", col) if isinstance(col, dict) else col)
    return cols


_MUTATING = {"CreateEntity", "UpdateEntity", "DeleteEntity"}
_AUDIT_ATTRS = {"CreatedAt", "UpdatedAt", "CreatedBy", "UpdatedBy"}


def _entities_map(spec: dict) -> dict:
    return {e["name"]: e for e in spec.get("dataModel", {}).get("entities", [])}


def _form_fields(spec: dict, entity: str, cap: int = 4) -> list:
    """User-editable text fields for a create/edit form: drop the identifier, FKs (set
    programmatically), and audit columns."""
    out = []
    for a in _entities_map(spec).get(entity, {}).get("attributes", []):
        if a.get("isIdentifier") or a.get("references") or a["name"] in _AUDIT_ATTRS:
            continue
        out.append(a["name"])
    return out[:cap] or ["Name"]


def _screen_write_entity(spec: dict, screen: dict) -> str | None:
    """The entity a write-path on this screen mutates. Prefer the screen's data-bound
    entity (the thing the screen is ABOUT — a list of Tasks on the tasks screen means
    CreateTask makes a Task); fall back to an entity-typed input parameter only for a
    pure detail/form screen with no data component (its input param IS the record).
    (A cleaner fix is for the spec action to name its target entity — seam logged.)"""
    for c in screen.get("components", []):
        if c.get("boundTo"):
            return c["boundTo"].split(".")[0]
    for ip in screen.get("inputParameters", []):
        if ip.get("references"):
            return ip["references"]
    return None


def _screen_id_param(screen: dict, entity: str) -> str | None:
    """The screen's OWN-record id input param (the create/edit toggle), or None when the
    screen has no input param referencing this entity — a create-only screen. Do NOT
    fabricate an <Entity>Id that doesn't exist; that made the recipe author against a
    phantom input (iteration-3 seam 3b)."""
    for ip in screen.get("inputParameters", []):
        if ip.get("references") == entity:
            return ip["name"]
    return None


def _context_fk(spec: dict, entity: str, screen: dict, user_entity: str | None = None) -> dict | None:
    """A mandatory parent FK on `entity` that must be filled from one of the screen's
    context input params (e.g. Task.ListId <- the tasks screen's ListId input, which
    arrives via navigation from the parent list). The user/creator FK is excluded — it's
    wired from session identity via creator_attr, not from a screen param. Returns
    {"attr", "from_param"} or None (iteration-3 seam 3a)."""
    params = screen.get("inputParameters", [])
    for a in _entities_map(spec).get(entity, {}).get("attributes", []):
        parent = a.get("references")
        if not parent or not a.get("mandatory"):
            continue
        if user_entity and parent == user_entity:
            continue
        for ip in params:
            if ip.get("references") == parent:
                return {"attr": a["name"], "from_param": ip["name"]}
    return None


def _creator_attr(spec: dict, entity: str, user_entity: str | None) -> str | None:
    if not user_entity:
        return None
    for a in _entities_map(spec).get(entity, {}).get("attributes", []):
        if a.get("references") == user_entity:
            return a["name"]
    return None


def _list_screen_for_entity(spec: dict, entity: str, exclude: str | None = None) -> str | None:
    for s in spec.get("screens", []):
        if s["id"] == exclude:
            continue
        for c in s.get("components", []):
            if c.get("type") in _DATA_COMPONENT_TYPES and (c.get("boundTo") or "").split(".")[0] == entity:
                return s["id"]
    return None


def plan_from_spec(spec: dict) -> list[dict]:
    """Derive an ordered list of pre-corrected build steps directly from an
    app_spec's first-class fields — the chain spec -> recipe -> (build) -> verify.
    Each step is {recipe, params, why}; render each with `render(step['recipe'],
    step['params'])`. Reads app.navigation, app.auth, and per-screen components +
    access. Order: shared nav block -> seed the user entity -> per data screen
    (bind its list, then gate it if access requires)."""
    steps: list[dict] = []
    screens = spec.get("screens", [])
    auth = spec.get("auth") or {}
    login = auth.get("loginScreen") or "Login"

    nav = spec.get("navigation")
    if nav and nav.get("items"):
        steps.append({"recipe": "nav-block", "why": "app.navigation declared", "params": {
            "block_name": nav.get("block", "SidebarNav"),
            "workspace_label": nav.get("workspaceLabel", ""),
            "logout_to": login,
            "items": [{"label": i.get("label", ""), "toScreen": i.get("toScreen", "")}
                      for i in nav["items"]],
        }})

    if auth.get("provider") == "app-local" and auth.get("userEntity") and auth.get("testUsers"):
        ue, aa = auth["userEntity"], auth.get("adminAttribute")
        rows = []
        for tu in auth["testUsers"]:
            row = {"label": tu.get("label", tu.get("role", ""))}
            if aa:
                row[aa] = bool(tu.get("isAdmin", tu.get("role") == "Admin"))
            rows.append(row)
        steps.append({"recipe": "seed-entity", "why": f"auth.testUsers seed {ue}",
                      "params": {"entity": ue, "rows": rows}})

    for s in screens:
        for c in s.get("components", []):
            if c.get("type") in _DATA_COMPONENT_TYPES and c.get("boundTo"):
                entity = c["boundTo"].split(".")[0]
                detail = next((e.get("toScreen") for e in s.get("navigation", [])
                               if e.get("fromComponent") == c["id"]), None)
                params = {"screen": s["id"], "entity": entity,
                          "columns": _columns_of(c) or ["(entity display fields)"],
                          "component_id": c["id"]}
                if detail:
                    params["detail_screen"] = detail
                steps.append({"recipe": "list-screen",
                              "why": f"{c['id']} ({c['type']}) bound to {entity}", "params": params})
                break  # one primary data list per screen
        acc = s.get("access") or {}
        if acc.get("adminOnly") or acc.get("requiresRole"):
            steps.append({"recipe": "role-gate", "why": f"screen.access on {s['id']}", "params": {
                "screen": s["id"],
                "user_entity": auth.get("userEntity", "Member"),
                "admin_attr": auth.get("adminAttribute", "IsAdmin"),
                "home": acc.get("redirectTo", "Home"),
                "login": login,
            }})
        # Phase 6 write-path: any action that mutates an entity becomes a create-form step.
        # This is the definition of done — the plan must not omit it (seam: linear Documents).
        for a in s.get("actions", []):
            if _MUTATING & set(a.get("does", [])):
                entity = _screen_write_entity(spec, s)
                if not entity:
                    continue
                p = {"screen": s["id"], "entity": entity,
                     "fields": _form_fields(spec, entity)}
                sid = _screen_id_param(s, entity)
                if sid:
                    p["id_param"] = sid
                ctx = _context_fk(spec, entity, s, auth.get("userEntity"))
                if ctx:
                    p["context_fk"] = ctx
                creator = _creator_attr(spec, entity, auth.get("userEntity"))
                if creator:
                    p["creator_attr"] = creator
                ret = _list_screen_for_entity(spec, entity, exclude=s["id"])
                if ret:
                    p["return_screen"] = ret
                steps.append({"recipe": "create-form",
                              "why": f"{s['id']}.{a['name']} does {sorted(_MUTATING & set(a.get('does', [])))}",
                              "params": p})
                break  # one write-path step per screen
    return steps
