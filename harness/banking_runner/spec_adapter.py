"""app_spec.json  →  recipe-renderable Entity dataclasses (the entity layer).

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
    authors nothing, makes no network/MCP calls."""
    manifest = spec_to_entities(app_spec)
    local_server = {e.name for e in manifest.server_entities}
    local_static = {e.name for e in manifest.static_entities}

    parts: list[str] = []
    for static in manifest.static_entities:
        parts.append(render_static_entity(static, recipes_dir))
    for server in topologically_order_server_entities(manifest.server_entities):
        parts.append(render_server_entity(server, local_server, local_static, recipes_dir))
    return "\n\n".join(parts)


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
