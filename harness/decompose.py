"""harness-decompose — the architect pass: a flat domain spec -> a modular ODC app topology.

This is the "propose" half of the hybrid decomposition loop (ARCHITECTURE_DECOMPOSITION.md).
`gate.py` accepts one deployed app; `architecture.py` accepts a system topology; THIS turns a flat
domain description into that topology by applying the split rubric mechanically, then self-checks its
own output with `architecture.check_system` (LLM/heuristic proposes, gate disposes — here the proposer
is deterministic so the two run back to back).

It is deliberately DETERMINISTIC (no LLM in v1) so it is testable and reproducible: the fuzzy part —
"where are the bounded-context seams" — is resolved by explicit `context` tags when present, else by
connected-components over the entity reference graph. A later pass can swap in an LLM clusterer; its
output still has to pass the same six invariants.

Input — a flat domain spec (no app boundaries yet):

  {
    "specVersion": "0.1",
    "domain": {
      "name": "retail_platform",
      "entities": [
        {"name": "Product",  "context": "catalog",  "references": ["Category"]},
        {"name": "Order",    "context": "ordering", "references": ["Product"]},   # cross-context ref
        ...
      ],
      "actors": ["shopper", "merchant"],
      "capabilities": [
        {"name": "Checkout", "actor": "shopper", "reads": ["Product"],
         "writes": ["Order"], "service": "PlaceOrder", "raisesEvent": "OrderPlaced"},
        {"name": "Fulfill", "orchestrates": true, "triggerEvent": "OrderPlaced",
         "steps": [{"ai": "ScoreOrderRisk", "reads": ["Order"]},
                   {"callsService": "CapturePayment"}]},
        ...
      ],
      "libraries": ["DesignSystem"]
    }
  }

Output — {system, invariants, modular}: a system topology (system_spec.v0 shape), the gate report on
it, and the boolean verdict.

Rubric applied (see the doc for rationale):
  bounded context      -> one Core app (owns its entities; intra-context refs become FKs, cross-context
                          refs become read-only consumes — never a cross-app FK, OS-DPL-50205)
  actor                -> one End-User app (consumes the Cores its capabilities touch)
  writing capability   -> a Service Action + optional Event exposed by the OWNING Core
  orchestrating cap    -> a Workflow (BPT) app triggered by the event, calling each step's service/agent
  AI step              -> an AI Agent app exposing that service, consuming the relevant Core
  declared library     -> a Foundation library

Usage:
  harness-decompose <domain_spec.json> [--json] [--emit-system <out.json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import architecture


def _domain(spec: dict) -> dict:
    return spec.get("domain") or spec


# ── bounded-context resolution ────────────────────────────────────────────────────────────────────
def _resolve_contexts(entities: list[dict]) -> dict[str, str]:
    """Map each entity name -> its bounded-context tag. Honor explicit `context`; for untagged
    entities, cluster by connected components over the (undirected) reference graph and name each
    component after its lowest-sorted member. Explicit tags always win and are never merged."""
    tagged = {e["name"]: e.get("context") for e in entities}
    names = list(tagged)

    # Union-find over references, but ONLY across untagged entities (explicit tags are authoritative).
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for e in entities:
        if tagged[e["name"]]:
            continue
        for ref in e.get("references", []) or []:
            if ref in parent and not tagged.get(ref):
                union(e["name"], ref)

    out: dict[str, str] = {}
    for n in names:
        if tagged[n]:
            out[n] = tagged[n]
        else:
            root = find(n)
            out[n] = f"ctx_{min(_component_members(parent, root, names))}".lower()
    return out


def _component_members(parent: dict, root: str, names: list[str]) -> list[str]:
    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    return [n for n in names if find(n) == root]


def _pascal(ctx: str) -> str:
    return "".join(p.capitalize() for p in ctx.replace("ctx_", "").replace("-", "_").split("_")) or ctx


# ── the architect pass ────────────────────────────────────────────────────────────────────────────
def decompose(spec: dict) -> dict:
    """Turn a flat domain spec into a system topology + its gate report."""
    dom = _domain(spec)
    entities = dom.get("entities", [])
    caps = dom.get("capabilities", [])
    actors = dom.get("actors", [])
    libraries = dom.get("libraries", [])

    ent_ctx = _resolve_contexts(entities)
    contexts = sorted(set(ent_ctx.values()))
    core_name = {ctx: f"{_pascal(ctx)}Core" for ctx in contexts}
    owner_app = {ent: core_name[ent_ctx[ent]] for ent in ent_ctx}

    apps: dict[str, dict] = {}

    # Foundation libraries.
    for lib in libraries:
        apps[lib] = {"name": lib, "kind": "Library", "layer": "foundation", "exposes": {}}

    # Core apps — one per bounded context.
    for ctx in contexts:
        apps[core_name[ctx]] = {
            "name": core_name[ctx], "kind": "WebApplication", "layer": "core", "context": ctx,
            "owns": [], "exposes": {"serviceActions": [], "events": [], "staticEntities": []},
            "foreignKeys": [], "consumes": [],
        }
    # Ownership + FK/consume split for entity references.
    consume_ents: dict[tuple[str, str], set] = {}  # (consumer_core, producer_core) -> {entities}
    for e in entities:
        name = e["name"]
        core = apps[owner_app[name]]
        core["owns"].append(name)
        for ref in e.get("references", []) or []:
            if ref not in owner_app:
                continue
            if owner_app[ref] == owner_app[name]:
                core["foreignKeys"].append({"from": name, "target": ref})  # intra-context -> real FK
            else:
                consume_ents.setdefault((owner_app[name], owner_app[ref]), set()).add(ref)  # cross -> consume

    # Writing capabilities -> Service Actions + Events on the owning Core.
    for cap in caps:
        if cap.get("orchestrates"):
            continue
        for ent in cap.get("writes", []) or []:
            if ent not in owner_app:
                continue
            core = apps[owner_app[ent]]
            svc = cap.get("service") or f"{cap['name']}"
            if svc not in core["exposes"]["serviceActions"]:
                core["exposes"]["serviceActions"].append(svc)
            ev = cap.get("raisesEvent")
            if ev and ev not in core["exposes"]["events"]:
                core["exposes"]["events"].append(ev)

    # AI steps -> Agent apps (one per distinct service name).
    agent_of_service: dict[str, str] = {}
    for cap in caps:
        for step in cap.get("steps", []) or []:
            ai_svc = step.get("ai")
            if not ai_svc or ai_svc in agent_of_service:
                continue
            agent_name = ai_svc if ai_svc.endswith("Agent") else f"{ai_svc}Agent"
            agent_of_service[ai_svc] = agent_name
            reads_core = _cores_for_entities(step.get("reads", []), owner_app)
            apps[agent_name] = {
                "name": agent_name, "kind": "AIAgent", "layer": "orchestration",
                "exposes": {"serviceActions": [ai_svc]},
                "consumes": [_consume(c, entities=list(ents)) for c, ents in reads_core.items()],
            }

    # Orchestrating capabilities -> Workflow (BPT) apps.
    for cap in caps:
        if not cap.get("orchestrates"):
            continue
        wf_name = cap["name"] if cap["name"].endswith("Workflow") else f"{cap['name']}Workflow"
        trigger = cap.get("triggerEvent")
        trigger_core = _core_raising_event(apps, trigger)
        consumes: list[dict] = []
        activities = []
        if trigger_core:
            consumes.append(_consume(trigger_core, events=[trigger]))
        for step in cap.get("steps", []) or []:
            if step.get("ai"):
                svc = step["ai"]
                activities.append({"name": step.get("name", svc), "callsServiceAction": svc})
                consumes.append(_consume(agent_of_service[svc], serviceActions=[svc]))
            elif step.get("callsService"):
                svc = step["callsService"]
                prod = _core_exposing_service(apps, svc)
                activities.append({"name": step.get("name", svc), "callsServiceAction": svc})
                if prod:
                    consumes.append(_consume(prod, serviceActions=[svc]))
        apps[wf_name] = {
            "name": wf_name, "kind": "BusinessProcess", "layer": "orchestration",
            "process": {"triggerEvent": trigger,
                        "startProcessOn": f"{trigger_core}.{trigger}" if trigger_core else trigger},
            "activities": activities, "consumes": _merge_consumes(consumes),
        }

    # End-user apps — one per actor. Consume every Core its capabilities touch.
    for actor in actors:
        touched: dict[str, dict] = {}
        for cap in caps:
            if cap.get("actor") != actor:
                continue
            for ent in (cap.get("reads", []) or []) + (cap.get("writes", []) or []):
                if ent not in owner_app:
                    continue
                c = owner_app[ent]
                touched.setdefault(c, {"entities": set(), "serviceActions": set()})["entities"].add(ent)
            for ent in cap.get("writes", []) or []:
                if ent in owner_app:
                    svc = cap.get("service") or cap["name"]
                    touched[owner_app[ent]]["serviceActions"].add(svc)
        consumes = [_consume(c, entities=sorted(v["entities"]), serviceActions=sorted(v["serviceActions"]))
                    for c, v in sorted(touched.items())]
        # In-app agent calls: a NON-orchestrating capability with an AI step is the "Call Agent"
        # pattern (agent embedded in a screen) — the actor's app consumes that agent's service action.
        # (An AI step inside an ORCHESTRATING capability is driven by the Workflow instead, not here.)
        agent_calls: dict[str, set] = {}
        for cap in caps:
            if cap.get("actor") != actor or cap.get("orchestrates"):
                continue
            for step in cap.get("steps", []) or []:
                svc = step.get("ai")
                if svc and svc in agent_of_service:
                    agent_calls.setdefault(agent_of_service[svc], set()).add(svc)
        for agent_app, svcs in sorted(agent_calls.items()):
            consumes.append(_consume(agent_app, serviceActions=sorted(svcs)))
        for lib in libraries:
            consumes.append(_consume(lib))
        apps[actor_app_name(actor)] = {
            "name": actor_app_name(actor), "kind": "WebApplication", "layer": "enduser",
            "actor": actor, "exposes": {"screens": _screens_for_actor(caps, actor)},
            "consumes": consumes,
        }

    # Cores consume cross-context entities they reference; Cores consume libraries too (optional: skip).
    for (consumer_core, producer_core), ents in consume_ents.items():
        apps[consumer_core]["consumes"].append(_consume(producer_core, entities=sorted(ents)))

    ordered = _order_apps(apps)
    system = {"specVersion": "0.1",
              "system": {"name": dom.get("name", "system"), "apps": ordered}}
    rows = architecture.check_system(system)
    return {"system": system, "invariants": rows, "modular": architecture.verdict(rows)}


# ── small builders / lookups ──────────────────────────────────────────────────────────────────────
def actor_app_name(actor: str) -> str:
    return "".join(p.capitalize() for p in actor.replace("-", "_").split("_")) + "App"


def _consume(app: str, *, entities=None, staticEntities=None, serviceActions=None, events=None) -> dict:
    d = {"app": app}
    if entities:
        d["entities"] = list(entities)
    if staticEntities:
        d["staticEntities"] = list(staticEntities)
    if serviceActions:
        d["serviceActions"] = list(serviceActions)
    if events:
        d["events"] = list(events)
    return d


def _merge_consumes(consumes: list[dict]) -> list[dict]:
    """Fold multiple consume entries for the same producer into one."""
    by_app: dict[str, dict] = {}
    for c in consumes:
        tgt = by_app.setdefault(c["app"], {"app": c["app"]})
        for k in ("entities", "staticEntities", "serviceActions", "events"):
            if c.get(k):
                tgt[k] = sorted(set(tgt.get(k, [])) | set(c[k]))
    return list(by_app.values())


def _cores_for_entities(ents: list[str], owner_app: dict) -> dict[str, set]:
    out: dict[str, set] = {}
    for e in ents or []:
        if e in owner_app:
            out.setdefault(owner_app[e], set()).add(e)
    return out


def _core_raising_event(apps: dict, event: str | None) -> str | None:
    if not event:
        return None
    for a in apps.values():
        if event in (a.get("exposes") or {}).get("events", []):
            return a["name"]
    return None


def _core_exposing_service(apps: dict, svc: str) -> str | None:
    for a in apps.values():
        if svc in (a.get("exposes") or {}).get("serviceActions", []):
            return a["name"]
    return None


def _screens_for_actor(caps: list[dict], actor: str) -> list[str]:
    return [c["name"] for c in caps if c.get("actor") == actor]


def _order_apps(apps: dict) -> list[dict]:
    """Emit apps in build order: foundation -> core -> orchestration -> enduser (producers first)."""
    rank = {"foundation": 0, "core": 1, "orchestration": 2, "enduser": 3}
    return [apps[k] for k in sorted(apps, key=lambda n: (rank.get(apps[n]["layer"], 9), n))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-decompose",
        description="Architect pass: turn a flat domain spec into a modular ODC app topology and "
                    "self-check it against the six no-monolith invariants.")
    ap.add_argument("domain", type=Path, help="flat domain_spec.json")
    ap.add_argument("--emit-system", type=Path, default=None,
                    help="write the proposed system_spec.json here")
    ap.add_argument("--json", action="store_true", help="emit the full result as JSON")
    args = ap.parse_args(argv)

    if not args.domain.exists():
        print(f"domain spec not found: {args.domain}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(args.domain.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"domain spec is not valid JSON: {e}", file=sys.stderr)
        return 2

    result = decompose(spec)
    if args.emit_system:
        args.emit_system.write_text(json.dumps(result["system"], indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        sysd = result["system"]["system"]
        print(f"harness-decompose — {sysd['name']}: "
              f"{'✅ MODULAR' if result['modular'] else '❌ MONOLITH'} "
              f"({len(sysd['apps'])} apps)")
        for a in sysd["apps"]:
            owns = f" owns={a['owns']}" if a.get("owns") else ""
            print(f"  · {a['layer']:<13} {a['name']}{owns}")
        for r in result["invariants"]:
            if r["status"] == "FAIL":
                print(f"  [FAIL] {r['gate']}: {r['results']}")
    return 0 if result["modular"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
