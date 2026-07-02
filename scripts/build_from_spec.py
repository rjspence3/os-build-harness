#!/usr/bin/env python3
"""Render an app_spec.json's entity layer to Mentor authoring batches (DRY-RUN).

This is the generalized counterpart to `scripts/build_banking.py`: instead of a
home_banking YAML manifest, it takes a schema-validated `app_spec.json` (see
`harness/schemas/app_spec.v0.json`), maps it onto the same renderer dataclasses
via `harness.banking_runner.spec_adapter`, and prints the entity-authoring
batches. It authors NOTHING — no MCP, no network. This is the first increment of
generalizing the runner off home_banking.

Usage:
    python scripts/build_from_spec.py --from-spec examples/task_tracker/app_spec.json --dry-run
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
    render_spec_entities,
    spec_to_entities,
)

SCHEMA_PATH = REPO_ROOT / "harness" / "schemas" / "app_spec.v0.json"


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-spec", required=True, type=Path, help="Path to app_spec.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print batches; author nothing (the only supported mode in this increment).",
    )
    parser.add_argument("--skip-validation", action="store_true", help="Skip JSON-Schema validation.")
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
    gaps = collect_spec_gaps(spec)

    print("=" * 78)
    print(f"App:            {manifest.app or '(unnamed)'}")
    print(f"Static entities: {len(manifest.static_entities)}  "
          f"[{', '.join(e.name for e in manifest.static_entities) or '-'}]")
    print(f"Server entities: {len(manifest.server_entities)}  "
          f"[{', '.join(e.name for e in manifest.server_entities) or '-'}]")
    if gaps:
        print(f"\nMapping gaps ({len(gaps)}):")
        for g in gaps:
            print(f"  - {g}")
    else:
        print("\nMapping gaps: none")
    print("=" * 78)

    batch_text = render_spec_entities(spec)
    print(batch_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
