#!/usr/bin/env python3
"""Emit the complete, repeatable BUILD PLAN for an app_spec.json (DRY-RUN, authors nothing).

The generalized counterpart to `scripts/build_banking.py`: it takes a
schema-validated `app_spec.json` (see `harness/schemas/app_spec.v0.json`), maps it
onto the renderer dataclasses via `harness.banking_runner.spec_adapter`, and prints
the ordered plan a captured Mentor build session executes:

    PHASE 1 · Author entities   — natural-language intent (Mentor authors NATIVELY;
                                  verbatim applyModelApiCode C# does not persist on
                                  fresh apps — proven). ONE committing turn so FKs see
                                  their targets.
    PHASE 2 · Author screens    — natural-language intent per screen.
    PHASE 3 · Verify            — read-only capture (context_entities + a read-only
                                  applyModelApiCode screen-walk per docs/SCREEN_WALK.md)
                                  fed to `harness-verify --phase live`. Expect exit 0.

It authors NOTHING — no MCP, no network. Authoring happens in a captured build
session that executes this plan; verification is deterministic and snapshot-fed.

Usage:
    python scripts/build_from_spec.py --from-spec examples/task_tracker/app_spec.json
    python scripts/build_from_spec.py --from-spec <spec> --emit-csharp   # legacy C# entity batch too
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.banking_runner.spec_adapter import (  # noqa: E402
    collect_spec_gaps,
    collect_spec_screen_gaps,
    render_spec_entities,
    render_spec_entities_nl,
    render_spec_screens_nl,
    spec_to_entities,
)
from harness.prompt_recipes import plan_gaps_from_spec  # noqa: E402
from harness.spec_ingest import plan_gaps_with_fidelity  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "harness" / "schemas" / "app_spec.v0.json"
_RULE = "=" * 78
_SUB = "─" * 78


def _validate_against_schema(spec: dict) -> list[str]:
    """Best-effort JSON-Schema validation. Returns a list of error strings
    (empty = valid or validator unavailable)."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return ["(jsonschema not installed — skipped schema validation)"]
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(spec), key=lambda e: list(e.path))
    ]


def _verify_plan_text(spec_path: Path) -> str:
    """The read-only verification recipe — deterministic, snapshot-fed, never a false pass."""
    return "\n".join([
        "After the build session publishes (revision must increment — the only trustworthy",
        "'landed' signal), capture live state READ-ONLY and verify:",
        "",
        "  1. Entities:  context_entities  ->  entities.json",
        "  2. Screens:   read-only applyModelApiCode screen-walk (one screen per call, per",
        "                docs/SCREEN_WALK.md; emits {id,type,boundTo,sourceEntity} + nav)  ->  screens.json",
        "  3. Verify:",
        f"       harness-verify --phase live --entities entities.json --screens screens.json {spec_path.name}",
        "",
        "     Expect every assertion [pass] and exit 0. A binding matches whether the walk",
        "     reports the aggregate (GetTaskLists.List) or the resolved sourceEntity (TaskList).",
        "     Empty snapshots -> exit 3 (inconclusive), never a false pass.",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-spec", required=True, type=Path, help="Path to app_spec.json")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Print the plan; author nothing (the only supported mode).")
    parser.add_argument("--skip-validation", action="store_true", help="Skip JSON-Schema validation.")
    parser.add_argument("--emit-csharp", action="store_true",
                        help="Also print the legacy applyModelApiCode C# entity batch "
                             "(superseded for authoring by the NL intent; kept for reference).")
    parser.add_argument("--fidelity", choices=["demo", "production"], default="demo",
                        help="Gap fidelity mode: demo (default, no blocking flags) or "
                             "production (auth:app-local + unhardened REST become blocking).")
    args = parser.parse_args(argv)

    spec_path: Path = args.from_spec
    if not spec_path.exists():
        print(f"ERROR: spec not found: {spec_path}", file=sys.stderr)
        return 2

    spec = json.loads(spec_path.read_text())

    if not args.skip_validation:
        errors = _validate_against_schema(spec)
        hard_errors = [e for e in errors if not e.startswith("(")]
        for e in errors:
            print(f"[schema] {e}")
        if hard_errors:
            print(f"ERROR: spec failed schema validation ({len(hard_errors)} error(s)).", file=sys.stderr)
            return 1

    manifest = spec_to_entities(spec)
    entity_gaps = collect_spec_gaps(spec)
    screen_gaps = collect_spec_screen_gaps(spec)

    # ── header ────────────────────────────────────────────────────────────────
    print(_RULE)
    print(f"BUILD PLAN · {manifest.app or '(unnamed app)'}   [DRY-RUN — authors nothing]")
    print(_RULE)
    print(f"Static entities: {len(manifest.static_entities)}  "
          f"[{', '.join(e.name for e in manifest.static_entities) or '-'}]")
    print(f"Server entities: {len(manifest.server_entities)}  "
          f"[{', '.join(e.name for e in manifest.server_entities) or '-'}]")
    print(f"Screens:         {len(spec.get('screens', []))}  "
          f"[{', '.join(s.get('id') or s.get('name') or '?' for s in spec.get('screens', [])) or '-'}]")
    for label, gaps in (("entity", entity_gaps), ("screen", screen_gaps)):
        if gaps:
            print(f"\n{label.capitalize()} mapping gaps ({len(gaps)}):")
            for g in gaps:
                print(f"  - {g}")
    if not entity_gaps and not screen_gaps:
        print("\nMapping gaps: none")

    # Production-coverage gaps: every spec ask classified against what the harness + ODC
    # can deliver — surfaced, never dropped silently. Four verdicts (see plan_gaps_from_spec).
    # --fidelity production adds a [BLOCKING] marker on auth:app-local + unhardened REST.
    plan_gaps = plan_gaps_with_fidelity(spec, args.fidelity)
    if plan_gaps:
        print(f"\n⚠ Gaps between spec and production build ({len(plan_gaps)}) "
              f"[fidelity={args.fidelity}]:")
        for kind, meaning in (("spec-wiring", "fix the spec"),
                              ("platform-native", "ODC covers it — configure/author + harden"),
                              ("demo-stub", "demo-only — replace for production"),
                              ("recipe-missing", "no recipe — learning-mode or git note")):
            group = [g for g in plan_gaps if g["kind"] == kind]
            if group:
                print(f"  {kind} ({meaning}):")
                for g in group:
                    blocking_marker = " [BLOCKING]" if g.get("blocking") else ""
                    print(f"    - [{g['capability']}]{blocking_marker} {g['detail']} — {g['where']}")
    else:
        print("\nProduction gaps: none")

    # ── PHASE 1 · entities (NL intent — the proven authoring path) ─────────────
    print(f"\n{_SUB}")
    print("PHASE 1 · Author entities — natural-language intent (ONE committing Mentor turn)")
    print(_SUB)
    print(render_spec_entities_nl(spec))

    # ── PHASE 2 · screens (NL intent) ──────────────────────────────────────────
    print(f"\n{_SUB}")
    print("PHASE 2 · Author screens — natural-language intent")
    print(_SUB)
    print(render_spec_screens_nl(spec))

    # ── PHASE 3 · verify (read-only, deterministic) ────────────────────────────
    print(f"\n{_SUB}")
    print("PHASE 3 · Verify — read-only capture -> harness-verify --phase live")
    print(_SUB)
    print(_verify_plan_text(spec_path))

    # ── optional legacy C# batch ───────────────────────────────────────────────
    if args.emit_csharp:
        print(f"\n{_SUB}")
        print("APPENDIX · Legacy applyModelApiCode C# entity batch (superseded — reference only)")
        print(_SUB)
        print(render_spec_entities(spec))

    print(f"\n{_RULE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
