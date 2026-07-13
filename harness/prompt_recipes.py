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
    "page-header page-title page-subtitle header-actions btn-primary btn-secondary "
    "kpi-card kpi-icon kpi-value kpi-label kpi-trend "
    "stepper step is-done is-active is-pending review-grid review-card review-status "
    "timeline timeline-item"
).split()


def _slug(text: str) -> str:
    """Lowercase a static value into a CSS-class-safe suffix (for literal chip/badge values)."""
    return "".join(c if c.isalnum() else "-" for c in str(text).lower()).strip("-")


def _pascal(text: str) -> str:
    """An identifier-safe PascalCase token (for a per-card aggregate name, e.g. 'Open Cases' -> 'OpenCases')."""
    parts = [p for p in "".join(c if c.isalnum() else " " for c in str(text)).split() if p]
    tok = "".join(p[:1].upper() + p[1:] for p in parts) or "Card"
    return tok if tok[0].isalpha() else "A" + tok


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
        return (f'`{label}`: a status {kind} — an Expression showing {q} INSIDE a Container (the Container '
                f'is REQUIRED — without it the value renders as bare text, not a pill; live-proven '
                f'structure-drop, harvest #2) whose Style is the EXPRESSION "{kind} {kind}-" + ToLower({q}) '
                f'(so ".{kind}" makes the rounded pill and ".{kind}-<value>" tints it per the theme). Do '
                f'NOT hardcode one class and do NOT drop the Container.')
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


def _apply_action_name(label: str) -> str:
    return "Apply" + _slug(label).title().replace("-", "")


def action_button(params: dict) -> str:
    """ONE state-transition action button on a detail screen — a workflow write-path. ATOMIC by phase
    (one concern per Mentor turn, like create-form): phase='action' authors ONLY the NON-PUBLIC server
    action; phase='wire' adds ONLY the button + wires it; phase='combined' (default) does both in one
    small turn. params: screen, entity, id_param, buttons:[{label, set:{field:value}, style?}], phase."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    id_param = _p(params, "id_param", f"{entity}Id")
    buttons = _p(params, "buttons", [], required=True)
    phase = _p(params, "phase", "combined")
    b = buttons[0]                                     # atomic recipe: one button per call
    label = b["label"]
    act = _apply_action_name(label)
    sets = "; ".join(f'{k} = "{v}"' for k, v in (b.get("set") or {}).items())
    style = f' (Style class "{b["style"]}")' if b.get("style") else ""

    action_txt = (
        f"Author ONE NON-PUBLIC server action {act} (it WRITES an entity, so it MUST be non-public — a public "
        f"entity-writer trips OS-DPL-50205 at publish). Give it a mandatory input Id (the {entity} Id). Inside: "
        f"fetch the {entity} whose Id = that input (an aggregate max 1), Assign {{ {sets} }} onto a typed local "
        f"{entity} record that carries the Id (NEVER an inline record literal), and call {entity}.UpdateAction on "
        f"it. Just this one server action, nothing else.")
    wire_txt = (
        f'On the {screen} screen, add a single Button labelled "{label}"{style} (data-spec-id="{_slug(label)}btn") '
        f'in an action bar near the top of the content. Wire its OnClick to a screen action that calls the existing '
        f'{act} server action passing the screen\'s {id_param} input as the Id, then RefreshData on the screen\'s '
        f'{entity} aggregate so the change shows without a reload. Do not author the {act} server action here — it '
        f'already exists.')

    if phase == "action":
        body = action_txt
    elif phase == "wire":
        body = wire_txt
    else:  # combined
        body = (f"On the {screen} screen, add ONE state-transition button that mutates the {entity} identified by "
                f"the screen's {id_param} input:\n1. {action_txt}\n2. {wire_txt}")
    return (
        f"{_PREAMBLE}\n\n{body}\n"
        f"Verify at RUNTIME that clicking the button changes the {entity}'s field(s) and the change survives a "
        f"reload. Do not publish."
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


def top_bar(params: dict) -> str:
    """Author the app-shell TOP BAR as a shared Web Block placed above the content on every screen —
    breadcrumb + env chip + a primary CTA. This horizontal band is the single biggest 'modern app'
    element; without it a themed app reads as unfinished (live-proven on the Rivian portal). Author it
    ONCE as a shared block (like nav_block) with a Crumb input, then place it. params: block_name
    (default AppTopBar), app_label, env_label (default 'ODC · PROD'), cta_label?, cta_screen?|cta_action?,
    screens?(to place on)."""
    block = _p(params, "block_name", "AppTopBar")
    app_label = _p(params, "app_label", "App")
    env_label = _p(params, "env_label", "ODC · PROD")
    cta_label = _p(params, "cta_label")
    cta_target = _p(params, "cta_screen") or _p(params, "cta_action")
    screens = _p(params, "screens", [])
    cta_txt = (f' a right-aligned primary Button labelled "{cta_label}" (Style class "btn-primary", '
               f'data-spec-id="topbarcta") wired to {cta_target}' if cta_label and cta_target else
               (f' a right-aligned primary Button labelled "{cta_label}" (Style class "btn-primary", '
                f'data-spec-id="topbarcta")' if cta_label else " no CTA button"))
    place_txt = (f" Then place ONE instance as the FIRST widget (above the content) on each of: "
                 f"{', '.join(screens)}, passing that screen's name as Crumb." if screens else
                 " Place ONE instance above the content area on each screen, passing the screen name as Crumb.")
    return (
        f"{_PREAMBLE}\n\n"
        f"Author a reusable Web Block named {block} — the app-shell TOP BAR — with a single Text input "
        f"parameter Crumb (the current screen label). Its root Container has Style class \"app-topbar\" "
        f"(a horizontal flex row, data-spec-id=\"apptopbar\") containing, left-to-right: (1) a breadcrumb "
        f"(Style class \"breadcrumb\") showing \"{app_label} / \" then the Crumb input inside a <b> "
        f"(Expression, bold current segment); (2) an env chip (Style class \"env-chip\", mono) showing "
        f"\"{env_label}\"; (3){cta_txt}. The theme paints .app-topbar/.breadcrumb/.env-chip/.btn-primary "
        f"(see the UI class contract) — do NOT inline colors.{place_txt} Author the block ONCE; never "
        f"rebuild it per screen. Do not publish.")


def page_header(params: dict) -> str:
    """A screen's lead header: a big title + optional subtitle + optional status/tier tag + a
    right-aligned row of action buttons (composes action-buttons into the header — mockup:
    'Acme Drivetrains — Regen Brake Module  T1·CRITICAL' + Approve/Send Back/Activate). params:
    screen, title (literal text or an Expression), subtitle?, tag?{text, kind?}, actions?:[{label,
    screen?|action?, primary?}]."""
    screen = _p(params, "screen", required=True)
    title = _p(params, "title", required=True)
    subtitle = _p(params, "subtitle")
    tag = _p(params, "tag")
    actions = _p(params, "actions", [])
    tag_txt = ""
    if tag:
        kind = _slug(tag.get("kind", "")) if isinstance(tag, dict) else ""
        text = tag.get("text", "") if isinstance(tag, dict) else str(tag)
        klass = f"tag tag-{kind}" if kind else "tag"
        tag_txt = f' followed inline by a tag (Container Style class "{klass}") showing "{text}"'
    sub_txt = f' Below the title, a subtitle (Style class "page-subtitle") showing {subtitle}.' if subtitle else ""
    if actions:
        btns = []
        for a in actions:
            label = a.get("label", "Action")
            target = a.get("screen") or a.get("action") or ""
            klass = "btn-primary" if a.get("primary") else "btn-secondary"
            wire = f" wired to {target}" if target else ""
            btns.append(f'a Button "{label}" (Style class "{klass}", data-spec-id="hdr{_slug(label)}btn"){wire}')
        act_txt = (f' A right-aligned action row (Container Style class "header-actions") with: '
                   f'{"; ".join(btns)}.')
    else:
        act_txt = ""
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {screen} screen, add a PAGE HEADER at the top of the content area (below the top bar, "
        f"right of the nav). It is a Container (Style class \"page-header\", data-spec-id=\"pageheader\") "
        f"containing: a heading (Style class \"page-title\") showing {title}{tag_txt}.{sub_txt}{act_txt} "
        f"The theme paints .page-title/.page-subtitle/.tag/.header-actions/.btn-primary — do NOT inline "
        f"colors. Every button must be a real Button widget with its data-spec-id. Do not publish.")


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


def _declared_create_button(spec: dict, screen_id: str, entity: str) -> dict | None:
    """Resolve the button declared on a CreateEntity action via trigger.onComponent (W4).

    Finds the screen's CreateEntity action, reads `trigger.onComponent`, then looks up that
    component in the screen's components list and returns {"id", "label"} when both are
    present.  Returns None for specs that don't declare the trigger (legacy specs fall back to
    the generated id/label).  Never invents a label."""
    screen = next((s for s in spec.get("screens", []) if s["id"] == screen_id), None)
    if not screen:
        return None
    # Find the CreateEntity action and its trigger.onComponent.
    trigger_component_id = None
    for a in screen.get("actions", []):
        if "CreateEntity" in set(a.get("does", [])):
            trigger_component_id = (a.get("trigger") or {}).get("onComponent")
            break
    if not trigger_component_id:
        return None
    # Look up that component and return its id + label.
    for c in screen.get("components", []):
        if c.get("id") == trigger_component_id and c.get("label"):
            return {"id": c["id"], "label": c["label"]}
    return None


def create_form(params: dict) -> str:
    """Wire a WORKING create/edit form for an entity — the write-path (Phase 6, the
    definition of done). Encodes every correction a hand-authored create turn needs.

    params: screen, entity, fields:[attr], return_screen?, id_param?, context_fk?,
            creator_attr?, phase?, button_id?, button_label?

    `phase` (iteration-3 seam 3f — thrash-free decomposition). Authoring the server action +
    form + save-wiring in ONE Mentor turn cascades for many minutes on a populated screen. The
    PROVEN thrash-free path is three sub-turns:
      - "action"  : the Save<Entity>Record server action only (fresh turn).
      - "widgets" : the form inputs + button bound to a local var, OnClick LEFT EMPTY (fresh turn).
      - "wire"    : wire the button OnClick — RESUME the widgets turn's session so it builds on
                    the unpublished widgets, then publish ONCE.
    phase=None (default) returns the single combined prompt (backward-compatible).

    `button_id` / `button_label` (W4): when supplied, the recipe authors EXACTLY that button
    id + label (from the spec's declared trigger.onComponent).  When absent, the recipe falls
    back to the legacy generated id (save<entity>btn) + label (Add <Entity>)."""
    screen = _p(params, "screen", required=True)
    entity = _p(params, "entity", required=True)
    fields = _p(params, "fields", [], required=True)
    ret = _p(params, "return_screen")
    id_param = _p(params, "id_param")              # None => create-only screen (no own-record id input)
    ctx = _p(params, "context_fk")                 # {"attr","from_param"} mandatory parent FK from a screen param
    creator = _p(params, "creator_attr")           # e.g. CreatorId — set from session identity
    phase = _p(params, "phase")
    # W4: declared button overrides the legacy generated id/label.
    button_id = _p(params, "button_id")
    button_label = _p(params, "button_label")
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
        # EDIT support (the write-path is create OR update): without prefilling the form from the existing
        # record, an edit opens a BLANK form and the save blanks every field. Load the record on screen-init.
        id_prefill_txt = (
            f" EDIT PREFILL — add a screen aggregate Get{entity}ById filtered by Id = {id_param}; on screen "
            f"initialize, WHEN {id_param} is a real (non-empty) identifier, Assign {local} = Get{entity}ById.List.Current "
            f"so the Form shows that {entity}'s CURRENT values (edit); when {id_param} is empty leave {local} empty (create).")
        id_assign_txt = (f"Assign {local}.Id = {id_param} when it is a real identifier — so Save{entity}Record calls "
                         f"UpdateAction and EDITS in place — else NullIdentifier() to create (cast with "
                         f"LongIntegerToIdentifier(TextToLongInteger(...)) if needed)")
    else:
        recv_txt = ("This is a CREATE-ONLY form: the screen has no own-record id input, so every save creates a "
                    "new record (Id = NullIdentifier()).")
        id_set_txt = "sets its Id = NullIdentifier() (always create)"
        id_prefill_txt = ""
        id_assign_txt = f"Assign {local}.Id = NullIdentifier()"
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
    # W4: use spec-declared button id+label when supplied; legacy fallback otherwise.
    # The save-click JS in _drive_create matches /save|create|add|submit/i so both
    # "Add Supplier" (legacy) and "+ New Supplier" (declared) are caught without changes.
    _btn_id    = button_id    or f"save{lentity}btn"
    _btn_label = button_label or f"Add {entity}"

    # The form's inputs live INSIDE a Form container widget. A BARE Input added directly to the screen
    # is the shape that intermittently phantoms (change_applied=true but nothing persists — batcha,
    # 2026-07-07, 4× fresh); the Form-wrapped build is what persisted. So every form path wraps its
    # inputs in a Form (also the idiomatic ODC create form).
    form_widgets = (
        f"a screen-local variable {local} of the {entity} data type; a Form container widget "
        f"(data-spec-id=\"{lentity}form\") whose Source record is {local}, and INSIDE that Form these editable "
        f"inputs: {inputs} (fields: {flist}); and a Button labeled \"{_btn_label}\" (data-spec-id=\"{_btn_id}\")")
    widgets_step = (
        f"On the {screen} screen, ADD ONLY these and nothing else — do NOT modify or rebind the existing table, "
        f"aggregate, or any existing widget: {form_widgets} with its OnClick LEFT EMPTY for now. Keep the screen "
        f"Anonymous. Do NOT add any screen action or save logic in this turn.")
    wire_step = (
        f"Wire the \"{_btn_label}\" button (data-spec-id=\"{_btn_id}\") you just created.{id_prefill_txt} Create ONE screen "
        f"action, set as that button's OnClick, that in order: {id_assign_txt};{context_txt}"
        f"{creator_txt} calls Save{entity}Record passing {local} as {entity}Record; then RefreshData the "
        f"{screen} list aggregate so the row appears/updates.{ret_txt} Leave the inputs' bindings intact. The prior "
        f"\"On Click must be set\" error MUST now be resolved.")
    # The PROVEN-persist shape (the batcha recovery): build the Form + inputs + button AND wire the OnClick
    # in ONE turn, AFTER the server action already exists. Keeps the action separate (so this is not the
    # action+form+wire mega-turn that cascades) while avoiding the fragile bare-widgets-only turn.
    combined_step = (
        f"On the {screen} screen, build a WORKING create/edit form in ONE turn (the {entity}'s Save{entity}Record server "
        f"action ALREADY exists — call it, do not re-author it). ADD ONLY (do NOT modify the existing table or its "
        f"aggregate): {form_widgets};{id_prefill_txt} then ONE screen action set as that Button's OnClick that in order: "
        f"{id_assign_txt};{context_txt}{creator_txt} calls Save{entity}Record passing {local} as "
        f"{entity}Record; then RefreshData the {screen} list aggregate so the row appears/updates.{ret_txt} Keep the "
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
        f'(data-spec-id="{_btn_id}").{creator_txt}{context_txt}{id_prefill_txt}\n'
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


# ODC defaults a new Text attribute to length 50 — too short for real data and a silent truncation risk
# (Mentor review flagged it on every Text attribute). Emit a production default of 255 for plain Text when
# the spec gives no explicit length; specs set `length` explicitly for free-text/content fields (1000-2000+).
_DEFAULT_TEXT_LENGTH = 255


def _attr_line(a: dict) -> str:
    if a.get("references"):
        return (f"{a['name']}: a {'mandatory ' if a.get('mandatory') else ''}foreign-key reference to "
                f"{a['references']}")
    dtype = a.get("dataType", "Text")
    seg = f"{a['name']}: {_DATATYPE_WORDS.get(dtype, dtype)}"
    if a.get("mandatory"):
        seg += ", mandatory"
    length = a.get("length") or (_DEFAULT_TEXT_LENGTH if dtype == "Text" else None)
    if length:
        seg += f", length {length}"
    if "default" in a:
        seg += f", default {a['default']}"
    return seg


def data_model(params: dict) -> str:
    """Author ALL entities in ONE turn (seam 3d). Interdependent entities must be created
    together (a later separate turn that references an earlier one can roll it back).

    `public` (modular topology): when True, EXPOSE every entity (Public=Yes) so CONSUMER apps can
    reference AND READ its data across the app boundary. A modular Core owns the data; if its entities
    are left private (the ODC default), a consumer's `app-reference` imports NOTHING from it and every
    consumer screen renders empty — the silent killer of the producer→consumer data flow."""
    entities = _p(params, "entities", [], required=True)
    public = _p(params, "public", False)
    lines = []
    for e in entities:
        attrs = [a for a in e.get("attributes", []) if not a.get("isIdentifier")]
        lines.append(f"- {e['name']}: " + "; ".join(_attr_line(a) for a in attrs))
    body = "\n".join(lines)
    enames = ", ".join(e["name"] for e in entities)
    public_txt = (
        f"EXPOSE FOR CROSS-APP USE — set EVERY entity's Public property = Yes ON THE EXISTING/ORIGINAL entity "
        f"(flip the property in place; do NOT create a new public copy — a public duplicate '<Name>2' next to a "
        f"private original is exactly the bug that crashes a consumer with OS-BEW-COMP-50008) so other apps can add "
        f"this app as a dependency and READ its data. This app is a data-owning producer (Core); leaving its "
        f"entities private (the default) means consumers reference nothing and render empty. After authoring, "
        f"CONFIRM each ORIGINAL entity reports Public=Yes and that NO '<Name>2' duplicate exists.\n"
        if public else "")
    return (
        f"{_PREAMBLE}\n\n"
        f"Create the app's data model. Author ALL of these entities in THIS ONE turn (they may reference each "
        f"other, so they must be created together). Do NOT create any screens or UI in this turn.\n{body}\n"
        f"IDEMPOTENT — REUSE, NEVER DUPLICATE (load-bearing on a rebuild/resume/reused app): an entity with any "
        f"of these names may ALREADY EXIST in this app. For EACH entity, FIRST look it up by name; if it exists, "
        f"UPDATE that EXISTING entity in place (add any missing attributes, and apply the Public setting below to "
        f"the existing entity) — do NOT create a new one. Only create an entity that does not already exist. NEVER "
        f"let a second entity share a logical name: ODC auto-suffixes a colliding name to '<Name>2', producing a "
        f"private original + a public duplicate that consumers then can't use (live-proven OS-BEW-COMP-50008 on a "
        f"consumer aggregate). If you find any pre-existing '<Name>2' duplicate, do NOT create more; reconcile onto "
        f"the ORIGINAL name.\n"
        f"{public_txt}"
        f"IDENTIFIER — settle it in THIS turn, before any publish (this is load-bearing: the create/edit form's "
        f"Save action later needs {entities[0]['name'] if entities else 'each entity'}.CreateAction and .Id, which "
        f"do not exist if the entity has no identifier). Every entity MUST end this turn with exactly ONE identifier "
        f"attribute: an auto-number Long-Integer named Id. ODC normally attaches this default Id on entity creation "
        f"— but do NOT assume it; after authoring, READ each entity back and CONFIRM it has an Id identifier "
        f"attribute. For ANY entity ({enames}) missing one, explicitly create an auto-number Long-Integer attribute "
        f"named Id and set it as that entity's identifier. Never leave an entity without an identifier, and never "
        f"CHANGE an existing identifier (post-first-publish that is irreversible, OS-DPL-RDBS-40020).\n"
        f"UPDATE BEHAVIOR — for any entity with more than 5 attributes, set its Update Behavior to \"Changed "
        f"Attributes\" (not the default \"Full\") so an update rewrites only changed columns, not every column "
        f"(a scalability win the platform review flags on wide entities).\n"
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
    """Author a complete ODC AI Agent (kind=AIAgent shell) in the CANONICAL Agent-Builder boilerplate —
    the exact 6-action shape of the stock ABC reference agent (inspected live 2026-07-10):
    `LoadMemory -> GetGroundingData -> BuildMessages -> [Call Agent widget] -> StoreMemory -> Response`,
    wrapped by a PUBLIC `Call<AgentName>` service action. The three steps a broken agent omits —
    MEMORY-load (LoadMemory), GROUNDING (GetGroundingData), and MEMORY-store (StoreMemory) — are
    first-class here. An agent with no grounding is the #1 failure: it 'reasons' but has no data
    (live-proven — a screening agent answered "I do not have access to screening data" and screened
    nothing; that agent had only 3 of these 6 actions and no grounding).

    params: agent_name, system_prompt, model_connection?, grounding?:[ str | {entity, key?} ] (entities
    the agent retrieves to ground its answer), max_loops?(default 8), expose_rest?(default True — a
    verification endpoint, strip for production), tools?:[ str | {name, description, parameters?, required?} ]
    (function-calling tools; grounding covers most needs, tools add multi-step action).

    JSON-OUTPUT CONSUMERS (live-proven dynamic_workflow 2026-07-11): when this agent is prompted to emit
    JSON, its Response STILL arrives wrapped in a ```json ... ``` markdown fence even with a strict
    "raw JSON only" system_prompt — the model ignores that instruction reliably enough that you must NOT
    trust the prompt. Any downstream action that deserializes the Response MUST extract robustly: take the
    substring from the first '{' to the LAST '}' (JsonStart = Index(Response,"{"); JsonEnd =
    Index(Response,"}",0,True) reverse-search; guard JsonStart<>-1 and JsonEnd>JsonStart) BEFORE
    JSONDeserialize — never deserialize the raw Response. This survived the fence and returned Valid=true.

    Why this shape (the stock ABC boilerplate agent, inspected live 2026-07-10): an ODC agent runs
    headless, and the LLM is invoked by the native "Call Agent" widget inside AgentFlow (Agent +
    Messages) — NOT a hand-written model call. Function-calling is NATIVE: tools are Server Actions
    attached to the agent's Action-calling config, and the reasoning loop (select tool -> runtime runs it
    -> feed result back -> continue) is executed BY THE AGENT RUNTIME, bounded by a Call Condition on the
    agent. The old "caller appends the tool output and calls again" orchestration was WRONG — the runtime
    does the loop. The model chooses tools by their DESCRIPTION, so every tool needs one. The agent
    exposes `Call<AgentName>` (SessionId + UserInput -> Response) as its consumption contract."""
    name = _p(params, "agent_name", required=True)
    prompt = _p(params, "system_prompt", "You are a helpful assistant.")
    model = _p(params, "model_connection", "TrialClaudeHaiku4_5")
    max_loops = _p(params, "max_loops", 8)
    # The REST endpoint is how the harness INVOKES + gates an agent (exec_in_app can't reach AIAgent
    # actions), so it's ON by default for verifiability — but it is a DEV/verification affordance that
    # MUST be auth-gated or stripped for production (anonymous HTTP on an agent is a security smell; the
    # real consumption path is the Call<AgentName> service action). Set expose_rest=False for a prod build.
    expose_rest = _p(params, "expose_rest", True)

    def _ground(g):
        return {"entity": g} if isinstance(g, str) else {"entity": g.get("entity", ""), "key": g.get("key", "")}
    grounding = [_ground(g) for g in (_p(params, "grounding", []) or []) if (g if isinstance(g, str) else g.get("entity"))]

    def _tool(t):
        if isinstance(t, str):
            return {"name": t, "description": f"Calls the {t} server action.", "parameters": "", "required": ""}
        return {"name": t.get("name", ""), "description": t.get("description", f"Calls {t.get('name','')}."),
                "parameters": t.get("parameters", ""), "required": t.get("required", "")}
    tools = [_tool(t) for t in (_p(params, "tools", []) or [])]

    # ── MEMORY-load + GROUNDING (workbench: LoadMemory, GetGroundingData) — the steps a broken agent omits ──
    loadmem_block = (
        f"1. LoadMemory server action (SessionId -> Messages, an AIMessage list) — RETRIEVE prior conversation for this "
        f"session so the agent has memory across turns. This is boilerplate action #1 of the stock agent; run it first.\n")
    if grounding:
        glines = "\n".join(f"   - query {g['entity']}" + (f" (filter/key: {g['key']})" if g.get("key") else "")
                           for g in grounding)
        ground_block = (
            f"2. GetGroundingData server action (UserInput -> GroundingData text) — RETRIEVE the real data the answer must "
            f"be grounded in, and return it as text/records to inject into the prompt. Query these REFERENCED entities via "
            f"aggregates:\n{glines}\n"
            f"   This is the step whose absence makes an agent say 'I don't have access to that data' — it MUST run "
            f"before BuildMessages and its results MUST be put into the messages.\n")
    else:
        ground_block = (
            f"2. (No grounding entities declared — this agent answers from the model + tools only. If it should reason "
            f"over app data, add a GetGroundingData step that queries the referenced entities.)\n")

    # ── TOOLS = the agent's native Action calling (NOT a hand-orchestrated loop) ──
    # Ground truth from the stock ABC boilerplate agent + a live tool-firing test (2026-07-11): the
    # reasoning loop is NATIVE to the agent element. The LLM is invoked by the "Call Agent" widget inside
    # AgentFlow; tools are Server Actions attached to the agent's Action-calling config; the loop (select
    # tool -> runtime runs it -> feed result back -> continue) is executed by the agent runtime and BOUNDED
    # by a Call Condition. The Call Condition is the BREAK/STOP condition (the loop continues while it is
    # FALSE) and MUST be expressed on the runtime's built-in LoopCount so it is FALSE on the first
    # iteration — `LoopCount >= N`. A custom static input (e.g. IterationCount) never increments, and
    # `IterationCount <= N` is TRUE at start, so it breaks the loop at 0 calls (live-proven failure).
    if tools:
        lines = "\n".join(
            f"   - {t['name']}: {t['description']}"
            + (f" Parameters: {t['parameters']}." if t['parameters'] else "")
            + (f" Required: {t['required']}." if t['required'] else "")
            for t in tools)
        tools_block = (
            f"4b. TOOLS (native Action calling). Enable Action calling on the agent (EnableActionCalling=true) and attach "
            f"each of these EXISTING Server Actions to its Action-calling config, each with a NAME + a clear DESCRIPTION "
            f"(the model selects tools BY description) + its parameters (mark model-supplied args AI-filled):\n{lines}\n"
            f"    Do NOT hand-orchestrate a call/append/recall loop. The agent runtime runs the reasoning loop itself: the "
            f"Call Agent widget selects a tool, the runtime executes that Server Action, feeds the result back, and continues. "
            f"Bound it with the agent Call Condition set to EXACTLY `LoopCount >= {max_loops}` — LoopCount is the runtime's "
            f"built-in counter (0 on the first iteration, so `0 >= {max_loops}` is FALSE and the loop proceeds to call a tool; "
            f"it breaks once LoopCount reaches {max_loops}). Do NOT use a custom static input or a `<= N` form — that is TRUE "
            f"at start and breaks the loop at 0 tool calls (live-proven). Each tool just needs to be ATTACHED with its "
            f"description; the agent calls it dynamically.\n")
    else:
        tools_block = ""

    rest_block = (
        f"6. VERIFICATION endpoint (DEV/test — the harness invokes the agent through it; AUTH-GATE OR STRIP for "
        f"production, anonymous HTTP on an agent is a security smell; the real consumption path is Call{name}). Add a "
        f"REST API named EXACTLY \"AgentAPI\", POST method \"Ask\", Authentication=None, Text input \"Question\" -> Text "
        f"output \"Answer\"; inside call AgentFlow(Question) and Assign Response to Answer. ServerRequestTimeout=120. "
        f"Resolves to POST /<module>/rest/AgentAPI/ask.\n"
        if expose_rest else "")

    return (
        f"{_PREAMBLE}\n\n"
        f"This is a blank ODC AI Agent app (kind=AIAgent). Author a COMPLETE working agent named {name} in the CANONICAL "
        f"Agent-Builder BOILERPLATE — the exact 6-action shape of the stock ABC reference agent: LoadMemory -> "
        f"GetGroundingData -> BuildMessages -> [Call Agent widget] -> StoreMemory -> Response, wrapped by a PUBLIC "
        f"Call{name} service action. An ODC agent runs headless; the LLM is invoked by the native \"Call Agent\" widget "
        f"(Agent + Messages) inside AgentFlow, and it exposes Call{name} to consuming apps.\n"
        f"0. Create the agent element and bind its AIModel slot to the EXISTING AIModelConnection \"{model}\" (Trial is "
        f"fine for dev — bindable via MCP, publishes clean, no OS-APPS-40028; parameterize to the client's model for "
        f"production).{' Attach the tools (step 4b) to its Action-calling config and set a Call Condition to bound the loop.' if tools else ''}\n"
        f"{loadmem_block}"
        f"{ground_block}"
        f"3. BuildMessages server action (UserInput + GroundingData + SessionId -> Messages, MessageToStoreInMemory) — "
        f"build the ChatMessages (AIMessage list): a System message whose SystemMessageContent.ContentText is exactly "
        f'"{prompt}"'
        f", plus the LoadMemory Messages prepended so prior turns are in context"
        f"{' PLUS the GetGroundingData results injected as context so the model answers FROM the data' if grounding else ''}"
        f", and a User message from the UserInput text parameter (typed local + Assign per attribute; an inline "
        f"[{{Role:...}}] literal is rejected by the parser).\n"
        f"4. AgentFlow server action (SessionId + UserInput -> Response) that runs the flow in order: LoadMemory -> "
        f"{'GetGroundingData -> ' if grounding else ''}BuildMessages -> the \"Call Agent\" widget (Agent={name}, "
        f"Messages=BuildMessages.Messages){' which runs the native tool loop below' if tools else ''} -> StoreMemory -> "
        f"return the Call Agent Response. Do NOT hand-write a model call — the Call Agent widget IS the model invocation.\n"
        f"{tools_block}"
        f"5. StoreMemory server action (MessageToStoreInMemory + the response message + SessionId) — persist this turn so "
        f"the agent has conversation memory across turns; call it after the Call Agent widget returns, before returning.\n"
        f"{rest_block}"
        f"7. A PUBLIC service action Call{name} (SessionId + UserInput -> Response) that calls AgentFlow — the standard, "
        f"documented consumption contract for any consuming app. ServerRequestTimeout=120 (LLM + tool-loop latency).\n"
        f"COLD-START CAVEAT (live-proven OS-CLRT-60900): a SCREEN action that invokes this agent synchronously "
        f"(screen -> server/service action -> Call Agent) hits a 10s CLIENT-side timeout on the FIRST (cold) call — "
        f"the model connection cold-starts in >10s even though ServerRequestTimeout is 120 (that governs the SERVER, "
        f"not the client). Mitigate: warm the model once before a demo, invoke the agent from a background/async path, "
        f"or expect (and retry) a first-call timeout; the warm call returns in ~2s.\n"
        f"After authoring, confirm change_applied=true and report: the AIModel binding, that the flow has all "
        f"6 boilerplate actions (LoadMemory, GetGroundingData, BuildMessages, AgentFlow, "
        f"StoreMemory, Call{name}), that GetGroundingData "
        f"{'queries ' + ', '.join(g['entity'] for g in grounding) if grounding else 'is absent (no grounding declared)'}, "
        f"the attached tool names, and that AgentFlow invokes the model via the Call Agent widget (not a hand-written "
        f"call). The app MUST then publish to `succeeded` with NO OS-APPS-40028. Do not publish.")


# ODC ships EXACTLY these 7 chart widgets (Highcharts 12.5.0 under the hood). Anything else
# (gauge/scatter/bubble/waterfall/heatmap/funnel/…) is NOT a widget — reach it via the
# SetHighcharts*Configs escape hatch off a base widget, or treat as a spec wall.
_CHART_TYPES = ("Area", "Bar", "Column", "Line", "Pie", "Donut", "Radar")
_CHART_SINGLE_SERIES = ("Pie", "Donut")
_CHART_TYPE_NOTES = {
    "Area":   'stacked area: set StackingType = Entities.StackingType.Stacked (else overlaid).',
    "Bar":    'horizontal bars — axes are inverted, so ChartXAxis addon controls the VERTICAL axis.',
    "Column": 'vertical bars; set ShowDataPointValues on ChartSeriesStyling for on-bar data labels.',
    "Line":   'set Spline=True for a smoothed curve; add point Markers via ChartSeriesStyling.Marker.',
    "Pie":    'SINGLE series — each DataPoint is a slice, SeriesName is unused; delete the ChartLegend addon to hide the legend.',
    "Donut":  'Pie + InnerSize (a percentage string, default "50%") for the center hole; single series.',
    "Radar":  'polar/multi-series; mix a series\' render type via ChartSeriesStyling.SeriesType.',
}


def chart(params: dict) -> str:
    """Author a NATIVE ODC chart widget (ODC charts are toolbox widgets — NOT a referenced
    OutSystemsCharts block; that is O11 framing). params: screen, chart_type (one of the 7 ODC
    widgets: Area|Bar|Column|Line|Pie|Donut|Radar), category_field, series:[{name,value_field}],
    source_aggregate?, advanced?(free-text Highcharts config note for the SetHighcharts* escape hatch)."""
    scr = _p(params, "screen", required=True)
    ctype = _p(params, "chart_type", "Column")
    if ctype not in _CHART_TYPES:
        raise ValueError(
            f"chart: unknown chart_type {ctype!r}; ODC has exactly {_CHART_TYPES}. For gauge/scatter/"
            f"bubble/etc. author a base widget + the SetHighcharts*Configs escape hatch (pass `advanced`).")
    cat = _p(params, "category_field", required=True)
    series = _p(params, "series", [], required=True)
    src = _p(params, "source_aggregate")
    advanced = _p(params, "advanced")
    single = ctype in _CHART_SINGLE_SERIES
    stxt = "; ".join(f'{s.get("name", s.get("value_field"))} = {s.get("value_field")}' for s in series)
    src_txt = (f"the {src} aggregate" if src else "a screen aggregate")
    axis_txt = ("" if single else
                f"3. Add the ChartXAxis + ChartYAxis addons (drop into the chart's AddOns placeholder). "
                f"For a Bar chart remember the axes are inverted. Add a ChartLegend addon (set Position, "
                f"e.g. Entities.LegendPosition.TopRight) when there are multiple series; delete it to hide.\n")
    series_txt = ("each DataPoint is a slice (single series — do NOT set SeriesName)" if single else
                  f"set SeriesName per series ({stxt}) so the {len(series) or 'N'} series render grouped/stacked")
    adv_txt = (f"\n5. ADVANCED (escape hatch): {advanced} — apply via the SetHighcharts"
               f"{{Chart,XAxis,YAxis,Series}}Configs client actions with raw Highcharts 12.5.0 config "
               f"(this is also the ONLY way to get gauge/scatter/bubble/tooltips/click-drilldown — none "
               f"are widget properties)." if advanced else
               "\n5. For custom tooltips, axis min/max, click/drilldown, or a non-widget series type, use the "
               "SetHighcharts{Chart,XAxis,YAxis,Series}Configs client actions (raw Highcharts config).")
    return (
        f"{_PREAMBLE}\n\n"
        f"On the {scr} screen, add a NATIVE {ctype} Chart widget from the toolbox. ODC charts are "
        f"first-class toolbox WIDGETS — do NOT addReferenceToElements an OutSystemsCharts block and do "
        f"NOT create a ReferenceWebBlock for the chart (that is O11/monorepo framing and does not exist "
        f"in ODC). ODC has exactly 7 chart widgets: {', '.join(_CHART_TYPES)}.\n"
        f"1. Drop the {ctype} Chart widget; set data-spec-id=\"{_slug(scr)}{ctype.lower()}chart\" on it.\n"
        f"2. DATA: bind the widget's DataPointList to {src_txt} — each DataPoint maps {{ Label: {cat}, "
        f"Value: <numeric value_field> }}. Value must be Decimal (wrap an Integer in IntegerToDecimal(...)). "
        f"Build the list from a data AGGREGATE — NEVER (System).ListAppend onto a client-action node (it "
        f"throws 'target of invocation' and rolls back the turn). {series_txt}. Qualify aggregate APIs with "
        f"the OutSystems.Model.Logic.Aggregates namespace.\n"
        f"{axis_txt}"
        f"4. COLORS: add a ChartSeriesStyling addon (target one series via SeriesName, or leave SeriesName "
        f"empty to style ALL series) — QUOTE hex colors (a bare '#' is a parser error: use \"#5E6AD2\"). "
        f"TYPE NOTE: {_CHART_TYPE_NOTES[ctype]}"
        f"{adv_txt}\n"
        f"Verify the chart renders REAL values at RUNTIME (an empty DataPointList renders nothing). Do not publish.")


# Canonical OutSystemsUI reset — PREPENDED to every theme stylesheet so the UI_CLASS_CONTRACT
# classes actually win over OutSystemsUI defaults. Live-proven gap (RivianReviewerPortal 2026-07-12):
# a `.nav-item` Container is styled, but its inner Link renders as the browser/OSUI default
# (color rgb(0,0,238) + underline) because NOTHING resets `.nav-item a`. Design CSS is appended
# AFTER this block, so a build's own rules still override the reset.
THEME_RESET_CSS = (
    "/* harness reset: make the UI class contract beat OutSystemsUI link/button defaults */\n"
    ".app-sidebar a,.nav-item a,.nav-item a:link,.nav-item a:visited,.app-topbar a{"
    "color:inherit;text-decoration:none;}\n"
    ".nav-item:hover a,.nav-item.is-active a{color:inherit;}\n"
    "a.btn-primary,.btn-primary a,a.is-primary{text-decoration:none;}\n"
)


def theme(params: dict) -> str:
    """Set + ACTIVATE a theme's stylesheet (a fresh theme is inert until activated; @import is stripped
    at publish). Prepends THEME_RESET_CSS so the UI class contract wins over OutSystemsUI link defaults.
    params: css, font_faces?(css @font-face text), activate?(default true)."""
    css = THEME_RESET_CSS + "\n" + _p(params, "css", required=True)
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
    columns?(default 3), phase?("structure"|"aggregate"|"bind"|None).

    Each card's value is a live aggregate COUNT when `entity`/`aggregate` is given, else literal.

    W5b/W5d: `phase` enables atomic authoring for COUNT cards (one-step-per-unit, commit 654f038):
      - phase="structure": author the .kpi-card CONTAINERS + value/label/icon widgets (placeholder "0",
        no aggregate) — W5d fix: without this the bind turn ("do not add widgets") left the value bare.
      - phase="aggregate": author the Count{Ent} screen aggregate for each COUNT card (data-only turn, no bind).
      - phase="bind":      set each KPI Expression Value to Count{Ent}.Count (bind-only turn).
      - phase=None (default): combined single prompt (legacy back-compat — unchanged when no COUNT cards)."""
    screen = _p(params, "screen", required=True)
    cards = _p(params, "cards", [], required=True)
    ncols = _p(params, "columns", min(len(cards), 4) or 1)
    phase = _p(params, "phase")

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

    # W5b: phase-split path for COUNT cards.
    count_cards = [c for c in cards if c.get("entity") or c.get("aggregate")]
    # UNIQUE aggregate name PER CARD (by label slug), not per entity: two cards over the SAME entity
    # (e.g. "Open Cases" + "Overdue", both QualificationCase) would otherwise both be named
    # CountQualificationCase — two same-named screen aggregates on one screen is a compile collision
    # (OS-BEW-COMP-50008). Naming by the card keeps them distinct.
    def _agg_name(card):
        return "Count" + _pascal(card.get("label") or (card.get("entity") or card.get("aggregate")))
    if phase == "structure":
        # W5d (live-proven gap, RivianReviewerPortal 2026-07-12): the phased path authored the
        # aggregate + the bind but NEVER the card STRUCTURE — the "bind" turn was told "do not add
        # widgets", so the .kpi-card Container was never created and the value rendered bare (DOM had
        # .kpi-value but ZERO .kpi-card). This turn authors ONLY the card structure (no aggregates,
        # no real values) so the bind turn has a .kpi-card/.kpi-value to point at.
        struct_lines = []
        for c in cards:
            icon = c.get("icon", "chart-bar")
            label = c.get("label", "")
            trend = f' plus a trend tag (Style class "kpi-trend") "{c["trend"]}"' if c.get("trend") else ""
            struct_lines.append(
                f'  - a KPI card: a Container (Style class "kpi-card", data-spec-id="kpi{_slug(label)}") — '
                f'the card CHROME the theme paints; it MUST be this Container, not a bare value — containing '
                f'a CSS-icon (Container Style class "kpi-icon glyph-{icon}"), a big value Expression (Style '
                f'class "kpi-value") showing the literal "0" as a placeholder (the bind turn sets the real '
                f'count), and a label (Style class "kpi-label") "{label}"{trend}.')
        return (
            f"{_PREAMBLE}\n\n"
            f"On the {screen} screen, author ONLY the KPI card STRUCTURE — a row of {len(cards)} stat cards in "
            f"a {ncols}-column responsive grid (a flex Container with Style class \"kpi-row\"), placed at the "
            f"top of the content area. NO screen aggregates and NO real values this turn — every value "
            f"Expression is the placeholder \"0\". Each card MUST be a Container whose Style class is "
            f"\"kpi-card\" (without this container the value renders bare — live-proven):\n"
            + "\n".join(struct_lines)
            + "\nDo not publish."
        )

    if phase == "aggregate" and count_cards:
        agg_lines = []
        for c in count_cards:
            ent = c.get("entity") or c.get("aggregate")
            filt = f' filtered where {c["filter"]}' if c.get("filter") else ""
            agg_lines.append(
                f'  - Add a screen aggregate named {_agg_name(c)} over {ent}{filt}, '
                f'Max Records = 1 (count-only query). Do NOT bind it to any widget yet.'
            )
        return (
            f"{_PREAMBLE}\n\n"
            f"On the {screen} screen, author ONLY the COUNT screen aggregate(s) — no widgets, no bindings. "
            f"Give EACH aggregate the DISTINCT name below (never reuse one name for two aggregates — a "
            f"duplicate screen-aggregate name fails compilation, OS-BEW-COMP-50008).\n"
            + "\n".join(agg_lines)
            + "\nDo not publish."
        )

    if phase == "bind" and count_cards:
        bind_lines = []
        for c in count_cards:
            agg = _agg_name(c)
            slug = _slug(c.get("label", ""))
            bind_lines.append(
                f'  - Set the Expression Value inside [data-spec-id="kpi{slug}"] .kpi-value '
                f'to {agg}.Count (the aggregate\'s total-count output). '
                f'Do NOT bind to {agg}.List.Length (wrong: page-size, not count).'
            )
        return (
            f"{_PREAMBLE}\n\n"
            f"On the {screen} screen, ONLY update the KPI Expression bindings — do not add new widgets.\n"
            + "\n".join(bind_lines)
            + "\nDo not publish."
        )

    # phase=None: combined single prompt (backward-compatible).
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
            f'per team: {", ".join(teams)}; {src}. EACH card MUST be its own Container with Style class '
            f'"review-card" (the theme paints the card chrome) — do NOT emit a bare status without the '
            f'review-card Container, or it renders as loose text (live-proven structure-drop, harvest #2).')
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


# ── Dynamic-workflow engine constants ─────────────────────────────────────────
_ENGINE_ACTIONS = [
    "ResolveScenario", "InstantiateWorkflow", "AdvanceInstance", "CompleteTask",
    "ClaimTask", "EscalateOverdue", "ValidateComposition", "ComposeInstance",
    "GetInstanceStatus", "GetOpenTasksForActor",
]
_ENGINE_ENTITY_DEFAULTS = {
    "task_template": "TaskTemplate", "scenario": "Scenario", "scenario_step": "ScenarioStep",
    "transition_rule": "TransitionRule", "decision_row": "DecisionRow",
    "workflow_instance": "WorkflowInstance", "task_instance": "TaskInstance",
    "audit_event": "AuditEvent",
}


def _en(entities: dict, role: str) -> str:
    """Resolve an entity role to its name, falling back to _ENGINE_ENTITY_DEFAULTS."""
    return (entities or {}).get(role, _ENGINE_ENTITY_DEFAULTS[role])


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
    (OS-DPL-50205 is a generic bucket — also fires for a cross-app-entity FK, a public raise-event
    action, and consuming a Service Action cross-app from a SCREEN-BEARING reactive (CrossDevice)
    producer — for that last case co-locate the orchestration INSIDE the producer so the calls stay
    local (see app_reference); always diagnose the specific element read-only.)"""
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
            f"non-public Server Action. TESTABILITY: this public-Service -> private *Internal-Server split is ALSO "
            f"how the logic becomes runtime-testable — the ASE test harness (exec_in_app) exposes ONLY Server Actions, "
            f"never Service Actions, so put the real logic in a private *Internal Server Action and have this Service "
            f"Action delegate to it (mirrors AdvanceInstance->AdvanceInternal; live-proven dynamic_workflow 2026-07-11). "
            f"Build the flow with Start + End nodes and the operation between. After "
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
    """Author a Business Process (BPT) — cross-app refs + a MINIMAL process in ONE turn (runtime-proven,
    wfprobe 2026-07-07). The trigger Global Event + the Service Actions the activities call live in a
    PRODUCER app (a NORMAL app — CreateGlobalEvent THROWS in a Workflow app) and are referenced cross-app.
    Sequence (owned by the driver/plan): the producer app already holds the event + PUBLIC service
    action(s); `app_create kind=BusinessProcess` registers the Workflow app WITHOUT auto-publishing
    (0 deployments — the safe window); this turn references the producer's elements AND authors the
    process; then the orchestrator publishes ONCE with the process present. A 0-process Workflow app
    publish corrupts its verify cache, so NEVER publish before this turn lands.

    KEEP THE PROCESS MINIMAL — push logic to the Core (live-proven 2026-07-11). A node-heavy process
    (multiple decision gateways + a human activity + several write activities) authored in one turn
    TIMES OUT at 900s. So model the workflow as a few automatic activities + AT MOST one decision + at
    most one human activity, and push ALL branching / parsing / risk-gating into CORE service actions the
    activities call. Example HITL shape: Start -> CallAgent -> a single Core handler service action
    HandleProposal(...) that parses+persists+auto-executes the low-risk path and returns NeedsApproval ->
    Decision(NeedsApproval) -> [human activity -> a Core Finalize service action] or [End]. Structures
    (for JSON deserialize) CANNOT live in a BPT app — author them + the handler in the Core and reference
    it. If a process still needs many nodes, STAGE it across turns (turn 1 refs, turn 2 the linear
    skeleton, turn 3 the decision/human branch). params: name, producer_app, trigger_event,
    activities:[{name, calls_service_action}] (an auto-activity can call ONLY a PUBLIC Service Action);
    optional decision:{on, then_activity, else_activity} (one gateway on a process variable) and
    human_activity:{name, role} (a wait step; falls back to end-and-defer-to-portal if a Human/Wait
    activity is not authorable via the Model API)."""
    name = _p(params, "name", required=True)
    producer = _p(params, "producer_app", required=True)
    trigger = _p(params, "trigger_event", required=True)
    activities = _p(params, "activities", [], required=True)
    decision = _p(params, "decision", None)
    human = _p(params, "human_activity", None)
    # skeleton=True renders the tiny FIRST turn only (refs + Start->End, no activities) — for a COMPLEX
    # process built up across many small turns (each node added by a `workflow-add` step). This is the
    # non-greedy path: every turn lands in 1-4 min instead of one 900s-timeout turn.
    skeleton = _p(params, "skeleton", False)
    # Accept either the snake_case (`calls_service_action`) or the camelCase (`callsServiceAction`, as
    # expand.py emits) key — the spec factory + the hand-authored path use different casings.
    def _sa(a):
        return a.get("calls_service_action") or a.get("callsServiceAction") or ""
    acts_ok = [a for a in activities if _sa(a)]
    sa_names = sorted({_sa(a) for a in acts_ok})
    if skeleton:
        return (f"{_PREAMBLE}\n\n"
                f"This is a Workflow (BusinessProcess-kind) app with ZERO processes; it has NEVER been published and "
                f"must NOT be published until it has a process (a 0-process Workflow app corrupts its verify cache). "
                f"Do ONLY this small unit (the process SKELETON — nodes are added in later turns), then STOP (do NOT "
                f"publish):\n"
                f"1. Reference the producer app '{producer}' and import (all PUBLIC): the Global Event {trigger}"
                f"{' and the Service Action(s) ' + ', '.join(sa_names) if sa_names else ''}. Use addReferenceToElements "
                f"+ AddDependency(ParseGlobalKey) + RefreshDependencies. The event resolves under the reference's "
                f"GlobalEvents collection; service actions under its ServiceActions collection.\n"
                f"2. Author a Business Process named {name} (eSpace.CreateBusinessProcess) with a Start node "
                f"(StartProcessOn = the referenced {trigger} Global Event, TriggerMode = Event) wired directly to an End "
                f"node. NO activities yet — they are added one per follow-up turn. After the skeleton lands and is "
                f"published, the app is safe (it has a process).\n"
                f"After authoring, run model validation (0 errors; a 'missing event handler' + 'no User Provider' "
                f"warning are BENIGN). Do NOT publish — the orchestrator publishes.")
    acts = "\n".join(
        f"   - an Automatic Activity node '{a.get('name', _sa(a))}' whose ActionToTrigger is the referenced PUBLIC "
        f"Service Action {_sa(a)} (an auto-activity can call ONLY a Public Service Action; set its "
        f"arguments — e.g. NullIdentifier() for an Identifier input when no business value is needed; capture its "
        f"outputs into process variables if a later decision needs them)"
        for a in acts_ok)
    n_nodes = 2 + len(acts_ok) + (1 if decision else 0) + (1 if human else 0)  # Start + End + activities + branch nodes
    decision_block = ""
    if decision:
        decision_block = (
            f"   - a SINGLE Decision node on the process variable '{decision.get('on', '?')}': when it matches, go to "
            f"'{decision.get('then_activity', 'the human branch')}'; otherwise go to '{decision.get('else_activity', 'End')}'. "
            f"Do NOT add nested/second gateways — do multi-way branching inside a Core service action, not in the process.\n")
    human_block = ""
    if human:
        human_block = (
            f"   - a Human activity '{human.get('name', 'Approve')}' assigned to role '{human.get('role', 'User')}' that "
            f"WAITS for a human to approve; after it completes, continue to the finalize activity. IMPORTANT: if a "
            f"Human/Wait activity CANNOT be authored via the Model API in a BPT app, OMIT it and END that branch "
            f"instead (the record stays in its pending state for a human to approve later in a portal inbox), and "
            f"clearly REPORT which shape you used.\n")
    staging = ("" if n_nodes <= 6 else
               f"\nNOTE: this process is ~{n_nodes} nodes — that risks a 900s authoring timeout. Prefer to STAGE it: "
               f"author the references + Start + the automatic activities + End in THIS turn, and add the decision/human "
               f"branch in a SEPARATE follow-up turn. Or push more logic into a Core handler to cut node count.\n")
    return (f"{_PREAMBLE}\n\n"
            f"This is a Workflow (BusinessProcess-kind) app with ZERO processes; it has NEVER been published and "
            f"must NOT be published until it has a process (a 0-process Workflow app corrupts its verify cache). "
            f"KEEP THE PROCESS MINIMAL — a BPT process is orchestration only; all branching/parsing/risk logic belongs "
            f"in CORE service actions this process calls (a node-heavy process times out at 900s; structures can't live "
            f"in a BPT app). Author BOTH of the following in THIS one turn, then STOP (do NOT publish):\n"
            f"1. Reference the producer app '{producer}' and import (all PUBLIC): the Global Event {trigger} and the "
            f"Service Action(s) {', '.join(sa_names)}. Use addReferenceToElements + AddDependency(ParseGlobalKey) + "
            f"RefreshDependencies. The event resolves under the reference's GlobalEvents collection; the service "
            f"actions under its ServiceActions collection.\n"
            f"2. Author a Business Process named {name} (eSpace.CreateBusinessProcess) with CreateNode<T> + "
            f".Target/ConnectedBelow:\n"
            f"   - a Start node with StartProcessOn = the referenced {trigger} Global Event and TriggerMode = Event;\n{acts}\n"
            f"{decision_block}{human_block}"
            f"   - an End node; wire Start -> activities -> {'decision -> branches -> ' if decision else ''}End.\n"
            f"{staging}"
            f"After authoring, run model validation (expect 0 errors; a 'missing event handler' + a 'no User "
            f"Provider' warning are BENIGN for a consume-only workflow app). Do NOT publish — the orchestrator "
            f"publishes the process + refs in one shot (never a 0-process Workflow app).")


def workflow_add(params: dict) -> str:
    """Add ONE node to an EXISTING Business Process — the non-greedy staged path (one small turn per node,
    each lands in 1-4 min, no 900s timeout). Used after the `workflow` skeleton turn (Start->End) to build
    a complex process up incrementally. params: process(name), kind ('activity'|'decision'|'human'), plus
    per-kind detail:
      activity: calls_service_action, name?  (an auto-activity calls ONLY a PUBLIC Service Action)
      decision: on(process variable), then_activity, else_activity
      human:    name, role  (falls back to end-and-defer if a Human/Wait activity isn't authorable).
    Each add-node turn re-opens the process, inserts the node just BEFORE the End node, and rewires the
    connector (whatever currently flows into End now flows into the new node, then onward to End)."""
    proc = _p(params, "process", required=True)
    kind = _p(params, "kind", "activity")
    if kind == "activity":
        sa = _p(params, "calls_service_action") or _p(params, "callsServiceAction") or _p(params, "service_action", required=True)
        node = (f"an Automatic Activity node '{_p(params, 'name', sa)}' whose ActionToTrigger is the referenced PUBLIC "
                f"Service Action {sa} (an auto-activity can call ONLY a Public Service Action; set its arguments, using "
                f"process variables captured from earlier activities where needed — e.g. NullIdentifier() for an unused "
                f"Identifier input). Capture its outputs into process variables if a later decision needs them")
    elif kind == "decision":
        on = _p(params, "on", required=True)
        node = (f"a SINGLE Decision node on the process variable '{on}': when it matches, go to "
                f"'{_p(params, 'then_activity', 'the next node')}'; otherwise go to '{_p(params, 'else_activity', 'End')}'. "
                f"Do NOT add nested/second gateways — multi-way branching belongs in a Core service action, not the process")
    elif kind == "human":
        node = (f"a Human activity '{_p(params, 'name', 'Approve')}' assigned to role '{_p(params, 'role', 'User')}' that "
                f"WAITS for a human to approve. IMPORTANT: if a Human/Wait activity CANNOT be authored via the Model API "
                f"in a BPT app, OMIT it and END that branch instead (the record stays pending for a human to approve in a "
                f"portal inbox); clearly REPORT which shape you used")
    else:
        node = f"a node of kind '{kind}'"
    return (f"{_PREAMBLE}\n\n"
            f"This app already has a Business Process named {proc} (with at least a Start node and an End node) and the "
            f"needed cross-app references. Do ONLY this ONE small edit (one node — small turns are deliberate; a "
            f"node-heavy single turn times out at 900s), then STOP:\n"
            f"INSERT into process {proc}, immediately BEFORE the End node, {node}.\n"
            f"Rewire the connectors: whatever currently connects INTO the End node must now connect into this new node, "
            f"and the new node connects onward to End (or to its branch targets for a decision). Do not touch any other "
            f"node. After authoring, run model validation (0 errors; benign event-handler / User-Provider warnings ok). "
            f"Do NOT publish — the orchestrator publishes after this small turn lands.")


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
            f"2026-07-07, static AND regular). Referenced Global Events + Service Actions from a HEADLESS Service/Core "
            f"producer are call/consume targets and deploy fine (proven, wfprobe) — BUT consuming a Service Action "
            f"cross-app from a SCREEN-BEARING reactive producer (a CrossDevice app that owns screens / a portal) ALSO "
            f"trips OS-DPL-50205 at publish (live-proven dynamic_workflow 2026-07-11: the reactive producer's UI model "
            f"features leak into the consumer's validation surface, 0 in-session errors then a failed publish). When the "
            f"producer is screen-bearing, do NOT build a separate consumer/orchestrator app that calls its Service "
            f"Actions — CO-LOCATE the orchestration action INSIDE that producer (its own Service/Server Actions become "
            f"local calls) and keep only genuinely-headless refs (e.g. an AI agent) external. Import EVERY entity you "
            f"touch INCLUDING any STATIC entity — an entity "
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


def kpi_rebind(params: dict) -> str:
    """W5c: applyModelApiCode corrective — locate each KPI Expression and rebind its Value to
    the screen aggregate's `.Count`.  A deterministic fallback when the NL bind step (W5b) still
    produces the wrong binding (e.g. Mentor persists .List.Length despite explicit instructions).

    params: screen, cards:[{label, entity}].

    Only emitted when plan_from_spec(..., kpi_model_api_fallback=True). Default is False."""
    screen = _p(params, "screen", required=True)
    cards = _p(params, "cards", [], required=True)
    bind_lines = []
    for c in cards:
        ent = c.get("entity") or c.get("aggregate")
        if not ent:
            continue
        label = c.get("label", "")
        slug = _slug(label)
        agg = "Count" + _pascal(label or ent)      # per-card name (two cards on one entity must not collide)
        bind_lines.append(
            f'  - Find the Expression inside [data-spec-id="kpi{slug}"] .kpi-value. '
            f'Set its Value to the screen aggregate {agg}.Count. '
            f'{agg} must be a screen aggregate over {ent} with Max Records=1. '
            f'Use applyModelApiCode to make this change directly — do NOT use NL authoring for this rebind.'
        )
    body = "\n".join(bind_lines)
    return (
        f"{_PREAMBLE}\n\n"
        f"CORRECTIVE REBIND (Model-API only): On the {screen} screen, re-wire each KPI Expression "
        f"to the correct aggregate count. This step exists because the NL bind produced the wrong "
        f"expression (likely .List.Length instead of .Count). Fix ONLY the Expression values:\n"
        f"{body}\n"
        f"Do NOT change the card structure, labels, or aggregate definitions. Do not publish."
    )


def workflow_engine(params: dict) -> str:
    """Author the FIXED, N-invariant data-driven state-machine engine inside a producer Core app.
    The engine is a set of public Service Actions, each delegating to a private *Internal Server Action
    (the OS-DPL-50205 split + ASE-testability rule). params: entities (role->name dict), actions (list
    of engine action names to author this turn; default 4-action set), core_app (default
    WorkflowEngineCore), model_output_consumer (bool; default True — emit robust-JSON paragraph)."""
    entities = _p(params, "entities", {})
    requested = _p(params, "actions", _ENGINE_ACTIONS[:4])
    core_app = _p(params, "core_app", "WorkflowEngineCore")
    model_output_consumer = _p(params, "model_output_consumer", True)

    # Filter unknown actions; preserve order; tolerate empty list
    valid_set = set(_ENGINE_ACTIONS)
    actions = [a for a in (requested or []) if a in valid_set]

    # Entity name shortcuts
    tt = _en(entities, "task_template")
    sc = _en(entities, "scenario")
    ss = _en(entities, "scenario_step")
    tr = _en(entities, "transition_rule")
    dr = _en(entities, "decision_row")
    wi = _en(entities, "workflow_instance")
    ti = _en(entities, "task_instance")
    ae = _en(entities, "audit_event")

    # Cross-cutting split rule (always emitted even for empty action list)
    split_rule = (
        f"SPLIT RULE (OS-DPL-50205, live-proven): every engine operation is a PUBLIC Service Action that "
        f"delegates ALL logic (including every entity write) to a NON-public *Internal Server Action "
        f"(mirrors AdvanceInstance->AdvanceInternal). The public action may NOT Create/Update/Delete any "
        f"entity — that trips OS-DPL-50205 at publish. The split ALSO makes the logic runtime-testable: "
        f"the ASE harness exposes only Server Actions, so the real logic lives in the *Internal Server "
        f"Action. co-locate all engine Service Actions INSIDE {core_app} (the producer Core) — do NOT "
        f"author engine actions in a separate consumer/orchestrator app (also OS-DPL-50205 when the "
        f"producer is screen-bearing)."
    )

    chunk_warning = ""
    if len(actions) > 4:
        chunk_warning = (
            f"\nCHUNK WARNING: {len(actions)} actions requested. Authoring all in one turn risks the "
            f"900s Mentor session timeout (WALL-005). Recommend splitting into ≤4 actions per turn.\n"
        )

    # Per-action doctrine blocks
    action_blocks = []

    _action_docs = {
        "ResolveScenario": (
            f"ResolveScenario (Public Service Action -> ResolveScenarioInternal Server Action): "
            f"given a context/criteria input, look up the matching {sc}.Id by scoring against {dr} rows "
            f"(indexed priority match — each {dr} row has a priority/rank; pick the highest-priority "
            f"matching row). This lookup MUST be N-invariant: never scans the full {dr} table "
            f"unconditionally; the filter is indexed on the priority/matching columns so it scales with "
            f"any N rows. Returns the resolved {sc}.Id."
        ),
        "InstantiateWorkflow": (
            f"InstantiateWorkflow (Public Service Action -> InstantiateWorkflowInternal Server Action): "
            f"create a {wi} record (State=Running), then spawn ONLY the FIRST wave of {ti}(s): "
            f"the {ss} row(s) at the MINIMUM Sequence value for the {sc} (several only if they share "
            f"that first Sequence's ParallelGroup). SEQUENCE IS THE PRIMARY FRONTIER (live-proven "
            f"parallel-spawn bug): do NOT spawn 'all steps with no DependsOnStep' — in the common linear "
            f"case DependsOnStep is unset on every step, so 'no unmet dependency' matches EVERY step and "
            f"spawns the ENTIRE workflow at once. That defeats sequential gating AND the rework loop: "
            f"AdvanceInstance's 'return early while sibling {ti} still Active' guard then suppresses the "
            f"{tr} reject-routing, so a rejected approval is never reworked and the instance can complete "
            f"with a step bypassed. DependsOnStep is an ADDITIONAL gate ONLY when explicitly populated — "
            f"never the sole readiness test. Write an {ae} row for the instantiation. Return the new {wi}.Id."
        ),
        "AdvanceInstance": (
            f"AdvanceInstance (Public Service Action -> AdvanceInstanceInternal Server Action — "
            f"load-bearing; called by CompleteTask): check if ALL Active {ti}(s) for the {wi} are Done. "
            f"If not, nothing to advance yet (return early). If yes, evaluate {tr}.Condition expressions "
            f"over the completed {ti}.OutputData to pick the next transition (first-match wins). Spawn "
            f"next {ti}(s) at the next frontier: the matched {tr} target, else the {ss} at the completed "
            f"step's Sequence+1 (the linear frontier). Honor ParallelGroup (spawn all steps sharing that "
            f"next Sequence's group). DependsOnStep is an ADDITIONAL gate ONLY when populated (spawn a step "
            f"only once its declared dependencies are Done) — an UNSET DependsOnStep must NOT count as "
            f"'ready', or the whole graph spawns at once (live-proven parallel-spawn bug). Set {wi}.State "
            f"to Running (more steps remain) or Completed (all steps done). Write an {ae} for the transition. "
            f"BRANCHING + PARALLELISM (off-by-one bug — live-proven): iterate the target steps and spawn "
            f"EXACTLY ONE {ti} INSIDE the loop body per step. Do NOT carry a single 'chosen step' variable "
            f"out of the loop and spawn once after it — that pattern keeps only the LAST iteration's step "
            f"(the off-by-one bug: it spawned the last step instead of each). One Create per iteration "
            f"guarantees every step in a ParallelGroup is spawned exactly once. "
            f"FRONTIER, NOT A COUNT (live-proven over-advance bug): NEVER pick the next step by COUNTING "
            f"completed {ti} rows or by an ordinal count of done tasks — a rework / loop-back (a rejected "
            f"approval routed by a {tr} back to an earlier {ss}) adds EXTRA Done tasks, so a count "
            f"OVER-ADVANCES and skips steps (e.g. jumps straight to Completed). Determine the next step from "
            f"the GRAPH only: follow the matched {tr} (which may route BACKWARD to an earlier {ss} for "
            f"rework — a single {ss} can therefore have MULTIPLE {ti} over the instance's lifetime), or "
            f"spawn the next unstarted step by DependsOnStep satisfaction. Reachability is defined by "
            f"transitions/dependencies, never by how many tasks have completed."
        ),
        "CompleteTask": (
            f"CompleteTask (Public Service Action -> CompleteTaskInternal Server Action): inputs "
            f"TaskInstanceId, OutputData, and ActorRole (Text — the acting user's role). Output Accepted "
            f"(Boolean). "
            f"ROLE ENFORCEMENT (server-side gate — routing is not enforcement): BEFORE any write, fetch "
            f"the {ti} -> its {tt}.DefaultRole (the RequiredRole for this step). If RequiredRole is "
            f"non-empty AND ActorRole <> RequiredRole, REFUSE: do NOT set Done, do NOT advance, write an "
            f"{ae} row ('refused: <ActorRole> may not complete step requiring <RequiredRole>'), set "
            f"Accepted=False, and return. Only a role-matched (or unrestricted, empty-RequiredRole) "
            f"completion proceeds. A filtered queue is UX only; this match-check in the NON-public "
            f"*Internal Server Action is the real boundary. "
            f"IDENTITY TRUST BOUNDARY (never trust a client-supplied role): the PUBLIC CompleteTask "
            f"Service Action (and any screen action) must DERIVE ActorRole from the authenticated user — "
            f"GetUserId() -> look up that user's role in the app's user/role mapping — and pass THAT to "
            f"CompleteTaskInternal. It must NOT accept a role value from the client request; a "
            f"client-passed role is spoofable. The Internal action enforces the match; the public wrapper "
            f"sources the role from identity. (Because the wrapper sources identity, and the Internal is "
            f"non-public, a client cannot bypass the gate.) "
            f"On an accepted completion: set the {ti}.State to Done, write the OutputData payload, write an "
            f"{ae} row, THEN call AdvanceInstance to evaluate whether the workflow can progress. Sequence "
            f"matters: persist the task completion BEFORE advancing. APPROVAL OUTCOME: an approval task whose "
            f"OutputData carries a Reject outcome must route (via its {tr}) BACK to a rework {ss} — a "
            f"loop, not forward progress — and does NOT mark the instance Completed (see AdvanceInstance "
            f"FRONTIER rule); an Approve outcome advances normally. DETECT THE VALUE, NOT A BARE TOKEN "
            f"(live-proven false-positive): the submitted OutputData JSON may include the decision field's "
            f"Options (e.g. [\"Approve\",\"Reject\"]), so a bare Index(OutputData,\"Reject\") ALWAYS matches "
            f"and Approve wrongly loops. Match the chosen VALUE — the substring \"Value\":\"Reject\" (built "
            f"with Chr(34) for the quotes, since OSAL has no quote escape) — not the bare token. When there "
            f"is no {tr}, advance linearly to the {ss} at the completed step's Sequence+1 (a per-instance "
            f"frontier), else mark Completed — never by a global done-task count."
        ),
        "ClaimTask": (
            f"ClaimTask (Public Service Action -> ClaimTaskInternal Server Action): set the "
            f"{ti}.Assignee to the claiming user. FETCH-THEN-MODIFY: fetch the {ti} record first "
            f"(GetTaskInstanceById aggregate), then set only the Assignee field on the fetched record, "
            f"then Update — a bare {{Id, Assignee}} record blanks all other columns (wipes unset columns, "
            f"live-proven ODC bug). Write an {ae} for the claim."
        ),
        "EscalateOverdue": (
            f"EscalateOverdue (Public Service Action -> EscalateOverdueInternal Server Action): a Timer "
            f"sweep over active {ti} rows whose DueAt is past the current timestamp. Set State to "
            f"Escalated (or equivalent). This action is called BY A TIMER ONLY — do not wire it to any "
            f"screen or user-triggered event."
        ),
        "ValidateComposition": (
            f"ValidateComposition (Public Service Action -> ValidateCompositionInternal Server Action): "
            f"validate a proposed workflow composition before instantiation. Checks: every {ss} step "
            f"resolves to a real {tt} (no orphan {ss} with an invalid {tt}Id); every {tt}.DefaultRole "
            f"exists and is non-empty; no orphan steps and no cycle in the DependsOnStep graph; "
            f"{ss}.SlaHours is positive and sane. Invalid compositions are rejected with a clear error — "
            f"nothing runs unvalidated."
        ),
        "ComposeInstance": (
            f"ComposeInstance (Public Service Action -> ComposeInstanceInternal Server Action): "
            f"assemble the {ss} step graph from the GOVERNED library of {tt} TaskTemplates — read the "
            f"{sc} + its {ss} rows, resolve each to the declared {tt}, and build the composition. "
            f"This action is composition only: never invents a task not in the {tt} library."
        ),
        "GetInstanceStatus": (
            f"GetInstanceStatus — the task-queue / instance-state READ (live-proven required): any "
            f"worker UI (a 'my open tasks' queue, an instance detail) needs this, and it is ALSO how you "
            f"drive+observe the engine at runtime (the ASE test harness's db_query is v1 template-only and "
            f"returns no SELECT rows, so drive/verify must read through action RETURNS). "
            f"READ ACTION — EXCEPTION TO THE SPLIT RULE: it performs NO entity writes, so it does NOT need "
            f"the public->*Internal write-split. Author it as a NON-public Server Action directly "
            f"(same-app screens call Server Actions, and the ASE harness exposes ONLY Server Actions — this "
            f"is what makes the engine runtime-drivable). Add a thin PUBLIC Service Action wrapper only if a "
            f"different app must read it (allowed — it is side-effect-free). "
            f"INPUT: WorkflowInstanceId ({wi} Identifier). OUTPUTS: State (Text — the {wi}.State), "
            f"OpenTaskId ({ti} Identifier — the first still-open task), OpenStepCode (Text — that task's "
            f"{tt}.Code), OpenCount (Integer — how many open tasks remain). LOGIC: fetch {wi} by Id -> "
            f"State; aggregate {ti} JOINed to {tt} ({ti}.{tt}Id = {tt}.Id) filtered to "
            f"{ti}.WorkflowInstanceId = the input AND {ti}.Status <> \"Done\" (use <> \"Done\" as the open "
            f"test — do NOT hardcode a specific open-status literal), sorted by {ti}.Id ascending; "
            f"OpenCount = its count; if > 0 set OpenTaskId + OpenStepCode from the first row, else leave "
            f"them empty. The role-scoped queue variant is GetOpenTasksForActor (below)."
        ),
        "GetOpenTasksForActor": (
            f"GetOpenTasksForActor — the role-scoped WORKER QUEUE read (this is what makes 'more than one "
            f"KIND of worker' real: each role sees only its own tasks). Same READ character as "
            f"GetInstanceStatus — EXCEPTION TO THE SPLIT RULE (no writes -> NON-public Server Action, no "
            f"public/*Internal split; add a thin public Service Action wrapper only for cross-app read). "
            f"INPUT: ActorRole (Text). OUTPUT: a List of open tasks (each row: TaskInstanceId ({ti} "
            f"Identifier), StepCode (Text = {tt}.Code), WorkflowInstanceId ({wi} Identifier), InstanceNo "
            f"(Text)) plus Count (Integer). LOGIC: aggregate {ti} JOINed to {tt} ({ti}.{tt}Id = {tt}.Id) "
            f"and to {wi} ({ti}.WorkflowInstanceId = {wi}.Id), filtered to {tt}.DefaultRole = ActorRole "
            f"AND {ti}.Status <> \"Done\" (open across ALL instances), sorted by {ti}.Id ascending; return "
            f"the rows + Count. This is N-invariant: the filter is indexed on DefaultRole + Status, never a "
            f"full scan. IDENTITY NOTE: like CompleteTask, the production wrapper/screen should derive "
            f"ActorRole from the authenticated user (GetUserId -> role mapping), not from a client param — "
            f"the queue is scoped to who you ARE, not to a role you claim."
        ),
    }

    for action in actions:
        if action in _action_docs:
            action_blocks.append(f"- {_action_docs[action]}")

    actions_section = "\n".join(action_blocks) if action_blocks else "(no actions selected this turn)"

    robust_json = ""
    if model_output_consumer:
        robust_json = (
            f"\nROBUST JSON EXTRACTION (for any action that deserializes a model/agent Response): "
            f"the Response arrives wrapped in a ```json ... ``` markdown fence even with a strict "
            f"'raw JSON only' system prompt. Extract robustly: JsonStart = Index(Response,\"{{\"); "
            f"JsonEnd = Index(Response,\"}}\",0,True) (reverse-search for the last '}}'); "
            f"guard JsonStart<>-1 and JsonEnd>JsonStart; extract the substring [first '{{' .. last '}}'] "
            f"BEFORE JSONDeserialize — never deserialize the raw Response. "
            f"Index(Response,\"}}\",0,True) with the reverse flag finds the last '}}' (avoiding fence "
            f"chars after the JSON block). Guard -1 means not-yet-found (no JSON in Response).\n"
        )

    return (
        f"{_PREAMBLE}\n\n"
        f"Author the FIXED N-invariant state-machine engine inside the producer Core app {core_app}. "
        f"This engine is DATA-DRIVEN: the workflow shape, steps, transitions, and rules are stored in "
        f"entities ({tt}, {sc}, {ss}, {tr}, {dr}) — the engine code never changes for new workflow types, "
        f"only the data does.\n\n"
        f"{split_rule}\n"
        f"{chunk_warning}"
        f"Author the following engine Service Actions this turn:\n"
        f"{actions_section}\n"
        f"{robust_json}"
        f"After authoring each action, run model validation and report errors. Do not publish."
    )


def dynamic_form(params: dict) -> str:
    """Author a reactive Web Block that renders a TaskTemplate.FieldDefinition JSON array at runtime
    via a FIXED Switch/If over known field types — no dynamic widget. params: block_name (default
    DynamicTaskForm), screen (default TaskDetail), entities dict (roles task_template/task_instance),
    field_types (default 6-set), complete_action (default CompleteTask), structure_name (default FieldDef),
    role_gate (bool, default True)."""
    block_name = _p(params, "block_name", "DynamicTaskForm")
    screen = _p(params, "screen", "TaskDetail")
    entities = _p(params, "entities", {})
    field_types = _p(params, "field_types", ["text", "textarea", "number", "date", "select", "checkbox"])
    complete_action = _p(params, "complete_action", "CompleteTask")
    structure_name = _p(params, "structure_name", "FieldDef")
    role_gate = _p(params, "role_gate", True)

    tt = _en(entities, "task_template")
    ti = _en(entities, "task_instance")

    field_types_str = ", ".join(field_types)

    # Only emit Switch branches for the chosen field_types
    branch_lines = "\n".join(
        f"   - type='{ft}': render the appropriate {ft} input widget" for ft in field_types
    )

    role_gate_block = ""
    if role_gate:
        role_gate_block = (
            f"\nROLE GATE: before rendering the submit/complete action, gate actioning via "
            f"ln_current_user — check the current user's role matches the TaskInstance.AssignedRole. "
            f"Non-assignees see the form read-only; only the assignee (matched via ln_current_user) "
            f"can submit. Keep the screen Anonymous (the role gate is enforced in logic, not as a "
            f"platform Role).\n"
        )
    else:
        role_gate_block = (
            f"\nNO role gate requested — the form is writable by any authenticated user. "
            f"Keep the screen Anonymous.\n"
        )

    robust_json = (
        f"ROBUST JSON PARSE of FieldDefinition (live-proven this session): FieldDefinition is a JSON array "
        f"string like [{{\"key\",\"label\",\"type\",\"required\",\"options\"}}]. Parse it into a "
        f"{structure_name} Structure list. TWO ODC gotchas that MUST be handled or the form renders BLANK:\n"
        f"  1. RESERVED WORD: name the field-type attribute 'FType', NOT 'Type' ('Type' is a reserved word).\n"
        f"  2. JSONDeserialize is CASE-SENSITIVE on property names: the lowercase JSON keys do NOT map to the "
        f"Structure attributes unless NORMALIZED first. Before JSONDeserialize, chain Replace() on the JSON "
        f"string to match the attribute names exactly: \"type\": -> \"FType\":, \"key\": -> \"Key\":, "
        f"\"label\": -> \"Label\":, \"required\": -> \"Required\":, \"options\": -> \"Options\": (these only "
        f"match property NAMES, which are followed by a colon; field VALUES are untouched). Omitting this "
        f"leaves Label/Key blank — the live-proven empty-label bug.\n"
        f"  Extract the array robustly first: JsonStart = Index(FieldDefJson,\"{{\") (the first '{{'); "
        f"JsonEnd = Index(FieldDefJson,\"}}\",0,True) (the last '}}'); guard JsonStart<>-1 and JsonEnd>JsonStart."
    )

    return (
        f"{_PREAMBLE}\n\n"
        f"SPIKE — prototype this block carefully; the FieldDefinition rendering pattern is novel in this "
        f"codebase. Render a {tt}.FieldDefinition JSON array at RUNTIME on the {screen} screen (or a "
        f"{block_name} block) — the field list is DATA, not hardcoded widgets.\n\n"
        f"PARSE STRUCTURE: author a {structure_name} Structure (FormField) in the producer Core (a Structure "
        f"cannot live in a BPT app; import it here) with attributes: Key (Text), Label (Text), FType (Text), "
        f"Required (Boolean), Options (List of Text), Value (Text).\n\n"
        f"ACTIVE-TASK AGGREGATE + LoadActiveForm: an aggregate fetches the current active {ti} "
        f"(Status <> \"Done\") joined to {tt} to read its FieldDefinition. A LoadActiveForm screen action "
        f"clears a Fields (List of {structure_name}) local, then parses FieldDefinition into it (see ROBUST "
        f"JSON PARSE below), each JSON element -> a FormField (Value=\"\"). Call LoadActiveForm on screen "
        f"load AND after each submit so the next task's form loads.\n\n"
        f"FIXED FIELD-TYPE SET (no dynamic widget): render ONE input per Fields row via a Switch/If over "
        f"FType — one branch per known type only (do NOT build a generic/dynamic widget). Show each field's "
        f"Label ABOVE its input. Branches for this form: {field_types_str}.\n"
        f"Switch branches:\n{branch_lines}\n"
        f"SELECT LIMITATION (live-proven): an ODC Dropdown inside a per-row List cannot bind its Options/Value "
        f"to the OUTER list's current row — so 'select'-type fields FALL BACK to a text Input (the user types "
        f"the value). Render select as a text input unless the option set is static (not per-row).\n\n"
        f"PRE-FILL: read {ti}.InputData (JSON) and pre-fill each row's Value from the matching key before the "
        f"user edits.\n\n"
        f"SUBMIT: on submit, serialize the field values to JSON -> write to {ti}.OutputData -> call "
        f"{complete_action}, then refresh the active-task aggregate + LoadActiveForm. For approval-type tasks, "
        f"write the Approve/Reject outcome into OutputData so a TransitionRule.Condition can branch on it.\n"
        f"SERIALIZATION CAVEAT (live-proven false-positive): if you JSONSerialize the WHOLE FormField list, the "
        f"output INCLUDES each field's Options metadata (e.g. the select's [\"Approve\",\"Reject\"]) — so a "
        f"downstream substring check on OutputData for \"Reject\" ALWAYS matches, even on Approve, and the "
        f"engine's reject-branch fires wrongly. Mitigate BOTH ends: (a) prefer serializing ONLY the Key->Value "
        f"pairs (drop Label/FType/Options) so OutputData carries just the answers; AND (b) any outcome check "
        f"must match the VALUE precisely — e.g. the substring \"Value\":\"Reject\" (the chosen value), never the "
        f"bare token \"Reject\" (which also appears in Options).\n\n"
        f"{robust_json}\n"
        f"{role_gate_block}"
        f"Set data-spec-id on each rendered input widget so harness-capture can resolve inputs. Keep the "
        f"screen Anonymous. After authoring, run model validation and report errors. Do not publish."
    )


def library_import(params: dict) -> str:
    """Author a deterministic library loader for any N library rows — two modes.
    seed: NON-PUBLIC LoadLibrary orchestrator; FK order; DELETE-then-INSERT; Confirm-param-gated
    (ODC has NO IsInDevStage() built-in — a phantom stage call fails publish OS-DPL-50205).
    etl: consumed/exposed REST bulk endpoint; natural-key upsert; FK order; NOT delete-then-insert.
    params: mode ('seed'|'etl'), library_entities (default FK-ordered 5), source (mode-dependent
    default), natural_key (default 'Code'), loader_name (default LoadLibrary/BulkImportLibrary)."""
    mode = _p(params, "mode", "seed")
    if mode not in ("seed", "etl"):
        raise ValueError(f"library_import: unknown mode {mode!r}; expected 'seed' or 'etl'")

    default_entities = ["TaskTemplate", "Scenario", "ScenarioStep", "TransitionRule", "DecisionRow"]
    library_entities = _p(params, "library_entities", default_entities)
    natural_key = _p(params, "natural_key", "Code")

    if mode == "seed":
        loader_name = _p(params, "loader_name", "LoadLibrary")
        source = _p(params, "source", "a JSON resource file bundled with the app")
        entities_ordered = ", ".join(f"{i+1}. {e}" for i, e in enumerate(library_entities))

        return (
            f"{_PREAMBLE}\n\n"
            f"Author a NON-PUBLIC Server Action named {loader_name} that seeds the workflow library "
            f"entities for any N rows (N-invariant — not hardcoded row counts). This loader is "
            f"NON-PUBLIC (OS-DPL-50205: a public action may not perform entity writes; the loader "
            f"writes every entity — keep it non-public and call it from a non-public orchestrator).\n\n"
            f"SOURCE: read library data from {source}.\n\n"
            f"FK ORDER (parents before children): create rows in this order so FK references resolve:\n"
            f"{entities_ordered}\n\n"
            f"DELETE-then-INSERT (re-runnable): before inserting, DELETE all existing rows in REVERSE "
            f"FK order (children before parents) so re-runs are idempotent and safe.\n\n"
            f"RE-RUN GUARD — NO IsInDevStage() IN ODC (live-proven, OS-DPL-50205): ODC has no "
            f"IsInDevStage() / GetPersonalAreaName() / stage-detection built-in. Do NOT call one — "
            f"Mentor will substitute a non-existent function and PUBLISH then fails model-features "
            f"validation (OS-DPL-50205) even though authoring reports 0 errors (this validation runs "
            f"only at publish, not at authoring). Instead gate on an explicit Boolean INPUT PARAMETER "
            f"named Confirm (default False): the loader no-ops (returns immediately) unless the caller "
            f"passes Confirm=True. This is the ODC-safe dev-only guard — production code never calls it "
            f"with Confirm=True, so the destructive delete-then-insert cannot run by accident.\n\n"
            f"HEADLESS-CORE CAVEAT: if the Core app has no screens (screens:[]), its OnReady action "
            f"never fires and the seed never runs. Give the Core a minimal bootstrap screen and call "
            f"{loader_name} with Confirm:=True from that screen's OnReady — do not rely on a timer or a "
            f"WhenPublished trigger alone for a headless data-owner (live-proven: headless core cannot "
            f"seed via OnReady). The bootstrap screen is the dev-only trigger; do not deploy it (or do "
            f"not pass Confirm=True) in production.\n\n"
            f"After authoring, run model validation and report errors. Do not publish."
        )
    else:
        # mode == "etl"
        loader_name = _p(params, "loader_name", "BulkImportLibrary")
        source = _p(params, "source", "a REST API caller (consumed endpoint)")
        entities_ordered = ", ".join(f"{i+1}. {e}" for i, e in enumerate(library_entities))

        return (
            f"{_PREAMBLE}\n\n"
            f"Author a REST bulk-import endpoint named {loader_name} for any N rows (N-invariant). "
            f"Expose it as a consumed/exposed REST endpoint so external systems can push library data.\n\n"
            f"NATURAL-KEY UPSERT — natural-key upsert (not delete-then-insert): for each incoming "
            f"record, look up by {natural_key} (the natural key). If found: fetch the existing record "
            f"first (fetch-then-modify to avoid wipes unset columns — a bare {{Id, changed_field}} "
            f"record blanks all other columns), then Update only the changed fields. If not found: "
            f"Create a new row.\n\n"
            f"FK ORDER / FK order (parents before children): process rows in this order so FK "
            f"references resolve:\n"
            f"{entities_ordered}\n\n"
            f"NOT delete-then-insert: the ETL upsert is incremental — do not DELETE rows before "
            f"importing (that would wipe live data; delete-then-insert is only for the seed/dev mode).\n\n"
            f"SOURCE: data arrives from {source}.\n\n"
            f"After authoring, run model validation and report errors. Do not publish."
        )


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
    "workflow-add": workflow_add,
    "app-reference": app_reference,
    "external-library": external_library,
    "screen": screen,
    "nav-block": nav_block,
    "place-nav": place_nav,
    "top-bar": top_bar,
    "page-header": page_header,
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
    "kpi-rebind": kpi_rebind,
    "workflow-engine": workflow_engine,
    "dynamic-form": dynamic_form,
    "library-import": library_import,
}


def render(name: str, params: dict) -> str:
    if name not in RECIPES:
        raise KeyError(f"unknown recipe {name!r}; known: {', '.join(sorted(RECIPES))}")
    return RECIPES[name](params or {})


# ── spec -> ordered build plan (the loop-closer) ─────────────────────────────
_DATA_COMPONENT_TYPES = {"Table", "List", "Card", "Board"}

# ── STEP ATOMICITY MODEL ──────────────────────────────────────────────────────
# Every plan step maps to ONE Mentor turn. The single biggest reliability lever (learned the hard
# way, live) is keeping each turn ATOMIC — one concern, few authored elements. Overloaded turns hang
# (R1) or fail/phantom; atomic ones land. So the planner splits multi-element work into one-concern
# steps (create-form → action then form+wire; row-actions → edit/delete; action-button → action then
# wire, per button; seeds → per-entity or one FK graph). `_step_weight` estimates a step's turn-load
# so heavy steps are visible and can be split BEFORE they fail.
#
# The exceptions — recipes that MUST be one turn because their elements are interdependent within a
# single Model-API transaction (a later separate turn would roll them back / can't share locals):
#   * data-model  — interdependent entities (a FK to a not-yet-created entity fails); one turn.
#   * seed-graph  — captured parent-Id locals are shared across the child creates; one action.
# These are exempt from the split rule but their weight is still surfaced (keep rows/entities lean).
_ATOMIC_UNIT_RECIPES = {"data-model", "seed-graph"}
MAX_STEP_WEIGHT = 14        # a turn beyond ~this many authored elements risks overload/hang


def _step_weight(recipe: str, params: dict) -> int:
    """Rough count of the elements a step asks Mentor to author in one turn (advisory)."""
    p = params or {}
    if recipe == "data-model":
        return sum(1 + len([a for a in e.get("attributes", []) if not a.get("isIdentifier")])
                   for e in p.get("entities", []))
    if recipe == "seed-graph":
        return sum(len(e.get("rows", []) or []) for e in p.get("entities", []))
    if recipe == "seed-entity":
        return len(p.get("rows", []) or [])
    if recipe == "action-button":
        return 4 if p.get("phase") in (None, "combined") else 2
    if recipe == "create-form":
        return len(p.get("fields", []) or []) + 2
    if recipe == "list-screen":
        return len(p.get("columns", []) or []) + 2
    if recipe == "detail":
        return len(p.get("stages", []) or []) + len(p.get("review_teams", []) or []) + 2
    if recipe == "nav-block":
        return len(p.get("items", []) or []) + 2
    if recipe == "screen":
        return len(p.get("screens", []) or [])
    if recipe == "dashboard":
        return len(p.get("cards", []) or []) + 1
    return 2


def annotate_weights(steps: list[dict]) -> list[dict]:
    """Attach a `weight` (est. Mentor-turn load) to each step + an `atomicity_warning` on any heavy,
    non-exempt step. Pure/advisory — does not split; surfaces steps a human/loop should split."""
    for st in steps:
        w = _step_weight(st["recipe"], st.get("params", {}))
        st["weight"] = w
        if w > MAX_STEP_WEIGHT:
            if st["recipe"] in _ATOMIC_UNIT_RECIPES:
                # can't split (interdependent) — but honestly flag the load; keep it lean
                st["atomicity_note"] = (f"heavy (~{w}) but must be one turn — keep entities/rows lean; "
                                        f"the recovery loop (R1) absorbs an occasional hang")
            else:
                st["atomicity_warning"] = f"heavy step (~{w} > {MAX_STEP_WEIGHT}); split for one concern/turn"
    return steps


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


def _is_entity_bound_screen(spec_screen: dict, entity: str) -> bool:
    """True when at least one data component on this screen is bound to `entity`."""
    for c in spec_screen.get("components", []):
        if c.get("type") in _DATA_COMPONENT_TYPES and (c.get("boundTo") or "").split(".")[0] == entity:
            return True
    return False


def _list_screen_for_entity(
    spec: dict, entity: str, exclude: str | None = None, prefer: str | None = None
) -> str | None:
    """Return the id of a screen that shows a data list for `entity`.

    Selection order (W2):
    1. If `prefer` names a screen that is itself entity-bound, return it (anchor to
       the action's own screen — fixes the create-form measurement seam).
    2. Else: the first non-excluded entity-bound screen (legacy behaviour).
    3. None when no entity-bound screen exists.

    `prefer` is keyword-optional with default None so all existing call-sites that
    pass positional (spec, entity) or (spec, entity, exclude) are byte-identical."""
    screens = spec.get("screens", [])
    # Step 1: honour the preferred anchor if it is entity-bound.
    if prefer:
        for s in screens:
            if s["id"] == prefer and _is_entity_bound_screen(s, entity):
                return s["id"]
    # Step 2: first non-excluded entity-bound screen (original behaviour).
    for s in screens:
        if s["id"] == exclude:
            continue
        if _is_entity_bound_screen(s, entity):
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


def plan_from_spec(spec: dict, *, kpi_model_api_fallback: bool = False) -> list[dict]:
    """Derive an ordered list of pre-corrected build steps directly from an
    app_spec's first-class fields — the chain spec -> recipe -> (build) -> verify.
    Each step is {recipe, params, why}; render each with `render(step['recipe'],
    step['params'])`. Reads app.navigation, app.auth, and per-screen components +
    access. Order: shared nav block -> seed the user entity -> per data screen
    (bind its list, then gate it if access requires).

    kpi_model_api_fallback (W5c, default False): when True, append one `kpi-rebind`
    step after each dashboard bind step — a deterministic Model-API corrective for
    the KPI rebind if the NL bind still produces .List.Length.  Off by default."""
    steps: list[dict] = []
    screens = list(spec.get("screens", []) or [])
    auth = spec.get("auth") or {}
    login = auth.get("loginScreen") or "Login"

    # B2a — headless data-owner seed safeguard: a spec that OWNS seed data (sampleData) but has NO
    # screens (a modular Core) can never RUN its seed — the seed is triggered by a screen's OnReady, and
    # the WhenPublished timer is unreliable. Synthesize a minimal bootstrap Home screen so the seed fires
    # on first load. (A consumer app owns no entities, so this only affects data-owning producers.)
    _owns_seed = any(e.get("sampleData") for e in (spec.get("dataModel", {}) or {}).get("entities", []))
    if _owns_seed and not screens:
        screens = [{"id": "home", "name": "Home", "isDefault": True,
                    "components": [{"id": "coreHealth", "type": "Container",
                                    "label": (spec.get("app", {}) or {}).get("name", "Core") + " — data service"}],
                    "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "coreHealth"}]}}]

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
        # Expose entities (Public=Yes) when the spec marks this app a data-owning producer, so consumer
        # apps can reference + read them (else the modular producer→consumer data flow is silently empty).
        public = bool((spec.get("dataModel") or {}).get("public") or (spec.get("app") or {}).get("exposesData"))
        steps.append({"recipe": "data-model", "why": "spec.dataModel.entities (all in one turn)",
                      "params": {"entities": entities, "public": public}})
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
        # top-bar: the app-shell header (breadcrumb + env chip + CTA). Emit for FREE whenever the app
        # has a sidebar (a modern shell has both) — unless navigation.topBar is explicitly false.
        tb = nav.get("topBar", {})
        if screens and tb is not False:
            tb = tb if isinstance(tb, dict) else {}
            tb_params = {"app_label": nav.get("brand") or (spec.get("app") or {}).get("name") or "App",
                         "screens": [s.get("name", s["id"]) for s in screens]}
            if tb.get("env"):
                tb_params["env_label"] = tb["env"]
            cta = tb.get("cta") or {}
            if cta.get("label"):
                tb_params["cta_label"] = cta["label"]
            if cta.get("screen") or cta.get("action"):
                tb_params["cta_screen"] = cta.get("screen") or cta.get("action")
            steps.append({"recipe": "top-bar", "why": "app-shell top bar (breadcrumb + env chip + CTA)",
                          "params": tb_params})

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
        # page-header: a screen's lead header (title + tag + action row), emitted when declared.
        hdr = s.get("header")
        if hdr and hdr.get("title"):
            hp = {"screen": s["id"], "title": hdr["title"]}
            for k in ("subtitle", "tag", "actions"):
                if hdr.get(k) is not None:
                    hp[k] = hdr[k]
            steps.append({"recipe": "page-header", "why": f"{s['id']} page header", "params": hp})
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
                # W4: resolve the declared button from the action's trigger.onComponent.
                btn = _declared_create_button(spec, s["id"], entity)
                if btn:
                    p["button_id"] = btn["id"]
                    p["button_label"] = btn["label"]
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
        # UI-A: a KPI dashboard header on this screen -> `dashboard` step(s).
        # W5b: when any card is a COUNT card, split into two atomic steps (aggregate, then bind)
        # so each turn has a single responsibility (proven one-step-per-unit pattern, commit 654f038).
        dash = s.get("dashboard")
        if dash and dash.get("cards"):
            p_base = {"screen": s["id"], "cards": dash["cards"]}
            if dash.get("columns"):
                p_base["columns"] = dash["columns"]
            has_count_card = any(c.get("entity") or c.get("aggregate") for c in dash["cards"])
            if has_count_card:
                # W5e (live-proven OS-BEW-COMP crash, RivianReviewerPortal3/4): author the COUNT aggregates
                # FIRST, onto a screen WITHOUT the kpi widgets. Adding aggregates AFTER the kpi-card
                # structure exists deterministically crashes the ODC compiler (OS-BEW-COMP-50008); the
                # old aggregate-first order compiled fine. So: aggregate -> structure -> bind.
                steps.append({"recipe": "dashboard",
                              "why": f"{s['id']} KPI dashboard — author COUNT aggregates on a clean screen (atomic step 1/3)",
                              "params": {**p_base, "phase": "aggregate"}})
                steps.append({"recipe": "dashboard",
                              "why": f"{s['id']} KPI dashboard — author card STRUCTURE (.kpi-card containers, atomic step 2/3)",
                              "params": {**p_base, "phase": "structure"}})
                steps.append({"recipe": "dashboard",
                              "why": f"{s['id']} KPI dashboard — bind KPI Expressions to Count.Count (atomic step 3/3)",
                              "params": {**p_base, "phase": "bind"}})
                # W5c: deterministic Model-API corrective — only when explicitly requested.
                if kpi_model_api_fallback:
                    rebind_cards = [{"label": c.get("label", ""), "entity": c.get("entity") or c.get("aggregate")}
                                    for c in dash["cards"] if c.get("entity") or c.get("aggregate")]
                    steps.append({"recipe": "kpi-rebind",
                                  "why": f"{s['id']} KPI corrective rebind (applyModelApiCode)",
                                  "params": {"screen": s["id"], "cards": rebind_cards}})
            else:
                steps.append({"recipe": "dashboard", "why": f"{s['id']} KPI dashboard header",
                              "params": p_base})
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
            # workflow state-transition buttons that mutate the screen's entity-typed input record.
            # ONE step per button — a single action+button turn is reliable; 3-in-one overloads the
            # turn and fails (live Rivian 2026-07-08: a 3-button action-button halted after 3 retries).
            if det.get("stateActions"):
                ip = next((x for x in s.get("inputParameters", []) if x.get("references")), None)
                if ip:
                    for b in det["stateActions"]:
                        base = {"screen": s["id"], "entity": ip["references"],
                                "id_param": ip["name"], "buttons": [b]}
                        # ATOMIC: author the server action, then (separate turn) add + wire the button.
                        steps.append({"recipe": "action-button", "why": f"{s['id']} {b['label']} — server action",
                                      "params": {**base, "phase": "action"}})
                        steps.append({"recipe": "action-button", "why": f"{s['id']} {b['label']} — button + wire",
                                      "params": {**base, "phase": "wire"}})

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
    # An entity that DECLARES sampleData is seeded even if this app renders no screen for it — a
    # headless data-owning Core (no screens) seeds the graph the portals that reference it display.
    listed |= {e["name"] for e in (spec.get("dataModel") or {}).get("entities", []) if e.get("sampleData")}
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
                                 "grounding": ag.get("grounding", []),
                                 "tools": ag.get("tools", [])}})
    # workflow-engine: chunked ≤4 actions/step (D6). Emitted before logic so engine SAs are
    # clearly separated from any remaining generic logic units.
    eng = spec.get("engine")
    if eng:
        actions = list(eng.get("actions") or [])
        entities = eng.get("entities") or {}
        core_app = eng.get("coreApp") or "WorkflowEngineCore"
        for i in range(0, max(len(actions), 1), 4):
            chunk = actions[i:i + 4]
            if not chunk:
                break
            steps.append({"recipe": "workflow-engine",
                          "why": f"engine actions {', '.join(chunk)} on {core_app}",
                          "params": {"entities": entities, "actions": chunk, "core_app": core_app}})

    # dynamic-form: one step per screen that declares a dynamicForm block.
    for s in spec.get("screens") or []:
        df = s.get("dynamicForm")
        if not df:
            continue
        steps.append({"recipe": "dynamic-form",
                      "why": f"dynamic task form on {s.get('name', s['id'])}",
                      "params": {"block_name": "DynamicTaskForm",
                                 "screen": s.get("name", s["id"]),
                                 "entities": {"task_template": df["taskTemplate"],
                                              "task_instance": df["taskInstance"]},
                                 "complete_action": df.get("completeAction", "CompleteTask")}})

    # library-import: one step when the spec declares a libraryImport block.
    lib = spec.get("libraryImport")
    if lib:
        steps.append({"recipe": "library-import",
                      "why": f"seed workflow library ({', '.join(lib.get('libraryEntities') or [])})",
                      "params": {"mode": lib.get("mode", "seed"),
                                 "library_entities": lib.get("libraryEntities") or []}})

    # Batch B: standalone logic units (emitted last — a service action may wrap a write-path server action).
    # D4 defense-in-depth: skip any serviceAction whose name is already in the engine's action list,
    # so engine names never appear as both a workflow-engine step AND a generic logic service-action step.
    _engine_names = set((spec.get("engine") or {}).get("actions") or [])
    _LOGIC_KIND = {"serviceAction": "service-action", "clientAction": "client-action",
                   "sqlAction": "sql-action", "globalEvent": "global-event"}
    for unit in spec.get("logic", []) or []:
        recipe = _LOGIC_KIND.get(unit.get("kind"))
        if not recipe:
            continue
        # D4: skip engine action names from generic logic loop.
        if unit.get("kind") == "serviceAction" and unit.get("name") in _engine_names:
            continue
        p = {k: v for k, v in unit.items() if k != "kind"}
        steps.append({"recipe": recipe, "why": f"logic {unit['kind']} {unit.get('name', '')}", "params": p})
    # Batch C: Business Processes LAST — a process needs its trigger Global Event + the PUBLIC Service Actions
    # its activities call to already exist. (The driver app_creates a BusinessProcess-kind app + authors the
    # process before the FIRST publish — a 0-process Workflow app corrupts its verify cache.)
    for proc in spec.get("processes", []) or []:
        acts = proc.get("activities", []) or []
        decision = proc.get("decision")
        human = proc.get("humanActivity") or proc.get("human_activity")
        base = {"name": proc["name"], "producer_app": proc["producerApp"], "trigger_event": proc["triggerEvent"]}
        # A SIMPLE process (few activities, no decision/human) authors in one turn. A COMPLEX process is
        # STAGED into many small turns — a skeleton (refs + Start->End) then one `workflow-add` per node —
        # so no single turn is Mentor-greedy / times out (900s). See bpt-process-keep-minimal doctrine.
        if not decision and not human and len(acts) <= 2:
            steps.append({"recipe": "workflow", "why": f"business process {proc['name']}",
                          "params": {**base, "activities": acts}})
        else:
            steps.append({"recipe": "workflow", "why": f"process {proc['name']} — skeleton (refs + Start->End)",
                          "params": {**base, "activities": acts, "skeleton": True}})
            for a in acts:
                sa = a.get("callsServiceAction") or a.get("calls_service_action")
                if not sa:
                    continue
                steps.append({"recipe": "workflow-add", "why": f"{proc['name']} += activity {sa}",
                              "params": {"process": proc["name"], "kind": "activity",
                                         "name": a.get("name", sa), "calls_service_action": sa}})
            if decision:
                steps.append({"recipe": "workflow-add", "why": f"{proc['name']} += decision on {decision.get('on')}",
                              "params": {"process": proc["name"], "kind": "decision", **decision}})
            if human:
                steps.append({"recipe": "workflow-add", "why": f"{proc['name']} += human approval",
                              "params": {"process": proc["name"], "kind": "human", **human}})
    return annotate_weights(steps)
