"""Recipe template loader + renderer.

Loads a recipe markdown file from data/MCP_RECIPES/, extracts its
`## Mentor prompt (paste verbatim)` C# block, and fills the
`{{PLACEHOLDERS}}` from manifest data.

Each public renderer takes a manifest model (StaticEntity, ServerEntity, Role,
Action) and returns a full prompt string: PROMPT_PREAMBLE + filled recipe body.

The hardest part is the C# block generation for entity attributes — FK
identifier types need declared variables at the top of the recipe call, so the
renderer must scan attributes first, emit resolution statements, then emit the
attribute-add calls.

Status v1: Recipe 01 (server entity), 02 (static entity), 03 (role) fully
rendered. Action recipes (04/05/06/16) render signature-only stubs.
Screen + theme + verify recipes are TBD.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from harness.banking_runner.manifest import (
    Action,
    ActionParameter,
    Attribute,
    Role,
    ServerEntity,
    StaticEntity,
)

DEFAULT_RECIPES_DIR = Path(__file__).resolve().parents[2] / "builds" / "home_banking" / "MCP_RECIPES"


class RecipeError(Exception):
    """Raised when a recipe template can't be loaded or rendered."""


# ─── Recipe template loader ────────────────────────────────────────────────────

@dataclass
class RecipeTemplate:
    """A loaded recipe markdown file. The .csharp_body field is the substring
    inside the `## Mentor prompt (paste verbatim)` fenced ```csharp ... ``` block."""
    name: str                  # e.g. "01_entity_server"
    csharp_body: str           # the ```csharp ... ``` content (no fence markers)
    imports: list[str]         # required `imports` list (parsed from the "Required imports" block)


_CSHARP_FENCE_RE = re.compile(
    # Match either "## Mentor prompt (paste verbatim...)" OR "## Verification probe..."
    # — both signal "the C# block below is the recipe body".
    r"##\s*(?:Mentor prompt\s*\(paste verbatim[^)]*\)|Verification probe[^\n]*)\s*\n```csharp\n(.*?)\n```",
    re.DOTALL,
)

_IMPORTS_FENCE_RE = re.compile(
    r"Required imports.*?:\s*\n```\n(.*?)\n```",
    re.DOTALL,
)


def load_recipe(name: str, recipes_dir: Path = DEFAULT_RECIPES_DIR) -> RecipeTemplate:
    """Load a recipe by stem (e.g. '01_entity_server' or '01')."""
    path = _resolve_recipe_path(name, recipes_dir)
    text = path.read_text()

    body_match = _CSHARP_FENCE_RE.search(text)
    if not body_match:
        raise RecipeError(
            f"Recipe {name}: could not find ```csharp Mentor prompt block. "
            f"Expected '## Mentor prompt (paste verbatim, with {{}} substituted)' "
            f"followed by a ```csharp fenced block."
        )

    imports_match = _IMPORTS_FENCE_RE.search(text)
    imports = (
        [line.strip() for line in imports_match.group(1).splitlines() if line.strip()]
        if imports_match else []
    )

    return RecipeTemplate(
        name=path.stem,
        csharp_body=body_match.group(1),
        imports=imports,
    )


def _resolve_recipe_path(name: str, recipes_dir: Path) -> Path:
    """Map '01', '01_entity_server', or '01_entity_server.md' → actual file path."""
    if name.endswith(".md"):
        candidate = recipes_dir / name
        if candidate.exists():
            return candidate
        raise RecipeError(f"Recipe file not found: {candidate}")

    # Try exact match first, then prefix match
    for p in sorted(recipes_dir.glob("*.md")):
        if p.stem == name:
            return p
    for p in sorted(recipes_dir.glob("*.md")):
        if p.stem.startswith(name + "_") or p.stem == name:
            return p
    raise RecipeError(f"Recipe not found: {name}")


# ─── Prompt preamble loader ────────────────────────────────────────────────────

_PREAMBLE_FENCE_RE = re.compile(
    r"## Paste verbatim, prefixed to the recipe body\s*\n```\n(.*?)\n```",
    re.DOTALL,
)


def load_preamble(recipes_dir: Path = DEFAULT_RECIPES_DIR) -> str:
    """Read PROMPT_PREAMBLE.md and extract the paste-verbatim block."""
    path = recipes_dir / "PROMPT_PREAMBLE.md"
    text = path.read_text()
    match = _PREAMBLE_FENCE_RE.search(text)
    if not match:
        raise RecipeError("PROMPT_PREAMBLE.md missing the 'Paste verbatim' fenced block")
    return match.group(1)


# ─── Data-type → C# generators ─────────────────────────────────────────────────

# How a YAML dataType string maps to the recipe's AddX helper. Order matters for
# overlapping prefixes — most specific first.
_BASIC_TYPE_HELPERS = {
    "Text": "AddText",
    "Long Integer": "AddLongInt",     # NEW helper (recipe 01 doesn't have this yet — handle inline)
    "Integer": "AddInt",
    "Boolean": "AddBool",
    "Decimal": "AddDecimal",
    "Date Time": "AddDateTime",
    "Date": "AddDate",
    "Email": "AddEmail",              # recipe 01 doesn't have AddEmail; renderer emits Text(256) instead
    "Phone Number": "AddPhone",       # ditto, Text(20)
    "Currency": "AddCurrency",
    "Binary Data": "AddBinary",
}


def render_attribute_line(attr: Attribute, fk_var_lookup: dict[str, str]) -> str:
    """One C# line for one attribute. Returns a string like 'AddText(e, "Name", 50, true);'.

    fk_var_lookup maps "<EntityName>" → the C# variable holding its IdentifierType.
    E.g. {"User": "userIdentType", "HBCustomer": "hbCustomerEntity.IdentifierType"}.
    """
    name = attr.name
    dt = attr.data_type
    mand = "true" if attr.is_mandatory else "false"

    # FK detection: dataType ends in " Identifier"
    if dt.endswith(" Identifier"):
        target = dt[: -len(" Identifier")]
        target_var = fk_var_lookup.get(target)
        if not target_var:
            return f'/* FK {name} → {target}: target not resolved (manifest gap) */'
        # `target_var` is the BARE entity variable (e.g. `hBDocumentTypeStatic`).
        # AddIdentFk's 3rd param is statically typed `IIdentifierType`, so emit
        # `{var}?.IdentifierType` (null-safe). If the entity wasn't found at
        # runtime the param goes null → AddIdentFk null-checks + reports the
        # missing FK clearly. Earlier the lookup string included a
        # `?? eSpace.TextType` fallback that widened the static type to
        # `IBasicType` and caused CS1503 against the typed param (verified live
        # 2026-06-02 on Core rebake1 batch 1).
        return f'AddIdentFk(e, "{name}", {target_var}?.IdentifierType, {mand});'

    # First-class OS types that have their own *Type property on eSpace
    if dt == "Email":
        length = attr.length or 256
        return f'AddEmail(e, "{name}", {length}, {mand});'
    if dt == "Phone Number":
        length = attr.length or 20
        return f'AddPhone(e, "{name}", {length}, {mand});'
    if dt == "Currency":
        return f'AddCurrency(e, "{name}", {mand});'
    if dt == "Binary Data":
        return f'AddBinary(e, "{name}");'
    if dt == "Date":
        return f'AddDate(e, "{name}", {mand});'
    if dt == "Long Integer":
        return f'AddLongInt(e, "{name}", {mand});'

    # Basic types
    if dt == "Text":
        length = attr.length or 50
        return f'AddText(e, "{name}", {length}, {mand});'
    if dt == "Integer":
        return f'AddInt(e, "{name}");'
    if dt == "Boolean":
        return f'AddBool(e, "{name}");'
    if dt == "Decimal":
        length = attr.length or 37
        decimals = attr.decimals or 8
        return f'AddDecimal(e, "{name}", {length}, {decimals});'
    if dt == "Date Time":
        return f'AddDateTime(e, "{name}", {mand});'

    # Unknown
    return f'/* unsupported dataType "{dt}" for {name} */'


def collect_fk_targets(attributes: list[Attribute]) -> list[str]:
    """Return unique FK target entity names referenced by these attributes,
    preserving first-seen order."""
    seen: list[str] = []
    for a in attributes:
        if a.data_type.endswith(" Identifier"):
            target = a.data_type[: -len(" Identifier")]
            if target not in seen:
                seen.append(target)
    return seen


def topologically_order_server_entities(
    server_entities: list[ServerEntity],
) -> list[ServerEntity]:
    """Return server entities in FK-dependency order (dependencies first).

    Mentor authoring requires entity B to be PUBLISHED before any entity A whose
    recipe does `eSpace.Entities.OfType<IServerEntity>().Named("B").IdentifierType`
    — otherwise the lookup returns null and the recipe NPEs at .IdentifierType.
    Manifest order is NOT guaranteed to be topological (R12 hit this: CustomerGoal
    at manifest position 2 depends on HBAccount at position 8). Kahn's-algorithm
    topo sort over the local-server-entity FK DAG. Non-local FK targets (e.g.
    referenced entities like User/Employee, or statics from a separate dispatch)
    are excluded from the sort — they're already-published prerequisites."""
    local_names = {e.name for e in server_entities}
    name_to_ent = {e.name: e for e in server_entities}
    deps: dict[str, set[str]] = {}
    for e in server_entities:
        targets = collect_fk_targets(e.attributes)
        deps[e.name] = {t for t in targets if t in local_names and t != e.name}

    ordered: list[ServerEntity] = []
    remaining = dict(deps)
    while remaining:
        # Drain everything with zero remaining deps this pass; sort the ready
        # set so output is deterministic across runs.
        ready = sorted(n for n, d in remaining.items() if not d)
        if not ready:
            cycle = sorted(remaining.keys())
            raise RecipeError(f"FK cycle among server entities: {cycle}")
        for name in ready:
            ordered.append(name_to_ent[name])
            del remaining[name]
            for d in remaining.values():
                d.discard(name)
    return ordered


def render_fk_resolution_block(
    fk_targets: list[str],
    local_entities: set[str],
    local_statics: set[str],
) -> tuple[str, dict[str, str]]:
    """For each FK target, emit a C# `var ...` declaration that resolves the
    target's IdentifierType. Returns (csharp_block, lookup_dict).

    Resolution rules:
      - "User" → eSpace.References (System).User → IdentifierType
      - "<LocalServerEntity>" → eSpace.Entities.OfType<IServerEntity>().Named(...)
      - "<LocalStaticEntity>" → eSpace.Entities.OfType<IStaticEntity>().Named(...)
      - "<RemoteEntity>" → eSpace.References.SelectMany(r => r.Entities).First(...)
    """
    lines: list[str] = []
    lookup: dict[str, str] = {}
    # Maps "<EntityName>" → the C# var holding the resolved entity OBJECT (not
    # its IdentifierType). Used for entity-record-typed action params, where
    # `p.DataType = <entityVar>` sets the param to the full record type
    # (verified live 2026-05-29). User is excluded — its var holds an
    # IdentifierType, not an entity object, and User is never a record param.
    var_lookup: dict[str, str] = {}
    # Portal Phase A learning: `.First()` throws "Sequence contains no matching
    # element" at runtime when an FK target doesn't exist (e.g. recipe-library
    # hallucinated entity name like `Locale2` for a param that's actually
    # plain Text). The runtime exception aborts the whole batch (all-or-
    # nothing applyModelApiCode semantics), so a single hallucinated name
    # kills the entire dispatch. The defensive pattern is FirstOrDefault +
    # null-coalesce to `eSpace.TextType`: if the entity isn't found, the
    # param falls back to Text (functionally fine for stub-level actions),
    # the batch survives, and R13 can fix the manifest later.
    for target in fk_targets:
        if target == "User":
            # Declare the User ENTITY (not its IdentifierType) so callers can
            # uniformly emit `{var}?.IdentifierType`. The earlier shape
            # `userIdentType = ...?.IdentifierType ?? eSpace.TextType` widened
            # the static type to IBasicType and broke typed-method-call sites.
            var = "userEntity"
            lines.append(
                f'var {var} = eSpace.References.SelectMany(r => r.Entities)'
                f'.FirstOrDefault(e => e.Name == "User");'
            )
            lookup[target] = f"({var}?.IdentifierType ?? eSpace.TextType)"
        elif target == "Employee" or target == "EmployeePicture" or target == "JobTitle":
            # AppsCommonCore.Employee etc.
            var = _camel(target) + "Entity"
            lines.append(
                f'var {var} = eSpace.References.SelectMany(r => r.Entities)'
                f'.FirstOrDefault(e => e.Name == "{target}");'
            )
            lookup[target] = f"({var}?.IdentifierType ?? eSpace.TextType)"
        elif target in local_statics:
            var = _camel(target) + "Static"
            lines.append(
                f'var {var} = eSpace.Entities.OfType<OutSystems.Model.Data.IStaticEntity>()'
                f'.Named("{target}");'
            )
            lookup[target] = f"({var}?.IdentifierType ?? eSpace.TextType)"
        elif target in local_entities:
            var = _camel(target) + "Entity"
            lines.append(
                f'var {var} = eSpace.Entities.OfType<OutSystems.Model.Data.IServerEntity>()'
                f'.Named("{target}");'
            )
            lookup[target] = f"({var}?.IdentifierType ?? eSpace.TextType)"
        else:
            # Unknown — generic referenced lookup. Most likely failure point
            # (hallucinated/missing entity name). FirstOrDefault + Text fallback.
            var = _camel(target) + "Entity"
            lines.append(
                f'var {var} = eSpace.References.SelectMany(r => r.Entities)'
                f'.FirstOrDefault(e => e.Name == "{target}");  // unknown source — verify after publish'
            )
            lookup[target] = f"({var}?.IdentifierType ?? eSpace.TextType)"

        # var_lookup ALWAYS maps target → the bare entity variable name.
        # AddIdentFk callers append `?.IdentifierType` at the call site (so the
        # typed-method-call gets `IIdentifierType?`). Earlier User was excluded
        # from var_lookup because its var WAS the IdentifierType (with TextType
        # fallback) — that asymmetry caused render_attribute_line to look up
        # the wrong key. Now User's var is the entity (uniform shape) and is
        # populated unconditionally.
        var_lookup[target] = var

    return ("\n    ".join(lines), lookup, var_lookup)


def _camel(s: str) -> str:
    """PascalCase → camelCase (first letter lowered)."""
    return s[0].lower() + s[1:] if s else s


# ─── Recipe 01 (server entity) renderer ────────────────────────────────────────

def render_server_entity(
    entity: ServerEntity,
    local_server_entities: set[str],
    local_static_entities: set[str],
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
) -> str:
    """Render Recipe 01 for one server entity. Returns the prompt string
    (preamble + filled recipe body) ready to send to mentor_start."""
    template = load_recipe("01_entity_server", recipes_dir)
    preamble = load_preamble(recipes_dir)

    fk_targets = collect_fk_targets(entity.attributes)
    fk_block, fk_lookup, fk_var_lookup = render_fk_resolution_block(
        fk_targets, local_server_entities, local_static_entities
    )

    # IMPORTANT: pass fk_var_lookup (bare var names), NOT fk_lookup (parenthesized
    # `({var}?.IdentifierType ?? eSpace.TextType)` expressions). The action-param
    # codepath at line 527/533 accepts the wider IBasicType-typed fallback for
    # DataType assignment; AddIdentFk's typed IIdentifierType param does NOT.
    attr_lines = [render_attribute_line(a, fk_var_lookup) for a in entity.attributes]
    attributes_block = "\n    ".join(attr_lines)

    description = (entity.description or "").replace('"', '\\"')

    body = template.csharp_body
    body = _replace_braces(body, {
        "ENTITY_NAME": entity.name,
        "ENTITY_DESCRIPTION": description,
        "ATTRIBUTES_BLOCK": attributes_block,
    })

    # Inject the FK resolution block at the top by replacing the comment placeholder
    # in recipe 01's body, which has a "// example: local static entity..." comment.
    # Simpler: replace the "// ─── FK type resolution" block entirely.
    fk_section_start = body.find("// ─── FK type resolution")
    fk_section_end = body.find("// ─── Per-type attribute helpers")
    if fk_section_start >= 0 and fk_section_end > fk_section_start:
        new_fk_section = (
            "// ─── FK type resolution (auto-generated from manifest) ───\n"
            f"    {fk_block}\n\n    "
        )
        body = body[:fk_section_start] + new_fk_section + body[fk_section_end:]

    return _assemble_prompt(preamble, body, template.imports)


# ─── Recipe 02 (static entity) renderer ────────────────────────────────────────

def render_static_entity(
    entity: StaticEntity,
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
) -> str:
    """Render Recipe 02 for one static entity."""
    template = load_recipe("02_entity_static", recipes_dir)
    preamble = load_preamble(recipes_dir)

    # Extra attributes (beyond the PK): emit AddText/Int/Bool/etc.
    # Recipe 02's EXTRA_ATTRS_BLOCK is generated; we don't need FK lookup for statics
    # (they rarely have FKs).
    extra_attrs_lines = [
        render_attribute_line(a, fk_var_lookup={}) for a in entity.attributes
    ]
    extra_attrs_block = "\n    ".join(extra_attrs_lines)

    # Records block: each record needs explicit Id + Label values, otherwise
    # OutSystems' validator emits "Required Property Value" errors on publish.
    # We auto-generate:
    #   - Id: sequential 1..N (matches OutSystems' default static-entity ordering)
    #   - Label: the identifier text itself (good enough for rebuild; original
    #     Label values would need a richer manifest schema)
    # Other mandatory attrs (e.g. Order, Is_Active) default to safe values:
    #   - Order: sequential 1..N
    #   - Is_Active: True
    #   - Any other mandatory Text: empty string ""
    #   - Any other mandatory Bool: False
    #   - Any other mandatory Int: 0
    has_attr = {a.name: a for a in entity.attributes}

    def record_block(i: int, rec: str) -> str:
        lines = [f'{{']
        lines.append(f'    var r = e.CreateRecord("{rec}");')
        # Id — required for Integer/Long Integer PK
        if entity.pk_data_type in ("Integer", "Long Integer"):
            lines.append(f'    SetRecordAttr(e, r, "{entity.pk_name}", "{i}");')
        else:
            lines.append(f'    SetRecordAttr(e, r, "{entity.pk_name}", "\\"{rec}\\"");')
        # Label — almost universally present
        if "Label" in has_attr:
            lines.append(f'    SetRecordAttr(e, r, "Label", "\\"{rec}\\"");')
        # Order, Is_Active — common patterns
        if "Order" in has_attr and has_attr["Order"].is_mandatory:
            lines.append(f'    SetRecordAttr(e, r, "Order", "{i}");')
        if "Is_Active" in has_attr and has_attr["Is_Active"].is_mandatory:
            lines.append(f'    SetRecordAttr(e, r, "Is_Active", "True");')
        # Any other mandatory attrs get safe defaults
        for a in entity.attributes:
            if not a.is_mandatory or a.name in ("Label", "Order", "Is_Active", entity.pk_name):
                continue
            if a.data_type == "Text" or a.data_type == "Email" or a.data_type == "Phone Number":
                lines.append(f'    SetRecordAttr(e, r, "{a.name}", "\\"\\"");')
            elif a.data_type == "Boolean":
                lines.append(f'    SetRecordAttr(e, r, "{a.name}", "False");')
            elif a.data_type in ("Integer", "Long Integer"):
                lines.append(f'    SetRecordAttr(e, r, "{a.name}", "0");')
            elif a.data_type == "Decimal":
                lines.append(f'    SetRecordAttr(e, r, "{a.name}", "0.0");')
            elif a.data_type == "Currency":
                lines.append(f'    SetRecordAttr(e, r, "{a.name}", "0");')
        lines.append('}')
        return "\n    ".join(lines)

    records_block = "\n    ".join(
        record_block(i, rec) for i, rec in enumerate(entity.records, start=1)
    )

    # Map YAML dataType ("Integer" | "Text" | "Long Integer") → C# expression
    pk_type_map = {
        "Integer": "eSpace.IntegerType",
        "Text": "eSpace.TextType",
        "Long Integer": "eSpace.LongIntegerType",
    }
    pk_cs_type = pk_type_map.get(entity.pk_data_type, f'/* unsupported PK type: {entity.pk_data_type} */')

    # Length: Text PKs need a length; Integer/Long Integer don't.
    pk_length_arg = f"{entity.pk_length}" if entity.pk_length else "null"

    body = template.csharp_body
    body = _replace_braces(body, {
        "ENTITY_NAME": entity.name,
        "PK_NAME": entity.pk_name,
        "PK_DATATYPE": pk_cs_type,
        "PK_LENGTH": pk_length_arg,
        "EXTRA_ATTRS_BLOCK": extra_attrs_block,
        "RECORDS_BLOCK": records_block,
    })

    # For non-Text PKs, the `pkAttr.Length = null` line is harmless but odd.
    # Recipe 02's template always emits it. That's fine — OutSystems accepts
    # null Length on Integer attributes.

    return _assemble_prompt(preamble, body, template.imports)


# ─── Recipe 03 (role) renderer ─────────────────────────────────────────────────

def render_role(role: Role, recipes_dir: Path = DEFAULT_RECIPES_DIR) -> str:
    template = load_recipe("03_role", recipes_dir)
    preamble = load_preamble(recipes_dir)

    description = role.description.replace('\n', ' ').replace('"', '\\"').strip()

    body = template.csharp_body
    body = _replace_braces(body, {
        "ROLE_NAME": role.name,
        "ROLE_DESCRIPTION": description,
        "IS_PUBLIC": "true" if role.is_public else "false",
    })

    return _assemble_prompt(preamble, body, template.imports)


# ─── Recipe 04 (action — minimal stub) renderer ────────────────────────────────

def render_action_stub(
    action: Action,
    local_server_entities: set[str],
    local_static_entities: set[str],
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
) -> str:
    """Render Recipe 04 for one action as a signature-only stub.

    Builds the C# directly rather than patching the full Recipe 04 template,
    because stub actions skip most of Recipe 04's template surface (no
    producer module, no targetSA, no call node, no arg bindings).

    FK resolution is auto-injected — any param typed "<Entity> Identifier"
    gets a resolver declaration at the top.
    """
    preamble = load_preamble(recipes_dir)

    # Scan params for FK targets, build resolution block + lookup
    fk_targets: list[str] = []
    for p in action.parameters:
        if p.data_type.endswith(" Identifier"):
            t = p.data_type[: -len(" Identifier")]
            if t not in fk_targets:
                fk_targets.append(t)
        elif p.data_type in local_server_entities or p.data_type in local_static_entities:
            # entity-record-typed param: resolve the entity OBJECT so the param
            # DataType can be set to the full record type (p.DataType = entVar).
            if p.data_type not in fk_targets:
                fk_targets.append(p.data_type)
    fk_block, fk_lookup, fk_var_lookup = render_fk_resolution_block(
        fk_targets, local_server_entities, local_static_entities
    )

    inputs_lines = [
        _render_action_param("AddInput", p, fk_lookup, fk_var_lookup)
        for p in action.inputs
    ]
    inputs_block = "\n    ".join(inputs_lines) if inputs_lines else "// (no inputs)"

    outputs_lines = [
        _render_action_param("AddOutput", p, fk_lookup, fk_var_lookup)
        for p in action.outputs
    ]
    outputs_block = "\n    ".join(outputs_lines) if outputs_lines else "// (no outputs)"

    # v2 SWAP (2026-06-08): emit IServiceAction instead of IServerAction.
    # IServerAction.Public=true triggers OS-BLD-40409 (the
    # ModelFeature_ServerActionPublicPropertyApp removed-feature wall). ODC's
    # blessed cross-app exposure surface is IServiceAction — same API surface
    # as IServerAction (inherits from IAction: CreateInputParameter,
    # CreateOutputParameter, CreateNode<>, ConnectedBelow). Differences:
    # CreateServiceAction returns IServiceAction; Public=true is REQUIRED;
    # MaxRecordsPerBatch/ExposedAsRest/CacheInMinutes/Function/Transaction
    # do NOT exist on IServiceAction (don't emit them).
    # Verified live 2026-06-08 on HomeBankingPortalRebake2 (Ping ServiceAction
    # publish rev 2→3). Helper signatures use IAction (the common base) so
    # they remain reusable across both action kinds.
    is_public = "true"

    # Build the C# body directly. Stubs don't need the helpers/wiring of
    # Recipe 04's full template — just create action, declare params, wire
    # Start → End.
    body = f"""eSpace => {{
    // ─── FK resolution (auto-generated from action signature) ───
    {fk_block if fk_block else '// (no FK params)'}

    // ─── Helpers ───────────────────────────────────────────────────────────
    void AddInput(OutSystems.Model.Logic.IAction act, string name,
                   OutSystems.Model.Types.ITypeSignature type, bool mandatory) {{
        var p = act.CreateInputParameter(name);
        p.DataType = type;
        p.IsMandatory = mandatory;
    }}
    void AddOutput(OutSystems.Model.Logic.IAction act, string name,
                    OutSystems.Model.Types.ITypeSignature type) {{
        var p = act.CreateOutputParameter(name);
        p.DataType = type;
    }}

    // ─── Create action ─────────────────────────────────────────────────────
    var a = eSpace.CreateServiceAction("{action.name}");
    a.Public = {is_public};

    // Inputs
    {inputs_block}

    // Outputs
    {outputs_block}

    // Stub body: Start → End (no work).
    // Empirical (T1.1, 2026-05-27): IServerAction.StartNode/EndNode properties
    // don't exist. Newly-created actions have an empty .Nodes collection. Must
    // explicitly CreateNode<IStartNode>() + CreateNode<IEndNode>() + wire via
    // end.ConnectedBelow(start). Recorded in [[odc_mcp_action_node_wiring]].
    var startNode = a.CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>();
    var endNode = a.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>();
    endNode.ConnectedBelow(startNode);

    Console.WriteLine($"Recipe 04: {action.name} | Created: action (Public={{a.Public}}, {{a.InputParameters.Count()}} in, {{a.OutputParameters.Count()}} out) | Status: OK");
}}"""

    imports = [
        "System.Linq",
        "OutSystems.Model",
        "OutSystems.Model.Data",
        "OutSystems.Model.Logic",
        "OutSystems.Model.Types",
    ]
    return _assemble_prompt(preamble, body, imports)


# ─── Recipe 10 (theme) renderer ────────────────────────────────────────────────

def render_theme(
    theme_name: str,
    css_path: Path,
    is_default: bool = True,
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
) -> str:
    """Render Recipe 10 for one theme. Reads the CSS file from disk and slots
    it into the recipe template.

    NB: CSS files can be 28-30 KB. The resulting Mentor prompt is large but
    well under the per-call limits (typical theme prompts ~32 KB)."""
    template = load_recipe("10_theme_replace", recipes_dir)
    preamble = load_preamble(recipes_dir)

    css = css_path.read_text() if css_path.exists() else ""
    # Escape for C# verbatim string (@""): just double any embedded double-quotes
    css_escaped = css.replace('"', '""')

    body = template.csharp_body
    body = _replace_braces(body, {
        "THEME_NAME": theme_name,
        "CSS_CONTENT": css_escaped,
        "IS_DEFAULT": "true" if is_default else "false",
    })

    return _assemble_prompt(preamble, body, template.imports)


# ─── Recipe 11 (default screen) renderer ───────────────────────────────────────

def render_default_screen(
    screen_name: str,
    flow_name: str = "MainFlow",
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
) -> str:
    """Render Recipe 11 — set the app's DefaultScreen to the given screen."""
    template = load_recipe("11_default_screen", recipes_dir)
    preamble = load_preamble(recipes_dir)

    body = template.csharp_body
    body = _replace_braces(body, {
        "DEFAULT_SCREEN_NAME": screen_name,
        "FLOW_NAME": flow_name,
    })

    return _assemble_prompt(preamble, body, template.imports)


# ─── Recipe 99 (verify probe) renderer ─────────────────────────────────────────

def render_verify_probe(
    expected_entities: int,
    expected_screens: int,
    expected_actions: int,
    expected_default_screen: str | None = None,
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
) -> str:
    """Render Recipe 99 verification probe. The probe runs as an
    applyModelApiCode read-only call that returns per-counter status.

    Caller uses this AFTER publish_status=Finished + a brief context cache
    delay. The Mentor stdoutOutput is the verification report."""
    template = load_recipe("99_publish_verify", recipes_dir)
    preamble = load_preamble(recipes_dir)

    body = template.csharp_body
    body = _replace_braces(body, {
        "EXPECTED_ENTITY_COUNT": str(expected_entities),
        "EXPECTED_SCREEN_COUNT": str(expected_screens),
        "EXPECTED_ACTION_COUNT": str(expected_actions),
        # Default screen verification dropped in Recipe 99 — it lives on
        # eSpace.DefaultMobileFlow.DefaultScreen, not eSpace.DefaultScreen
        # (TBD: separate verification call once Recipe 11 is tested).
    })

    return _assemble_prompt(preamble, body, template.imports)


def _render_action_param(
    helper: str,
    p: ActionParameter,
    fk_lookup: dict[str, str],
    var_lookup: dict[str, str] | None = None,
) -> str:
    """One C# line (or inline block) for an action parameter."""
    name = p.name
    mand = "true" if p.is_mandatory else "false"
    var_lookup = var_lookup or {}

    if p.data_type.endswith(" Identifier"):
        target = p.data_type[: -len(" Identifier")]
        target_var = fk_lookup.get(target, f"/* unresolved {target} */")
        if helper == "AddInput":
            return f'{helper}(a, "{name}", {target_var}, {mand});'
        return f'{helper}(a, "{name}", {target_var});'

    # Entity-record-typed parameter: DataType is the entity OBJECT directly.
    # Verified live 2026-05-29: `p.DataType = <IServerEntity var>` compiles and
    # sets the param to the full record type. Emitted as a self-contained brace
    # block (not via the AddInput/AddOutput helpers, whose ITypeSignature-typed
    # arg need not accept IServerEntity) so repeated `rp` locals never collide.
    if p.data_type in var_lookup:
        ent_var = var_lookup[p.data_type]
        if helper == "AddInput":
            return (
                f'{{ var rp = a.CreateInputParameter("{name}"); '
                f'rp.DataType = {ent_var}; rp.IsMandatory = {mand}; }}'
            )
        return (
            f'{{ var rp = a.CreateOutputParameter("{name}"); '
            f'rp.DataType = {ent_var}; }}'
        )

    # Map basic types to eSpace.<Type>Type
    type_map = {
        "Text": "eSpace.TextType",
        "Integer": "eSpace.IntegerType",
        "Long Integer": "eSpace.LongIntegerType",
        "Boolean": "eSpace.BooleanType",
        "Decimal": "eSpace.DecimalType",
        "Date Time": "eSpace.DateTimeType",
        "Date": "eSpace.DateType",
        "Email": "eSpace.TextType",
        "Phone Number": "eSpace.TextType",
        "Currency": "eSpace.CurrencyType",
        "Binary Data": "eSpace.BinaryDataType",
    }
    cs_type = type_map.get(p.data_type, f'/* unsupported {p.data_type} */')

    if helper == "AddInput":
        return f'{helper}(a, "{name}", {cs_type}, {mand});'
    return f'{helper}(a, "{name}", {cs_type});'


# ─── Prompt assembly ───────────────────────────────────────────────────────────

def _assemble_prompt(preamble: str, body: str, imports: list[str]) -> str:
    """Glue preamble + body + imports declaration into the final prompt string
    that gets sent to mentor_start."""
    imports_lines = "\n".join(f"  - {i}" for i in imports) if imports else "  (none)"
    return (
        preamble.strip()
        + "\n\n```csharp\n"
        + body.strip()
        + "\n```\n\n"
        + f"Required imports for the `imports` array on the applyModelApiCode call:\n{imports_lines}\n"
    )


def _replace_braces(template: str, substitutions: dict[str, str]) -> str:
    """Replace {{KEY}} occurrences with values. Does NOT touch single-brace
    C# string interpolation tokens like ${var}."""
    out = template
    for key, value in substitutions.items():
        out = out.replace("{{" + key + "}}", value)
    return out
