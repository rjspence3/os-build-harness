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
    "to a screen unless this unit is explicitly about auth — keep screens Anonymous. Author DIRECTLY and rely on the "
    "final model validation — do NOT run read-only introspection loops to enumerate or 'verify' your own work. In "
    "particular, do NOT read a `.Name` PROPERTY off Model-API node/widget/type interfaces: MANY do not expose one and "
    "it is a compile error (IMobileWidget, IActionNode, IFlowNode, ITypeSignature, IUIFlowNodeSignature, "
    "IIdentifierType, IBasicType all lack `.Name`). If you must name a type use GetInterface().Name; otherwise skip "
    "the diagnostic and just author. After authoring, run the model validation and report errors/warnings; do NOT "
    "publish (the orchestrator publishes)."
)


def _p(params: dict, key: str, default=None, required: bool = False):
    if required and key not in params:
        raise ValueError(f"recipe missing required param: {key!r}")
    return params.get(key, default)


# ── product-UI CSS class contract ────────────────────────────────────────────
# The rich recipes below author widgets that carry these STABLE class hooks; the
# app theme stylesheet (design.theme.css, applied via the `theme` recipe) styles
# them. This is the seam that turned "bare Table" into clone-grade UI: the recipe
# emits the STRUCTURE + class hook, the theme paints it. Keep this list and the
# classes the recipes emit in lockstep — a theme author targets exactly these.
#
#   App shell      .app-sidebar .nav-section .nav-item .nav-item.is-active
#                  .nav-tag (mono 3-letter chip) .nav-badge (count) .sidebar-brand
#                  .sidebar-user  .app-topbar .breadcrumb .env-chip
#   Data cells     .cell-id (mono identifier) .chip .chip-<value> (status pill)
#                  .badge .badge-<value> (state badge) .tag .tag-<value> (tier tag)
#                  .avatar (round initials) .glyph .glyph-<set> (CSS-icon, data-value)
#   Dashboard      .kpi-card .kpi-icon .kpi-value .kpi-label .kpi-trend
#   Case detail    .stepper .step .step.is-done .step.is-active .step.is-pending
#                  .review-grid .review-card .review-status
#                  .timeline .timeline-item
# Value-suffixed classes (chip-<value>, badge-<value>, glyph[data-value]) are set
# from an EXPRESSION (Style = "chip chip-" + Lower(Entity.Attr)) so the color
# tracks the row's data — the theme defines the per-value colors.
UI_CLASS_CONTRACT = (
    "app-sidebar nav-section nav-item is-active nav-tag nav-badge sidebar-brand sidebar-user "
    "app-topbar breadcrumb env-chip cell-id chip badge tag avatar glyph "
    "kpi-card kpi-icon kpi-value kpi-label kpi-trend "
    "stepper step is-done is-active is-pending review-grid review-card review-status "
    "timeline timeline-item"
).split()


def _slug(text: str) -> str:
    """Lowercase a static value into a CSS-class-safe suffix (for literal chip/badge values)."""
    return "".join(c if c.isalnum() else "-" for c in str(text).lower()).strip("-")


def _cell_instruction(col, entity: str) -> str:
    """One column's cell-authoring instruction for the list_screen table, keyed on the
    columnSpec `kind`. A plain string column (back-compat) renders as a text cell.

    chip/badge/tag/glyph/avatar/identifier are PRODUCT-UI cells: the recipe authors the
    STRUCTURE + a class hook (see UI_CLASS_CONTRACT) and the theme paints it. Value-tinted
    classes are built with an Expression so the color tracks the row value."""
    if isinstance(col, str):
        return f'`{col}`: a plain text cell showing {entity}.{col}.'
    field = col.get("field", "")
    kind = col.get("kind", "text")
    label = col.get("label") or field
    q = f"{entity}.{field}" if "." not in field else field
    if kind in ("text", "date"):
        fmt = " (format the Date/Date Time for display)" if kind == "date" else ""
        return f'`{label}`: a plain Expression cell showing {q}{fmt}.'
    if kind == "identifier":
        return (f'`{label}`: a monospace id cell — an Expression showing {q} inside a Container '
                f'whose Style class is "cell-id".')
    if kind in ("chip", "badge", "tag"):
        return (f'`{label}`: a status {kind} — an Expression showing {q} INSIDE a Container whose '
                f'Style is the EXPRESSION "{kind} {kind}-" + ToLower({q}) (so ".{kind}" makes the '
                f'rounded pill and ".{kind}-<value>" tints it per the theme). Do NOT hardcode one class.')
    if kind == "avatar":
        return (f'`{label}`: a round avatar cell — a Container Style class "avatar" containing an '
                f'Expression = ToUpper(Substr({q}, 0, 2)) (the initials). The theme rounds + colors it.')
    if kind == "glyph":
        gset = col.get("glyphSet", "state")
        return (f'`{label}`: a CSS-icon cell — a Container whose Style class is "glyph glyph-{gset}" '
                f'and which carries an HTML attribute data-value = {q} (the theme renders the icon via '
                f'.glyph-{gset}[data-value=...]::before — do NOT put raw HTML/SVG in a widget, it is '
                f'HTML-encoded at runtime).')
    if kind == "link":
        return f'`{label}`: a Link cell showing {q} that navigates to the row detail passing the Id.'
    return f'`{label}`: a plain Expression cell showing {q}.'


# ── recipes ──────────────────────────────────────────────────────────────────
def nav_block(params: dict) -> str:
    """Author the app's persistent app-shell navigation ONCE as a reusable Web Block — the
    product-UI sidebar (brand header, optional section groups, per-item mono tag chip + count
    badge, active-item highlight, user footer), not a bare link list. The theme paints the
    .app-sidebar/.nav-item/.nav-tag/.nav-badge classes (see UI_CLASS_CONTRACT).
    params: block_name, items:[{label,toScreen,tag?,badge?,section?}], logout_to(login screen),
    workspace_label?, brand?, subtitle?, user_label?, user_role?"""
    block = _p(params, "block_name", "SidebarNav")
    items = _p(params, "items", [], required=True)
    logout_to = _p(params, "logout_to")          # None ⇒ no auth ⇒ no logout link (avoid a nav to a
    #                                              non-existent Login screen; see below)
    workspace = _p(params, "workspace_label", "")
    brand = _p(params, "brand", workspace or "App")
    subtitle = _p(params, "subtitle", "")
    user_label = _p(params, "user_label", "")
    user_role = _p(params, "user_role", "")
    # Group items by their optional `section` (preserving first-seen order); ungrouped items
    # fall under an implicit lead section so the render loop is uniform.
    sections: list[tuple[str, list]] = []
    by_name: dict[str, list] = {}
    for it in items:
        sec = it.get("section", "") if isinstance(it, dict) else ""
        if sec not in by_name:
            by_name[sec] = []
            sections.append((sec, by_name[sec]))
        by_name[sec].append(it)
    blocks = []
    for sec, sec_items in sections:
        lines = []
        for i in sec_items:
            tag = f' with a leading mono tag chip (Container Style class "nav-tag") showing "{i["tag"]}"' if i.get("tag") else ""
            badge = f' and a trailing count badge (Container Style class "nav-badge") showing "{i["badge"]}"' if i.get("badge") not in (None, "") else ""
            lines.append(
                f'   - a nav item (Container Style class "nav-item", data-spec-id="{i["toScreen"]}") whose link is '
                f'labelled EXACTLY "{i["label"]}" and navigates to the {i["toScreen"]} screen{tag}{badge}. When the '
                f'current screen IS {i["toScreen"]}, add the "is-active" class to that item.')
        header = (f'   - a section header (Style class "nav-section") "{sec}"\n' if sec else "")
        blocks.append(header + "\n".join(lines))
    body = "\n".join(blocks)
    role_clause = f' and role "{user_role}"' if user_role else ""
    user_name = user_label or "the current user"
    # The localStorage identity read only makes sense in an app-local-auth app (logout_to set).
    read_name = " (read the name from localStorage ln_current_name)" if logout_to else ""
    user_txt = (
        f'   - a footer user block (Container Style class "sidebar-user") showing '
        f'"{user_name}"{role_clause}{read_name}, with an online dot.\n'
        if (user_label or user_role) else "")
    logout_txt = (
        f'   - a "Log out" link (Style class "nav-item") that clears the session (localStorage keys '
        f"ln_current_user + ln_current_name) and navigates to the {logout_to} screen.\n"
        if logout_to else "")
    sub_txt = f' and a subtitle "{subtitle}"' if subtitle else ""
    return (
        f"{_PREAMBLE}\n\n"
        f"Create ONE reusable Web Block named {block} that renders the app's persistent left app-shell sidebar, so "
        f"every screen references this single block instead of re-authoring the nav. This is an INTERNAL app-shell "
        f"block — author it NON-PUBLIC (Public=false; a new block may default to Public=true). CRITICAL: a PUBLIC "
        f"Web Block whose internal screen action performs a navigation (a DestinationNode, e.g. the logout) trips "
        f"OS-DPL-50205 'Model features validation failed' at PUBLISH (0 errors in-session) — the platform can't "
        f"guarantee the target screen exists in a consuming app. Keep this block Public=false. Give the block's root "
        f'Container the Style class "app-sidebar" (the theme paints the dark shell). The block contains, in order:\n'
        f'   - a brand header (Style class "sidebar-brand") showing "{brand}"{sub_txt}.\n'
        f"{body}\n"
        f"{user_txt}"
        f"{logout_txt}"
        f"CRITICAL: each link must be a single link whose displayed text is EXACTLY its label and nothing else — "
        f"OutSystems gives a new Link widget a default literal \"link\" Text widget; DELETE that literal \"link\" "
        f"ITextWidget from each link so it does not render \"linkInbox\"-style prefixes (a scan of Expression "
        f"children alone looks clean and misses it — find and remove the literal-text widget). Set "
        f"data-spec-id on each item = its toScreen id. Do not fan this nav out per screen; this block IS the nav."
    )


def action_button(params: dict) -> str:
    """State-transition action buttons on a detail screen — the workflow write-paths (approve /
    send-back / activate etc.). Each button runs a NON-PUBLIC server action that fetches the record
    by the screen's id param, assigns the target fields, updates it, and refreshes the screen.
    params: screen, entity, id_param, buttons:[{label, set:{field: value}, style?}]."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    id_param = _p(params, "id_param", f"{entity}Id")
    buttons = _p(params, "buttons", [], required=True)
    lines = []
    for b in buttons:
        sets = "; ".join(f'{k} = "{v}"' for k, v in (b.get("set") or {}).items())
        style = f' (Style class "{b["style"]}")' if b.get("style") else ""
        lines.append(
            f'   - a Button labelled "{b["label"]}"{style} (data-spec-id="{_slug(b["label"])}btn") whose OnClick '
            f'runs a NON-PUBLIC server action Apply{_slug(b["label"]).title().replace("-","")}: it fetches the '
            f'{entity} whose Id = the screen\'s {id_param} input (an aggregate max 1, or Get{entity}ById), then '
            f'Assigns {{ {sets} }} onto a typed local {entity} record and calls {entity}.UpdateAction (the local '
            f'must carry the Id). After the server action, RefreshData on the screen\'s {entity} aggregate so the '
            f'change shows without a reload.')
    body = "\n".join(lines)
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {screen} screen, add these state-transition action buttons that mutate the {entity} identified by "
        f"the screen's {id_param} input parameter. Place them in an action bar near the top of the content.\n{body}\n"
        f"CRITICAL: each Apply* server action WRITES an entity, so it MUST be NON-PUBLIC (a public entity-writing "
        f"action trips OS-DPL-50205 at publish). Use {entity}.UpdateAction with a typed local carrying the Id; do "
        f"NOT use an inline record literal. Verify at RUNTIME that clicking a button changes the {entity}'s field(s) "
        f"and the change survives a reload. Do not publish."
    )


def place_nav(params: dict) -> str:
    """Place the shared nav Web Block onto every screen — authoring the block (nav_block) is NOT
    enough; each screen must INSTANTIATE it or the sidebar never renders. params: block_name,
    screens:[screen id/name]. One block instance per screen, as the first widget."""
    block = _p(params, "block_name", "SidebarNav")
    screens = _p(params, "screens", [], required=True)
    slist = ", ".join(screens)
    return (
        f"{_PREAMBLE}\n\n"
        f"The reusable Web Block {block} already EXISTS but is not placed on any screen, so the app-shell "
        f"sidebar does not render. On EACH of these screens — {slist} — add exactly ONE instance of the "
        f"{block} block as the FIRST widget of the screen's content: CreateWidget<IMobileBlockInstanceWidget> "
        f"with SourceBlock set to the {block} web block (resolve it via the app's Web Blocks). Do NOT "
        f"re-author the block itself, and never add it more than once per screen. Its root Container has the "
        f'"app-sidebar" class; the theme positions it as a fixed left rail (the screen body is padded left to '
        f"make room). After authoring, confirm each listed screen has exactly one {block} instance, then run "
        f"validation. Do not publish.")


def list_screen(params: dict) -> str:
    """Bind a screen's data list/table to an entity so it renders real rows — with PRODUCT-UI
    styled cells (status chips, tier tags, avatars, CSS-icons, mono ids), not a bare grid.
    params: screen, entity, columns:[str | {field,kind,label,glyphSet}], sort_by?, join?,
    detail_screen?, component_id?. String columns still render as plain text cells (back-compat)."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    columns = _p(params, "columns", [], required=True)
    cid = _p(params, "component_id", f"{entity.lower()}Table")
    sort_by = _p(params, "sort_by")
    join = _p(params, "join")
    detail = _p(params, "detail_screen")
    nav_label = _p(params, "nav_label")            # the spec's declared row-nav button label (seam 3e)
    nav_cid = _p(params, "nav_component_id")
    sort_txt = f" sorted by {sort_by}" if sort_by else ""
    join_txt = (f" Join to {join} so its display fields resolve (use an explicit join in the aggregate, "
                f"never a second data source).") if join else ""
    # Rich per-column cell instructions (chip/badge/avatar/glyph/id) — the case-queue look.
    styled = any(isinstance(c, dict) and c.get("kind") not in (None, "text") for c in columns)
    cell_lines = "\n".join(f"   - {_cell_instruction(c, entity)}" for c in columns)
    cells_intro = (
        " Render EACH column as its specified product-UI cell (not a raw value grid) — the theme's "
        "stylesheet paints the chip/badge/tag/avatar/glyph classes below into the real look:"
        if styled else " with these columns:")
    if detail and nav_label:
        # emit the spec's explicit nav component so the runtime gate's parent-nav finds it by label
        detail_txt = (f' Each row must have a Link with the text "{nav_label}" (data-spec-id="'
                      f'{(nav_cid or "opendetailbtn").lower()}") that navigates to the {detail} screen passing '
                      f"that row's Id.")
    elif detail:
        detail_txt = f" Each row links to the {detail} screen passing the record's Id."
    else:
        detail_txt = ""
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {screen} screen, add a screen aggregate over the {entity} entity{sort_txt} (pin the aggregate "
        f"name so it is not auto-renamed).{join_txt} Add a Table with component id {cid} (set data-spec-id="
        f"\"{cid}\" and data-entity=\"{entity}\" on it) bound to that aggregate. Put it in the screen's content "
        f"area (to the right of the nav).{cells_intro}\n{cell_lines}\n"
        f"Set data-spec-id=\"<field>cell\" on each styled cell container so runtime verification resolves it."
        f"{detail_txt} The table must render the real rows — if it comes up empty, the aggregate binding is "
        f"wrong; fix it, do not leave an empty table."
    )


def role_gate(params: dict) -> str:
    """App-local Admin gate for a screen (no platform role / no end-user IdP). Looks the user up by
    the IDENTITY ATTR (the same value the login stores in localStorage) — NOT by Id — so there is no
    Text->Id cast and Mentor never 'reconciles' by changing the entity identifier (seam E).
    params: screen, user_entity, admin_attr, home, login, identity_attr(default Name)"""
    screen = _p(params, "screen", required=True)
    user_entity = _p(params, "user_entity", "Member")
    admin_attr = _p(params, "admin_attr", "IsAdmin")
    home = _p(params, "home", "Issues")
    login = _p(params, "login", "Login")
    identity_attr = _p(params, "identity_attr", "Name")
    return (
        f"{_PREAMBLE}\n\n"
        f"Add app-local access control to the {screen} screen so only Admin users can view it. IMPORTANT: do NOT "
        f"add any platform Role (keep it Anonymous — a platform role breaks this app's localStorage identity), and "
        f"do NOT modify the {user_entity} entity in any way — especially do NOT change its identifier/Id (that is an "
        f"irreversible post-publish change, OS-DPL-RDBS-40020); only READ {user_entity}. Add an OnReady screen "
        f"action that runs in order:\n"
        f"1. A JavaScript node reading localStorage: OutUser = localStorage.getItem('ln_current_user')||''.\n"
        f"2. An Assign copying OutUser into a Text local CurrentUser.\n"
        f"3. An If: when CurrentUser = \"\" -> Destination {login}.\n"
        f"4. A screen Aggregate (max 1) fetching the single {user_entity} where {user_entity}.{identity_attr} = "
        f"CurrentUser (a plain Text equality — NO cast to the Id), refreshed AFTER CurrentUser is set.\n"
        f"5. An If: when that aggregate is empty OR the {user_entity}'s {admin_attr} is False -> Destination {home}.\n"
        f"So: logged-out -> {login}, non-admin -> {home}, admin -> through. The login stores the user's {identity_attr} "
        f"in 'ln_current_user', so this lookup matches it directly with no identifier change. Verify all three paths."
    )


def login(params: dict) -> str:
    """App-local login screen: identity input -> lookup user -> write the localStorage session
    the role-gate reads ('ln_current_user' = Id, 'ln_current_name' = identity). No platform role /
    no ODC end-user IdP. params: screen, user_entity, identity_attr(default Name), home."""
    screen = _p(params, "screen", required=True)
    user_entity = _p(params, "user_entity", required=True)
    identity_attr = _p(params, "identity_attr", "Name")
    home = _p(params, "home", required=True)
    return (
        f"{_PREAMBLE}\n\n"
        f"Make the {screen} screen an APP-LOCAL login (Anonymous — do NOT add any platform Role; identity is bridged "
        f"via browser localStorage, not an ODC end-user provider). The session keys are 'ln_current_user' (the user's "
        f"Id) and 'ln_current_name' (their {identity_attr}) — the role-gate reads these.\n"
        f"1. Add a text Input (data-spec-id=\"loginidentityinput\") for the user's {identity_attr}, and a Button "
        f"labeled \"Log in\" (data-spec-id=\"loginbtn\").\n"
        f"2. Add a screen aggregate (max 1 record) fetching the SINGLE {user_entity} row whose {identity_attr} equals "
        f"the input value. Wire the Log in button OnClick to a screen action that FIRST calls RefreshData on that "
        f"aggregate (a screen aggregate is fetched at screen-load when the input is still empty — it MUST be "
        f"re-fetched with the typed value before the check, or every login reads as not-found), THEN: if a row "
        f"is found -> a JavaScript node sets BOTH localStorage['ln_current_user'] AND localStorage['ln_current_name'] "
        f"to that {user_entity}'s {identity_attr} value, then Destination to the {home} screen. If NO row is "
        f"found -> show a 'Invalid login' message and stay on the screen.\n"
        f"The app-local session key IS the {identity_attr} (what the role-gate looks the user up by) — do NOT use or "
        f"change the entity's Id/identifier. Keep the screen Anonymous. At runtime a valid {identity_attr} must log "
        f"in, set both session keys, and land on {home}."
    )


def seed_entity(params: dict) -> str:
    """Seed sample rows for an entity via a LoadSampleData orchestrator — deterministically.
    params: entity, rows:[{...}], fk_refs?:[{attr,parent,parent_key}] (SEED-A: FK attrs whose row
    values are natural-key references to already-seeded parents, resolved to real Ids at seed time),
    fk_notes?, bootstrap_screens?:[screen] (entry screens whose OnReady also calls LoadSampleData, so
    seeding does NOT depend on the flaky WhenPublished timer — seam B).

    KEEP THE ROW COUNT LEAN. Each row is authored as a CreateAction + one Assign PER attribute — a
    node-heavy Model-API build. A single seed action with ~20+ multi-attribute rows (≈200 nodes) chokes
    authoring: it can run 10-15+ min and risks an upstream turn failure (live SLATracker 2026-07-07: a
    22-record seed was cancelled at 14 min; a lean 11-record set authored fine). Cap at ~10-12 rows per
    turn; for a bigger dataset, split across per-entity turns (owners → applications → children, so FKs
    resolve) rather than one mega-action. A seed action WRITES entities, so it must be NON-public
    (a public entity-writing action trips OS-DPL-50205 — see service_action)."""
    entity = _p(params, "entity", required=True)
    rows = _p(params, "rows", [], required=True)
    fk_notes = _p(params, "fk_notes", "")
    fk_refs = _p(params, "fk_refs", []) or []
    bootstrap = _p(params, "bootstrap_screens", []) or []
    rows_txt = "\n".join(f"   - {json_1line(r)}" for r in rows)
    fk_parts = []
    if fk_refs:
        mapping = "; ".join(
            f"{r['attr']} → a {r['parent']} matched on {r['parent']}.{r['parent_key']}" for r in fk_refs)
        fk_parts.append(
            f"FOREIGN KEYS (seed PARENTS BEFORE CHILDREN — this app's LoadSampleData seeds in dependency "
            f"order, so {entity}'s parents are already seeded above): in each {entity} row below, the value "
            f"under each FK attribute is a NATURAL-KEY reference to a parent row, NOT a literal Id ({mapping}). "
            f"For every row, BEFORE calling {entity}.CreateAction, resolve each FK — fetch the parent with an "
            f"aggregate (max 1) filtered on that natural-key attribute equal to the row's reference value, take "
            f"the parent's Id, and Assign it to the new {entity}'s FK attribute. If a parent lookup is empty, "
            f"SKIP that row (never write a dangling FK — it fails at runtime).")
    if fk_notes:
        fk_parts.append(fk_notes)
    fk_txt = (" " + " ".join(fk_parts)) if fk_parts else ""
    bootstrap_txt = (
        f"3. DETERMINISTIC BOOTSTRAP (a WhenPublished timer is NOT reliable — it has silently failed to seed): "
        f"ALSO call LoadSampleData as the FIRST node of the OnReady screen action of {', '.join(bootstrap)} (create "
        f"the OnReady action if absent), so the data is guaranteed present on first load before any lookup/login. "
        f"The step-1 empty-guard makes this call safe and idempotent. Add the call only if that OnReady does not "
        f"already invoke LoadSampleData.\n"
        if bootstrap else "")
    return (
        f"{_PREAMBLE}\n\n"
        f"Seed the {entity} entity with sample data. Do NOT assume a sample-data mechanism already exists; on a fresh "
        f"app there is none, so CREATE it (and REUSE it if already present):\n"
        f"1. A server action LoadSampleData. Inside, guard on emptiness: use an aggregate (max 1 row) to check "
        f"whether {entity} has zero rows; ONLY if empty, create these rows — each via the {entity} CreateAction "
        f"using a typed local {entity} variable with one Assign PER attribute (NEVER an inline record literal, which "
        f"fails on fresh apps).{fk_txt}\n{rows_txt}\n"
        f"   CRITICAL — INDEPENDENT PER-ENTITY GUARD: {entity}'s emptiness check must be its OWN branch that is "
        f"reached and evaluated on EVERY call, in SEQUENCE, regardless of whether OTHER entities are already "
        f"seeded. If a LoadSampleData already exists, ADD {entity}'s guarded block as a SEPARATE sequential block "
        f"AFTER the existing ones — do NOT nest it inside another entity's empty-guard True-branch, and do NOT "
        f"gate the whole action behind the first entity's check. Wire it so: [check {entity} empty -> if empty, "
        f"seed {entity}] then continue to the next block. (The classic bug: all entities nested under the first "
        f"entity's guard, so once that entity is populated the later entities NEVER seed — live Rivian 2026-07-08.) "
        f"The {entity} rejoin/merge node after its If must lead onward to the next block or End, never back into "
        f"another entity's guard.\n"
        f"2. Also create a Timer (e.g. BootstrapData) whose action is LoadSampleData and whose Schedule is "
        f"WhenPublished (a best-effort belt-and-suspenders alongside the bootstrap below), if no such timer exists.\n"
        f"{bootstrap_txt}"
        f"After authoring, run validation. Verify the {entity} rows exist at RUNTIME (load an entry screen, which "
        f"triggers the OnReady bootstrap)."
    )


def seed_graph(params: dict) -> str:
    """Seed a FK-linked entity GRAPH in ONE LoadSampleData action — the robust FK seed.
    params: entities:[{name, natural_key?, rows:[{...}], fk_refs:[{attr,parent,parent_key}]}]
    (in dependency order: parents first), bootstrap_screens?:[screen].

    WHY this and not per-entity seed_entity for FK data: at RUNTIME an aggregate does NOT see rows
    created earlier in the SAME action, so the natural-key parent LOOKUP returns empty and every FK
    child gets skipped (live Rivian 2026-07-08: Supplier seeded, Part/Case seeded 0). The fix is to
    CAPTURE each parent's Id from its CreateAction RETURN VALUE into a local and reference it directly
    in children — no lookup. That requires ONE action so the parent-Id locals are in scope for children."""
    entities = _p(params, "entities", [], required=True)
    bootstrap = _p(params, "bootstrap_screens", []) or []
    # entities whose Id a child references -> their created Id must be captured into a local
    parents = {fr["parent"] for e in entities for fr in (e.get("fk_refs") or [])}
    blocks = []
    for e in entities:
        name = e["name"]
        nkey = e.get("natural_key")
        fk_by_attr = {r["attr"]: r for r in (e.get("fk_refs") or [])}
        row_lines = []
        for r in e.get("rows", []):
            nk_val = r.get(nkey) if nkey else None
            id_local = f"{name}_{_slug(nk_val)}_Id" if (name in parents and nk_val) else None
            assigns = []
            for k, v in r.items():
                if k in fk_by_attr:
                    fk = fk_by_attr[k]
                    assigns.append(f"{k} = the captured local {fk['parent']}_{_slug(v)}_Id "
                                   f"(the {fk['parent']} whose {fk['parent_key']}=\"{v}\")")
                else:
                    assigns.append(f'{k} = "{v}"')
            capture = f", then CAPTURE its returned Id into local {id_local}" if id_local else ""
            row_lines.append(f"      • {name} {{ {'; '.join(assigns)} }} -> {name}.CreateAction{capture}")
        blocks.append(
            f"   - INDEPENDENT guard: aggregate (max 1) — if {name} has 0 rows, seed these (each via a typed "
            f"local {name} + one Assign per attribute, then {name}.CreateAction):\n" + "\n".join(row_lines))
    body = "\n".join(blocks)
    ent_names = ", ".join(e["name"] for e in entities)
    bootstrap_txt = (
        f"3. Call LoadSampleData as the FIRST node of the OnReady screen action of {', '.join(bootstrap)} "
        f"(create the OnReady if absent) so the graph is present on first load.\n" if bootstrap else "")
    return (
        f"{_PREAMBLE}\n\n"
        f"Seed this FK-linked entity graph ({ent_names}) with ONE server action LoadSampleData (create it if "
        f"absent; if it exists, REPLACE its body with this). Author the entities IN THIS ORDER (parents first) "
        f"so each child can reference its parent's captured Id:\n"
        f"1. CRITICAL FK RULE — resolve every FK by CAPTURING the parent's Id from its CreateAction RETURN VALUE "
        f"into a local variable, then setting the child's FK attribute to that local. Do NOT look up parents "
        f"with an aggregate: at runtime an aggregate does NOT return rows created earlier in the SAME action, so "
        f"a lookup yields empty and the child is skipped. The captured-Id locals are named {ent_names.split(',')[0]}"
        f"_<naturalkey>_Id etc.\n"
        f"2. Each entity gets its OWN INDEPENDENT emptiness guard, in sequence (not nested), so re-runs are "
        f"idempotent and a later entity still seeds if an earlier one is already populated:\n{body}\n"
        f"{bootstrap_txt}"
        f"Make LoadSampleData NON-PUBLIC (a public entity-writer trips OS-DPL-50205). Keep each row's Assigns "
        f"minimal. After authoring, run validation and confirm change_applied. Do not publish (orchestrator "
        f"publishes). At runtime, every listed entity — including the FK children — must have its rows."
    )


def create_form(params: dict) -> str:
    """Wire a WORKING create/edit form for an entity — the write-path (Phase 6, the
    definition of done). Encodes every correction a hand-authored create turn needs.

    params: screen, entity, fields:[attr], return_screen?, id_param?, context_fk?, creator_attr?, phase?

    `phase` (iteration-3 seam 3f — thrash-free decomposition). Authoring the server action +
    form + save-wiring in ONE Mentor turn cascades for many minutes on a populated screen. The
    PROVEN thrash-free path is three sub-turns:
      - "action"  : the Save<Entity>Record server action only (fresh turn).
      - "widgets" : the form inputs + button bound to a local var, OnClick LEFT EMPTY (fresh turn).
      - "wire"    : wire the button OnClick — RESUME the widgets turn's session so it builds on
                    the unpublished widgets, then publish ONCE.
    phase=None (default) returns the single combined prompt (backward-compatible)."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    fields = _p(params, "fields", [], required=True)
    ret = _p(params, "return_screen")
    id_param = _p(params, "id_param")              # None => create-only screen (no own-record id input)
    ctx = _p(params, "context_fk")                 # {"attr","from_param"} mandatory parent FK from a screen param
    creator = _p(params, "creator_attr")           # e.g. CreatorId — set from session identity
    phase = _p(params, "phase")
    lentity = entity.lower()
    local = f"New{entity}"
    flist = ", ".join(fields)
    inputs = "; ".join(f'an Input bound to {local}.{f} (data-spec-id="{f.lower()}input")' for f in fields)
    creator_txt = (
        f" Assign {local}.{creator} from the logged-in user: read localStorage 'ln_current_user' via a JavaScript "
        f"node and set {creator} = LongIntegerToIdentifier(TextToLongInteger(thatValue))."
        if creator else "")
    context_txt = (
        f" Assign {local}.{ctx['attr']} = the screen's {ctx['from_param']} input parameter — a MANDATORY parent "
        f"reference the record CANNOT be saved without; it arrives via navigation from the parent list "
        f"(cast with LongIntegerToIdentifier(TextToLongInteger(...)) only if a type cast is required)."
        if ctx else "")
    if id_param:
        recv_txt = (f"The screen receives a {id_param} input ({id_param} = a null/empty identifier means CREATE "
                    f"a new record; a real id means EDIT that one).")
        id_set_txt = f"sets its Id from {id_param} (use LongIntegerToIdentifier(TextToLongInteger(...)) if a cast is needed)"
    else:
        recv_txt = ("This is a CREATE-ONLY form: the screen has no own-record id input, so every save creates a "
                    "new record (Id = NullIdentifier()).")
        id_set_txt = "sets its Id = NullIdentifier() (always create)"
    ret_txt = f" After saving, Destination back to the {ret} screen." if ret else " After saving, RefreshData the screen's list aggregate."

    action_step = (
        f"Author a server action Save{entity}Record with Public=FALSE (a Public server action fails to publish, "
        f"OS-BLD-40409). Input: a {entity} record named {entity}Record. Inside: an If on {entity}Record.Id = "
        f"NullIdentifier() — True branch calls {entity}.CreateAction, False branch calls {entity}.UpdateAction — "
        f"return the resulting Id as an output. Build any record with a TYPED LOCAL variable + one Assign PER "
        f"attribute; NEVER an inline record literal (they fail on fresh apps). "
        f"Do NOT modify the {entity} ENTITY itself in any way — in particular do NOT rename, re-key, add, or change "
        f"its identifier/Id attribute (the identifier is already settled; changing an entity identifier after its "
        f"first publish is IRREVERSIBLE and blocks the deploy with OS-DPL-RDBS-40020). Only READ {entity} via its "
        f"CreateAction/UpdateAction and a typed {entity} local — author ONLY the server action, touch no entity schema.")
    # The form's inputs live INSIDE a Form container widget. A BARE Input added directly to the screen
    # is the shape that intermittently phantoms (change_applied=true but nothing persists — batcha,
    # 2026-07-07, 4× fresh); the Form-wrapped build is what persisted. So every form path wraps its
    # inputs in a Form (also the idiomatic ODC create form).
    form_widgets = (
        f"a screen-local variable {local} of the {entity} data type; a Form container widget "
        f"(data-spec-id=\"{lentity}form\") whose Source record is {local}, and INSIDE that Form these editable "
        f"inputs: {inputs} (fields: {flist}); and a Button labeled \"Add {entity}\" (data-spec-id=\"save{lentity}btn\")")
    widgets_step = (
        f"On the {screen} screen, ADD ONLY these and nothing else — do NOT modify or rebind the existing table, "
        f"aggregate, or any existing widget: {form_widgets} with its OnClick LEFT EMPTY for now. Keep the screen "
        f"Anonymous. Do NOT add any screen action or save logic in this turn.")
    wire_step = (
        f"Wire the \"Add {entity}\" button (data-spec-id=\"save{lentity}btn\") you just created. Create ONE screen "
        f"action, set as that button's OnClick, that in order: Assign {local}.Id = NullIdentifier();{context_txt}"
        f"{creator_txt} calls Save{entity}Record passing {local} as {entity}Record; then RefreshData the "
        f"{screen} list aggregate so the new row appears.{ret_txt} Leave the inputs' bindings intact. The prior "
        f"\"On Click must be set\" error MUST now be resolved.")
    # The PROVEN-persist shape (the batcha recovery): build the Form + inputs + button AND wire the OnClick
    # in ONE turn, AFTER the server action already exists. Keeps the action separate (so this is not the
    # action+form+wire mega-turn that cascades) while avoiding the fragile bare-widgets-only turn.
    combined_step = (
        f"On the {screen} screen, build a WORKING create form in ONE turn (the {entity}'s Save{entity}Record server "
        f"action ALREADY exists — call it, do not re-author it). ADD ONLY (do NOT modify the existing table or its "
        f"aggregate): {form_widgets}; then ONE screen action set as that Button's OnClick that in order: Assign "
        f"{local}.Id = NullIdentifier();{context_txt}{creator_txt} calls Save{entity}Record passing {local} as "
        f"{entity}Record; then RefreshData the {screen} list aggregate so the new row appears.{ret_txt} Keep the "
        f"screen Anonymous.")

    # PHANTOM SELF-CHECK for the widgets phase: leaving OnClick empty MUST raise the "On Click must be set"
    # validation error. If change_applied=true but that error is ABSENT, the widgets silently did NOT persist
    # (a phantom) — re-author in a FRESH session; do NOT proceed to wire against widgets that aren't there.
    widgets_phantom_check = (
        "After authoring, run model validation. The Button's \"On Click must be set\" error is EXPECTED here "
        "(OnClick is empty) — it is resolved in the next turn, which RESUMES this session. If that error is "
        "ABSENT, the widgets did NOT persist (a phantom despite a success summary): re-author this SAME step in a "
        "FRESH session before continuing. Do not publish.")

    if phase == "action":
        return (f"{_PREAMBLE}\n\n{action_step}\nDo NOT add or modify any screen or widget in this turn — ONLY the "
                f"server action. Do not publish.")
    if phase == "widgets":
        return f"{_PREAMBLE}\n\n{widgets_step}\n{widgets_phantom_check}"
    if phase == "wire":
        return (f"{_PREAMBLE}\n\n{wire_step}\nThe result MUST persist to the database and survive a page reload.")
    if phase == "combined":
        return (f"{_PREAMBLE}\n\n{combined_step}\nThe result MUST persist to the database and survive a page reload. "
                f"Do not publish.")

    # phase=None: the single combined prompt (backward-compatible)
    return (
        f"{_PREAMBLE}\n\n"
        f"Make the {screen} screen a WORKING create/edit form for the {entity} entity that PERSISTS — a write-path, "
        f"not a display. {recv_txt}\n"
        f"1. {action_step}\n"
        f"2. On the screen, add editable inputs: {inputs} (fields: {flist}), and a Save button "
        f'(data-spec-id="save{lentity}btn").{creator_txt}{context_txt}\n'
        f"3. Wire Save OnClick to a screen action that reads the form values into the typed {entity} local, {id_set_txt}, "
        f"calls Save{entity}Record, then RefreshData.{ret_txt}\n"
        f"The result MUST persist to the database and survive a page reload. If a 'New {entity}' entry point navigates "
        f"here with an empty id, this screen IS the create form — do not leave it read-only."
    )


_DATATYPE_WORDS = {
    "Identifier": "Identifier", "Text": "Text", "Integer": "Integer", "LongInteger": "Long Integer",
    "Decimal": "Decimal", "Currency": "Currency", "Boolean": "Boolean", "DateTime": "DateTime",
    "Date": "Date", "Time": "Time", "Email": "Email", "PhoneNumber": "Phone Number",
}


def _attr_line(a: dict) -> str:
    if a.get("references"):
        return (f"{a['name']}: a {'mandatory ' if a.get('mandatory') else ''}foreign-key reference to "
                f"{a['references']}")
    seg = f"{a['name']}: {_DATATYPE_WORDS.get(a.get('dataType', 'Text'), a.get('dataType', 'Text'))}"
    if a.get("mandatory"):
        seg += ", mandatory"
    if a.get("length"):
        seg += f", length {a['length']}"
    if "default" in a:
        seg += f", default {a['default']}"
    return seg


def data_model(params: dict) -> str:
    """Author ALL entities in ONE turn (seam 3d). Interdependent entities must be created
    together (a later separate turn that references an earlier one can roll it back)."""
    entities = _p(params, "entities", [], required=True)
    lines = []
    for e in entities:
        attrs = [a for a in e.get("attributes", []) if not a.get("isIdentifier")]
        lines.append(f"- {e['name']}: " + "; ".join(_attr_line(a) for a in attrs))
    body = "\n".join(lines)
    enames = ", ".join(e["name"] for e in entities)
    return (
        f"{_PREAMBLE}\n\n"
        f"Create the app's data model. Author ALL of these entities in THIS ONE turn (they may reference each "
        f"other, so they must be created together). Do NOT create any screens or UI in this turn.\n{body}\n"
        f"IDENTIFIER — settle it in THIS turn, before any publish (this is load-bearing: the create/edit form's "
        f"Save action later needs {entities[0]['name'] if entities else 'each entity'}.CreateAction and .Id, which "
        f"do not exist if the entity has no identifier). Every entity MUST end this turn with exactly ONE identifier "
        f"attribute: an auto-number Long-Integer named Id. ODC normally attaches this default Id on entity creation "
        f"— but do NOT assume it; after authoring, READ each entity back and CONFIRM it has an Id identifier "
        f"attribute. For ANY entity ({enames}) missing one, explicitly create an auto-number Long-Integer attribute "
        f"named Id and set it as that entity's identifier. Never leave an entity without an identifier, and never "
        f"CHANGE an existing identifier (post-first-publish that is irreversible, OS-DPL-RDBS-40020).\n"
        f"After authoring, run model validation AND report each entity's identifier attribute by name (so a silent "
        f"drop is caught now, not at the first write-path). Do not publish.")


def screen(params: dict) -> str:
    """Scaffold ALL screens in ONE turn with ANONYMOUS baked at creation (seam 3d/3d-anon).
    A hand-authored screen otherwise inherits the module Role and renders _error for anon
    visitors, costing a whole extra fix-up turn (R6). Verify change_applied (phantom, R7)."""
    screens = _p(params, "screens", [], required=True)
    lines = []
    for s in screens:
        parts = [f'"{s.get("name", s["id"])}" at route {s.get("route", "/" + s["id"])}']
        ips = s.get("input_params") or []
        if ips:
            desc = ", ".join(
                f'{ip["name"]} ({ip["references"] + " Identifier" if ip.get("references") else _DATATYPE_WORDS.get(ip.get("dataType", "Text"), ip.get("dataType", "Text"))}'
                f'{", mandatory" if ip.get("isRequired") or ip.get("mandatory") else ""})'
                for ip in ips)
            parts.append(f"with input parameter(s): {desc}")
        if s.get("default"):
            parts.append("set as the app's default (home) screen")
        lines.append("- Screen " + ", ".join(parts))
    body = "\n".join(lines)
    return (
        f"{_PREAMBLE}\n\n"
        f"Create these screens in the app's main Reactive Web UI flow (create the flow, e.g. MainFlow, if the app "
        f"has none). For EVERY screen, BAKE Anonymous access at creation: clear all platform Roles and enable "
        f"Anonymous access — an auto-attached module Role makes unauthenticated visitors hit _error, and gating is "
        f"done app-locally, not by a screen Role. Do NOT add tables, widgets, or data — ONLY the screens and their "
        f"input parameters.\n{body}\n"
        f"After authoring, CONFIRM each screen persisted (change_applied MUST be true; if a screen did not persist, "
        f"re-author it in a fresh attempt) and run model validation. Do not publish.")


def agent(params: dict) -> str:
    """Author a complete AI Agent from a blank `app_create kind=AIAgent` shell — internals AND
    model binding, entirely via MCP (wall lifted + runtime-proven 2026-07-05). params: agent_name,
    system_prompt, model_connection?(default a Trial connection), tools?:[server_action_name]."""
    name = _p(params, "agent_name", required=True)
    prompt = _p(params, "system_prompt", "You are a helpful assistant.")
    model = _p(params, "model_connection", "TrialClaudeHaiku4_5")
    tools = _p(params, "tools", []) or []
    tools_txt = (
        f"\n5. Give the agent these tools (each an existing Server Action): {', '.join(tools)}. Wire each with a "
        f"PARAMETERLESS handler = agent.CreateActionHandler(); handler.Action = <the server action>; for system-"
        f"supplied args set IsFilledByAI=false. (A tool is just a Server Action — there is no special Tool type.)"
        if tools else "")
    return (
        f"{_PREAMBLE}\n\n"
        f"This is a blank ODC AI Agent app (app_create kind=AIAgent ships an empty shell). Author a COMPLETE working "
        f"agent named {name} entirely in-model:\n"
        f"1. Create the agent element{' (EnableActionCalling=true)' if tools else ''}.\n"
        f"2. A BuildMessages server action that builds the AIMessage list: a System message whose "
        f'SystemMessageContent.ContentText is exactly "{prompt}", and a User message from a UserInput text parameter '
        f"(build the record with a typed local + Assign per attribute; an inline [{{Role:...}}] literal is rejected by "
        f"the parser).\n"
        f"3. An AgentFlow server action: call BuildMessages, then call the agent (CreateNode<ICallAgentNode>; "
        f"n.Agent=agent), and Assign the agent's response text to a Response output.\n"
        f"4. Bind the agent's AIModel slot to the EXISTING AIModelConnection named \"{model}\" (a Trial model — Trial "
        f"connections ARE reference-able + bindable via MCP and publish clean; do NOT expect OS-APPS-40028).{tools_txt}\n"
        f"6. A PUBLIC service action Call{name} exposing SessionId + UserInput -> Response (the standard agent "
        f"contract). Set ServerRequestTimeout=120 on the call node (LLM latency).\n"
        f"7. An exposed REST endpoint so the agent is invocable + verifiable over HTTP (exec_in_app does not reach "
        f"AIAgent actions): a REST API integration named EXACTLY \"AgentAPI\" with a POST method named EXACTLY \"Ask\", "
        f"Authentication=None (anonymous), a Text request-body input \"Question\" and a Text response-body output "
        f"\"Answer\"; inside, call AgentFlow passing Question as the user input (RequestId/SessionId = 0 / empty "
        f"grounding) and Assign the agent's Response to Answer. Set ServerRequestTimeout=120 on that call node. "
        f"The endpoint resolves to POST /<module>/rest/AgentAPI/ask.\n"
        f"After authoring, confirm change_applied=true and report the AIModel binding + any errors. The app MUST then "
        f"publish to `succeeded` with NO OS-APPS-40028. Do not publish.")


def chart(params: dict) -> str:
    """Add a native OutSystemsCharts widget (the ColumnChart 'wall' is retired — native charts author
    via MCP; only DATA wiring is grammar-friction). params: screen, chart_type(Column|Pie),
    category_field, series:[{name,value_field}], source_aggregate?."""
    scr = _p(params, "screen", required=True)
    ctype = _p(params, "chart_type", "Column")
    cat = _p(params, "category_field", required=True)
    series = _p(params, "series", [], required=True)
    src = _p(params, "source_aggregate")
    stxt = "; ".join(f'{s.get("name", s.get("value_field"))} = {s.get("value_field")}' for s in series)
    src_txt = (f" Source the DataPoints from the {src} aggregate" if src else
               " Source the DataPoints from a screen aggregate")
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {scr} screen, add a native {ctype}Chart. Do NOT declare this a wall — it authors via MCP:\n"
        f"1. addReferenceToElements the OutSystemsCharts {ctype}Chart block (it resolves as a ReferenceWebBlock in "
        f"MobileFlows[\"Charts\"]).\n"
        f"2. CreateWidget<IMobileBlockInstanceWidget> with SourceBlock = Charts\\{ctype}Chart. Set its data-spec-id via "
        f"the widget's ExtendedProperties / IObject API (a block-instance widget does NOT support .Attributes.Create()).\n"
        f"3. Build the DataPoint list(s) — ONE list per series ({stxt}), category = {cat}.{src_txt}. Build the list "
        f"from a data AGGREGATE, NEVER (System).ListAppend onto a client-action node (it throws 'target of invocation' "
        f"and rolls back the turn). Bind the DataPointList as an argument expression of shape "
        f"`<Aggregate>.List` mapped to {{ Value: <numeric valueField>, Label: <categoryField {cat}> }} — Value must be "
        f"Decimal, so wrap an Integer valueField in IntegerToDecimal(...). Qualify aggregate APIs with the "
        f"OutSystems.Model.Logic.Aggregates namespace.\n"
        f"4. Add per-series ChartSeriesStyling for colors — QUOTE hex colors (a bare '#' is a parser error, e.g. use "
        f"\"#5E6AD2\"). Verify the bars/slices render real values at RUNTIME.\nDo not publish.")


def theme(params: dict) -> str:
    """Set + ACTIVATE a theme's stylesheet (a fresh theme is inert until activated; @import is stripped
    at publish). params: css, font_faces?(css @font-face text), activate?(default true)."""
    css = _p(params, "css", required=True)
    fonts = _p(params, "font_faces")
    fonts_txt = (f" Include these @font-face rules for custom fonts (NOT @import — it is stripped at publish): "
                 f"{fonts}." if fonts else "")
    return (
        f"{_PREAMBLE}\n\n"
        f"Apply this theme stylesheet to the app:\n"
        f"1. theme = eSpace.MobileThemes.First() ?? eSpace.CreateMobileTheme(\"AppTheme\"). Set theme.StyleSheet to the "
        f"CSS below. The setter's same-call read is stale — verify the stylesheet with a SECOND applyModelApiCode call."
        f"{fonts_txt}\n"
        f"2. ACTIVATE the theme (a freshly-created theme is wired to NOTHING and renders inert): set it as the app's "
        f"DefaultMobileTheme and/or the MainFlow.Theme so screens actually use it.\n"
        f"3. Remember: Style = the class attribute (SetStyle/SetStyleClasses with class names as STRING literals — "
        f"escape \\\" ; a bare identifier is read as a variable), CustomStyle = the inline style attribute.\n"
        f"CSS:\n{css}\n"
        f"Verify at RUNTIME (loaded stylesheets / body background), not in-model. Do not publish.")


def dashboard(params: dict) -> str:
    """A KPI dashboard header: a row of stat cards (icon + big value + label + optional trend
    tag), laid out in a responsive columns grid. The theme paints .kpi-card/.kpi-icon/.kpi-value.
    params: screen, cards:[{label, value_field?|aggregate?|value?, icon?, trend?, entity?}],
    columns?(default 3). Each card's value is a live aggregate COUNT when `entity`/`aggregate`
    is given, else the literal `value`."""
    screen = _p(params, "screen", required=True)
    cards = _p(params, "cards", [], required=True)
    ncols = _p(params, "columns", min(len(cards), 4) or 1)
    lines = []
    for c in cards:
        icon = c.get("icon", "chart-bar")
        label = c.get("label", "")
        trend = f' plus a trend tag (Style class "kpi-trend") "{c["trend"]}"' if c.get("trend") else ""
        if c.get("entity") or c.get("aggregate"):
            ent = c.get("entity") or c.get("aggregate")
            filt = f' filtered where {c["filter"]}' if c.get("filter") else ""
            val = (f"the TOTAL row COUNT of {ent}{filt} — add a screen aggregate over {ent} and bind the "
                   f"Expression to that aggregate's `.Count` output (the total matching-row count). Do NOT "
                   f"bind to `.List.Length` (that is the fetched-page length, which is 1 for a count-only "
                   f"aggregate and shows a wrong '1') nor to `.List.Current.*`")
        elif c.get("value_field"):
            val = f"the value of {c['value_field']}"
        else:
            val = f'the literal "{c.get("value", "0")}"'
        lines.append(
            f'   - a KPI card (Container Style class "kpi-card", data-spec-id="kpi{_slug(label)}") containing: a '
            f'CSS-icon (Container Style class "kpi-icon glyph-{icon}"), a big value Expression (Style class '
            f'"kpi-value") showing {val}, a label (Style class "kpi-label") "{label}"{trend}.')
    body = "\n".join(lines)
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {screen} screen, add a KPI dashboard header — a row of {len(cards)} stat cards in a "
        f"{ncols}-column responsive grid (use the OutSystems UI Columns{ncols} layout or a flex Container with "
        f'Style class "kpi-row"), placed at the top of the content area (right of the nav). Author each card '
        f"structurally with its class hooks so the theme paints it (do NOT inline colors):\n{body}\n"
        f"Where a card shows a COUNT, add the backing screen aggregate and bind the value Expression to its Count "
        f"— it must render the REAL number at runtime, not a placeholder. Do not publish."
    )


def detail(params: dict) -> str:
    """The case-detail screen = the workflow made visual: a horizontal STAGE STEPPER (each stage
    done/active/pending), an optional PARALLEL-REVIEW panel (per-team status), and an optional
    AUDIT TIMELINE bound to an event entity. The theme paints .stepper/.step/.review-grid/.timeline.
    params: screen, stages:[{label, state?} | str], review_teams?:[str], review_entity?,
    review_state_field?, timeline_entity?, timeline_fields?:[str]."""
    screen = _p(params, "screen", required=True)
    stages = _p(params, "stages", [], required=True)
    teams = _p(params, "review_teams", []) or []
    review_entity = _p(params, "review_entity")
    review_state = _p(params, "review_state_field", "State")
    timeline_entity = _p(params, "timeline_entity")
    tfields = _p(params, "timeline_fields", []) or []

    def _stage(s):
        if isinstance(s, str):
            return {"label": s, "state": "pending"}
        return {"label": s.get("label", ""), "state": s.get("state", "pending")}
    stage_items = [_stage(s) for s in stages]
    steps_txt = "; ".join(
        f'step "{s["label"]}" (class "step is-{s["state"]}")' for s in stage_items)
    parts = [
        f'1. A horizontal STAGE STEPPER at the top: a Container (Style class "stepper") with, left to right, '
        f'a step per stage — {steps_txt}. Each step shows its label and a state marker; the theme colors '
        f'is-done (check), is-active (accent ring), is-pending (muted).']
    if teams:
        if review_entity:
            src = (f'bind these from the {review_entity} records for this case (each card shows the team and its '
                   f'{review_entity}.{review_state} as a status chip — Container Style "review-status chip chip-" '
                   f'+ ToLower({review_entity}.{review_state}))')
        else:
            src = "each card shows the team name and a placeholder status chip"
        parts.append(
            f'2. A PARALLEL-REVIEW panel (Container Style class "review-grid") with one review card '
            f'(Style class "review-card") per team: {", ".join(teams)}; {src}.')
    if timeline_entity:
        fld = ", ".join(tfields) if tfields else "the event description and timestamp"
        parts.append(
            f'3. An AUDIT TIMELINE (Container Style class "timeline") bound to a screen aggregate over '
            f'{timeline_entity} for this case, newest first: one timeline item (Style class "timeline-item") '
            f"per row showing {fld}. This is the immutable activity trail — READ only, never edited here.")
    body = "\n".join(parts)
    return (
        f"{_PREAMBLE}\n\n"
        f"Make the {screen} screen a rich case-detail view — the workflow made visual. Author, in order:\n{body}\n"
        f"Author each region structurally with its class hooks so the theme paints it (stepper / review grid / "
        f"timeline); do NOT inline colors. Bound regions must render REAL rows at runtime. Do not publish."
    )


def row_actions(params: dict) -> str:
    """Per-row Edit/Delete affordances on a list screen — the Update + Delete write-paths.
    Reuses the create-form's local var (New<Entity>) + Save<Entity>Record. Authored as separate
    `edit` and `delete` phases (a combined per-row action-wiring turn on a populated screen cascades,
    same lesson as create-form seam 3f). params: screen, entity, phase(edit|delete), save_action?."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    phase = _p(params, "phase", "delete")
    save_action = _p(params, "save_action", f"Save{entity}Record")
    lentity = entity.lower()
    local = f"New{entity}"
    if phase == "edit":
        body = (
            f"On the {screen} screen's {entity} table, ADD an \"Edit\" Link to EACH row (set data-spec-id="
            f"\"edit{lentity}btn\"). Do NOT rebuild the table or aggregate — only add the link cell. Its OnClick "
            f"screen action does a SINGLE Assign: {local} = <the table's aggregate>.List.Current.{entity} (the whole "
            f"row record, incl. its Id) — so the create/edit form is prefilled AND its Id is set. Because "
            f"{save_action} calls UpdateAction when the record's Id is not NullIdentifier(), a subsequent Save then "
            f"UPDATES that row. Do not change {save_action} or the form inputs; only add the Edit link + its action.")
    else:
        body = (
            f"On the {screen} screen's {entity} table, ADD a \"Delete\" Button to EACH row (set data-spec-id="
            f"\"delete{lentity}btn\"). Do NOT rebuild the table or aggregate — only add the button cell. Its OnClick "
            f"screen action calls the {entity} entity's DeleteAction passing the CURRENT row's Id, then RefreshData "
            f"the table aggregate so the row disappears. Do NOT add a confirmation dialog (keep it drivable).")
    return (f"{_PREAMBLE}\n\n{body}\nKeep the screen Anonymous. The change MUST persist + survive a page reload. "
            f"Do not publish.")


def static_entity(params: dict) -> str:
    """Author a STATIC entity (enum / lookup) WITH its records. Static entities need a MANUAL
    Long-Integer PK + EXPLICIT record Ids — auto-number is unsupported for static (memory
    `odc_mcp_local_entity_authoring_gotchas`). params: name, records:[{label, values?}],
    attributes?:[{name,dataType}] beyond the implicit Label."""
    name = _p(params, "name", required=True)
    records = _p(params, "records", [], required=True)   # flat {attr: value} per row (schema shape)
    extra = _p(params, "attributes", []) or []
    attr_txt = ""
    if extra:
        attr_txt = (" Beyond the default Label (Text) attribute, add: "
                    + "; ".join(f"{a['name']} ({_DATATYPE_WORDS.get(a.get('dataType', 'Text'), 'Text')})"
                                for a in extra) + ".")
    rec_lines = []
    for i, r in enumerate(records, 1):
        pairs = ", ".join(f"{k}={v!r}" for k, v in r.items()) or f"Label={name}{i!r}"
        rec_lines.append(f"  {i}. Id={i}, {pairs}")
    body = "\n".join(rec_lines)
    return (
        f"{_PREAMBLE}\n\n"
        f"Author a STATIC entity named {name} (CreateStaticEntity), Public=TRUE. Give it a MANUAL identifier "
        f"attribute Id of type Long Integer (NOT auto-number — auto-number is unsupported for static entities) "
        f"and set it as the identifier BEFORE adding records. It has a Label (Text) attribute by default.{attr_txt}\n"
        f"Create these records with EXPLICIT Long-Integer Ids (CreateRecord(label) then SetAttributeValue per "
        f"attribute; creating a record whose Id already exists THROWS — create each exactly once):\n{body}\n"
        f"Do NOT create screens or UI. After authoring, run model validation and report errors. Do not publish.")


def structure(params: dict) -> str:
    """Author a non-persistent Structure — a typed record shape for action / agent signatures (NOT a
    persisted entity; it has NO identifier). params: name, attributes:[{name,dataType,mandatory?,length?}]."""
    name = _p(params, "name", required=True)
    attrs = _p(params, "attributes", [], required=True)
    body = "; ".join(_attr_line(a) for a in attrs)
    return (
        f"{_PREAMBLE}\n\n"
        f"Author a non-persistent Structure named {name} (create it under the app's Structures — NOT an "
        f"entity; a Structure has NO identifier, it is a plain typed record shape). Add these attributes:\n"
        f"- {name}: {body}\n"
        f"Do NOT create an entity, screen, or UI. After authoring, run model validation and report errors. "
        f"Do not publish.")


def input_validation(params: dict) -> str:
    """Add INPUT VALIDATION to a create/edit form's save path so an invalid submit NEVER writes a row.
    params: screen, entity, fields:[{name, mandatory?, format?(Email/PhoneNumber/Integer/Decimal)}],
    save_action?. A recipe enhancement over create-form — insert a validation gate, don't rebuild the form."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    fields = _p(params, "fields", [], required=True)
    save_action = _p(params, "save_action", f"Save{entity}Record")
    local = f"New{entity}"
    checks = []
    for f in fields:
        fn = f["name"]
        if f.get("mandatory"):
            checks.append(f"{local}.{fn} is non-empty (Trim() <> \"\")")
        if f.get("format"):
            checks.append(f"{local}.{fn} is a valid {f['format']}")
    checks_txt = "; ".join(checks) or f"every input on {local} is non-empty"
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {screen} screen's save OnClick screen action for {entity}, insert INPUT VALIDATION that runs "
        f"BEFORE {save_action} is called: verify {checks_txt}. Implement it as: set each offending Input widget's "
        f"Valid=False + a ValidationMessage, and an If that SHORT-CIRCUITS the action (does NOT call {save_action} "
        f"and does NOT navigate) when ANY check fails — so an invalid submit NEVER persists a row. Also set the "
        f"mandatory flag on each required Input so the client blocks empty submits too. Do NOT rebuild the form or "
        f"the {save_action} body — only insert the validation gate ahead of the save. After authoring, run model "
        f"validation. Do not publish.")


def exception_handler(params: dict) -> str:
    """Add an OnException handler to a server/screen action's flow so it stops warning "No Exception
    Handling" and fails gracefully. params: action (the flow/action to guard), scope?(server|screen),
    message?."""
    action = _p(params, "action", required=True)
    scope = _p(params, "scope", "server")
    message = _p(params, "message", "Something went wrong. Please try again.")
    graceful = (f"show the feedback message {message!r} and end (do not let the exception propagate)"
                if scope == "screen"
                else f"log the error and return a Success=False / ErrorMessage output rather than letting the "
                     f"exception propagate")
    return (
        f"{_PREAMBLE}\n\n"
        f"Add exception handling to the {action} action's flow. Create an Exception Handler branch that handles "
        f"AllExceptions and: {graceful}. This resolves the flow's \"No Exception Handling\" warning. Do NOT change "
        f"the action's happy path. After authoring, run model validation and report remaining warnings. Do not publish.")


def _sig(items) -> str:
    return ", ".join(f"{i['name']} ({_DATATYPE_WORDS.get(i.get('dataType', 'Text'), i.get('dataType', 'Text'))})"
                     for i in (items or [])) or "none"


def service_action(params: dict) -> str:
    """Author a PUBLIC Service Action — the cross-app-callable API unit (also how an AI agent's Tools are
    exposed). A Server Action CANNOT be Public in an app (OS-BLD-40409); a Service Action IS the exposed
    operation. params: name, inputs, outputs, wraps?(existing server action the flow calls).

    TWO build-time rules the in-session validator does NOT catch — both surface as OS-DPL-50205 "model
    features validation failed" only at PUBLISH (live-proven SLATracker 2026-07-07):
      1. An exposed/public action must be SIDE-EFFECT-FREE — NO entity writes (Create/Update/Delete/
         DeleteAll/CreateOrUpdate) anywhere in its flow. Keep writes in a NON-public Server Action.
      2. Its signature must use only PORTABLE types — primitives, Structures, Lists thereof. NO Entity
         Record and NO Entity Identifier parameters. Take an entity key as a plain Long Integer input and
         cast internally with LongIntegerToIdentifier(x) where the FK comparison needs the identifier type.
    (OS-DPL-50205 is a generic bucket — also fires for a cross-app-entity FK and a public raise-event
    action; always diagnose the specific element read-only.)"""
    name = _p(params, "name", required=True)
    wraps = _p(params, "wraps")
    writes = _p(params, "writes", False)  # does the wrapped operation mutate entities?
    body = (f"Its flow calls the existing Server Action {wraps} and maps its result to the output(s)."
            if wraps else "Its flow performs the operation and sets the output(s) (typed local + Assign per "
                          "attribute; never an inline record literal).")
    write_guard = (" NOTE: this operation writes entities — a PUBLIC action may not perform entity writes "
                   "(OS-DPL-50205). Put the write in a NON-public Server Action and either make THIS action "
                   "non-public, or have it call a read-only path only." if writes else "")
    return (f"{_PREAMBLE}\n\n"
            f"Author a Service Action named {name} with Public=TRUE (a Service Action IS cross-app callable; a "
            f"Server Action can NOT be Public — OS-BLD-40409). Input parameter(s): {_sig(_p(params, 'inputs', []))}. "
            f"Output parameter(s): {_sig(_p(params, 'outputs', []))}. {body}{write_guard} "
            f"PUBLIC-SIGNATURE RULE (OS-DPL-50205 at publish, not caught in-session): use ONLY primitive / "
            f"Structure / List types in the signature — NO Entity Record or Entity Identifier parameters; take "
            f"an entity key as Long Integer and cast with LongIntegerToIdentifier() internally. PUBLIC-WRITE "
            f"RULE: this action must NOT Create/Update/Delete/DeleteAll any entity — keep writes in a separate "
            f"non-public Server Action. Build the flow with Start + End nodes and the operation between. After "
            f"authoring, run model validation and report errors. Do not publish.")


def client_action(params: dict) -> str:
    """Author a Client Action — reusable CLIENT-side logic (runs in the browser, no DB round-trip; NOT a
    server/service action). params: name, inputs, outputs, purpose."""
    name = _p(params, "name", required=True)
    purpose = _p(params, "purpose", "perform the client-side computation and set the outputs")
    return (f"{_PREAMBLE}\n\n"
            f"Author a Client Action named {name} — reusable CLIENT-side logic that runs in the browser (NOT a "
            f"Server or Service Action; do not touch the database). Input parameter(s): {_sig(_p(params, 'inputs', []))}. "
            f"Output parameter(s): {_sig(_p(params, 'outputs', []))}. The flow should: {purpose}. Build Start + End "
            f"nodes with the logic between (Assign nodes; identify each by its Variable name, not flow order). After "
            f"authoring, run model validation and report errors. Do not publish.")


def sql_action(params: dict) -> str:
    """Author a Server Action whose body is a SQL query node. params: name, statement (use {Entity} braces,
    [Attr] brackets, @Param placeholders), inputs:[{name,dataType}], returns?(a Structure/entity the rows map to)."""
    name = _p(params, "name", required=True)
    statement = _p(params, "statement", required=True)
    inputs = _p(params, "inputs", []) or []
    returns = _p(params, "returns")
    in_txt = "; ".join(f"@{i['name']} ({_DATATYPE_WORDS.get(i.get('dataType', 'Text'), 'Text')})" for i in inputs) or "none"
    ret_txt = (f" Map the result set to an output List of {returns}." if returns else "")
    return (f"{_PREAMBLE}\n\n"
            f"Author a Server Action named {name} (Public=FALSE) whose body is a single SQL query node "
            f"(CreateNode<ISQLNode>). Set its Statement VERBATIM to (in the OutSystems SQL dialect: an entity is "
            f"written {{EntityName}} in braces, an attribute [AttrName] in brackets, a query parameter @Name):\n"
            f"{statement}\n"
            f"Declare each @parameter as a node input (CreateInputParameter named without the @) and BIND it: {in_txt} "
            f"(cast a Long to an Id arg with LongIntegerToIdentifier where an identifier is compared).{ret_txt} Wire "
            f"Start -> SQL node -> End. After authoring, run model validation and report errors. Do not publish.")


def aggregate_join(params: dict) -> str:
    """Add a JOIN to a LIST screen's aggregate so it shows a related entity's display field(s) instead of a
    raw FK Id. params: screen, primary_entity, join_entity, join_attr (the FK on primary), display_fields:
    [{entity, field}]. NOT for detail screens (R2 cascade) — a list screen only."""
    screen = _p(params, "screen", required=True)
    primary = _p(params, "primary_entity", required=True)
    join_entity = _p(params, "join_entity", required=True)
    join_attr = _p(params, "join_attr", required=True)
    cols = ", ".join(f"{d['entity']}.{d['field']}" for d in _p(params, "display_fields", []) or []) or f"{join_entity}.Label"
    return (f"{_PREAMBLE}\n\n"
            f"On the {screen} screen's EXISTING list aggregate over {primary}, ADD ONE join to {join_entity} "
            f"(matching {primary}.{join_attr} = {join_entity}.Id) and surface these columns in the table: {cols}. "
            f"Use the OutSystems.Model.Logic.Aggregates API (CreateJoin) — the WRONG namespace is a CS0234 compile "
            f"error. {join_entity} must be Public + fully imported. Do NOT rebuild the aggregate or the table — only "
            f"add the join + the display column(s). Keep the screen Anonymous. After authoring, run model validation. "
            f"Do not publish.")


def global_event(params: dict) -> str:
    """Author a Global Event (+ payload). params: name, payload:[{name,dataType}]. CreateGlobalEvent THROWS in a
    BusinessProcess/Workflow-kind app — this must be a normal app."""
    name = _p(params, "name", required=True)
    return (f"{_PREAMBLE}\n\n"
            f"Author a Global Event named {name} (CreateGlobalEvent). This app must NOT be a BusinessProcess/Workflow "
            f"app — CreateGlobalEvent THROWS there. Payload parameter(s): {_sig(_p(params, 'payload', []))}. Do NOT add "
            f"a screen or entity in this turn. After authoring, run model validation and report errors. Do not publish.")


def entity_index(params: dict) -> str:
    """Add an index (optionally UNIQUE) over an entity's attribute(s). params: entity, attributes:[name], unique."""
    entity = _p(params, "entity", required=True)
    attrs = ", ".join(_p(params, "attributes", [], required=True))
    unique_txt = " as a UNIQUE index (reject duplicate values)" if _p(params, "unique") else ""
    return (f"{_PREAMBLE}\n\n"
            f"On the {entity} entity, add an index over attribute(s) {attrs}{unique_txt}. Do NOT change the entity's "
            f"identifier or any attribute, and do NOT add a screen/UI — ONLY add the index. After authoring, run model "
            f"validation and report errors. Do not publish.")


def workflow(params: dict) -> str:
    """Author a Business Process (BPT) — cross-app refs + process in ONE turn (runtime-proven, wfprobe
    2026-07-07). The trigger Global Event + the Service Actions the activities call live in a PRODUCER app
    (a NORMAL app — CreateGlobalEvent THROWS in a Workflow app) and are referenced cross-app. Sequence
    (owned by the driver/plan): the producer app already holds the event + PUBLIC service action(s);
    `app_create kind=BusinessProcess` registers the Workflow app WITHOUT auto-publishing (0 deployments —
    the safe window); this turn references the producer's elements AND authors the process; then the
    orchestrator publishes ONCE with the process present. A 0-process Workflow app publish corrupts its
    verify cache, so NEVER publish before this turn lands. params: name, producer_app, trigger_event,
    activities:[{name, calls_service_action}] (an auto-activity can call ONLY a PUBLIC Service Action)."""
    name = _p(params, "name", required=True)
    producer = _p(params, "producer_app", required=True)
    trigger = _p(params, "trigger_event", required=True)
    activities = _p(params, "activities", [], required=True)
    sa_names = sorted({a["calls_service_action"] for a in activities})
    acts = "\n".join(
        f"   - an Automatic Activity node '{a['name']}' whose ActionToTrigger is the referenced PUBLIC Service "
        f"Action {a['calls_service_action']} (an auto-activity can call ONLY a Public Service Action; set its "
        f"arguments — e.g. NullIdentifier() for an Identifier input when no business value is needed)"
        for a in activities)
    return (f"{_PREAMBLE}\n\n"
            f"This is a Workflow (BusinessProcess-kind) app with ZERO processes; it has NEVER been published and "
            f"must NOT be published until it has a process (a 0-process Workflow app corrupts its verify cache). "
            f"Author BOTH of the following in THIS one turn, then STOP (do NOT publish):\n"
            f"1. Reference the producer app '{producer}' and import (all PUBLIC): the Global Event {trigger} and the "
            f"Service Action(s) {', '.join(sa_names)}. Use addReferenceToElements + AddDependency(ParseGlobalKey) + "
            f"RefreshDependencies. The event resolves under the reference's GlobalEvents collection; the service "
            f"actions under its ServiceActions collection.\n"
            f"2. Author a Business Process named {name} (eSpace.CreateBusinessProcess) with CreateNode<T> + "
            f".Target/ConnectedBelow:\n"
            f"   - a Start node with StartProcessOn = the referenced {trigger} Global Event and TriggerMode = Event;\n{acts}\n"
            f"   - an End node; wire Start -> activities -> End.\n"
            f"After authoring, run model validation (expect 0 errors; a 'missing event handler' + a 'no User "
            f"Provider' warning are BENIGN for a consume-only workflow app). Do NOT publish — the orchestrator "
            f"publishes the process + refs in one shot (never a 0-process Workflow app).")


def app_reference(params: dict) -> str:
    """Reference another app's PUBLIC elements so this app can consume them. params: producer_app,
    elements:[{kind, name}] (kind: Entity | ServiceAction | StaticEntity). Import EVERY touched entity
    INCLUDING static ones — a hidden Id-only FK stub trips OS-APPS-40028 at publish."""
    producer = _p(params, "producer_app", required=True)
    elements = _p(params, "elements", [], required=True)
    el = ", ".join(f"{e['name']} ({e.get('kind', 'Entity')})" for e in elements)
    return (f"{_PREAMBLE}\n\n"
            f"Add a dependency on the producer app '{producer}' and import these PUBLIC elements so this app can use "
            f"them: {el}. Use addReferenceToElements (it does the dependency wiring; the globalKey is "
            f"producerKey*elementKey with an ASTERISK — ParseGlobalKey rejects the colon form), then RefreshDependencies. "
            f"A referenced ENTITY is CONSUME-ONLY: read it via an aggregate/read logic — do NOT create a local entity "
            f"with a FOREIGN KEY to a cross-app referenced entity; that FK constraint cannot be materialized across app "
            f"database boundaries and FAILS the deploy with OS-DPL-50205 'Model features validation failed' (verified "
            f"2026-07-07, static AND regular). Referenced Service Actions + Global Events are call/consume targets and "
            f"deploy fine (proven, wfprobe). Import EVERY entity you touch INCLUDING any STATIC entity — an entity "
            f"referenced only by Id (a hidden Id-only stub, not fully imported) can make the OML invalid at publish "
            f"(OS-APPS-40028); recover in-session via TryParseGlobalKey + AddDependency + RefreshDependencies. After "
            f"authoring, run model validation. Do not publish.")


def external_library(params: dict) -> str:
    """NOT a Mentor turn — the extlib_* MCP lifecycle for an external .NET library. Emitted so the driver
    executes the upload/publish flow (not mentor_start). params: name, source? (path/description). Needs
    .NET 8; a GenerationError is TERMINAL; publishing on a non-ReadyForReview status returns HTTP 500."""
    name = _p(params, "name", required=True)
    source = _p(params, "source", "the provided .NET assembly")
    return (f"[EXTERNAL-LIBRARY LIFECYCLE — NOT a mentor_start turn; use the extlib_* MCP tools]\n"
            f"Publish the external .NET library '{name}' from {source}:\n"
            f"1. extlib_upload(the .NET 8 assembly bytes) — returns an operation to poll.\n"
            f"2. Poll extlib_status to terminal. A GenerationError is TERMINAL (do NOT retry blindly — the assembly "
            f"is incompatible; needs .NET 8).\n"
            f"3. Only once status is ReadyForReview, extlib_publish — publishing on any other status returns HTTP 500.\n"
            f"Verify with extlib_status / extlib_contents that the library's actions are exposed, then reference it "
            f"from a consumer app via the app-reference flow.")


def json_1line(obj) -> str:
    import json
    return json.dumps(obj, separators=(", ", "="))


RECIPES = {
    "data-model": data_model,
    "static-entity": static_entity,
    "structure": structure,
    "input-validation": input_validation,
    "exception-handler": exception_handler,
    "service-action": service_action,
    "client-action": client_action,
    "sql-action": sql_action,
    "aggregate-join": aggregate_join,
    "global-event": global_event,
    "entity-index": entity_index,
    "workflow": workflow,
    "app-reference": app_reference,
    "external-library": external_library,
    "screen": screen,
    "nav-block": nav_block,
    "place-nav": place_nav,
    "action-button": action_button,
    "list-screen": list_screen,
    "role-gate": role_gate,
    "login": login,
    "seed-entity": seed_entity,
    "seed-graph": seed_graph,
    "create-form": create_form,
    "row-actions": row_actions,
    "agent": agent,
    "chart": chart,
    "theme": theme,
    "dashboard": dashboard,
    "detail": detail,
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


def _columns_structured(comp: dict) -> list:
    """The component's columns preserving each cell's render `kind` (chip/badge/avatar/glyph/…)
    so list_screen authors styled cells. Falls back to bare field strings if none declared."""
    return list(comp.get("columns", []) or [])


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


def _identity_attr(spec: dict, user_entity: str) -> str:
    """The login-identity attribute of the user entity — the first non-id, non-audit Text attr
    (what testUsers seed populates and the login screen matches on)."""
    for a in _entities_map(spec).get(user_entity, {}).get("attributes", []):
        if a.get("dataType") == "Text" and not a.get("isIdentifier") and a["name"] not in _AUDIT_ATTRS:
            return a["name"]
    return "Name"


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


def _sample_rows(spec: dict, entity: str, n: int = 3) -> list:
    """Rows to seed a display entity (seam 3g): the spec's `sampleData` if present, else n
    deterministic placeholder rows over the entity's editable text fields."""
    ent = _entities_map(spec).get(entity, {})
    if ent.get("sampleData"):
        return ent["sampleData"]
    fields = [f for f in _form_fields(spec, entity, cap=2) if f != "Name" or "Name" in
              [a["name"] for a in ent.get("attributes", [])]]
    if not fields:
        return []
    return [{f: f"Sample {entity} {i}" for f in fields} for i in range(1, n + 1)]


def _natural_key(spec: dict, entity: str) -> str:
    """The attribute a child seed row references a PARENT by — a human-readable, unique-ish key (not
    the auto-number Id, which does not exist until the parent is created). Prefers an attribute flagged
    `naturalKey: true`, else the first non-id, non-FK, non-audit Text attribute, else 'Name'."""
    attrs = _entities_map(spec).get(entity, {}).get("attributes", [])
    for a in attrs:
        if a.get("naturalKey"):
            return a["name"]
    for a in attrs:
        if (a.get("dataType") == "Text" and not a.get("isIdentifier")
                and not a.get("references") and a["name"] not in _AUDIT_ATTRS):
            return a["name"]
    return "Name"


def _fk_refs(spec: dict, entity: str) -> list:
    """FK attributes on `entity`, each paired with its parent + the parent's natural key. Lets the seed
    resolve a natural-key value carried in a child row to the parent's real Id (SEED-A). Returns
    [{attr, parent, parent_key}]."""
    refs = []
    for a in _entities_map(spec).get(entity, {}).get("attributes", []):
        parent = a.get("references")
        if parent and not a.get("isIdentifier"):
            refs.append({"attr": a["name"], "parent": parent, "parent_key": _natural_key(spec, parent)})
    return refs


def _seed_topo_order(names: list, spec: dict) -> list:
    """Order entity names PARENTS-BEFORE-CHILDREN so a child's FK can resolve to an already-seeded
    parent (Kahn). Only FK deps WITHIN the set constrain order; external/already-seeded parents are
    treated as satisfied. Deterministic (ties alphabetical); a cycle emits its remainder alphabetically
    (best-effort — a real FK cycle is a data-model smell the arch-gate flags, not seed's job to fix)."""
    nameset = set(names)
    deps = {n: {a.get("references")
                for a in _entities_map(spec).get(n, {}).get("attributes", [])
                if a.get("references") in nameset and a.get("references") != n}
            for n in names}
    ordered, remaining = [], set(names)
    while remaining:
        ready = sorted(n for n in remaining if not (deps[n] & remaining))
        if not ready:
            ordered.extend(sorted(remaining))
            break
        ordered.extend(ready)
        remaining -= set(ready)
    return ordered


def _theme_css(t: dict) -> str:
    """Compile design.theme tokens (palette/typography/spacing + raw css) into a stylesheet string
    for the theme recipe. Each token group becomes deterministic :root custom properties so the same
    token set always renders byte-identical CSS. Palette keys stay UNPREFIXED (--primary), so the
    --<paletteKey> runtime theme-applied check keeps working; typography -> --font-<k>, spacing ->
    --space-<k>. fontFaces flows separately via the recipe's font_faces param."""
    root_vars = []
    for prefix, group in (("", t.get("palette") or {}),
                          ("font-", t.get("typography") or {}),
                          ("space-", t.get("spacing") or {})):
        for k, v in group.items():
            root_vars.append(f"--{prefix}{k}: {v}")
    parts = []
    if root_vars:
        parts.append(":root { " + "; ".join(root_vars) + " }")
    if t.get("css"):
        parts.append(t["css"])
    return "\n".join(parts) or "/* theme */"


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

    # Scaffold FIRST (seam 3d): the data model, then all screens with Anonymous baked. list-screen
    # and create-form steps below assume the entities + screens already exist.
    all_entities = spec.get("dataModel", {}).get("entities", [])
    # Batch C: foundational cross-app plumbing FIRST — an external .NET library (extlib lifecycle, not a
    # Mentor turn), then references to producer apps/libraries (elements other units consume).
    for lib in spec.get("externalLibraries", []) or []:
        steps.append({"recipe": "external-library", "why": f"external .NET library {lib['name']}",
                      "params": {"name": lib["name"], "source": lib.get("source", "the provided .NET assembly")}})
    for ref in spec.get("appReferences", []) or []:
        steps.append({"recipe": "app-reference", "why": f"reference {ref['producerApp']}",
                      "params": {"producer_app": ref["producerApp"], "elements": ref.get("elements", [])}})
    # Batch A: structures + static entities (enums) are authored BEFORE the regular data model — a
    # regular entity may FK a static one, and structures type action signatures. Each static entity is
    # its own turn (explicit records + manual Long PK); structures one per turn.
    for st in spec.get("structures", []) or []:
        steps.append({"recipe": "structure", "why": f"spec.structures {st['name']}",
                      "params": {"name": st["name"], "attributes": st.get("attributes", [])}})
    for e in [e for e in all_entities if e.get("isStatic")]:
        steps.append({"recipe": "static-entity", "why": f"static entity {e['name']} + records",
                      "params": {"name": e["name"], "records": e.get("records", []),
                                 "attributes": [a for a in e.get("attributes", [])
                                                if not a.get("isIdentifier") and a.get("name") != "Label"]}})
    entities = [e for e in all_entities if not e.get("isStatic")]
    if entities:
        steps.append({"recipe": "data-model", "why": "spec.dataModel.entities (all in one turn)",
                      "params": {"entities": entities}})
    # Batch B: entity indexes (after the entities exist).
    for e in all_entities:
        for idx in e.get("indexes", []) or []:
            steps.append({"recipe": "entity-index",
                          "why": f"index on {e['name']}.{'+'.join(idx.get('attributes', []))}",
                          "params": {"entity": e["name"], "attributes": idx.get("attributes", []),
                                     "unique": bool(idx.get("unique"))}})
    if screens:
        scaffold = []
        for i, s in enumerate(screens):
            scaffold.append({"id": s["id"], "name": s.get("name", s["id"]),
                             "route": s.get("route", "/" + s["id"]),
                             "input_params": s.get("inputParameters", []),
                             "default": bool(s.get("isDefault")) or (i == 0 and not any(
                                 sc.get("isDefault") for sc in screens))})
        steps.append({"recipe": "screen", "why": "spec.screens scaffold (Anonymous baked, change_applied-gated)",
                      "params": {"screens": scaffold}})

    nav = spec.get("navigation")
    if nav and nav.get("items"):
        def _nav_item(i: dict) -> dict:
            item = {"label": i.get("label", ""), "toScreen": i.get("toScreen", "")}
            for k in ("tag", "badge", "section"):   # product-UI shell extras, only when declared
                if i.get(k) not in (None, ""):
                    item[k] = i[k]
            return item
        nav_params = {
            "block_name": nav.get("block", "SidebarNav"),
            "workspace_label": nav.get("workspaceLabel", ""),
            "items": [_nav_item(i) for i in nav["items"]],
        }
        # Only wire a logout link when the app actually has a login screen — otherwise it would
        # navigate to a non-existent screen, and the block's nav-in-a-(would-be-public)-block risk.
        if auth.get("loginScreen"):
            nav_params["logout_to"] = login
        for src, dst in (("brand", "brand"), ("subtitle", "subtitle"),
                         ("userLabel", "user_label"), ("userRole", "user_role")):
            if nav.get(src):
                nav_params[dst] = nav[src]
        steps.append({"recipe": "nav-block", "why": "app.navigation declared", "params": nav_params})
        # Placing the block on every screen is a SEPARATE step — authoring the block does not render it.
        if screens:
            steps.append({"recipe": "place-nav", "why": "instantiate the nav block on every screen",
                          "params": {"block_name": nav_params["block_name"],
                                     "screens": [s.get("name", s["id"]) for s in screens]}})

    if auth.get("provider") == "app-local" and auth.get("userEntity") and auth.get("testUsers"):
        ue, aa = auth["userEntity"], auth.get("adminAttribute")
        id_attr = _identity_attr(spec, ue)   # the login identity attr the seed must populate + login matches on
        rows = []
        for tu in auth["testUsers"]:
            row = {id_attr: tu.get("label", tu.get("role", ""))}
            if aa:
                row[aa] = bool(tu.get("isAdmin", tu.get("role") == "Admin"))
            rows.append(row)
        steps.append({"recipe": "seed-entity", "why": f"auth.testUsers seed {ue}",
                      "params": {"entity": ue, "rows": rows, "bootstrap_screens": [login]}})
        # app-local login screen: identity input -> lookup -> localStorage session -> home.
        login_screen = auth.get("loginScreen")
        if login_screen:
            home = next((s["id"] for s in screens if s["id"] != login_screen), login_screen)
            steps.append({"recipe": "login", "why": f"app-local login on {login_screen}",
                          "params": {"screen": login_screen, "user_entity": ue,
                                     "identity_attr": id_attr, "home": home}})

    for s in screens:
        for c in s.get("components", []):
            if c.get("type") in _DATA_COMPONENT_TYPES and c.get("boundTo"):
                entity = c["boundTo"].split(".")[0]
                params = {"screen": s["id"], "entity": entity,
                          "columns": _columns_structured(c) or ["(entity display fields)"],
                          "component_id": c["id"]}
                # seam 3e: emit the spec's declared row-nav component (its label + id) so the
                # gate's parent-nav finds it — from ANY nav entry on the screen, not just the table.
                nav_entry = next((e for e in s.get("navigation", []) if e.get("toScreen")), None)
                if nav_entry:
                    params["detail_screen"] = nav_entry["toScreen"]
                    comp = next((cc for cc in s.get("components", [])
                                 if cc.get("id") == nav_entry.get("fromComponent")), None)
                    if comp and comp.get("label"):
                        params["nav_label"] = comp["label"]
                        params["nav_component_id"] = comp["id"]
                steps.append({"recipe": "list-screen",
                              "why": f"{c['id']} ({c['type']}) bound to {entity}", "params": params})
                # Batch B: an aggregate JOIN on this list to show a related entity's display fields.
                aj = s.get("aggregateJoin")
                if aj:
                    steps.append({"recipe": "aggregate-join",
                                  "why": f"{s['id']} join {entity} -> {aj['joinEntity']}",
                                  "params": {"screen": s["id"], "primary_entity": entity,
                                             "join_entity": aj["joinEntity"], "join_attr": aj["joinAttr"],
                                             "display_fields": aj.get("displayFields", [])}})
                break  # one primary data list per screen
        acc = s.get("access") or {}
        if acc.get("adminOnly") or acc.get("requiresRole"):
            steps.append({"recipe": "role-gate", "why": f"screen.access on {s['id']}", "params": {
                "screen": s["id"],
                "user_entity": auth.get("userEntity", "Member"),
                "admin_attr": auth.get("adminAttribute", "IsAdmin"),
                "home": acc.get("redirectTo", "Home"),
                "login": login,
                "identity_attr": _identity_attr(spec, auth.get("userEntity", "Member")),
            }})
        # Phase 6 write-paths: mutating actions become build steps (definition of done).
        # CreateEntity -> create-form (3 thrash-free phases); UpdateEntity/DeleteEntity -> row-actions.
        does_all = set()
        for a in s.get("actions", []):
            does_all |= set(a.get("does", []))
        entity = _screen_write_entity(spec, s) if (_MUTATING & does_all) else None
        if entity:
            if "CreateEntity" in does_all:
                p = {"screen": s["id"], "entity": entity, "fields": _form_fields(spec, entity)}
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
                # Seam 3f (revised after batcha): action FIRST (its own turn), then Form+widgets+wire in
                # ONE turn — the PROVEN-persist shape. The old bare-widgets-only turn phantomed 4× (batcha);
                # keeping the action separate avoids the action+form+wire mega-cascade the split guarded against.
                why = f"{s['id']} CreateEntity {entity}"
                steps.append({"recipe": "create-form", "why": f"{why} — server action (fresh turn)",
                              "params": {**p, "phase": "action"}})
                steps.append({"recipe": "create-form",
                              "why": f"{why} — Form + inputs + wire in one turn (fresh; publish once after)",
                              "params": {**p, "phase": "combined"}})
                # Batch A opt-ins on the write-path: input validation + exception handling.
                create_actions = [a for a in s.get("actions", []) if "CreateEntity" in set(a.get("does", []))]
                if any(a.get("validate") for a in create_actions):
                    attrs = {a["name"]: a for a in _entities_map(spec).get(entity, {}).get("attributes", [])}
                    vfields = [{"name": fld,
                                "mandatory": bool(attrs.get(fld, {}).get("mandatory")),
                                "format": (attrs.get(fld, {}).get("dataType")
                                           if attrs.get(fld, {}).get("dataType") in
                                           {"Email", "PhoneNumber", "Integer", "Decimal"} else None)}
                               for fld in p["fields"]]
                    steps.append({"recipe": "input-validation", "why": f"{s['id']} validate {entity} inputs",
                                  "params": {"screen": s["id"], "entity": entity, "fields": vfields}})
                if any(a.get("guardExceptions") for a in create_actions):
                    steps.append({"recipe": "exception-handler", "why": f"{s['id']} guard Save{entity}Record",
                                  "params": {"action": f"Save{entity}Record", "scope": "server"}})
            # Update/Delete: per-row affordances on a LIST, each its own turn (avoid the combined-edit
            # cascade). Skip on a detail screen with an id_param — its create-form already updates in place.
            has_list = any(c.get("type") in _DATA_COMPONENT_TYPES
                           and (c.get("boundTo") or "").split(".")[0] == entity
                           for c in s.get("components", []))
            if has_list and "UpdateEntity" in does_all:
                steps.append({"recipe": "row-actions", "why": f"{s['id']} UpdateEntity {entity} (per-row Edit)",
                              "params": {"screen": s["id"], "entity": entity, "phase": "edit"}})
            if has_list and "DeleteEntity" in does_all:
                steps.append({"recipe": "row-actions", "why": f"{s['id']} DeleteEntity {entity} (per-row Delete)",
                              "params": {"screen": s["id"], "entity": entity, "phase": "delete"}})
        # v0.3: native charts declared on the screen -> one `chart` step each.
        for ch in s.get("charts", []) or []:
            steps.append({"recipe": "chart",
                          "why": f"{s['id']}.{ch['id']} ({ch['chartType']}Chart)",
                          "params": {"screen": s["id"], "chart_type": ch["chartType"],
                                     "category_field": ch["categoryField"], "series": ch["series"],
                                     "source_aggregate": ch.get("sourceAggregate")}})
        # UI-A: a KPI dashboard header on this screen -> `dashboard` step.
        dash = s.get("dashboard")
        if dash and dash.get("cards"):
            p = {"screen": s["id"], "cards": dash["cards"]}
            if dash.get("columns"):
                p["columns"] = dash["columns"]
            steps.append({"recipe": "dashboard", "why": f"{s['id']} KPI dashboard header", "params": p})
        # UI-A: a rich case-detail screen (stepper + parallel reviews + audit timeline) -> `detail` step.
        det = s.get("detail")
        if det and det.get("stages"):
            p = {"screen": s["id"], "stages": det["stages"]}
            for src, dst in (("reviewTeams", "review_teams"), ("reviewEntity", "review_entity"),
                             ("reviewStateField", "review_state_field"),
                             ("timelineEntity", "timeline_entity"), ("timelineFields", "timeline_fields")):
                if det.get(src):
                    p[dst] = det[src]
            steps.append({"recipe": "detail", "why": f"{s['id']} case-detail (workflow made visual)",
                          "params": p})
            # workflow state-transition buttons that mutate the screen's entity-typed input record
            if det.get("stateActions"):
                ip = next((x for x in s.get("inputParameters", []) if x.get("references")), None)
                if ip:
                    steps.append({"recipe": "action-button",
                                  "why": f"{s['id']} workflow state actions",
                                  "params": {"screen": s["id"], "entity": ip["references"],
                                             "id_param": ip["name"], "buttons": det["stateActions"]}})

    # Seam 3g: an entity rendered in a list but with NO create UI can never be populated at runtime —
    # seed it so its list renders (and any parent-context create on it can be reached by the gate).
    listed = {c["boundTo"].split(".")[0] for s in screens for c in s.get("components", [])
              if c.get("type") in _DATA_COMPONENT_TYPES and c.get("boundTo")}
    # a detail screen's review/timeline panels bind entities that appear in no table — seed them too,
    # else the "workflow made visual" hero renders empty review cards + timeline.
    for s in screens:
        det = s.get("detail") or {}
        for k in ("reviewEntity", "timelineEntity"):
            if det.get(k):
                listed.add(det[k])
    created = set()
    for s in screens:
        for a in s.get("actions", []):
            if "CreateEntity" in set(a.get("does", [])):
                we = _screen_write_entity(spec, s)
                if we:
                    created.add(we)
    already_seeded = {st["params"].get("entity") for st in steps if st["recipe"] == "seed-entity"}
    default_screen = next((s["id"] for s in screens if s.get("isDefault")),
                          screens[0]["id"] if screens else None)
    # SEED-A: parents-before-children (topo over FKs). An FK-linked set is seeded as ONE graph
    # (seed-graph: capture parent Id from CreateAction return — an aggregate lookup can't see rows
    # created in the same action at runtime). A standalone set stays per-entity seed-entity.
    # FK integrity: a captured-Id seed graph needs its PARENTS seeded even if a parent has a create
    # UI (is in `created`) — else the child's captured-Id FK ref points at a never-created local.
    graph_set = set(listed - created - already_seeded)
    changed = True
    while changed:
        changed = False
        for ent in list(graph_set):
            for fr in _fk_refs(spec, ent):
                parent = fr["parent"]
                if parent in listed and parent not in graph_set and parent not in already_seeded:
                    graph_set.add(parent)
                    changed = True
    seed_order = _seed_topo_order(sorted(graph_set), spec)
    seed_ents = []
    for ent in seed_order:
        rows = _sample_rows(spec, ent)
        if rows:
            seed_ents.append({"name": ent, "rows": rows, "natural_key": _natural_key(spec, ent),
                              "fk_refs": _fk_refs(spec, ent)})
    if any(e["fk_refs"] for e in seed_ents) and len(seed_ents) > 1:
        p = {"entities": seed_ents}
        if default_screen:
            p["bootstrap_screens"] = [default_screen]
        steps.append({"recipe": "seed-graph",
                      "why": f"FK-linked seed graph ({', '.join(e['name'] for e in seed_ents)})", "params": p})
    else:
        for e in seed_ents:
            p = {"entity": e["name"], "rows": e["rows"]}
            if e["fk_refs"]:
                p["fk_refs"] = e["fk_refs"]
            if default_screen:
                p["bootstrap_screens"] = [default_screen]
            steps.append({"recipe": "seed-entity",
                          "why": f"{e['name']} is listed but has no create UI — seed so its list renders",
                          "params": p})

    # v0.3: app theme from design.theme tokens.
    design = spec.get("design") or {}
    if design.get("theme"):
        t = design["theme"]
        steps.append({"recipe": "theme", "why": "design.theme tokens",
                      "params": {"css": _theme_css(t), "font_faces": t.get("fontFaces")}})
    # v0.3: app-level AI agents — each is its OWN app_create kind=AIAgent (a separate app).
    for ag in spec.get("agents", []) or []:
        steps.append({"recipe": "agent", "why": f"AI agent {ag['name']} (separate AIAgent app)",
                      "params": {"agent_name": ag["name"], "system_prompt": ag["systemPrompt"],
                                 "model_connection": ag.get("modelConnection", "TrialClaudeHaiku4_5"),
                                 "tools": ag.get("tools", [])}})
    # Batch B: standalone logic units (emitted last — a service action may wrap a write-path server action).
    _LOGIC_KIND = {"serviceAction": "service-action", "clientAction": "client-action",
                   "sqlAction": "sql-action", "globalEvent": "global-event"}
    for unit in spec.get("logic", []) or []:
        recipe = _LOGIC_KIND.get(unit.get("kind"))
        if not recipe:
            continue
        p = {k: v for k, v in unit.items() if k != "kind"}
        steps.append({"recipe": recipe, "why": f"logic {unit['kind']} {unit.get('name', '')}", "params": p})
    # Batch C: Business Processes LAST — a process needs its trigger Global Event + the PUBLIC Service Actions
    # its activities call to already exist. (The driver app_creates a BusinessProcess-kind app + authors the
    # process before the FIRST publish — a 0-process Workflow app corrupts its verify cache.)
    for proc in spec.get("processes", []) or []:
        steps.append({"recipe": "workflow", "why": f"business process {proc['name']}",
                      "params": {"name": proc["name"], "producer_app": proc["producerApp"],
                                 "trigger_event": proc["triggerEvent"],
                                 "activities": proc.get("activities", [])}})
    return steps
