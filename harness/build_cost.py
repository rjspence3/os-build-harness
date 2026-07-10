"""harness-build-cost — the NON-GREEDY diagnostic: measure the MCP load of a build before running it.

Every plan step = one Mentor authoring TURN and (today) one PUBLISH. Session-reuse already collapses
the per-tenant SESSION (cap-slot) cost to 1/build — so the remaining greediness is TURNS and PUBLISHES.
Authoring turns can't shrink (atomicity is a reliability requirement — see STEP_ATOMICITY.md), but
PUBLISHES can batch: consecutive pure-structural-UI steps don't gate a data/behavioral verify, so they
can author into the one reused session and publish ONCE instead of per step.

This tool quantifies it for a spec or a whole system — turns, publishes, cap-sessions, verify-reads, a
per-recipe breakdown, the heavy steps, and the publish-batch opportunity — so optimization is measured,
not guessed. It runs OFFLINE (no MCP, no cap): pure plan analysis.

    harness-build-cost <app_spec.json>
    harness-build-cost <system_spec.json> --system [--domain domain.json]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness.prompt_recipes import plan_from_spec

# A step needs its OWN publish when a later step (or the gate) must VERIFY its effect before proceeding:
# the data model (entities must exist), seeds (rows must land), write-paths (behavioral verify), theme
# (render verify), and cross-app/logic plumbing (references/actions/events other units bind to). Pure
# STRUCTURAL-UI steps in between don't gate anything downstream, so a run of them can publish ONCE.
_BATCHABLE_RECIPES = {"screen", "nav-block", "place-nav", "list-screen", "dashboard", "detail", "row-actions"}


@dataclass
class BuildCost:
    app: str
    steps: int = 0
    turns: int = 0                 # Mentor authoring turns (= steps)
    publishes_per_unit: int = 0    # current model: one publish per step
    publishes_batched: int = 0     # publish-per-phase model (batch contiguous structural-UI)
    sessions_reuse: int = 1        # cap-slots with session-reuse
    sessions_greedy: int = 0       # cap-slots WITHOUT reuse (= steps)
    verify_reads: int = 0          # ~one independent read per step
    by_recipe: dict = field(default_factory=dict)
    heavy: list = field(default_factory=list)   # (target, weight) for atomicity-flagged steps

    @property
    def publish_savings(self) -> int:
        return self.publishes_per_unit - self.publishes_batched


def cost_of_plan(app: str, steps: list[dict]) -> BuildCost:
    c = BuildCost(app=app)
    c.steps = c.turns = c.publishes_per_unit = c.sessions_greedy = c.verify_reads = len(steps)
    c.by_recipe = dict(Counter(s["recipe"] for s in steps))
    c.heavy = [(_target(s, i), s.get("weight", 0)) for i, s in enumerate(steps)
               if s.get("atomicity_warning") or s.get("atomicity_note")]
    # batched publishes: each own-publish step = 1; each maximal run of batchable steps = 1
    batched, in_run = 0, False
    for s in steps:
        if s["recipe"] in _BATCHABLE_RECIPES:
            if not in_run:
                batched += 1
                in_run = True
        else:
            batched += 1
            in_run = False
    c.publishes_batched = batched
    return c


def cost_of_spec(spec: dict) -> BuildCost:
    app = (spec.get("app") or {}).get("name", "app")
    return cost_of_plan(app, plan_from_spec(spec))


def cost_of_system(system: dict, domain: Optional[dict], specs_dir: Optional[Path] = None) -> list[BuildCost]:
    from harness import expand
    from harness.run_system import topo_order
    exp = expand.expand_system(system, domain)
    specs, libs = dict(exp["specs"]), set(exp["libraries"])
    if specs_dir:                              # honor enriched on-disk specs (match what build_system builds)
        for logical in list(specs):
            p = Path(specs_dir) / f"{logical}.app_spec.json"
            if p.exists():
                specs[logical] = json.loads(p.read_text())
    order = [n for n in topo_order(system) if n not in libs]
    out = []
    for name in order:
        spec = specs.get(name)
        if spec:
            out.append(cost_of_plan(name, plan_from_spec(spec)))
    return out


def _target(step: dict, i: int) -> str:
    p = step.get("params", {})
    return f"{step['recipe']}:{p.get('entity') or p.get('screen') or p.get('name') or i}"


def _print_one(c: BuildCost) -> None:
    print(f"\n■ {c.app}")
    print(f"    authoring turns : {c.turns}")
    print(f"    publishes       : {c.publishes_per_unit}  (per-unit)  →  {c.publishes_batched}  (batched)"
          f"   save {c.publish_savings}")
    print(f"    cap sessions    : {c.sessions_reuse}  (session-reuse)   vs  {c.sessions_greedy}  (greedy/no-reuse)")
    print(f"    verify reads    : ~{c.verify_reads}")
    print(f"    by recipe       : " + ", ".join(f"{k}×{v}" for k, v in sorted(c.by_recipe.items())))
    if c.heavy:
        print(f"    heavy steps     : " + ", ".join(f"{t}(w{w})" for t, w in c.heavy))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="harness-build-cost",
                                 description="Measure a build's MCP load (turns/publishes/sessions) offline.")
    ap.add_argument("spec", type=Path, help="app_spec.json (or system_spec.json with --system)")
    ap.add_argument("--system", action="store_true", help="the spec is a system_spec — cost every app")
    ap.add_argument("--domain", type=Path, default=None, help="domain spec (system mode, for expand)")
    ap.add_argument("--specs-dir", type=Path, default=None, help="prefer enriched on-disk specs (system mode)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    raw = json.loads(args.spec.read_text())
    if args.system:
        domain = json.loads(args.domain.read_text()) if args.domain else None
        costs = cost_of_system(raw, domain, specs_dir=args.specs_dir)
    else:
        costs = [cost_of_spec(raw)]

    if args.json:
        print(json.dumps([c.__dict__ for c in costs], indent=2, default=lambda o: o.__dict__))
        return 0

    for c in costs:
        _print_one(c)
    if len(costs) > 1:
        t = sum(c.turns for c in costs)
        pu = sum(c.publishes_per_unit for c in costs)
        pb = sum(c.publishes_batched for c in costs)
        sg = sum(c.sessions_greedy for c in costs)
        print(f"\n═ SYSTEM TOTAL ({len(costs)} apps)")
        print(f"    authoring turns : {t}")
        print(f"    publishes       : {pu}  (per-unit)  →  {pb}  (batched)   save {pu - pb}")
        print(f"    cap sessions    : {len(costs)}  (1/app, session-reuse)   vs  {sg}  (greedy/no-reuse)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
