"""harness-system-gate — the system-level DEFINITION OF DONE (runtime, cross-app).

`architecture.py` proves a topology is MODULAR (six static invariants). `gate.py` proves ONE app is
runtime-green against its spec. This is the tier between/above them: it proves the ASSEMBLED SYSTEM
works — that the cross-app data actually flows across the boundaries the topology declares.

From a system topology it DERIVES the runtime flow contracts that must hold end to end — one per
declared cross-app edge:

  read        a consumer renders a producer's entity        (channel: capture — load the consumer
                                                              screen bound to the referenced entity,
                                                              confirm producer rows render)
  call        a consumer invokes a producer's Service Action (channel: behavioral — invoke it, confirm
                                                              the effect persists)
  orchestrate raising a Workflow's trigger event launches the (channel: drive — raise the event, confirm
              process, which runs each activity's SA in order  each activity fires + state transitions;
                                                              the submit -> AI -> approve pattern proven
                                                              live this program)
  agent       an AI Agent reasons over its inputs and writes (channel: agent-invoke — call it, confirm a
              a result back to a Core                          reasoned, grounded result)

It follows verify.py's HONEST-CHANNEL discipline: a flow whose live channel isn't wired returns
`unconfigured` (needs the deployed system + a driver) — NEVER a fake pass. So the system is DONE only
when it is MODULAR (static) AND every derived flow is runtime-green — and it can never be reported DONE
from static analysis alone. The DERIVATION is deterministic and fully tested; the live execution is the
session's job (it drives Mentor/CDP), exactly as with gate.py/verify.py.

Usage:
  harness-system-gate <system.json> [--live] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import architecture

# Grounded channel per flow kind (what read path actually proves it). Mirrors verify.LIVE_CHANNELS.
FLOW_CHANNELS: dict[str, tuple[str, str]] = {
    "read": ("capture",
             "load the consumer screen bound to the referenced entity via CDP; confirm producer rows render "
             "(the appReference read path — consumer imports producer's entity, binds a Table to it)."),
    "call": ("behavioral",
             "invoke the referenced public Service Action at runtime; confirm its effect persists in the "
             "producer (cross-app writes go through the owner's public SA — OS-DPL-50205 forbids shared FKs)."),
    "orchestrate": ("drive",
                    "raise the trigger Global Event; confirm the BPT process launches and each automatic "
                    "activity fires its Service Action in order, with the entity state transitioning "
                    "(submit -> AI review -> human approve -> complete; proven live 2026-07-07)."),
    "agent": ("agent-invoke",
              "invoke the agent's public Call Service Action; confirm a reasoned, input-grounded result "
              "(AIAgent authored + bound to a Trial model, invoked from a BPT activity; proven live)."),
}


def _apps(system: dict) -> list[dict]:
    return (system.get("system") or system).get("apps", [])


def derive_system_flows(system: dict) -> list[dict]:
    """The cross-app runtime contracts a modular system must satisfy, derived from its topology.
    One `read` per consumed entity, one `call` per consumed Service Action, one `orchestrate` per BPT
    process, one `agent` per AI Agent. Deterministic + order-stable."""
    flows: list[dict] = []
    for app in _apps(system):
        name, kind = app.get("name", "?"), app.get("kind")
        for c in app.get("consumes", []) or []:
            producer = c.get("app")
            for ent in c.get("entities", []) or []:
                flows.append({"kind": "read", "consumer": name, "producer": producer, "element": ent})
            for sa in c.get("serviceActions", []) or []:
                flows.append({"kind": "call", "consumer": name, "producer": producer, "element": sa})
        if kind == "BusinessProcess" and (app.get("process") or app.get("activities")):
            proc = app.get("process") or {}
            acts = [a.get("callsServiceAction") for a in app.get("activities", []) if a.get("callsServiceAction")]
            flows.append({"kind": "orchestrate", "app": name,
                          "trigger": proc.get("triggerEvent"), "activities": acts})
        if kind == "AIAgent":
            svc = (app.get("exposes") or {}).get("serviceActions", [])
            flows.append({"kind": "agent", "app": name, "service": svc[0] if svc else None})
    return flows


def _flow_label(f: dict) -> str:
    if f["kind"] == "read":
        return f"{f['consumer']} reads {f['producer']}.{f['element']}"
    if f["kind"] == "call":
        return f"{f['consumer']} calls {f['producer']}.{f['element']}"
    if f["kind"] == "orchestrate":
        return f"{f['app']} on '{f['trigger']}' -> [{', '.join(f['activities'])}]"
    if f["kind"] == "agent":
        return f"{f['app']} reasons via {f['service']}"
    return f["kind"]


def _row(gate: str, status: str, detail: str, results=None) -> dict:
    return {"gate": gate, "status": status, "detail": detail, "results": results or []}


def run_system_gate(system: dict, *, live_configured: bool = False) -> dict:
    """Compose the system definition of done: the six static invariants THEN the derived runtime flows.
    Without a live driver every flow is `unconfigured` (honest — never a fake pass), so a system is only
    DONE when it is MODULAR and every flow is runtime-green."""
    static_rows = architecture.check_system(system)
    modular = architecture.verdict(static_rows)

    flows = derive_system_flows(system)
    flow_rows: list[dict] = []
    for f in flows:
        channel, _rationale = FLOW_CHANNELS[f["kind"]]
        if not live_configured:
            flow_rows.append(_row(f"{f['kind']}", "unconfigured",
                                  f"{_flow_label(f)} — channel '{channel}' needs the deployed system + a driver"))
        else:
            # A live system is present but no flow executor is wired yet — never a fake pass.
            flow_rows.append(_row(f"{f['kind']}", "not-implemented",
                                  f"{_flow_label(f)} — channel '{channel}' executor TODO"))

    flows_green = bool(flow_rows) and all(r["status"] == "PASS" for r in flow_rows)
    done = modular and flows_green
    return {"static": static_rows, "flows": flow_rows, "modular": modular,
            "flows_green": flows_green, "done": done}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-system-gate",
        description="System-level DEFINITION OF DONE: the six static no-monolith invariants plus the "
                    "derived cross-app runtime flow contracts (read / call / orchestrate / agent). A flow "
                    "with no wired live channel is 'unconfigured', never a fake pass.")
    ap.add_argument("system", type=Path, help="system_spec.json topology")
    ap.add_argument("--live", action="store_true",
                    help="a deployed system + driver is available (flows become 'not-implemented' until an "
                         "executor is wired, still never a fake pass)")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args(argv)

    if not args.system.exists():
        print(f"system spec not found: {args.system}", file=sys.stderr)
        return 2
    system = json.loads(args.system.read_text(encoding="utf-8"))
    report = run_system_gate(system, live_configured=args.live)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        name = (system.get("system") or system).get("name", args.system.name)
        verdict = "✅ DONE" if report["done"] else ("◻ MODULAR, runtime unverified" if report["modular"]
                                                    else "❌ NOT MODULAR")
        print(f"harness-system-gate — {name}: {verdict}")
        print("  static invariants:")
        for r in report["static"]:
            mark = {"PASS": "ok ", "FAIL": "FAIL", "OMIT": "—  "}[r["status"]]
            print(f"    [{mark}] {r['gate']}")
        print(f"  runtime flows ({len(report['flows'])} derived):")
        for r in report["flows"]:
            mark = {"PASS": "ok ", "FAIL": "FAIL", "unconfigured": "…  ", "not-implemented": "…  "}.get(r["status"], "?")
            print(f"    [{mark}] {r['gate']:<12} {r['detail']}")
    # exit 0 only when truly DONE; 1 otherwise (unverified runtime is NOT done)
    return 0 if report["done"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
