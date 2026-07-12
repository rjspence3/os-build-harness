"""harness-expand — expand a system topology into one app_spec.v0 per app.

The final bridge in the modular pipeline: `decompose.py` turned a flat domain into a `system.apps`
topology, `architecture.py` proved it modular; THIS turns each app node into an `app_spec.v0` document
the existing per-app build loop (`plan_from_spec` + `BUILD_LOOP`) already knows how to build. The
cross-app WIRING is the whole point — it maps the topology's `owns` / `exposes` / `consumes` onto the
app_spec fields that were built for exactly this (`dataModel`, `logic`, `appReferences`, `processes`,
`agents`):

  Core (service)   layer=core          -> dataModel.entities (owned, with intra-context FKs) +
                                          logic (serviceAction per exposed SA, globalEvent per event) +
                                          appReferences (cross-context entity reads); NO screens
  End-User         layer=enduser       -> appReferences (consumed entities/SAs/statics) + screens
                                          (one per capability, placeholder-bound for now); owns NO entities
  Workflow (BPT)   layer=orchestration -> processes (trigger event + activities) + appReferences (step SAs)
  AI Agent         layer=orchestration -> agents (systemPrompt/model/tools) + appReferences (reads + SAs)
  Library          layer=foundation    -> NOT an app_spec; returned in `libraries` (own recipe path)

The two shapes a monolith never needed — a service app (entities, no screens) and a consumer app
(references + screens, no owned entities) — are why app_spec.v0.2 relaxed dataModel/screens to
minItems 0. A cross-context reference becomes an appReference (read-only), NEVER a local FK — the
FK-vs-consume split was already resolved by decompose (OS-DPL-50205). Data-BOUND consumer screens
need harness-verify to accept appReference entities as binding targets — a flagged v2 seam; v1 emits
non-binding placeholder screens so every produced spec passes verify.validate_spec as-is.

Usage:
  harness-expand <system_spec.json> [--domain <domain_spec.json>] [--out-dir DIR] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import architecture
from harness.prompt_recipes import _ENGINE_ACTIONS, _ENGINE_ENTITY_DEFAULTS

_ID_ATTR = {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}

# ── workflow-engine / dynamic-form / library-import detector helpers ──────────
# All helpers are pure, never raise, and return empty/False on missing data.

_LIBRARY_ENTITY_ORDER = ["TaskTemplate", "Scenario", "ScenarioStep", "TransitionRule", "DecisionRow"]


def _engine_actions_for_core(owns: list[str], capabilities: list[dict]) -> list[str]:
    """Return engine action names that belong on this Core (owns ∩ cap reads/writes non-empty),
    in canonical _ENGINE_ACTIONS order. Never raises; returns [] on empty/missing data.

    Collection logic (D3):
      (a) Caps whose service ∈ _ENGINE_ACTIONS AND (reads ∪ writes) ∩ owns is non-empty.
      (b) Orchestration steps whose callsService ∈ _ENGINE_ACTIONS (picks up InstantiateWorkflow etc.)
      (c) Orchestration cap names that are themselves ∈ _ENGINE_ACTIONS (picks up EscalateOverdue).
    """
    if not owns or not capabilities:
        return []
    owns_set = set(owns)
    engine_set = set(_ENGINE_ACTIONS)
    found_a: set[str] = set()    # (a) top-level engine service caps, OWNS-GATED on their own entities
    found_bc: set[str] = set()   # (b)/(c) orchestration references — no entity of their own to owns-gate

    for cap in capabilities or []:
        # (a) regular cap with a service field, gated on owning one of its read/write entities
        svc = cap.get("service")
        if svc and svc in engine_set:
            entity_refs = set(cap.get("reads") or []) | set(cap.get("writes") or [])
            if entity_refs & owns_set:
                found_a.add(svc)
        # (b) orchestration callsService steps (e.g. InstantiateWorkflow, referenced only here)
        for step in cap.get("steps") or []:
            cs = step.get("callsService")
            if cs and cs in engine_set:
                found_bc.add(cs)
        # (c) orchestration cap name itself is an engine action (e.g. EscalateOverdue)
        if cap.get("orchestrates") and cap.get("name") in engine_set:
            found_bc.add(cap["name"])

    # (b)/(c) are orchestration references with no entity of their own to owns-gate. Attribute them to
    # the ENGINE Core ONLY — the Core that already owns >=1 top-level engine service cap (found_a). Without
    # this gate a MULTI-Core workflow domain would stamp InstantiateWorkflow/EscalateOverdue onto every
    # Core, not just the one owning the workflow entities (FIX-001). Single-engine-Core is unaffected.
    found = found_a | (found_bc if found_a else set())
    return [a for a in _ENGINE_ACTIONS if a in found]


def _engine_entity_map(owns: list[str]) -> dict[str, str]:
    """Return role->entity-name map for roles whose default entity is owned by this Core.
    Roles whose default is not in owns are omitted (recipe _en() falls back to defaults).
    Returns {} on empty/missing data (D5)."""
    if not owns:
        return {}
    owns_set = set(owns)
    return {role: default for role, default in _ENGINE_ENTITY_DEFAULTS.items()
            if default in owns_set}


def _library_entities_for_core(owns: list[str]) -> list[str]:
    """Return library entity names owned by this Core, in FK parent-before-child order (D10).
    Returns [] if none of the canonical 5 are owned."""
    if not owns:
        return []
    owns_set = set(owns)
    return [e for e in _LIBRARY_ENTITY_ORDER if e in owns_set]


def _has_bulk_load_integration(domain: dict | None) -> bool:
    """Return True when the domain declares a consume-kind integration whose purpose
    mentions 'bulk-load' (case-insensitive). Returns False when domain is None (D9)."""
    if not domain:
        return False
    dom = (domain.get("domain") or domain)
    for integ in dom.get("integrations") or []:
        if (integ.get("kind") == "consume"
                and "bulk-load" in (integ.get("purpose") or "").lower()):
            return True
    return False


def _task_screen_ids(capabilities: list[dict], domain_entities: dict, actor: str | None) -> list[str]:
    """Return capability names (= screen ids) for task screens that should get a dynamicForm.

    A task screen = a capability where:
      - cap.actor == actor
      - cap.reads includes a TaskTemplate-role entity (has FieldDefinition attribute)
      - cap.reads includes a TaskInstance-role entity: an entity that references BOTH the template
        entity AND a workflow-instance-like entity (has WorkflowInstance in its references)

    The dual-reference requirement (template + workflow-instance) distinguishes a task runtime screen
    (TaskInstance) from a library-management screen (ScenarioStep, which references TaskTemplate but
    not a WorkflowInstance-like entity). (D8)
    """
    if not actor or not capabilities:
        return []
    result = []
    for cap in capabilities:
        if cap.get("actor") != actor:
            continue
        reads = set(cap.get("reads") or [])
        if len(reads) < 2:
            continue
        # Find the template entity (has FieldDefinition attribute)
        template_name = None
        for ent_name in reads:
            ent = domain_entities.get(ent_name) or {}
            if any(a.get("name") == "FieldDefinition" for a in (ent.get("attributes") or [])):
                template_name = ent_name
                break
        if not template_name:
            continue
        # Find the instance entity: references BOTH the template AND a WorkflowInstance-like entity
        # (i.e. an entity that has a WorkflowInstance reference — distinguishes TaskInstance from ScenarioStep)
        instance_name = None
        for ent_name in reads:
            if ent_name == template_name:
                continue
            ent = domain_entities.get(ent_name) or {}
            refs = set(ent.get("references") or [])
            # Must reference the template AND at least one entity that itself has a WorkflowInstance ref
            # or is a "workflow_instance"-role entity.
            if template_name not in refs:
                continue
            # Also verify this entity references something workflow-instance-like (not just library entities)
            workflow_instance_default = _ENGINE_ENTITY_DEFAULTS.get("workflow_instance", "WorkflowInstance")
            if workflow_instance_default in refs:
                instance_name = ent_name
                break
        if template_name and instance_name:
            result.append(cap["name"])
    return result


def _apps(system: dict) -> list[dict]:
    return (system.get("system") or system).get("apps", [])


def _domain_entities(domain: dict | None) -> dict[str, dict]:
    if not domain:
        return {}
    return {e["name"]: e for e in (domain.get("domain") or domain).get("entities", [])}


def _role_for(app: dict) -> str:
    actor = app.get("actor")
    if actor:
        return "".join(p.capitalize() for p in actor.replace("-", "_").split("_"))
    return "User"


# ── per-layer builders ────────────────────────────────────────────────────────────────────────────
def _entity_spec(name: str, fks: list[dict], domain_entities: dict) -> dict:
    """An app_spec entity for an OWNED entity: Id identifier + domain attributes + intra-context FKs."""
    attrs = [dict(_ID_ATTR)]
    for a in (domain_entities.get(name) or {}).get("attributes", []) or []:
        attrs.append({k: v for k, v in a.items() if k in
                      ("name", "dataType", "mandatory", "isIdentifier", "length", "decimals", "description", "default")})
    if len(attrs) == 1:  # no domain attributes -> a minimal display field so the entity is buildable
        attrs.append({"name": "Name", "dataType": "Text", "mandatory": True})
    for fk in fks:
        if fk.get("from") == name:
            attrs.append({"name": f"{fk['target']}Id", "dataType": "Identifier",
                          "references": fk["target"], "mandatory": False})
    return {"name": name, "attributes": attrs}


def _app_references(consumes: list[dict]) -> list[dict]:
    """Cross-app consumes -> app_spec appReferences (Entity / StaticEntity / ServiceAction elements).
    Events are wired via the process block, not appReferences (no GlobalEvent element kind)."""
    refs = []
    for c in consumes or []:
        elements = []
        for e in c.get("entities", []) or []:
            elements.append({"name": e, "kind": "Entity"})
        for e in c.get("staticEntities", []) or []:
            elements.append({"name": e, "kind": "StaticEntity"})
        for s in c.get("serviceActions", []) or []:
            elements.append({"name": s, "kind": "ServiceAction"})
        if elements:
            refs.append({"producerApp": c["app"], "elements": elements})
    return refs


def _core_spec(app: dict, domain_entities: dict,
               capabilities: list[dict] | None = None,
               bulk_load: bool = False) -> dict:
    owns = app.get("owns", [])
    fks = app.get("foreignKeys", []) or []
    entities = [_entity_spec(n, fks, domain_entities) for n in owns]
    exposes = app.get("exposes") or {}
    for st in exposes.get("staticEntities", []) or []:
        entities.append({"name": st, "isStatic": True,
                         "attributes": [dict(_ID_ATTR), {"name": "Label", "dataType": "Text", "mandatory": True}]})

    # Detect engine actions BEFORE building logic so we can remove duplicates (D4).
    engine_actions = _engine_actions_for_core(owns, capabilities or [])
    engine_names = set(engine_actions)

    logic = [{"kind": "serviceAction", "name": sa} for sa in exposes.get("serviceActions", []) or []
             if sa not in engine_names]
    logic += [{"kind": "globalEvent", "name": ev} for ev in exposes.get("events", []) or []]
    spec = {
        "specVersion": "0.2",
        "app": {"name": app["name"], "roles": ["User"],
                "description": f"Core service ({app.get('context', '?')} context)"},
        # A Core is a data-owning producer: EXPOSE its entities (Public=Yes) so the consumer apps that
        # reference it can actually READ its data. Without this, app-reference imports nothing and every
        # consumer screen renders empty (the modular producer→consumer data flow silently breaks).
        "dataModel": {"entities": entities, "public": True},
        "screens": [],
    }
    if logic:
        spec["logic"] = logic
    refs = _app_references(app.get("consumes", []))
    if refs:
        spec["appReferences"] = refs

    # Stamp engine block when this Core owns engine capabilities (D2, D3, D5, D6).
    if engine_actions:
        spec["engine"] = {
            "coreApp": app["name"],
            "actions": engine_actions,
            "entities": _engine_entity_map(owns),
        }

    # Stamp libraryImport when this Core owns library entities AND the domain has a bulk-load integration (D9, D10).
    if bulk_load:
        lib_ents = _library_entities_for_core(owns)
        if lib_ents:
            spec["libraryImport"] = {"mode": "seed", "libraryEntities": lib_ents}

    return spec


def _list_screen(sid: str, name: str, entity: str | None) -> dict:
    """A consumer screen. When it has a consumed entity to show, it binds a Table to that (referenced)
    entity — verify now accepts appReference entities as binding targets — else a titled placeholder."""
    if entity:
        comp_id = f"{sid}_{entity.lower()}_table"
        return {"id": sid, "name": name,
                "components": [{"id": comp_id, "type": "Table", "boundTo": entity, "label": name}],
                "acceptance": {"assertions": [
                    {"kind": "componentPresent", "componentId": comp_id},
                    {"kind": "binding", "componentId": comp_id, "boundTo": entity}]}}
    return {"id": sid, "name": name,
            "components": [{"id": f"{sid}_title", "type": "Label", "label": name}],
            "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": f"{sid}_title"}]}}


def _consumed_entities(app: dict) -> list[str]:
    out = []
    for c in app.get("consumes", []) or []:
        out.extend(c.get("entities", []) or [])
    return out


def _enduser_spec(app: dict, capabilities: list[dict],
                  domain_entities: dict | None = None) -> dict:
    role = _role_for(app)
    read_entities = _consumed_entities(app)
    screen_names = (app.get("exposes") or {}).get("screens", [])

    # Detect task screens for dynamic-form stamping (D7, D8).
    task_screen_set = set(_task_screen_ids(capabilities, domain_entities or {}, app.get("actor")))

    # Build a lookup from domain entities for task screen details.
    # For a task screen we need to know: which entity is the template (has FieldDefinition)
    # and which is the instance (references the template).
    def _task_form_info(cap_name: str) -> dict | None:
        """Return {taskInstance, taskTemplate, completeAction} for a task screen cap, or None."""
        cap = next((c for c in (capabilities or []) if c.get("name") == cap_name), None)
        if not cap:
            return None
        de = domain_entities or {}
        reads = cap.get("reads") or []
        template_name = None
        instance_name = None
        for ent_name in reads:
            ent = de.get(ent_name) or {}
            if any(a.get("name") == "FieldDefinition" for a in (ent.get("attributes") or [])):
                template_name = ent_name
        for ent_name in reads:
            if ent_name == template_name:
                continue
            ent = de.get(ent_name) or {}
            refs = ent.get("references") or []
            if template_name and template_name in refs:
                instance_name = ent_name
                break
        if template_name and instance_name:
            return {"taskInstance": instance_name, "taskTemplate": template_name,
                    "completeAction": "CompleteTask"}
        return None

    screens = []
    for i, s in enumerate(screen_names):
        # bind each screen to a consumed entity round-robin so the app shows real producer data
        ent = read_entities[i % len(read_entities)] if read_entities else None
        screen = _list_screen(s, s, ent)
        # Stamp dynamicForm when this screen is a task screen (D7, D8).
        if s in task_screen_set:
            info = _task_form_info(s)
            if info:
                screen["dynamicForm"] = info
        screens.append(screen)
    if not screens:
        screens = [_list_screen("home", "Home", read_entities[0] if read_entities else None)]
    if screens:
        screens[0]["isDefault"] = True
    spec = {
        "specVersion": "0.2",
        "app": {"name": app["name"], "roles": [role],
                "description": f"End-user app for {app.get('actor', role)}"},
        "dataModel": {"entities": []},
        "screens": screens,
    }
    refs = _app_references(app.get("consumes", []))
    if refs:
        spec["appReferences"] = refs
    return spec


def _workflow_spec(app: dict) -> dict:
    proc = app.get("process") or {}
    trigger = proc.get("triggerEvent")
    # producer of the trigger event = the app whose consume carries that event
    producer = None
    for c in app.get("consumes", []) or []:
        if trigger and trigger in (c.get("events") or []):
            producer = c["app"]
            break
    process = {"name": app["name"].replace("Workflow", "") + "Process" if app["name"].endswith("Workflow") else app["name"] + "Process",
               "producerApp": producer or (proc.get("startProcessOn", "").split(".")[0] or "Unknown"),
               "triggerEvent": trigger,
               "activities": [{"name": a.get("name", a.get("callsServiceAction", "step")),
                               "callsServiceAction": a.get("callsServiceAction")}
                              for a in app.get("activities", []) if a.get("callsServiceAction")]}
    spec = {
        "specVersion": "0.2",
        "app": {"name": app["name"], "roles": ["User"], "description": "Business process (BPT orchestration)"},
        "dataModel": {"entities": []},
        "screens": [],
        "processes": [process],
    }
    # SAs the activities call become appReferences (the trigger event is carried by the process block).
    sa_consumes = [c for c in app.get("consumes", []) or [] if c.get("serviceActions")]
    refs = _app_references(sa_consumes)
    if refs:
        spec["appReferences"] = refs
    return spec


def _consumed_service_actions(app: dict) -> list[str]:
    out = []
    for c in app.get("consumes", []) or []:
        out.extend(c.get("serviceActions", []) or [])
    return out


def _agent_spec(app: dict) -> dict:
    svc = (app.get("exposes") or {}).get("serviceActions", ["Answer"])[0]
    # An agent that consumes producer entities MUST ground on them, and consumed producer service actions
    # become its tools — otherwise it 'reasons' with no data / no actions (the #1 agent failure mode).
    grounding = _consumed_entities(app)
    tools = _consumed_service_actions(app)
    ground_line = (f" Ground every answer in the referenced data ({', '.join(grounding)}) — never answer "
                   f"without first retrieving it." if grounding else "")
    tool_line = (f" Use your tools ({', '.join(tools)}) to take actions when needed." if tools else "")
    spec = {
        "specVersion": "0.2",
        "app": {"name": app["name"], "roles": ["User"], "description": "AI Agent (reasoning)"},
        "dataModel": {"entities": []},
        "screens": [],
        "agents": [{"name": svc, "modelConnection": "TrialClaudeHaiku4_5",
                    "systemPrompt": (f"You are {app['name']}. Reason over the referenced inputs and return a "
                                     f"result.{ground_line}{tool_line}"),
                    "grounding": grounding, "tools": tools}],
    }
    refs = _app_references(app.get("consumes", []))
    if refs:
        spec["appReferences"] = refs
    return spec


# ── the expansion ─────────────────────────────────────────────────────────────────────────────────
def expand_system(system: dict, domain: dict | None = None) -> dict:
    """Return {"specs": {app_name: app_spec}, "libraries": [names]}.
    Each spec is app_spec.v0.2-valid; libraries are returned separately (own recipe path)."""
    domain_entities = _domain_entities(domain)
    capabilities = (domain.get("domain") or domain).get("capabilities", []) if domain else []
    # Compute once: does the domain have a bulk-load integration? (D9, guards None domain)
    bulk_load = _has_bulk_load_integration(domain)
    specs: dict[str, dict] = {}
    libraries: list[str] = []
    for app in _apps(system):
        layer = app.get("layer")
        if layer == "foundation":
            libraries.append(app["name"])
        elif layer == "core":
            specs[app["name"]] = _core_spec(app, domain_entities, capabilities, bulk_load)
        elif layer == "orchestration":
            specs[app["name"]] = (_workflow_spec(app) if app.get("kind") == "BusinessProcess"
                                  else _agent_spec(app))
        elif layer == "enduser":
            specs[app["name"]] = _enduser_spec(app, capabilities, domain_entities)
    return {"specs": specs, "libraries": libraries}


def build_order(system: dict) -> list[str]:
    """App build order: foundation -> core -> orchestration -> enduser (producers before consumers)."""
    rank = {"foundation": 0, "core": 1, "orchestration": 2, "enduser": 3}
    return [a["name"] for a in sorted(_apps(system), key=lambda a: (rank.get(a.get("layer"), 9), a["name"]))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-expand",
        description="Expand a system topology into one app_spec.v0 per app (Core/End-User/Workflow/Agent), "
                    "wiring cross-app dependencies onto appReferences/processes/agents/logic.")
    ap.add_argument("system", type=Path, help="system_spec.json topology")
    ap.add_argument("--domain", type=Path, default=None, help="flat domain_spec.json (for entity attributes)")
    ap.add_argument("--out-dir", type=Path, default=None, help="write one <AppName>.app_spec.json per app here")
    ap.add_argument("--json", action="store_true", help="print the {specs, libraries} result as JSON")
    args = ap.parse_args(argv)

    if not args.system.exists():
        print(f"system spec not found: {args.system}", file=sys.stderr)
        return 2
    system = json.loads(args.system.read_text(encoding="utf-8"))
    domain = json.loads(args.domain.read_text(encoding="utf-8")) if args.domain and args.domain.exists() else None

    # A courtesy check: the topology should be modular before we expand it.
    modular = architecture.verdict(architecture.check_system(system))
    result = expand_system(system, domain)

    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for name, spec in result["specs"].items():
            (args.out_dir / f"{name}.app_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        sysd = (system.get("system") or system)
        print(f"harness-expand — {sysd.get('name', args.system.name)}: "
              f"{len(result['specs'])} app_spec(s)"
              + (f", {len(result['libraries'])} librar(y/ies)" if result["libraries"] else "")
              + (" — topology MODULAR" if modular else " — ⚠ topology NOT modular (run harness-arch-gate)"))
        for name in build_order(system):
            if name in result["specs"]:
                s = result["specs"][name]
                bits = []
                if s["dataModel"]["entities"]:
                    bits.append(f"{len(s['dataModel']['entities'])} entities")
                if s.get("logic"):
                    bits.append(f"{len(s['logic'])} logic")
                if s.get("appReferences"):
                    bits.append(f"{len(s['appReferences'])} refs")
                if s.get("processes"):
                    bits.append("process")
                if s.get("agents"):
                    bits.append("agent")
                if s["screens"]:
                    bits.append(f"{len(s['screens'])} screens")
                print(f"  · {name}: {', '.join(bits)}")
            elif name in result["libraries"]:
                print(f"  · {name}: library (recipe path)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
