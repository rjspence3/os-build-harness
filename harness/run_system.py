"""harness-run-system — the multi-app orchestration planner (top of the modular pipeline).

`plan_from_spec` plans ONE app's build. This plans a WHOLE SYSTEM's build: it composes the modular
pipeline end to end — decompose (if given a flat domain) -> arch-gate -> expand -> plan_from_spec per
app — into a single topo-ordered master plan a driving session executes, producer-before-consumer.

It is a PLANNER, not an executor: the actual Mentor authoring is the session's job (OAuth is
interactive; see BUILD_LOOP.md RUN MODEL). The plan encodes everything deterministic so execution is
mechanical: the build ORDER (a real topological sort over the consume DAG, not just layer rank, so a
Core that consumes another Core still builds after it), each app's `app_create` KIND, its per-app
authoring STEPS, its LIFECYCLE (the create->author->publish sequencing proven live — including the BPT
special case where app_create does NOT auto-publish and you publish ONCE with the process present), and
the cross-app GATES (an app's producers must be published before its phase runs).

It REFUSES to plan a monolith: the six no-monolith invariants (architecture.check_system) run first as
a precondition. A non-modular topology returns the gate failures and a nonzero exit — you cannot
orchestrate a build the architecture gate rejects.

Usage:
  harness-run-system <system.json>            [--emit-plan plan.json] [--json]
  harness-run-system <domain.json> --domain   [--emit-plan plan.json] [--json]   # decompose first
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import architecture, decompose, expand
from harness.prompt_recipes import plan_from_spec

_LAYER_RANK = {"foundation": 0, "core": 1, "orchestration": 2, "enduser": 3}

# app_create kind per app (the topology already carries `kind`; this is the fallback per layer).
_DEFAULT_KIND = {"foundation": "Library", "core": "WebApplication",
                 "orchestration": "AIAgent", "enduser": "WebApplication"}

# The create->author->publish lifecycle per ODC kind, encoding the sequencing proven live this program.
_LIFECYCLE = {
    "Library": ["app_create(Library)", "author(library recipe)", "publish", "release(version)"],
    "WebApplication": ["app_create(WebApplication)", "author(steps)", "publish", "gate"],
    "Mobile": ["app_create(Mobile)", "author(steps)", "publish", "gate"],
    "MobileApplication": ["app_create(Mobile)", "author(steps)", "publish", "gate"],
    "AIAgent": ["app_create(AIAgent)", "author(agent+BuildMessages+AgentFlow+bindModel)", "publish", "gate"],
    "BusinessProcess": ["app_create(BusinessProcess: NO auto-publish — safe window)",
                        "author(refs+process in ONE turn)",
                        "publish(ONCE, process present — 0-process publish corrupts verify cache)", "gate"],
}


def _apps(system: dict) -> list[dict]:
    return (system.get("system") or system).get("apps", [])


def _producers(app: dict) -> list[str]:
    """The apps this one depends on (must be published first): every producer it consumes from."""
    seen, out = set(), []
    for c in app.get("consumes", []) or []:
        p = c.get("app")
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def topo_order(system: dict) -> list[str]:
    """Kahn topological sort over the consume DAG (producer -> consumer), breaking ties by
    (layer rank, name) for determinism. The architecture gate guarantees the graph is acyclic;
    if a cycle somehow remains, the leftover nodes are appended in priority order (never dropped)."""
    apps = {a["name"]: a for a in _apps(system)}
    producers = {n: [p for p in _producers(a) if p in apps] for n, a in apps.items()}
    indeg = {n: len(set(producers[n])) for n in apps}

    def priority(n: str):
        return (_LAYER_RANK.get(apps[n].get("layer"), 9), n)

    ready = sorted([n for n, d in indeg.items() if d == 0], key=priority)
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in apps:
            if n in producers[m]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
        ready.sort(key=priority)
    # any nodes left (would indicate a cycle the gate should have caught) — append deterministically
    for n in sorted(set(apps) - set(order), key=priority):
        order.append(n)
    return order


def _kind_of(app: dict) -> str:
    return app.get("kind") or _DEFAULT_KIND.get(app.get("layer"), "WebApplication")


def plan_system(system: dict, domain: dict | None = None) -> dict:
    """Compose the whole-system build plan. Returns
    {modular, invariants, order, phases:[{app,layer,kind,dependsOn,lifecycle,stepCount,steps}]}.
    When not modular, phases is empty (you don't orchestrate a monolith)."""
    rows = architecture.check_system(system)
    modular = architecture.verdict(rows)
    result = {"modular": modular, "invariants": rows, "order": [], "phases": []}
    if not modular:
        return result

    exp = expand.expand_system(system, domain)
    specs, libraries = exp["specs"], set(exp["libraries"])
    by_name = {a["name"]: a for a in _apps(system)}
    order = topo_order(system)
    result["order"] = order

    phases = []
    for name in order:
        app = by_name[name]
        kind = _kind_of(app)
        depends = _producers(app)
        if name in libraries:
            phases.append({"app": name, "layer": app.get("layer"), "kind": "Library",
                           "dependsOn": depends, "lifecycle": _LIFECYCLE["Library"],
                           "stepCount": 0, "steps": []})
            continue
        spec = specs.get(name)
        steps = plan_from_spec(spec) if spec else []
        phases.append({"app": name, "layer": app.get("layer"), "kind": kind,
                       "dependsOn": depends,
                       "lifecycle": _LIFECYCLE.get(kind, _LIFECYCLE["WebApplication"]),
                       "stepCount": len(steps), "steps": steps})
    result["phases"] = phases
    return result


def plan_from_domain(domain: dict) -> dict:
    """Full pipeline from a flat domain spec: decompose -> plan_system."""
    system = decompose.decompose(domain)["system"]
    return plan_system(system, domain)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-run-system",
        description="Plan a whole modular system's build: topo-ordered per-app phases with app_create "
                    "kind, authoring steps, create->author->publish lifecycle, and cross-app gates. "
                    "Refuses to plan a monolith.")
    ap.add_argument("spec", type=Path, help="system_spec.json, or a flat domain_spec.json with --domain")
    ap.add_argument("--domain", action="store_true", help="treat <spec> as a flat domain spec (decompose first)")
    ap.add_argument("--emit-plan", type=Path, default=None, help="write the master plan JSON here")
    ap.add_argument("--json", action="store_true", help="print the full plan as JSON")
    args = ap.parse_args(argv)

    if not args.spec.exists():
        print(f"spec not found: {args.spec}", file=sys.stderr)
        return 2
    doc = json.loads(args.spec.read_text(encoding="utf-8"))
    plan = plan_from_domain(doc) if args.domain else plan_system(doc, None)

    if args.emit_plan:
        args.emit_plan.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        if not plan["modular"]:
            print("harness-run-system: ❌ topology is a MONOLITH — refusing to plan. Fix these first:")
            for r in plan["invariants"]:
                if r["status"] == "FAIL":
                    print(f"  [FAIL] {r['gate']}: {r['detail']}")
            return 1
        print(f"harness-run-system: ✅ MODULAR — {len(plan['phases'])} app(s), producer-before-consumer")
        for i, ph in enumerate(plan["phases"], 1):
            dep = f"  ⟵ after {ph['dependsOn']}" if ph["dependsOn"] else ""
            extra = f"{ph['stepCount']} steps" if ph["stepCount"] else "(library)"
            print(f"  {i:>2}. [{ph['layer']:<13}] {ph['app']:<22} kind={ph['kind']:<15} {extra}{dep}")
    return 0 if plan["modular"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
