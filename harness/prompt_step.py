"""harness-prompt-step — render bounded, pre-corrected build prompts from a recipe.

Renders ONE fully-formed Mentor prompt for a common build unit (nav-block,
list-screen, role-gate, seed-entity, ...) from the recipe catalog in
`harness/prompt_recipes.py`. Every known live-build correction is pre-applied so
the prompt authors correctly the first time — the orchestrator feeds the rendered
text to `mentor_start`. Deterministic + offline; the catalog is unit-tested.

  harness-prompt-step --list
  harness-prompt-step list-screen --params '{"screen":"documents","entity":"Document","columns":["Title","Author","UpdatedAt"]}'
  harness-prompt-step role-gate --params @gate.json          # @file to read params from a file

`--execute` (drive the rendered prompt through the ODC MCP) is intentionally not
built here: the judge/orchestrator owns the MCP client (harness doctrine HD D7),
so this tool renders and the main loop actuates. Requesting it exits 3, never a
false success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.prompt_recipes import RECIPES, render, plan_from_spec, plan_gaps_from_spec


# Verdict → (heading, one-line meaning). ODC-only taxonomy (see plan_gaps_from_spec).
_VERDICT_ORDER = [
    ("spec-wiring", "fix the spec so a build step is generated"),
    ("platform-native", "ODC covers it — configure/author (mind portal prereqs + hardening)"),
    ("demo-stub", "demo-only shortcut — MUST be replaced for production"),
    ("recipe-missing", "no recipe yet — learning-mode harvest or a git note to defer"),
]


def _print_gap_report(gaps: list[dict]) -> None:
    """Surface every spec ask against what the harness + ODC can deliver — nothing dropped
    silently. Four verdicts route the fix (see harness.prompt_recipes.plan_gaps_from_spec)."""
    if not gaps:
        print("\nproduction gaps: none — the plan covers the whole spec.")
        return
    print(f"\n⚠ {len(gaps)} gap(s) between this spec and a production build:")
    for kind, meaning in _VERDICT_ORDER:
        group = [g for g in gaps if g["kind"] == kind]
        if not group:
            continue
        print(f"\n  {kind} ({len(group)}) — {meaning}:")
        for g in group:
            print(f"    • [{g['capability']}] {g['detail']}")
            print(f"        at {g['where']}  →  {g['resolution']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-prompt-step",
        description="Render a fully-formed, pre-corrected Mentor prompt from the recipe catalog.")
    ap.add_argument("recipe", nargs="?", help="recipe name (see --list)")
    ap.add_argument("--params", default="{}",
                    help='recipe params as inline JSON, or @path to read JSON from a file')
    ap.add_argument("--list", action="store_true", help="list available recipes and exit")
    ap.add_argument("--plan", type=Path, default=None,
                    help="derive an ordered build plan from an app_spec.json (the spec->recipe loop-closer)")
    ap.add_argument("--render", action="store_true", help="with --plan: also render each step's full prompt")
    ap.add_argument("--json", action="store_true", help="emit {recipe, params, prompt} (or the plan) as JSON")
    ap.add_argument("--execute", action="store_true",
                    help="(not implemented) actuate via MCP — the orchestrator owns the MCP client")
    args = ap.parse_args(argv)

    if args.plan is not None:
        if not args.plan.exists():
            print(f"spec not found: {args.plan}", file=sys.stderr)
            return 1
        try:
            spec = json.loads(args.plan.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"spec is not valid JSON: {e}", file=sys.stderr)
            return 1
        steps = plan_from_spec(spec)
        gaps = plan_gaps_from_spec(spec)
        if args.json:
            plan_out = [dict(s, prompt=render(s["recipe"], s["params"])) for s in steps] if args.render else steps
            print(json.dumps({"plan": plan_out, "gaps": gaps}, indent=2))
            return 0
        print(f"build plan — {len(steps)} step(s) derived from {args.plan.name}:")
        for i, s in enumerate(steps, 1):
            print(f"\n[{i}] {s['recipe']}  ({s['why']})")
            if args.render:
                print(render(s["recipe"], s["params"]))
            else:
                print(f"    params: {json.dumps(s['params'])}")
        _print_gap_report(gaps)
        return 0

    if args.list:
        print("recipes:")
        for name in sorted(RECIPES):
            doc = (RECIPES[name].__doc__ or "").strip().splitlines()[0]
            print(f"  {name:14} {doc}")
        return 0

    if not args.recipe:
        print("no recipe given (see --list)", file=sys.stderr)
        return 1

    raw = args.params
    if raw.startswith("@"):
        p = Path(raw[1:])
        if not p.exists():
            print(f"--params file not found: {p}", file=sys.stderr)
            return 1
        raw = p.read_text(encoding="utf-8")
    try:
        params = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"--params is not valid JSON: {e}", file=sys.stderr)
        return 1

    try:
        prompt = render(args.recipe, params)
    except KeyError as e:
        print(str(e).strip('"'), file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"recipe '{args.recipe}': {e}", file=sys.stderr)
        return 1

    if args.execute:
        print("harness-prompt-step --execute is not implemented: the orchestrator (main CC loop) owns the "
              "MCP client — feed the rendered prompt below to mentor_start yourself.", file=sys.stderr)
        # still emit the prompt on stdout so the caller can use it
        print(prompt)
        return 3

    if args.json:
        print(json.dumps({"recipe": args.recipe, "params": params, "prompt": prompt}, indent=2))
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
