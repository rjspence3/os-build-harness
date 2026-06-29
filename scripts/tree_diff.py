#!/usr/bin/env python3
"""T4.3 structural-diff CLI — compare two captured screen trees.

Wraps `tree_parser.diff_screens()`. Used to verify a rebuilt screen matches its
original capture: zero significant differences = authoring-level identity =
runtime visual identity (per the OutSystems deterministic-rendering contract).

Usage:
    # Compare two .tree.md captures directly:
    python3 scripts/tree_diff.py <expected.tree.md> <actual.tree.md>

    # Compare every _raw capture against a re-capture directory (rebuild verify):
    python3 scripts/tree_diff.py --rebuild-dir <dir>

Exit code: 0 if zero significant differences for every comparison, 1 otherwise.
Coverage gate: a capture below 0.9 parse coverage is reported as UNVERIFIABLE
(can't trust a diff against a tree the parser couldn't read) and fails the run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from harness.banking_runner.tree_parser import (
    Difference,
    parse_coverage,
    parse_tree_file,
    diff_screens,
)

RAW_DIR = REPO / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw"
MIN_COVERAGE = 0.9


def _print_diffs(label: str, diffs: list[Difference]) -> None:
    if not diffs:
        print(f"  ✓ {label}: zero significant differences")
        return
    print(f"  ✗ {label}: {len(diffs)} difference(s)")
    for d in diffs[:50]:
        print(f"      [{d.path or 'root'}] {d.kind}: {d.detail}")
        print(f"          expected: {d.expected!r}")
        print(f"          actual:   {d.actual!r}")
    if len(diffs) > 50:
        print(f"      ... and {len(diffs) - 50} more")


def _coverage_ok(path: Path, label: str) -> bool:
    cov = parse_coverage(path.read_text())
    if cov["coverage"] < MIN_COVERAGE:
        print(f"  ⚠ {label}: UNVERIFIABLE — parse coverage {cov['coverage']:.2f} "
              f"({cov['parsed_nodes']}/{cov['widget_lines']}). Re-capture via "
              f"R8_CAPTURE_PROMPT.md before trusting a diff.")
        return False
    return True


def diff_pair(expected_path: Path, actual_path: Path) -> int:
    """Diff one expected/actual pair. Returns 0 if identical, 1 otherwise."""
    label = f"{expected_path.name} ↔ {actual_path.name}"
    ok = True
    ok &= _coverage_ok(expected_path, f"expected {expected_path.name}")
    ok &= _coverage_ok(actual_path, f"actual {actual_path.name}")
    if not ok:
        return 1
    expected = parse_tree_file(expected_path)
    actual = parse_tree_file(actual_path)
    diffs = diff_screens(expected, actual)
    _print_diffs(label, diffs)
    return 0 if not diffs else 1


def diff_rebuild_dir(rebuild_dir: Path) -> int:
    """Diff every _raw capture against a same-named file in rebuild_dir."""
    rc = 0
    matched = 0
    for original in sorted(RAW_DIR.glob("*.tree.md")):
        rebuilt = rebuild_dir / original.name
        if not rebuilt.exists():
            print(f"  - {original.name}: no rebuild capture in {rebuild_dir.name}/ (skipped)")
            continue
        matched += 1
        rc |= diff_pair(original, rebuilt)
    if matched == 0:
        print(f"FAIL: no matching rebuild captures found in {rebuild_dir}")
        return 1
    print(f"\nCompared {matched} screen(s).")
    return rc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("expected", nargs="?", type=Path, help="expected .tree.md")
    parser.add_argument("actual", nargs="?", type=Path, help="actual .tree.md")
    parser.add_argument("--rebuild-dir", type=Path,
                        help="diff every _raw capture against same-named file here")
    args = parser.parse_args(argv)

    if args.rebuild_dir:
        return diff_rebuild_dir(args.rebuild_dir)
    if args.expected and args.actual:
        if not args.expected.exists():
            print(f"FAIL: {args.expected} not found")
            return 1
        if not args.actual.exists():
            print(f"FAIL: {args.actual} not found")
            return 1
        return diff_pair(args.expected, args.actual)

    parser.error("provide either two .tree.md paths or --rebuild-dir")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
