"""harness-arch-gate — the machine-checkable NO-MONOLITH gate for a system's app topology.

The runtime `harness-gate` (gate.py) accepts ONE deployed app against its spec. This gate runs
one level UP: it accepts a SYSTEM's decomposition — the set of apps + libraries and how they own,
expose, and consume each other — BEFORE anything is built. It is the "dispose" half of the hybrid
decomposition loop: an architect pass PROPOSES a `system.apps` topology (from a flat domain spec),
this gate DISPOSES — a monolith fails, it does not merely get advised against.

The doctrine it enforces is the ODC 3-Layer Architecture Canvas (see ARCHITECTURE_DECOMPOSITION.md):

  foundation  (rank 0)  Libraries / stateless services      — reusable code, NO entities, NO state
  core        (rank 1)  Service apps, one per bounded ctx    — OWN the domain entities + business logic
  orchestration(rank 2) Workflow (BPT) + AI Agent apps       — coordinate Core via events + public SAs
  enduser     (rank 3)  Web / Mobile apps, one per actor     — UI only, OWN zero persistent entities

Dependencies flow DOWNWARD only (a consumer's layer rank is >= its producer's) and the graph is a DAG.

The six invariants (each returns PASS / FAIL / OMIT, exactly like gate.py):
  INV1  layer purity        only core/service apps own entities; foundation owns no state/events
  INV2  single owner        every entity is owned by exactly one app; every consume resolves to an owner
  INV3  no cross-app FK      a local FK target must be owned by the same app (OS-DPL-50205 is a hard
                             platform rule: a local entity cannot FK a cross-app entity) — OMIT if the
                             topology declares no foreignKeys to check
  INV4  acyclic + downward   consume edges form a DAG and never point UP a layer
  INV5  context cohesion     each data-owning app maps to exactly one bounded context; a context maps
                             to exactly one owning app (1:1) — no app spans contexts, no context is split
  INV6  orchestration out    multi-service coordination lives in orchestration apps; end-user apps
                             neither own nor raise events, and any process lives in a BPT/Agent app

Usage:
  harness-arch-gate <system_spec.json> [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Layer ranks: a dependency (consumer -> producer) is legal only when the producer sits at or below
# the consumer's rank. foundation is the floor everything may depend on; enduser is the ceiling
# nothing may depend on.
LAYER_RANK = {"foundation": 0, "core": 1, "orchestration": 2, "enduser": 3}

# Only these layers may OWN persistent entities. Everything else is UI (enduser), coordination
# (orchestration), or stateless reuse (foundation).
DATA_OWNING_LAYERS = {"core"}

# ODC asset kinds that are legal per layer (a soft check: kind must be consistent with the layer's role).
LAYER_KINDS = {
    "foundation": {"Library", "ReactiveLibrary", "MobileLibrary", "Service", "ExternalLibrary"},
    "core": {"WebApplication", "Service"},
    "orchestration": {"BusinessProcess", "AIAgent"},
    "enduser": {"WebApplication", "Mobile", "MobileApplication"},
}


def _gate_row(name: str, status: str, detail: str = "", results=None) -> dict:
    """One invariant's verdict, byte-shaped like gate.py's rows so both gates render/aggregate alike."""
    return {"gate": name, "status": status, "detail": detail, "results": results or []}


def _apps(system: dict) -> list[dict]:
    return (system.get("system") or system).get("apps", [])


def _owned_by(app: dict) -> list[str]:
    return list(app.get("owns", []) or [])


def _consumes(app: dict) -> list[dict]:
    return list(app.get("consumes", []) or [])


def _layer(app: dict) -> str:
    return app.get("layer", "")


# ── INV1 — layer purity ─────────────────────────────────────────────────────────────────────────
def check_layer_purity(apps: list[dict]) -> dict:
    """Only core/service apps own entities. enduser + orchestration apps own zero persistent
    entities (an enduser app that owns domain data is a UI/data monolith). foundation (Library) apps
    own no entities AND expose no events/persistent state (libraries are stateless by definition)."""
    bad = []
    for a in apps:
        name, layer = a.get("name", "?"), _layer(a)
        owns = _owned_by(a)
        if owns and layer not in DATA_OWNING_LAYERS:
            bad.append(f"{name} (layer={layer}) owns entities {owns} — only core apps may own data")
        if layer == "foundation":
            events = (a.get("exposes") or {}).get("events") or []
            if events:
                bad.append(f"{name} (foundation) exposes events {events} — libraries must be stateless")
        if layer and layer not in LAYER_RANK:
            bad.append(f"{name} has unknown layer '{layer}' (expected {sorted(LAYER_RANK)})")
        kind, allowed = a.get("kind"), LAYER_KINDS.get(layer, set())
        if kind and allowed and kind not in allowed:
            bad.append(f"{name} kind={kind} is inconsistent with layer={layer} (expected {sorted(allowed)})")
    return _gate_row("layer-purity", "FAIL" if bad else "PASS",
                     f"{len(apps)} app(s) checked" + (f", {len(bad)} violation(s)" if bad else ""), bad)


# ── INV2 — single owner ─────────────────────────────────────────────────────────────────────────
def check_single_owner(apps: list[dict]) -> dict:
    """Every entity is owned by exactly one app. Entities owned by two apps are a shared-table
    coupling (the monolith's favourite shortcut); a consumed entity owned by NO app is a dangling
    contract. Both fail."""
    owners: dict[str, list[str]] = {}
    for a in apps:
        for ent in _owned_by(a):
            owners.setdefault(ent, []).append(a.get("name", "?"))
    bad = [f"entity '{ent}' owned by multiple apps {who}" for ent, who in sorted(owners.items()) if len(who) > 1]

    all_owned = set(owners)
    for a in apps:
        for c in _consumes(a):
            producer = c.get("app")
            for ent in c.get("entities", []) or []:
                if ent not in all_owned:
                    bad.append(f"{a.get('name','?')} consumes '{ent}' from {producer} but no app owns it")
    return _gate_row("single-owner", "FAIL" if bad else "PASS",
                     f"{len(owners)} owned entit(y/ies)" + (f", {len(bad)} violation(s)" if bad else ""), bad)


# ── INV3 — no cross-app FK (OS-DPL-50205) ─────────────────────────────────────────────────────────
def check_no_cross_app_fk(apps: list[dict]) -> dict:
    """A local entity may only FK an entity owned by the SAME app. ODC rejects a local FK to a
    cross-app referenced entity at build (OS-DPL-50205, live-proven) — cross-app entities are
    consume-only, never FK targets. The topology declares FKs via per-app `foreignKeys:[{from,target}]`.
    If NONE are declared this is OMIT (nothing to check here; the app_spec/recipe layer still enforces it)."""
    declared = 0
    bad = []
    for a in apps:
        name = a.get("name", "?")
        owned = set(_owned_by(a))
        for fk in a.get("foreignKeys", []) or []:
            declared += 1
            target = fk.get("target")
            if target not in owned:
                bad.append(f"{name}: FK {fk.get('from','?')}->{target} targets a non-owned entity "
                           f"(OS-DPL-50205: cross-app entities cannot be FK targets)")
    if declared == 0:
        return _gate_row("no-cross-app-fk", "OMIT",
                         "no foreignKeys declared in topology (enforced at app_spec/recipe layer)")
    return _gate_row("no-cross-app-fk", "FAIL" if bad else "PASS",
                     f"{declared} FK(s) checked" + (f", {len(bad)} violation(s)" if bad else ""), bad)


# ── INV4 — acyclic + downward dependencies ────────────────────────────────────────────────────────
def check_acyclic_downward(apps: list[dict]) -> dict:
    """Consume edges (consumer -> producer) must (a) never point UP a layer — a producer's rank must
    be <= its consumer's rank (Core may not depend on EndUser; nothing may depend on an enduser app),
    and (b) form a DAG. A cycle is a coupling knot no clean architecture tolerates."""
    by_name = {a.get("name"): a for a in apps}
    edges: list[tuple[str, str]] = []
    bad = []
    for a in apps:
        cn, cl = a.get("name", "?"), _layer(a)
        for c in _consumes(a):
            pn = c.get("app")
            if pn == cn:
                continue  # self-consume is just intra-app; ignore
            edges.append((cn, pn))
            prod = by_name.get(pn)
            if prod is None:
                bad.append(f"{cn} consumes unknown app '{pn}'")
                continue
            pr, cr = LAYER_RANK.get(_layer(prod)), LAYER_RANK.get(cl)
            if pr is not None and cr is not None and pr > cr:
                bad.append(f"upward dependency: {cn}({cl}) -> {pn}({_layer(prod)}) "
                           f"— a consumer may only depend on its own layer or below")

    cycle = _find_cycle(edges)
    if cycle:
        bad.append("dependency cycle: " + " -> ".join(cycle))
    return _gate_row("acyclic-downward", "FAIL" if bad else "PASS",
                     f"{len(edges)} dependency edge(s)" + (f", {len(bad)} violation(s)" if bad else ""), bad)


def _find_cycle(edges: list[tuple[str, str]]) -> list[str] | None:
    """Return one cycle as a node list (a->b->...->a) if the directed graph has one, else None."""
    graph: dict[str, list[str]] = {}
    for u, v in edges:
        graph.setdefault(u, []).append(v)
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = GRAY
        stack.append(node)
        for nxt in graph.get(node, []):
            c = color.get(nxt, WHITE)
            if c == GRAY:
                return stack[stack.index(nxt):] + [nxt]
            if c == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for n in list(graph):
        if color.get(n, WHITE) == WHITE:
            found = visit(n)
            if found:
                return found
    return None


# ── INV5 — bounded-context cohesion ───────────────────────────────────────────────────────────────
def check_context_cohesion(apps: list[dict]) -> dict:
    """Each data-owning app maps to exactly ONE bounded context, and a context maps to exactly ONE
    owning app (1:1). An app that owns entities but declares no `context`, or a context split across
    two owning apps, is either a monolith-in-waiting or fragmentation. Non-data apps need no context."""
    bad = []
    context_owners: dict[str, list[str]] = {}
    for a in apps:
        name, layer = a.get("name", "?"), _layer(a)
        if layer not in DATA_OWNING_LAYERS or not _owned_by(a):
            continue  # only data-owning apps carry a bounded context
        ctx = a.get("context")
        if not ctx:
            bad.append(f"{name} owns entities but declares no bounded context")
            continue
        if isinstance(ctx, list):
            if len(ctx) != 1:
                bad.append(f"{name} spans multiple bounded contexts {ctx} — split it into one Core per context")
                continue
            ctx = ctx[0]
        context_owners.setdefault(ctx, []).append(name)
    for ctx, who in sorted(context_owners.items()):
        if len(who) > 1:
            bad.append(f"bounded context '{ctx}' is split across apps {who} — one context = one Core app")
    n = len(context_owners)
    return _gate_row("context-cohesion", "FAIL" if bad else "PASS",
                     f"{n} bounded context(s)" + (f", {len(bad)} violation(s)" if bad else ""), bad)


# ── INV6 — orchestration externalized ─────────────────────────────────────────────────────────────
def check_orchestration_externalized(apps: list[dict]) -> dict:
    """Multi-service coordination belongs in an orchestration app (Workflow/BPT or AI Agent), never
    buried in a UI app's event handlers. So: end-user apps neither OWN nor RAISE events, and any app
    that declares a `process` (BPT) must be an orchestration-layer BusinessProcess app."""
    bad = []
    for a in apps:
        name, layer = a.get("name", "?"), _layer(a)
        exposes = a.get("exposes") or {}
        if layer == "enduser":
            if exposes.get("events"):
                bad.append(f"{name} (enduser) exposes events {exposes.get('events')} — "
                           f"events are a Core-produces / orchestration-consumes concern")
            if a.get("raisesEvents"):
                bad.append(f"{name} (enduser) raises events {a.get('raisesEvents')} — move to an orchestration app")
        if a.get("process") or a.get("activities"):
            if layer != "orchestration" or a.get("kind") not in {"BusinessProcess", "AIAgent"}:
                bad.append(f"{name} declares a process but is not an orchestration BusinessProcess/AIAgent "
                           f"(layer={layer}, kind={a.get('kind')})")
    return _gate_row("orchestration-externalized", "FAIL" if bad else "PASS",
                     "checked event ownership + process placement" + (f", {len(bad)} violation(s)" if bad else ""),
                     bad)


INVARIANTS = (
    check_layer_purity,
    check_single_owner,
    check_no_cross_app_fk,
    check_acyclic_downward,
    check_context_cohesion,
    check_orchestration_externalized,
)


def check_system(system: dict) -> list[dict]:
    """Run every no-monolith invariant and return one row per invariant (PASS/FAIL/OMIT)."""
    apps = _apps(system)
    if not apps:
        return [_gate_row("topology", "FAIL", "system declares no apps")]
    return [inv(apps) for inv in INVARIANTS]


def verdict(rows: list[dict]) -> bool:
    """MODULAR iff no invariant FAILED (OMIT is fine; it just means nothing to check there)."""
    return not any(r["status"] == "FAIL" for r in rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-arch-gate",
        description="The machine-checkable NO-MONOLITH gate: check a system's app topology against the "
                    "ODC 3-Layer Canvas (layer purity, single owner, no cross-app FK, acyclic downward "
                    "deps, context cohesion, orchestration externalized) and emit one verdict.")
    ap.add_argument("system", type=Path, help="system_spec.json (a {system:{apps:[...]}} topology)")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args(argv)

    if not args.system.exists():
        print(f"system spec not found: {args.system}", file=sys.stderr)
        return 2
    try:
        system = json.loads(args.system.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"system spec is not valid JSON: {e}", file=sys.stderr)
        return 2

    rows = check_system(system)
    modular = verdict(rows)
    if args.json:
        print(json.dumps({"invariants": rows, "modular": modular,
                          "verdict": "MODULAR" if modular else "MONOLITH"}, indent=2))
    else:
        name = (system.get("system") or system).get("name", args.system.name)
        print(f"harness-arch-gate — {name}: {'✅ MODULAR' if modular else '❌ MONOLITH (fails no-monolith gate)'}")
        for r in rows:
            mark = {"PASS": "ok ", "FAIL": "FAIL", "OMIT": "—  "}[r["status"]]
            print(f"  [{mark}] {r['gate']:<26} {r['detail']}")
            for d in r["results"]:
                print(f"          · {d}")
    return 0 if modular else 1


if __name__ == "__main__":
    raise SystemExit(main())
