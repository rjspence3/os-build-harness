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

_ID_ATTR = {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}


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


def _core_spec(app: dict, domain_entities: dict) -> dict:
    owns = app.get("owns", [])
    fks = app.get("foreignKeys", []) or []
    entities = [_entity_spec(n, fks, domain_entities) for n in owns]
    exposes = app.get("exposes") or {}
    for st in exposes.get("staticEntities", []) or []:
        entities.append({"name": st, "isStatic": True,
                         "attributes": [dict(_ID_ATTR), {"name": "Label", "dataType": "Text", "mandatory": True}]})
    logic = [{"kind": "serviceAction", "name": sa} for sa in exposes.get("serviceActions", []) or []]
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


def _enduser_spec(app: dict, capabilities: list[dict]) -> dict:
    role = _role_for(app)
    read_entities = _consumed_entities(app)
    screen_names = (app.get("exposes") or {}).get("screens", [])
    screens = []
    for i, s in enumerate(screen_names):
        # bind each screen to a consumed entity round-robin so the app shows real producer data
        ent = read_entities[i % len(read_entities)] if read_entities else None
        screens.append(_list_screen(s, s, ent))
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


def _agent_spec(app: dict) -> dict:
    svc = (app.get("exposes") or {}).get("serviceActions", ["Answer"])[0]
    spec = {
        "specVersion": "0.2",
        "app": {"name": app["name"], "roles": ["User"], "description": "AI Agent (reasoning)"},
        "dataModel": {"entities": []},
        "screens": [],
        "agents": [{"name": svc, "modelConnection": "TrialClaudeHaiku4_5",
                    "systemPrompt": f"You are {app['name']}. Reason over the referenced inputs and return a result."}],
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
    specs: dict[str, dict] = {}
    libraries: list[str] = []
    for app in _apps(system):
        layer = app.get("layer")
        if layer == "foundation":
            libraries.append(app["name"])
        elif layer == "core":
            specs[app["name"]] = _core_spec(app, domain_entities)
        elif layer == "orchestration":
            specs[app["name"]] = (_workflow_spec(app) if app.get("kind") == "BusinessProcess"
                                  else _agent_spec(app))
        elif layer == "enduser":
            specs[app["name"]] = _enduser_spec(app, capabilities)
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
