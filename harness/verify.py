"""harness-verify — the judge.

Two phases, matching app_spec.v0.json's contract:

  spec phase (IMPLEMENTED, offline, deterministic) — validate-before-assert.
    1. JSON-Schema validation against harness/schemas/app_spec.v0.json.
    2. Static cross-reference integrity that JSON Schema cannot express (dangling
       screen/entity/component references, role subsetting, assertion-vs-model
       agreement). A spec that fails either is a spec-gap wall UP FRONT.
    3. NO-HOLES capability check (HD D11): when a `capabilities` layer is declared,
       every entity/screen/role must be covered by at least one user flow and every
       flow reference (screen/entity/role/action/step) must resolve — else spec-gap.
       A structure-only spec (no capabilities) stays valid with one advisory nudge.

  live phase — check the built ODC app against each screen's acceptance
    assertions. SNAPSHOT-FED (per HD D7): the orchestrator fetches live state via the
    MCP and passes it in — `--entities` (a context_entities response) drives
    entityExists/attribute; `--screens` (a structured applyModelApiCode screen-walk;
    contract by example in examples/task_tracker/live_screens.json) drives
    componentPresent/binding/navigates. Given the snapshot the per-kind executors
    return REAL pass/fail; with no snapshot each assertion is inconclusive and the
    phase NEVER returns a silent pass. integrationExists is unverifiable (no ODC read
    path). The judge does not open its own MCP client — the auto-fetch channel is
    intentionally unbuilt (you fetch the snapshot yourself).

Exit codes: 0 = clean (spec valid / all supplied live assertions pass); 1 = failure
(spec-gap findings, or a live assertion that failed against the snapshot); 3 =
inconclusive (live requested but no snapshot supplied, or unverifiable). The build
agent turns findings into WALLS.md entries (category spec-gap) per the harness doctrine.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "app_spec.v0.json"

# The Entity.Attribute binding form, e.g. "Account.Balance".
_DOTTED = lambda s: isinstance(s, str) and s.count(".") == 1 and all(s.split("."))


@dataclass
class Finding:
    severity: str   # "spec-gap" (gating) | "advisory" (non-gating)
    summary: str
    context: str

    def render(self) -> str:
        return f"[{self.severity}] {self.summary}\n    context: {self.context}"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _schema_findings(spec: dict) -> list[Finding]:
    """Phase 1 — JSON-Schema validation (draft 2020-12)."""
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(_load_schema())
    findings: list[Finding] = []
    for error in sorted(validator.iter_errors(spec), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(p) for p in error.absolute_path) or "(root)"
        findings.append(Finding("spec-gap", f"schema violation at {location}", error.message))
    return findings


def _crossref_findings(spec: dict) -> list[Finding]:
    """Phase 2 — integrity checks JSON Schema cannot express. Assumes the spec
    already passed Phase 1, so the shape is trusted."""
    findings: list[Finding] = []

    def gap(summary: str, context: str) -> None:
        findings.append(Finding("spec-gap", summary, context))

    def advise(summary: str, context: str) -> None:
        findings.append(Finding("advisory", summary, context))

    app_roles = set(spec["app"]["roles"])
    entities = {e["name"]: e for e in spec["dataModel"]["entities"]}
    screen_ids = {s["id"] for s in spec["screens"]}
    integration_names = {i["name"] for i in spec.get("integrations", [])}
    # Entities a CONSUMER app reads from producer apps (Batch C appReferences) are legitimate binding
    # targets even though they are not OWNED locally — the modular decomposition's consumer screens
    # bind to referenced Cores. Their attributes aren't in this spec, so attribute-level binding to one
    # is advisory (can't be disproved here), not a gap.
    referenced = {el["name"] for ref in spec.get("appReferences", [])
                  for el in ref.get("elements", []) if el.get("kind", "Entity") in ("Entity", "StaticEntity")}

    _check_unique([e["name"] for e in spec["dataModel"]["entities"]], "entity name", gap)
    _check_unique([s["id"] for s in spec["screens"]], "screen id", gap)
    _check_unique([i["name"] for i in spec.get("integrations", [])], "integration name", gap)

    default_screens = [s["id"] for s in spec["screens"] if s.get("isDefault")]
    if len(default_screens) > 1:
        gap("more than one screen marked isDefault",
            f"screens {default_screens} all set isDefault=true; at most one may be the app default")

    for entity in spec["dataModel"]["entities"]:
        ename = entity["name"]
        _check_unique([a["name"] for a in entity["attributes"]], f"attribute name in {ename}", gap)
        for attr in entity["attributes"]:
            ref = attr.get("references")
            if ref is not None and ref not in entities:
                gap("attribute FK references unknown entity",
                    f"{ename}.{attr['name']} references '{ref}' not in dataModel.entities")
        for rel in entity.get("relationships", []):
            if rel["to"] not in entities:
                gap("relationship targets unknown entity",
                    f"{ename}.relationship -> '{rel['to']}' not in dataModel.entities")

    for screen in spec["screens"]:
        sid = screen["id"]
        component_ids = {c["id"] for c in screen.get("components", [])}
        _check_unique([c["id"] for c in screen.get("components", [])], f"component id in screen '{sid}'", gap)

        for role in screen.get("roles", []):
            if role not in app_roles:
                gap("screen role not declared in app.roles",
                    f"screen '{sid}' role '{role}' not in {sorted(app_roles)}")

        access = screen.get("access")
        if access:
            rr = access.get("requiresRole")
            if rr is not None and rr not in app_roles:
                gap("screen access.requiresRole not in app.roles",
                    f"screen '{sid}' access.requiresRole '{rr}' not in {sorted(app_roles)}")
            rt = access.get("redirectTo")
            if rt is not None and rt not in screen_ids:
                gap("screen access.redirectTo targets unknown screen",
                    f"screen '{sid}' access.redirectTo '{rt}' not in screens")
            if access.get("adminOnly") and not spec.get("auth", {}).get("adminAttribute"):
                gap("screen access.adminOnly needs auth.adminAttribute",
                    f"screen '{sid}' is adminOnly but app.auth defines no adminAttribute to gate on")

        for comp in screen.get("components", []):
            _check_binding(comp, sid, entities, gap, advise, referenced)
            _check_product_ui(comp, sid, entities, screen_ids, gap)

        for edge in screen.get("navigation", []):
            if edge["toScreen"] not in screen_ids:
                gap("navigation targets unknown screen",
                    f"screen '{sid}' navEdge -> toScreen '{edge['toScreen']}' not in screens")
            fc = edge.get("fromComponent")
            if fc is not None and fc not in component_ids:
                gap("navigation fromComponent not on screen",
                    f"screen '{sid}' navEdge fromComponent '{fc}' not a component on this screen")

        for action in screen.get("actions", []):
            oc = action["trigger"]["onComponent"]
            if oc not in component_ids:
                gap("action trigger references unknown component",
                    f"screen '{sid}' action '{action['name']}' onComponent '{oc}' not on this screen")

        for chart in screen.get("charts", []):
            ce = chart["entity"]
            if ce not in entities:
                gap("chart entity unknown",
                    f"screen '{sid}' chart '{chart['id']}' entity '{ce}' not in dataModel.entities")
            else:
                attr_names = {a["name"] for a in entities[ce]["attributes"]}
                if chart["categoryField"] not in attr_names:
                    gap("chart categoryField not an attribute",
                        f"screen '{sid}' chart '{chart['id']}' categoryField '{chart['categoryField']}' not on {ce}")
                for ser in chart["series"]:
                    if ser["valueField"] not in attr_names:
                        gap("chart series valueField not an attribute",
                            f"screen '{sid}' chart '{chart['id']}' series valueField '{ser['valueField']}' not on {ce}")

        _check_assertions(screen, entities, screen_ids, integration_names, gap)

    # App-level shared navigation: every nav item + showOn must resolve to a screen.
    nav = spec.get("navigation")
    if nav:
        for item in nav.get("items", []):
            to = item.get("toScreen")
            if to is not None and to not in screen_ids:
                gap("app navigation item targets unknown screen",
                    f"navigation item '{item.get('label', '?')}' -> '{to}' not in screens")
        show_on = nav.get("showOn")
        if isinstance(show_on, list):
            for s in show_on:
                if s not in screen_ids:
                    gap("app navigation showOn references unknown screen",
                        f"navigation.showOn '{s}' not in screens")

    # App-level auth: user entity / admin attribute / login screen / test users must resolve.
    auth = spec.get("auth")
    if auth:
        provider = auth.get("provider")
        ue = auth.get("userEntity")
        if provider == "app-local" and ue is None:
            advise("app-local auth without a userEntity",
                   "auth.provider is app-local but no userEntity is declared — the identity source is unspecified")
        if ue is not None and ue not in entities:
            gap("auth.userEntity unknown", f"auth.userEntity '{ue}' not in dataModel.entities")
        aa = auth.get("adminAttribute")
        if aa is not None and ue in entities:
            attr_names = {a["name"] for a in entities[ue]["attributes"]}
            if aa not in attr_names:
                gap("auth.adminAttribute not on userEntity",
                    f"auth.adminAttribute '{aa}' is not an attribute of '{ue}'")
        ls = auth.get("loginScreen")
        if ls is not None and ls not in screen_ids:
            gap("auth.loginScreen targets unknown screen", f"auth.loginScreen '{ls}' not in screens")
        for tu in auth.get("testUsers", []):
            r = tu.get("role")
            if r is not None and r not in app_roles and r != "Admin":
                advise("auth testUser role not in app.roles",
                       f"auth.testUsers role '{r}' not in app.roles {sorted(app_roles)} (allowed: 'Admin')")

    agents = spec.get("agents", [])
    if agents:
        _check_unique([a["name"] for a in agents], "agent name", gap)

    _capability_findings(spec, entities, screen_ids, app_roles, gap, advise)

    return findings


def _capability_findings(spec: dict, entities: dict, screen_ids: set, app_roles: set, gap, advise) -> None:
    """NO-HOLES check (HD D11). The capabilities layer is the connectivity spine:
    every user flow must resolve, and every entity/screen/role must be exercised by
    at least one flow. Enforced as spec-gaps ONLY when a `capabilities` layer is
    declared — a structure-only spec (no capabilities) stays valid but gets one
    advisory nudge, preserving backward compatibility (e.g. the home_banking excerpt)."""
    entity_names = set(entities)
    caps = spec.get("capabilities")

    # Entities surfaced by a screen component binding (head of 'Entity[.Attr]').
    bound_entities: set[str] = set()
    for screen in spec["screens"]:
        for comp in screen.get("components", []):
            head = (comp.get("boundTo") or "").split(".")[0]
            if head in entity_names:
                bound_entities.add(head)

    # Actions declared per screen — a capability may only invoke actions on its screens.
    screen_actions = {s["id"]: {a["name"] for a in s.get("actions", [])} for s in spec["screens"]}

    if not caps:
        advise("no capabilities layer — spec is structure-only; NO-HOLES coverage not enforced",
               "add a `capabilities` array (HD D11) to hold this spec to the no-holes bar: "
               "every entity/screen/role covered by a user flow")
        return

    covered_entities: set[str] = set()
    covered_screens: set[str] = set()
    covered_roles: set[str] = set()

    for cap in caps:
        cname = cap["name"]
        for sid in cap["screens"]:
            (covered_screens.add(sid) if sid in screen_ids
             else gap("capability references unknown screen",
                      f"capability '{cname}' -> screen '{sid}' not in screens"))
        for en in cap["entities"]:
            (covered_entities.add(en) if en in entity_names
             else gap("capability references unknown entity",
                      f"capability '{cname}' -> entity '{en}' not in dataModel"))
        for role in cap["roles"]:
            (covered_roles.add(role) if role in app_roles
             else gap("capability role not declared in app.roles",
                      f"capability '{cname}' role '{role}' not in {sorted(app_roles)}"))

        cap_actions: set[str] = set()
        for sid in cap["screens"]:
            cap_actions |= screen_actions.get(sid, set())
        for act in cap.get("actions", []):
            if act not in cap_actions:
                gap("capability action not declared on any of its screens",
                    f"capability '{cname}' action '{act}' not an action on screens {cap['screens']}")
        for i, st in enumerate(cap.get("steps", [])):
            ssid = st.get("screen")
            if ssid is not None and ssid not in screen_ids:
                gap("capability step references unknown screen",
                    f"capability '{cname}' step {i} screen '{ssid}' not in screens")
            sact = st.get("action")
            if sact is not None and sact not in cap_actions:
                gap("capability step action not on the capability's screens",
                    f"capability '{cname}' step {i} action '{sact}' not declared on screens {cap['screens']}")

    # Coverage — these ARE the no-holes gates. Static/lookup entities are EXEMPT: an enum/lookup
    # is reference data backing other flows, not a user-flow entity of its own, so requiring it to
    # have its own capability is a false hole (surfaced by the Batch-A ContactStatus build).
    static_entity_names = {en for en in entity_names
                           if isinstance(entities.get(en), dict) and entities[en].get("isStatic")}
    for en in sorted(entity_names - covered_entities - static_entity_names):
        gap("entity not covered by any capability (hole)",
            f"entity '{en}' is in the data model but no capability exercises it")
    for sid in sorted(screen_ids - covered_screens):
        gap("screen not covered by any capability (hole)",
            f"screen '{sid}' is declared but no capability uses it")
    for role in sorted(app_roles - covered_roles):
        gap("role not covered by any capability (hole)",
            f"role '{role}' is declared but no capability uses it")

    # Softer connectivity smells — advisory, never gating.
    for en in sorted(entity_names - bound_entities):
        advise("entity not bound on any screen component",
               f"entity '{en}' is capability-covered but not bound on a screen (backing/join?) — confirm intended")
    refs_in: set[str] = set()
    refs_out: dict[str, list] = {}
    for e in spec["dataModel"]["entities"]:
        outs = [a["references"] for a in e["attributes"] if a.get("references")]
        refs_out[e["name"]] = outs
        refs_in.update(outs)
    for e in sorted(entity_names):
        if not refs_out.get(e) and e not in refs_in:
            advise("entity has no foreign-key relationship (possible orphan)",
                   f"entity '{e}' has no FK in or out — fine only if intentional (singleton/lookup)")


def _check_binding(comp: dict, sid: str, entities: dict, gap, advise, referenced: set | None = None) -> None:
    referenced = referenced or set()
    bound = comp.get("boundTo")
    if bound is None:
        return
    if _DOTTED(bound):
        ent, attr = bound.split(".")
        if ent in entities:
            if attr not in {a["name"] for a in entities[ent]["attributes"]}:
                gap("component bound to unknown attribute",
                    f"screen '{sid}' component '{comp['id']}' boundTo '{bound}' — '{ent}' has no attribute '{attr}'")
        elif ent in referenced:
            advise("component bound to a referenced (cross-app) entity — attribute not locally checkable",
                   f"screen '{sid}' component '{comp['id']}' boundTo '{bound}' — '{ent}' is an appReference; "
                   f"confirm '{attr}' against the producer in the build")
        else:
            gap("component bound to unknown entity",
                f"screen '{sid}' component '{comp['id']}' boundTo '{bound}' — entity '{ent}' unknown")
    elif bound in entities or bound in referenced:
        return
    else:
        advise("component binding not statically verifiable (assumed aggregate)",
               f"screen '{sid}' component '{comp['id']}' boundTo '{bound}' — not an Entity[.Attribute]; "
               f"confirm against live state in the build")


def _check_product_ui(comp: dict, sid: str, entities: dict, screen_ids: set, gap) -> None:
    """Validate PRODUCT-UI primitive refs (columns/board/nav). A bare field can't be
    resolved without the component's bound entity, so only 'Entity.Attribute' fields
    are checked; nav toScreen is always resolvable."""
    def check_field(f, where: str) -> None:
        if isinstance(f, str) and _DOTTED(f):
            ent, attr = f.split(".")
            if ent not in entities:
                gap("product-ui field references unknown entity",
                    f"screen '{sid}' {where} '{f}' — entity '{ent}' unknown")
            elif attr not in {a["name"] for a in entities[ent]["attributes"]}:
                gap("product-ui field references unknown attribute",
                    f"screen '{sid}' {where} '{f}' — '{ent}' has no attribute '{attr}'")

    cid = comp["id"]
    for col in comp.get("columns", []) or []:
        check_field(col.get("field"), f"component '{cid}' column")
    board = comp.get("board")
    if board:
        check_field(board.get("columnsBy"), f"component '{cid}' board.columnsBy")
        card = board.get("card", {}) or {}
        check_field(card.get("title"), f"component '{cid}' board.card.title")
        check_field(card.get("avatar"), f"component '{cid}' board.card.avatar")
        for b in card.get("badges", []) or []:
            check_field(b, f"component '{cid}' board.card.badge")
    for item in comp.get("nav", []) or []:
        t = item.get("toScreen")
        if t is not None and t not in screen_ids:
            gap("sidebar nav targets unknown screen",
                f"screen '{sid}' component '{cid}' nav -> '{t}' not in screens")


def _check_assertions(screen: dict, entities: dict, screen_ids: set, integration_names: set, gap) -> None:
    sid = screen["id"]
    component_ids = {c["id"] for c in screen.get("components", [])}
    components = {c["id"]: c for c in screen.get("components", [])}

    for a in screen["acceptance"]["assertions"]:
        kind = a["kind"]
        if kind == "entityExists":
            if a["entity"] not in entities:
                gap("assertion entityExists references unknown entity",
                    f"screen '{sid}' asserts entity '{a['entity']}' not in dataModel")
        elif kind == "attribute":
            ent = entities.get(a["entity"])
            if ent is None:
                gap("assertion attribute references unknown entity",
                    f"screen '{sid}' asserts {a['entity']}.{a['attribute']} — entity unknown")
                continue
            decl = next((x for x in ent["attributes"] if x["name"] == a["attribute"]), None)
            if decl is None:
                gap("assertion attribute references unknown attribute",
                    f"screen '{sid}' asserts {a['entity']}.{a['attribute']} — attribute not in entity")
            elif decl["dataType"] != a["dataType"]:
                gap("assertion dataType contradicts the data model",
                    f"screen '{sid}' asserts {a['entity']}.{a['attribute']} is {a['dataType']}, "
                    f"model declares {decl['dataType']}")
        elif kind == "componentPresent":
            if a["componentId"] not in component_ids:
                gap("assertion componentPresent references unknown component",
                    f"screen '{sid}' asserts component '{a['componentId']}' which is not declared on this screen")
        elif kind == "binding":
            cid = a["componentId"]
            if cid not in component_ids:
                gap("assertion binding references unknown component",
                    f"screen '{sid}' binding assertion on '{cid}' — component not declared")
            elif components[cid].get("boundTo") != a["boundTo"]:
                gap("assertion binding contradicts component boundTo",
                    f"screen '{sid}' asserts '{cid}' boundTo '{a['boundTo']}', "
                    f"component declares '{components[cid].get('boundTo')}'")
        elif kind == "navigates":
            if a["toScreen"] not in screen_ids:
                gap("assertion navigates to unknown screen",
                    f"screen '{sid}' navigates assertion -> '{a['toScreen']}' not in screens")
            fc = a.get("fromComponent")
            if fc is not None and fc not in component_ids:
                gap("assertion navigates fromComponent not on screen",
                    f"screen '{sid}' navigates assertion fromComponent '{fc}' not on this screen")
        elif kind == "integrationExists":
            if a["integration"] not in integration_names:
                gap("assertion integrationExists references unknown integration",
                    f"screen '{sid}' asserts integration '{a['integration']}' not in top-level integrations")


def _check_unique(names: list[str], label: str, gap) -> None:
    seen, dupes = set(), set()
    for n in names:
        (dupes if n in seen else seen).add(n)
    for d in sorted(dupes):
        gap(f"duplicate {label}", f"'{d}' declared more than once")


# An array-valued dataType: a trailing "[]" ("Text[]", "Image[]") or a List/Array
# wrapper ("List<Text>", "Array of Text", "list of image").
_ARRAY_DATATYPE_RE = re.compile(r"\[\s*\]\s*$|^\s*(list|array)\s*(<|\bof\b)", re.IGNORECASE)


def _is_array_datatype(dt) -> bool:
    return isinstance(dt, str) and bool(_ARRAY_DATATYPE_RE.search(dt))


def _datamodel_lint(spec: dict) -> list[Finding]:
    """B1 (RECIPE_GAPS): ODC entity/structure attributes CANNOT be list-valued — the
    dataType allow-list is basic types + Identifier only. Catch an array-valued attribute
    ('Image[]', 'Text[]', 'List<Text>') and emit the actionable 'promote to a child entity
    + FK' guidance, instead of the cryptic enum failure JSON-Schema would raise. Runs
    ALONGSIDE the schema layer (see validate_spec) so this message survives even though the
    array dataType also violates the odcDataType enum. Defensive against malformed shape —
    it also runs before the schema has vouched for the spec."""
    findings: list[Finding] = []

    def scan(owner_kind: str, owner_name: str, attrs) -> None:
        if not isinstance(attrs, list):
            return
        for attr in attrs:
            if isinstance(attr, dict) and _is_array_datatype(attr.get("dataType")):
                findings.append(Finding(
                    "spec-gap",
                    "array-valued attribute is not representable in ODC",
                    f"{owner_kind} {owner_name}.{attr.get('name', '?')} has dataType "
                    f"'{attr.get('dataType')}'. ODC entity/structure attributes cannot be "
                    f"list-valued (allow-list = basic types + Identifier). Model it as a CHILD "
                    f"ENTITY (one row per element, FK -> {owner_name}), or a denormalized CSV "
                    f"Text column."))

    dm = spec.get("dataModel")
    if isinstance(dm, dict):
        for e in dm.get("entities", []) or []:
            if isinstance(e, dict):
                scan("entity", e.get("name", "?"), e.get("attributes"))
    for st in spec.get("structures", []) or []:
        if isinstance(st, dict):
            scan("structure", st.get("name", "?"), st.get("attributes"))
    return findings


def validate_spec(spec: dict) -> list[Finding]:
    """Full spec-phase validation. Cross-ref checks run only if the schema shape
    is sound (otherwise they'd trip over the same structural problem). The data-model
    lint runs alongside the schema layer so an array-valued attribute yields its
    actionable message even though it also fails the schema enum (which short-circuits
    cross-ref)."""
    findings = _datamodel_lint(spec) + _schema_findings(spec)
    if any(f.severity == "spec-gap" for f in findings):
        return findings
    return findings + _crossref_findings(spec)


# ── Live phase: assertion-kind -> channel dispatch ──────────────────────────
# Channel per kind is GROUNDED in the MCP doctrine-notes ODC findings, NOT assumed.
# Channels: "mcp" (an established context_* read path returns the fact) ·
# "capture" (only observable on the rendered screen via CDP) · "unverifiable"
# (findings establish NO read path — never passes; exit 3).
LIVE_CHANNELS: dict[str, tuple[str, str]] = {
    "entityExists": (
        "mcp",
        "context_entities / context_search objects=['Entities'] returns entities "
        "(ODC_MCP_CATALOG: 'Full at entity level').",
    ),
    "attribute": (
        "mcp",
        "context_entities additionalData.attributes carries {dataType, isMandatory, "
        "isPrimaryKey, foreignKey} (ODC_MCP_CATALOG: 'Full at attribute level').",
    ),
    "componentPresent": (
        "mcp",
        "applyModelApiCode model-walk reads the screen's widget tree (D12, PROVEN live rev5: 17/17 screens). "
        "Evaluated by the screen-walk executor (load_screens_snapshot + _eval_component_present) against the "
        "structured walk snapshot the orchestrator supplies; CDP is the visual/pixel cross-check, not the gate.",
    ),
    "binding": (
        "mcp",
        "applyModelApiCode model-walk reads widget data bindings (D12, PROVEN live rev5: "
        "IssuesTable.SourceRecordList = GetIssues.List over Issue). Evaluated by _eval_binding against the "
        "structured walk snapshot (component boundTo).",
    ),
    "navigates": (
        "mcp",
        "applyModelApiCode model-walk reads OnClick/Link Destination (D12, PROVEN live rev5). Evaluated by "
        "_eval_navigates against the walk's nav edges; CDP click->observe is a behavioral cross-check.",
    ),
    "integrationExists": (
        "unverifiable",
        "context_connections is AI-model-connections only (live: empty for home_banking) and there is "
        "no context_* surface that lists consumed-REST integrations — they surface as Actions/Structures, "
        "not as a queryable integration. No established read path -> unverifiable (P1.5-confirmed 2026-06-17).",
    ),
}


@dataclass
class LiveResult:
    kind: str
    channel: str   # mcp | capture | unverifiable
    status: str    # pass | fail | unverifiable | unconfigured | not-implemented
    detail: str

    def render(self) -> str:
        return f"[{self.status}] {self.kind} via {self.channel} — {self.detail}"


def _mcp_configured(mcp_config: Path | None) -> bool:
    """A real .mcp.json with at least one server entry. The gate that keeps live
    reads from firing without a configured ODC MCP actuator."""
    if mcp_config is None or not mcp_config.exists():
        return False
    try:
        cfg = json.loads(mcp_config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool(cfg.get("mcpServers"))


def _via_channel(kind: str, target: str, mcp_config: Path | None) -> LiveResult:
    """Route a single assertion to its grounded channel. No channel executor is
    implemented yet, so a configured channel returns 'not-implemented' — never a
    fake pass."""
    channel, _rationale = LIVE_CHANNELS[kind]
    if channel == "unverifiable":
        return LiveResult(kind, channel, "unverifiable", f"{target}: no established ODC read path")
    if not _mcp_configured(mcp_config):
        needs = ".mcp.json" if channel == "mcp" else "CDP + .mcp.json"
        return LiveResult(kind, channel, "unconfigured", f"{target}: channel '{channel}' needs {needs} (absent)")
    return LiveResult(kind, channel, "not-implemented", f"{target}: channel '{channel}' executor TODO")


# ── mcp-channel executor (entityExists, attribute) ──────────────────────────
# Reads a context_entities snapshot the ORCHESTRATOR (CC) supplies (per HD D7:
# in session mode the judge consumes live state CC fetched; it does not open its
# own MCP client). Pure + deterministic — testable against a saved snapshot.
_DATATYPE_LIVE_TO_SPEC = {
    "Long Integer": "LongInteger",
    "Date Time": "DateTime",
    "Binary Data": "BinaryData",
    "Phone Number": "PhoneNumber",
}


def _normalize_datatype(live: str) -> str:
    """Live ODC dataType -> the spec's camelCase enum. Entity-typed FK identifiers
    ('HBCustomer Identifier') normalize to 'Identifier'."""
    if live in _DATATYPE_LIVE_TO_SPEC:
        return _DATATYPE_LIVE_TO_SPEC[live]
    if live.endswith(" Identifier"):
        return "Identifier"
    return live


def load_entities_snapshot(raw) -> dict:
    """Parse a context_entities response (a loaded dict, or a path/str to the JSON
    file) into {entityName: {'attributes': {name: {dataType(normalized), mandatory}}, 'isStatic': bool}}.
    Tolerant of the {data:[...], pagination} envelope and a bare list."""
    if isinstance(raw, (str, Path)):
        raw = json.loads(Path(raw).read_text(encoding="utf-8"))
    rows = raw.get("data", raw) if isinstance(raw, dict) else raw
    snap: dict = {}
    for r in rows:
        name = r.get("name")
        if not name:
            continue
        ad = r.get("additionalData") or {}
        attrs = ad.get("attributes") or r.get("attributes") or []
        amap = {}
        for a in attrs:
            if isinstance(a, dict) and a.get("name"):
                amap[a["name"]] = {
                    "dataType": _normalize_datatype(str(a.get("dataType", ""))),
                    "mandatory": bool(a.get("isMandatory", False)),
                }
        snap[name] = {"attributes": amap, "isStatic": bool(r.get("isStatic", False))}
    return snap


def _eval_entity_exists(a: dict, snap: dict) -> LiveResult:
    ok = a["entity"] in snap
    return LiveResult("entityExists", "mcp", "pass" if ok else "fail",
                      f"entity '{a['entity']}' {'present' if ok else 'NOT FOUND'} in live context_entities")


def _eval_attribute(a: dict, snap: dict) -> LiveResult:
    ent = snap.get(a["entity"])
    if ent is None:
        return LiveResult("attribute", "mcp", "fail", f"{a['entity']}.{a['attribute']}: entity not in live app")
    decl = ent["attributes"].get(a["attribute"])
    if decl is None:
        return LiveResult("attribute", "mcp", "fail", f"{a['entity']}.{a['attribute']}: attribute not in live app")
    if decl["dataType"] != a["dataType"]:
        return LiveResult("attribute", "mcp", "fail",
                          f"{a['entity']}.{a['attribute']}: live dataType {decl['dataType']} != spec {a['dataType']}")
    if "mandatory" in a and bool(a["mandatory"]) != decl["mandatory"]:
        return LiveResult("attribute", "mcp", "fail",
                          f"{a['entity']}.{a['attribute']}: live mandatory={decl['mandatory']} != spec {a['mandatory']}")
    return LiveResult("attribute", "mcp", "pass", f"{a['entity']}.{a['attribute']}:{a['dataType']} matches live")


# ── screen-walk executor (componentPresent, binding, navigates) — D12 ────────
# Consumes a STRUCTURED screen-walk snapshot the orchestrator fetches via a read-only
# applyModelApiCode walk. Contract per screen (keyed by id or name):
#   {"id"|"name", "components": [{"id","type"?,"boundTo"?,"sourceEntity"?,"groupBy"?,"columns"?}],
#    "navigation": [{"fromComponent"?,"event"?,"toScreen"}]}
# boundTo is the aggregate DisplayName (GetTaskLists.List); sourceEntity is the entity
# that aggregate queries (TaskList), resolved in the walk so entity-level spec bindings match.
# Pure + deterministic — testable against a saved walk JSON. (The walker in
# CAPTURE_PLAYBOOK must emit THIS shape; the rev5 narrative walk predates the contract.)
def load_screens_snapshot(raw) -> dict:
    """Parse a structured screen-walk into {screenKey: {'components': {id: {...}}, 'nav': [edge...]}},
    keyed by BOTH id and name (spec uses id; a walk may emit name)."""
    if isinstance(raw, (str, Path)):
        raw = json.loads(Path(raw).read_text(encoding="utf-8"))
    rows = raw.get("screens", raw) if isinstance(raw, dict) else raw
    snap: dict = {}
    for s in rows or []:
        if not isinstance(s, dict):
            continue
        comps = {c["id"]: c for c in (s.get("components") or []) if isinstance(c, dict) and c.get("id")}
        nav = [n for n in (s.get("navigation") or s.get("nav") or []) if isinstance(n, dict) and n.get("toScreen")]
        entry = {"components": comps, "nav": nav}
        for key in (s.get("id"), s.get("name")):
            if key:
                snap[key] = entry
    return snap


def _screen_entry(screen: dict, snap: dict):
    for key in (screen.get("id"), screen.get("name")):
        if key in snap:
            return snap[key]
    return None


def _eval_component_present(a: dict, screen: dict, snap: dict) -> LiveResult:
    entry = _screen_entry(screen, snap)
    if entry is None:
        return LiveResult("componentPresent", "mcp", "fail", f"screen '{screen['id']}' not in walk snapshot")
    ok = a["componentId"] in entry["components"]
    return LiveResult("componentPresent", "mcp", "pass" if ok else "fail",
                      f"screen '{screen['id']}' component '{a['componentId']}' {'present' if ok else 'NOT FOUND'} in walk")


def _eval_binding(a: dict, screen: dict, snap: dict) -> LiveResult:
    entry = _screen_entry(screen, snap)
    if entry is None:
        return LiveResult("binding", "mcp", "fail", f"screen '{screen['id']}' not in walk snapshot")
    comp = entry["components"].get(a["componentId"])
    if comp is None:
        return LiveResult("binding", "mcp", "fail",
                          f"screen '{screen['id']}' component '{a['componentId']}' not in walk")
    live = comp.get("boundTo")
    source_entity = comp.get("sourceEntity")
    spec = a["boundTo"]
    # A spec binding may name the aggregate (GetTaskLists.List) or the source ENTITY
    # (TaskList). The read-only walk carries both: boundTo (the aggregate DisplayName)
    # and sourceEntity (the entity that aggregate queries, resolved in the walk). Match
    # against either — so an entity-level assertion passes against an aggregate-bound
    # widget without a fragile name heuristic. sourceEntity is absent on pre-contract
    # walks; then only the aggregate form matches (backward compatible).
    ok = spec == live or (source_entity is not None and spec == source_entity)
    matched = " (matched sourceEntity)" if ok and spec != live else ""
    return LiveResult("binding", "mcp", "pass" if ok else "fail",
                      f"screen '{screen['id']}' '{a['componentId']}' spec={spec!r} "
                      f"live boundTo={live!r} sourceEntity={source_entity!r}{matched}")


def _eval_navigates(a: dict, screen: dict, snap: dict) -> LiveResult:
    entry = _screen_entry(screen, snap)
    if entry is None:
        return LiveResult("navigates", "mcp", "fail", f"screen '{screen['id']}' not in walk snapshot")
    fc, ev, to = a.get("fromComponent"), a.get("event"), a["toScreen"]
    for n in entry["nav"]:
        if n.get("toScreen") != to:
            continue
        if fc is not None and n.get("fromComponent") not in (None, fc):
            continue
        if ev is not None and n.get("event") not in (None, ev):
            continue
        return LiveResult("navigates", "mcp", "pass", f"screen '{screen['id']}' navigates -> '{to}' present in walk")
    return LiveResult("navigates", "mcp", "fail", f"screen '{screen['id']}' navigates -> '{to}' NOT FOUND in walk")


# One handler per assertion kind — (assertion, screen, mcp_config, entities_snap, screens_snap).
# entities_snap drives entityExists/attribute; screens_snap drives componentPresent/binding/navigates.
def _h_entity_exists(a, screen, mcp_config, ents, scrn) -> LiveResult:
    if ents is not None:
        return _eval_entity_exists(a, ents)
    return _via_channel("entityExists", f"entity '{a['entity']}'", mcp_config)


def _h_attribute(a, screen, mcp_config, ents, scrn) -> LiveResult:
    if ents is not None:
        return _eval_attribute(a, ents)
    return _via_channel("attribute", f"{a['entity']}.{a['attribute']}:{a['dataType']}", mcp_config)


def _h_component_present(a, screen, mcp_config, ents, scrn) -> LiveResult:
    if scrn is not None:
        return _eval_component_present(a, screen, scrn)
    return _via_channel("componentPresent", f"screen '{screen['id']}' component '{a['componentId']}'", mcp_config)


def _h_binding(a, screen, mcp_config, ents, scrn) -> LiveResult:
    if scrn is not None:
        return _eval_binding(a, screen, scrn)
    return _via_channel("binding", f"screen '{screen['id']}' '{a['componentId']}' boundTo '{a['boundTo']}'", mcp_config)


def _h_navigates(a, screen, mcp_config, ents, scrn) -> LiveResult:
    if scrn is not None:
        return _eval_navigates(a, screen, scrn)
    return _via_channel("navigates", f"screen '{screen['id']}' {a.get('fromComponent', '?')}->'{a['toScreen']}'", mcp_config)


def _h_integration_exists(a, screen, mcp_config, ents, scrn) -> LiveResult:
    return _via_channel("integrationExists", f"integration '{a['integration']}'", mcp_config)


_LIVE_HANDLERS = {
    "entityExists": _h_entity_exists,
    "attribute": _h_attribute,
    "componentPresent": _h_component_present,
    "binding": _h_binding,
    "navigates": _h_navigates,
    "integrationExists": _h_integration_exists,
}


def run_live_phase(spec: dict, mcp_config: Path | None, entities_snapshot: dict | None = None,
                   screens_snapshot: dict | None = None) -> list[LiveResult]:
    """Dispatch every screen assertion through its per-kind handler. entities_snapshot
    (parsed context_entities) drives entityExists/attribute; screens_snapshot (parsed
    applyModelApiCode walk) drives componentPresent/binding/navigates. A channel with no
    snapshot falls back to the grounded-channel router (never a fake pass)."""
    # Normalize nav-edge `toScreen` to the spec's screen id: a screen-walk may emit the
    # screen NAME (e.g. "Tasks") while the spec asserts by id ("tasks"). Both are valid
    # references, so map each edge's toScreen through {id|name -> id} before matching.
    if screens_snapshot:
        id_by_key: dict[str, str] = {}
        for s in spec.get("screens", []):
            for key in (s.get("id"), s.get("name")):
                if key:
                    id_by_key[key] = s["id"]
        for entry in screens_snapshot.values():
            for edge in entry.get("nav", []):
                ts = edge.get("toScreen")
                if ts in id_by_key:
                    edge["toScreen"] = id_by_key[ts]

    results: list[LiveResult] = []
    for screen in spec["screens"]:
        for a in screen["acceptance"]["assertions"]:
            results.append(_LIVE_HANDLERS[a["kind"]](a, screen, mcp_config, entities_snapshot, screens_snapshot))
    return results


def _live_exit_code(results: list[LiveResult]) -> int:
    if any(r.status == "fail" for r in results):
        return 1
    if results and all(r.status == "pass" for r in results):
        return 0
    return 3  # anything inconclusive (unconfigured / not-implemented / unverifiable)


def _run_spec_phase(spec_path: Path, as_json: bool) -> int:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"spec is not valid JSON: {e}", file=sys.stderr)
        return 1

    findings = validate_spec(spec)
    gating = [f for f in findings if f.severity == "spec-gap"]

    if as_json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        if not findings:
            print(f"PASS — {spec_path.name} conforms to app_spec.v0 (schema + cross-refs).")
        else:
            print(f"{len(gating)} spec-gap, {len(findings) - len(gating)} advisory finding(s) in {spec_path.name}:\n")
            for f in findings:
                print(f.render())
                print()
    return 1 if gating else 0


def _resolve_mcp_config(explicit: Path | None, spec_path: Path) -> Path | None:
    if explicit is not None:
        return explicit
    for candidate in (Path(".mcp.json"), spec_path.resolve().parent / ".mcp.json"):
        if candidate.exists():
            return candidate
    return None


def _run_live_phase(spec_path: Path, mcp_config: Path | None, as_json: bool, entities_path: Path | None = None,
                    screens_path: Path | None = None) -> int:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"spec is not valid JSON: {e}", file=sys.stderr)
        return 1

    # validate-before-assert: never run live against a structurally broken spec.
    gating = [f for f in validate_spec(spec) if f.severity == "spec-gap"]
    if gating:
        print(f"refusing live phase: {len(gating)} spec-gap finding(s) — fix the spec first "
              f"(run --phase spec).", file=sys.stderr)
        return 1

    snapshot = None
    if entities_path is not None:
        try:
            snapshot = load_entities_snapshot(entities_path)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"--entities snapshot unreadable: {e}", file=sys.stderr)
            return 1

    screens_snap = None
    if screens_path is not None:
        try:
            screens_snap = load_screens_snapshot(screens_path)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"--screens walk snapshot unreadable: {e}", file=sys.stderr)
            return 1

    results = run_live_phase(spec, mcp_config, snapshot, screens_snap)
    if as_json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        by_channel: dict[str, int] = {}
        for r in results:
            by_channel[r.channel] = by_channel.get(r.channel, 0) + 1
        print(f"live phase — {len(results)} assertion(s); channels: "
              f"{', '.join(f'{k}={v}' for k, v in sorted(by_channel.items()))}")
        print(f"entities snapshot: {entities_path or '(none)'} · screens walk: {screens_path or '(none)'}\n")
        for r in results:
            print("  " + r.render())
        missing = []
        if snapshot is None:
            missing.append("--entities <context_entities.json> (entityExists/attribute)")
        if screens_snap is None:
            missing.append("--screens <walk.json> (componentPresent/binding/navigates)")
        if missing:
            print("\nUnsupplied snapshots leave their mcp-channel kinds inconclusive (never a fake pass). Pass: "
                  + "; ".join(missing) + ". integrationExists is by-design unverifiable.")
    return _live_exit_code(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness-verify", description="Validate an app spec, then verify the built ODC app against it.")
    parser.add_argument("spec", type=Path, help="Path to the app spec JSON.")
    parser.add_argument("--phase", choices=["spec", "live", "all"], default="spec",
                        help="spec = schema+cross-ref validation (default); live = per-assertion channel dispatch against the built app; all = spec then live.")
    parser.add_argument("--mcp-config", type=Path, default=None,
                        help="Path to .mcp.json (ODC MCP server). Auto-detected from cwd / spec dir if omitted.")
    parser.add_argument("--entities", type=Path, default=None,
                        help="Path to a context_entities snapshot JSON (fetched by the orchestrator). When given, "
                             "the mcp-channel assertions (entityExists, attribute) are evaluated pass/fail against it.")
    parser.add_argument("--screens", type=Path, default=None,
                        help="Path to a structured applyModelApiCode screen-walk JSON (fetched by the orchestrator). "
                             "When given, componentPresent/binding/navigates are evaluated pass/fail against it (D12).")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    args = parser.parse_args(argv)

    if args.phase == "spec":
        return _run_spec_phase(args.spec, args.json)

    mcp_config = _resolve_mcp_config(args.mcp_config, args.spec)
    if args.phase == "live":
        return _run_live_phase(args.spec, mcp_config, args.json, args.entities, args.screens)

    # phase == all: spec then live. A spec-gap stops before live.
    rc_spec = _run_spec_phase(args.spec, args.json)
    if rc_spec != 0:
        return rc_spec
    print()
    return _run_live_phase(args.spec, mcp_config, args.json, args.entities, args.screens)


if __name__ == "__main__":
    raise SystemExit(main())
