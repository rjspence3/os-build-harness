"""app_spec.json  →  authoring bridges: Entity dataclasses (entity layer) + NL screen intent.

Two authoring bridges live here, both pure/deterministic/offline (no MCP, no network):
  * ENTITY layer — `spec_to_entities` maps the spec onto renderer dataclasses; the
    proven authoring bridge is `render_spec_entities_nl` (NL intent for Mentor to
    author natively — verbatim applyModelApiCode C# did not persist on a fresh app).
  * SCREEN layer — `render_spec_screens_nl` mirrors the entity NL bridge: it emits
    natural-language screen-authoring instructions (widgets named by their exact spec
    `id`, bindings, navigation) for Mentor to author natively, AFTER the entities exist.
    `collect_spec_screen_gaps` reports component types with no native NL phrasing.


The banking runner's renderers in `recipe.py` (`render_server_entity`,
`render_static_entity`, `render_attribute_line`, `collect_fk_targets`,
`topologically_order_server_entities`) are already generic: they consume the
`Attribute` / `ServerEntity` / `StaticEntity` dataclasses from `manifest.py` and
emit Mentor `applyModelApiCode` authoring batches. What was home_banking-specific
was only the INPUT loader (`manifest.load_entities`, which reads a home_banking
YAML manifest).

This module is the generalizing ADAPTER: it maps a schema-validated
`app_spec.json` document (see `harness/schemas/app_spec.v0.json`) onto those same
dataclasses, so the existing renderers can author ANY spec's entity layer with no
home_banking hardcoding.

The mapping is a pure, deterministic, offline function — no MCP, no network.

Mapping table (app_spec → manifest dataclass):

    app_spec                              manifest dataclass field
    ------------------------------------  --------------------------------------
    entity.name                           Entity.name
    entity.description                    Entity.description
    entity.isStatic=false (default)       -> ServerEntity
    entity.isStatic=true                  -> StaticEntity (records seeded)
    attribute.isIdentifier=true (the PK)  consumed into Entity PK (not an attr)
    attribute.name                        Attribute.name
    attribute.dataType (camel enum)       Attribute.data_type (ODC space-form)
    attribute.mandatory                   Attribute.is_mandatory
    attribute.length / .decimals          Attribute.length / .decimals
    attribute.references="Target"         Attribute.data_type = "Target Identifier"
    entity.relationships[kind=manyToOne]  synthesized FK Attribute ("<To>Id")

dataType enum mapping (app_spec camelCase  ->  ODC space-form the renderer emits):

    Text        -> Text          Integer     -> Integer
    LongInteger -> Long Integer   Decimal     -> Decimal
    Currency    -> Currency       Boolean     -> Boolean
    Date        -> Date           DateTime    -> Date Time
    Email       -> Email          PhoneNumber -> Phone Number
    BinaryData  -> Binary Data    Identifier  -> (PK or FK; never a bare column)
    Time        -> (GAP: renderer has no Time helper; see collect_spec_gaps)

Documented gaps (surfaced by `collect_spec_gaps`, never silently faked):
  * dataType "Time" has no renderer helper -> renders as an /* unsupported */ marker.
  * A bare "Identifier" attribute that is neither the PK nor a `references` FK has
    no resolvable target -> renders as /* unsupported */.
  * relationships of kind oneToMany (FK lives on the OTHER entity) and manyToMany
    (needs a junction entity) are NOT authored as attributes here.
  * Static-entity `records` are objects (attribute -> value) in app_spec but the
    static renderer takes record-identifier STRINGS; the identifier is derived
    best-effort (see `_record_identifier`) and non-PK column values are not seeded.
"""
from __future__ import annotations

from harness.banking_runner.manifest import (
    Attribute,
    EntitiesManifest,
    ServerEntity,
    StaticEntity,
)
from harness.banking_runner.recipe import (
    DEFAULT_RECIPES_DIR,
    render_server_entity,
    render_static_entity,
    topologically_order_server_entities,
)

# app_spec odcDataType enum -> the ODC space-form string the renderer expects.
# "Identifier" is intentionally absent: it is resolved contextually (PK or FK),
# never mapped to a bare column type.
SPEC_TO_ODC_DATATYPE: dict[str, str] = {
    "Text": "Text",
    "Integer": "Integer",
    "LongInteger": "Long Integer",
    "Decimal": "Decimal",
    "Currency": "Currency",
    "Boolean": "Boolean",
    "Date": "Date",
    "DateTime": "Date Time",
    "Email": "Email",
    "PhoneNumber": "Phone Number",
    "BinaryData": "Binary Data",
    # "Time" deliberately omitted -> flagged as a gap; passes through raw so the
    # renderer emits a visible /* unsupported dataType "Time" */ marker.
}

# Static-entity PK types the static renderer understands (recipe 02 pk_type_map).
_STATIC_PK_TYPES = {"Integer", "Text", "Long Integer"}


class SpecAdaptError(Exception):
    """Raised when an app_spec document is structurally unusable for the entity
    layer (e.g. missing dataModel.entities)."""


def spec_to_entities(app_spec: dict) -> EntitiesManifest:
    """Map an app_spec document onto an `EntitiesManifest` of renderer-ready
    `StaticEntity` / `ServerEntity` dataclasses — byte-identical in shape to what
    `manifest.load_entities` produces from a home_banking YAML manifest."""
    manifest, _gaps = _adapt(app_spec)
    return manifest


def collect_spec_gaps(app_spec: dict) -> list[str]:
    """Return human-readable warnings for spec features with no clean mapping to
    the renderer dataclasses. Empty list means a fully-mapped entity layer."""
    _manifest, gaps = _adapt(app_spec)
    return gaps


def render_spec_entities(app_spec: dict, recipes_dir=DEFAULT_RECIPES_DIR) -> str:
    """Render the full entity-authoring batch text for an app_spec: static
    entities first (recipe 02), then server entities in FK-topological order
    (recipe 01). Returns the concatenated Mentor prompt strings. Dry-run only —
    authors nothing, makes no network/MCP calls.

    NOTE: this emits `applyModelApiCode` C#. Live testing (2026-07-02) showed that
    verbatim C# does NOT reliably persist on a from-scratch app — use
    `render_spec_entities_nl` for actual authoring (Mentor native NL, proven to
    persist + produce a spec-conformant app). This C# render is retained for
    structure inspection / dry-run review, not as the authoring bridge."""
    manifest = spec_to_entities(app_spec)
    local_server = {e.name for e in manifest.server_entities}
    local_static = {e.name for e in manifest.static_entities}

    parts: list[str] = []
    for static in manifest.static_entities:
        parts.append(render_static_entity(static, recipes_dir))
    for server in topologically_order_server_entities(manifest.server_entities):
        parts.append(render_server_entity(server, local_server, local_static, recipes_dir))
    return "\n\n".join(parts)


def render_spec_entities_nl(app_spec: dict) -> str:
    """Render the entity layer as precise NATURAL-LANGUAGE authoring instructions for
    Mentor to author NATIVELY — not applyModelApiCode C#.

    Live finding (2026-07-02): on a from-scratch app, verbatim `applyModelApiCode`
    edits reported success in-turn but did NOT persist to the publishable model, while
    Mentor's own native (NL-driven) entity authoring committed reliably. So the
    generalized runner's authoring BRIDGE is natural-language intent, not rendered C#.
    The deterministic parse (`spec_to_entities` + FK topological order) is reused
    verbatim; only the output format changes. Deterministic, offline, no MCP.
    """
    manifest = spec_to_entities(app_spec)
    static_names = {e.name for e in manifest.static_entities}
    ordered = list(manifest.static_entities) + topologically_order_server_entities(
        manifest.server_entities
    )
    out = [
        "Author this OutSystems data model natively (create each entity, then add its "
        "attributes). Author the entities in the order below so references resolve. "
        "Each entity gets an auto-number Long Integer `Id` primary key. Add ONLY the "
        "attributes listed — nothing extra. Publish when done.",
        "",
    ]
    for i, ent in enumerate(ordered, 1):
        kind = "Static" if ent.name in static_names else "Server"
        out.append(f"{i}. {kind} entity `{ent.name}`:")
        for a in ent.attributes:
            out.append(f"   - {_nl_attribute(a)}")
        if ent.name in static_names and getattr(ent, "records", None):
            out.append(f"   - Seed records (by identifier): {', '.join(ent.records)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _nl_attribute(a: Attribute) -> str:
    """One human-readable authoring line for an attribute."""
    dt = a.data_type
    mand = " (mandatory)" if a.is_mandatory else ""
    if dt.endswith(" Identifier"):
        target = dt[: -len(" Identifier")]
        return f"reference `{a.name}` -> `{target}`{mand}"
    if dt == "Text" and a.length:
        return f"Text `{a.name}`, max {a.length} chars{mand}"
    if dt == "Decimal" and a.length:
        return f"Decimal `{a.name}` ({a.length},{a.decimals or 0}){mand}"
    return f"{dt} `{a.name}`{mand}"


# ─── screen layer (NL authoring bridge) ──────────────────────────────────────────
#
# Screen/component -> NL mapping (author from the explicit components/navigation,
# NEVER from acceptance.assertions — those are verify targets):
#
#   spec fragment                         emitted NL
#   ------------------------------------  ----------------------------------------
#   component.id                          the widget NAME ("Table named `listsTable`")
#   type Table / List  + boundTo=X        "showing `X` records"
#   type Form/Input/Dropdown + boundTo=X  "bound to `X`"
#   type Button / Link                    (navigation-capable; see below)
#   type Text / Image / Container         plain named widget
#   any other type                        best-effort "<Type> named `id`" + a GAP
#   component.label                       ' (label "…")'
#   component.groupBy / .columns          ' (grouped by `…`; columns `…`)'
#   navigation[] fromComponent==id        "that navigates to screen `<toScreen name>`"
#   component.nav[] (Sidebar/Nav items)   same, one target per nav item
#   navEdge.event != onClick              "that on <event> navigates to screen `…`"
#   screen.inputParameters[]              "receives input parameter `Name` referencing `E`"
#   screen.actions[] (non-Navigate does)  "action `Name` on `component` <event>: CreateEntity, …"
#
# toScreen ids are resolved to screen NAMES via the screens table; unknown ids pass
# through raw. Navigation edges already cover Navigate actions, so pure-Navigate
# actions are dropped from the actions section (no double-rendering).

_SCREEN_PREAMBLE = (
    "Author these screens natively AFTER the data model (entities) already exist, so "
    "that every data binding resolves against a real entity. Author each widget with "
    "the EXACT name shown in backticks — the screen-walk verifier keys on widget "
    "names, so an unnamed widget fails its assertion. Publish when done."
)

# Component types with a native 1:1 NL phrasing. Anything outside this set is emitted
# best-effort and flagged by `collect_spec_screen_gaps` (never faked coverage).
_SHOWING_COMPONENT_TYPES = {"Table", "List"}          # "showing `X` records"
_BOUND_COMPONENT_TYPES = {"Form", "Input", "Dropdown"}  # "bound to `X`"
_NAV_COMPONENT_TYPES = {"Button", "Link"}             # navigation source
_PLAIN_COMPONENT_TYPES = {"Text", "Image", "Container"}
_SHELL_COMPONENT_TYPES = {"Sidebar"}                  # app-shell with labeled nav items
_KPI_COMPONENT_TYPES = {"Card"}                       # dashboard KPI card
_CHART_COMPONENT_TYPES = {"Chart"}                    # dashboard chart
_RECOGNIZED_COMPONENT_TYPES = (
    _SHOWING_COMPONENT_TYPES
    | _BOUND_COMPONENT_TYPES
    | _NAV_COMPONENT_TYPES
    | _PLAIN_COMPONENT_TYPES
    | _SHELL_COMPONENT_TYPES
    | _KPI_COMPONENT_TYPES
    | _CHART_COMPONENT_TYPES
)


def render_spec_screens_nl(app_spec: dict) -> str:
    """Render the screen layer as precise NATURAL-LANGUAGE authoring instructions for
    Mentor to author NATIVELY — mirrors `render_spec_entities_nl` for the data model.

    Each component is named by its exact spec `id` (the screen-walk verifier keys on
    widget names). Data bindings, navigation edges, screen inputs, and non-navigation
    actions are rendered from the EXPLICIT spec fields (never from acceptance
    assertions). Deterministic, offline, no MCP. Author screens AFTER the entities so
    bindings resolve."""
    text, _gaps = _screens_nl(app_spec)
    return text


def collect_spec_screen_gaps(app_spec: dict) -> list[str]:
    """Return human-readable warnings for screen features with no clean native NL
    phrasing (e.g. composite component types like Board/Sidebar). Empty list means a
    fully-mapped screen layer."""
    _text, gaps = _screens_nl(app_spec)
    return gaps


def _screens_nl(app_spec: dict) -> tuple[str, list[str]]:
    screens = app_spec.get("screens")
    if not isinstance(screens, list) or not screens:
        raise SpecAdaptError("app_spec missing screens")

    screen_name_by_id = {
        s.get("id"): s.get("name") or s.get("id") or ""
        for s in screens
        if isinstance(s, dict)
    }

    gaps: list[str] = []
    out: list[str] = [_SCREEN_PREAMBLE, ""]
    for screen in screens:
        out.append(_screen_header(screen))
        for ip in screen.get("inputParameters", []) or []:
            out.append("   - " + _nl_input_parameter(ip))
        components = screen.get("components", []) or []
        if not components:
            out.append("   - (no components specified)")
        for comp in components:
            line, gap = _nl_component(comp, screen, screen_name_by_id)
            out.append("   - " + line)
            if gap:
                gaps.append(gap)
        out.extend(_nl_actions(screen))
        out.append("")
    return "\n".join(out).rstrip() + "\n", gaps


def _screen_header(screen: dict) -> str:
    name = screen.get("name") or screen.get("id") or ""
    meta: list[str] = []
    if screen.get("route"):
        meta.append(f"route {screen['route']}")
    if screen.get("uiFlow"):
        meta.append(f"flow {screen['uiFlow']}")
    roles = screen.get("roles") or []
    if roles:
        meta.append("role " + ", ".join(roles))
    suffix = f" ({', '.join(meta)})" if meta else ""
    return f"Screen `{name}`{suffix}:"


def _nl_input_parameter(ip: dict) -> str:
    name = ip.get("name", "?")
    ref = ip.get("references")
    if ref:
        return f"receives input parameter `{name}` referencing `{ref}`"
    return f"receives input parameter `{name}` ({ip.get('dataType', 'Text')})"


def _nl_component(
    comp: dict, screen: dict, screen_name_by_id: dict
) -> tuple[str, str | None]:
    ctype = comp.get("type") or ""
    cid = comp.get("id", "?")
    article = "an" if ctype[:1].upper() in {"A", "E", "I", "O", "U"} else "a"

    gap = None
    if ctype not in _RECOGNIZED_COMPONENT_TYPES:
        gap = (
            f'Screen "{screen.get("id", "?")}": component "{cid}" type '
            f'"{ctype or "(missing)"}" has no native NL phrasing; emitted best-effort '
            f"as a named {ctype or 'widget'}."
        )

    line = _component_lead_phrase(ctype, cid, article)
    line += _component_binding_phrase(comp, ctype)
    line += _component_extra_phrase(comp)
    label = comp.get("label")
    if label:
        line += f' (label "{label}")'
    # A Sidebar carries its own labeled nav items (comp.nav[]); render those with labels
    # rather than the generic "navigates to screens X, Y" collapse.
    if ctype in _SHELL_COMPONENT_TYPES:
        line += _sidebar_nav_phrase(comp, screen_name_by_id)
    else:
        line += _component_nav_phrase(comp, screen, screen_name_by_id)
    return line, gap


def _component_lead_phrase(ctype: str, cid: str, article: str) -> str:
    """Lead clause per component type — the three dashboard-shell types get a purpose-named
    phrasing so Mentor authors the intended widget, not a bare unnamed one."""
    if ctype in _SHELL_COMPONENT_TYPES:
        return f"a Sidebar app-shell named `{cid}`"
    if ctype in _KPI_COMPONENT_TYPES:
        return f"a KPI Card named `{cid}`"
    if ctype in _CHART_COMPONENT_TYPES:
        return f"a Chart named `{cid}`"
    return f"{article} {ctype or 'widget'} named `{cid}`"


def _sidebar_nav_phrase(comp: dict, screen_name_by_id: dict) -> str:
    items: list[str] = []
    for item in comp.get("nav", []) or []:
        if not isinstance(item, dict) or not item.get("toScreen"):
            continue
        target = screen_name_by_id.get(item["toScreen"], item["toScreen"])
        label = item.get("label")
        items.append(f"`{label}` -> screen `{target}`" if label else f"screen `{target}`")
    return " with navigation items: " + "; ".join(items) if items else ""


def _component_binding_phrase(comp: dict, ctype: str) -> str:
    bound = comp.get("boundTo")
    if not bound:
        return ""
    if ctype in _SHOWING_COMPONENT_TYPES:
        return f" showing `{bound}` records"
    # Form/Input/Dropdown (and any best-effort type carrying a binding).
    return f" bound to `{bound}`"


def _component_extra_phrase(comp: dict) -> str:
    parts: list[str] = []
    if comp.get("groupBy"):
        parts.append(f"grouped by `{comp['groupBy']}`")
    fields = [
        c.get("field")
        for c in (comp.get("columns") or [])
        if isinstance(c, dict) and c.get("field")
    ]
    if fields:
        parts.append("columns " + ", ".join(f"`{f}`" for f in fields))
    return f" ({'; '.join(parts)})" if parts else ""


def _component_nav_phrase(
    comp: dict, screen: dict, screen_name_by_id: dict
) -> str:
    cid = comp.get("id")
    simple: list[str] = []          # onClick / default-event targets
    evented: list[tuple[str, str]] = []  # (event, target) for non-onClick edges

    for edge in screen.get("navigation", []) or []:
        if edge.get("fromComponent") == cid and edge.get("toScreen"):
            target = screen_name_by_id.get(edge["toScreen"], edge["toScreen"])
            event = edge.get("event")
            if event and event != "onClick":
                evented.append((event, target))
            else:
                simple.append(target)
    for item in comp.get("nav", []) or []:
        if isinstance(item, dict) and item.get("toScreen"):
            simple.append(screen_name_by_id.get(item["toScreen"], item["toScreen"]))

    out = ""
    if len(simple) == 1:
        out += f" that navigates to screen `{simple[0]}`"
    elif simple:
        out += " that navigates to screens " + ", ".join(f"`{n}`" for n in simple)
    for event, target in evented:
        out += f" that on {event} navigates to screen `{target}`"
    return out


def _nl_actions(screen: dict) -> list[str]:
    lines: list[str] = []
    for act in screen.get("actions", []) or []:
        # Navigation is rendered from navigation edges; drop pure-Navigate actions
        # so they are not double-rendered.
        meaningful = [d for d in (act.get("does") or []) if d != "Navigate"]
        if not meaningful:
            continue
        trigger = act.get("trigger") or {}
        on = trigger.get("onComponent", "?")
        event = trigger.get("event", "onClick")
        lines.append(
            f"   - action `{act.get('name', '?')}` on `{on}` {event}: "
            + ", ".join(meaningful)
        )
    return lines


# ─── internals ──────────────────────────────────────────────────────────────────

def _adapt(app_spec: dict) -> tuple[EntitiesManifest, list[str]]:
    data_model = app_spec.get("dataModel")
    if not isinstance(data_model, dict) or "entities" not in data_model:
        raise SpecAdaptError("app_spec missing dataModel.entities")

    app_block = app_spec.get("app") or {}
    app_name = app_block.get("name", "")

    gaps: list[str] = []
    static_entities: list[StaticEntity] = []
    server_entities: list[ServerEntity] = []

    for ent in data_model["entities"]:
        if ent.get("isStatic", False):
            static_entities.append(_adapt_static_entity(ent, gaps))
        else:
            server_entities.append(_adapt_server_entity(ent, gaps))

    manifest = EntitiesManifest(
        app=app_name,
        app_asset_key="",  # app_spec has no asset key; caller supplies at author time
        static_entities=static_entities,
        server_entities=server_entities,
    )
    return manifest, gaps


def _adapt_server_entity(ent: dict, gaps: list[str]) -> ServerEntity:
    name = ent["name"]
    pk_attr = _find_pk_attribute(ent)
    pk_name = pk_attr["name"] if pk_attr else "Id"

    # Server-entity PK is canonical Long Integer auto-number unless the spec pins
    # an explicit non-Identifier PK type.
    pk_data_type = "Long Integer"
    if pk_attr and pk_attr.get("dataType") not in (None, "Identifier"):
        pk_data_type = SPEC_TO_ODC_DATATYPE.get(pk_attr["dataType"], "Long Integer")

    attributes = _adapt_attributes(ent, name, pk_attr, gaps)

    return ServerEntity(
        name=name,
        pk_name=pk_name,
        pk_data_type=pk_data_type,
        pk_is_auto_number=True,
        attributes=attributes,
        description=ent.get("description"),
    )


def _adapt_static_entity(ent: dict, gaps: list[str]) -> StaticEntity:
    name = ent["name"]
    pk_attr = _find_pk_attribute(ent)
    pk_name = pk_attr["name"] if pk_attr else "Id"

    # Static PK must be Integer / Text / Long Integer. Identifier or anything else
    # defaults to Integer (ODC's default static-entity PK).
    pk_data_type = "Integer"
    pk_length = None
    if pk_attr:
        mapped = SPEC_TO_ODC_DATATYPE.get(pk_attr.get("dataType", ""), "")
        if mapped in _STATIC_PK_TYPES:
            pk_data_type = mapped
            if mapped == "Text":
                pk_length = pk_attr.get("length")
        elif pk_attr.get("dataType") == "Identifier":
            pk_data_type = "Integer"
        else:
            gaps.append(
                f'Static entity "{name}": PK dataType '
                f'"{pk_attr.get("dataType")}" is not a valid static PK type; '
                f"defaulted to Integer."
            )

    attributes = _adapt_attributes(ent, name, pk_attr, gaps)

    records = _adapt_records(ent, name, gaps)

    return StaticEntity(
        name=name,
        pk_name=pk_name,
        pk_data_type=pk_data_type,
        pk_length=pk_length,
        attributes=attributes,
        records=records,
        description=ent.get("description"),
    )


def _adapt_attributes(ent: dict, entity_name: str, pk_attr: dict | None, gaps: list[str]) -> list[Attribute]:
    attributes: list[Attribute] = []
    referenced_targets: set[str] = set()

    for attr in ent.get("attributes", []):
        if attr is pk_attr:
            continue  # PK is carried on the Entity, not as a column

        data_type = _map_attribute_data_type(attr, entity_name, gaps)
        if data_type is None:
            continue

        ref = attr.get("references")
        if ref:
            referenced_targets.add(ref)

        attributes.append(
            Attribute(
                name=attr["name"],
                data_type=data_type,
                length=attr.get("length"),
                decimals=attr.get("decimals"),
                is_mandatory=attr.get("mandatory", False),
                description=attr.get("description"),
            )
        )

    # Entity-level relationships. Attribute-level `references` is preferred, so we
    # only synthesize an FK for manyToOne relationships not already covered by a
    # references attribute. oneToMany / manyToMany are documented gaps.
    for rel in ent.get("relationships", []) or []:
        to = rel.get("to")
        kind = rel.get("kind")
        if kind == "manyToOne":
            if to in referenced_targets:
                continue
            attributes.append(
                Attribute(
                    name=f"{to}Id",
                    data_type=f"{to} Identifier",
                    is_mandatory=rel.get("mandatory", False),
                )
            )
        else:
            gaps.append(
                f'Entity "{entity_name}": relationship kind "{kind}" -> "{to}" '
                f"is not authored as an attribute (only manyToOne maps to an FK "
                f"column; oneToMany/manyToMany need the other entity or a junction "
                f"entity)."
            )

    return attributes


def _map_attribute_data_type(attr: dict, entity_name: str, gaps: list[str]) -> str | None:
    """Return the ODC space-form dataType string for a NON-PK attribute, or the
    raw spec type (with a gap recorded) when there is no clean mapping."""
    spec_type = attr.get("dataType")
    name = attr.get("name", "?")

    if spec_type == "Identifier":
        ref = attr.get("references")
        if ref:
            return f"{ref} Identifier"
        gaps.append(
            f'Entity "{entity_name}": attribute "{name}" is a bare Identifier '
            f"with no `references` target and is not the PK; cannot resolve an FK "
            f"target (renders as /* unsupported */)."
        )
        return "Identifier"  # renderer emits a visible unsupported marker

    mapped = SPEC_TO_ODC_DATATYPE.get(spec_type)
    if mapped is None:
        gaps.append(
            f'Entity "{entity_name}": attribute "{name}" dataType "{spec_type}" '
            f"has no renderer helper (renders as /* unsupported */)."
        )
        return spec_type  # pass through so the gap is visible in the batch, not faked
    return mapped


def _find_pk_attribute(ent: dict) -> dict | None:
    """The identifier attribute: first isIdentifier=true, else an attribute named
    "Id", else None (renderer supplies a default Id PK)."""
    for attr in ent.get("attributes", []):
        if attr.get("isIdentifier", False):
            return attr
    for attr in ent.get("attributes", []):
        if attr.get("name") == "Id":
            return attr
    return None


def _adapt_records(ent: dict, entity_name: str, gaps: list[str]) -> list[str]:
    """Derive record-identifier strings from app_spec static `records` objects.

    The static renderer (recipe 02) takes a list of identifier strings and seeds
    Id/Label from them. app_spec records are attribute->value objects, so we pick
    a human label field best-effort. Non-identifier column values are NOT seeded
    (documented gap)."""
    raw_records = ent.get("records") or []
    identifiers: list[str] = []
    dropped_columns = False
    for rec in raw_records:
        ident = _record_identifier(rec)
        if ident is None:
            gaps.append(
                f'Static entity "{entity_name}": a record has no derivable '
                f"identifier (no Label/Name/Code/Id/text field); skipped."
            )
            continue
        if len(rec) > 1:
            dropped_columns = True
        identifiers.append(ident)
    if dropped_columns:
        gaps.append(
            f'Static entity "{entity_name}": only the record identifier is seeded; '
            f"other column values in `records` are not written (renderer takes "
            f"identifier strings only)."
        )
    return identifiers


def _record_identifier(rec: dict) -> str | None:
    """Best-effort human label for a static record object."""
    for key in ("Label", "Name", "Code", "Id"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val
    for val in rec.values():
        if isinstance(val, str) and val.strip():
            return val
    return None
