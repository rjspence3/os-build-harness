"""Learning mode — harvest AI gap-fills back into the harness.

When a spec-driven build falls short and the AI (or a human) takes over to fill the gap —
hand-applying a theme, correcting a recipe's output, working around a build-engine wall — that
intervention is a *signal*: the recipe/orchestrator should have done it. Learning mode makes the
harvest of that signal a first-class, auditable step instead of an ad-hoc thing someone remembers
to do.

The loop:
  1. DETECT   a gap — a failed step, or a gate/pixel-diff DEFECT the recipe caused.
  2. RECORD   the intervention — symptom, the EVIDENCE that pinned the root cause, and the fix.
  3. GENERALIZE into a harness change (recipe/orchestrator patch) + a TEST that pins it + a
     memory finding, so the harness improves monotonically and never silently regresses.
  4. GUARDRAIL the change lands only when its pinning test(s) exist and the suite is green.

This module is the ledger + integrity check for step 3/4. Each `HarvestEntry` must cite the
pinning test node(s); `verify()` fails if a cited test is missing — so a harvest without a
regression guard cannot be recorded as `landed`.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
LEDGER_PATH = _HERE / "harvest_ledger.jsonl"
MARKDOWN_PATH = _HERE / "HARVEST_LEDGER.md"
_TESTS_DIR = _HERE.parent / "tests"


@dataclass
class HarvestEntry:
    """One harvested gap-fill. `pins` are the test function names that guard the fix in place."""
    id: int
    slug: str                       # short kebab id, e.g. "theme-outsystemsui-reset"
    trigger: str                    # the symptom the AI took over to fix (what fell short)
    evidence: str                   # how the root cause was PINNED (live DOM query, publish log, gate diff)
    root_cause: str                 # why the recipe/orchestrator produced the gap
    harness_change: str             # what changed in the harness (files / recipe / orchestrator)
    pins: list[str] = field(default_factory=list)   # pinning test function names (regression guard)
    memory: Optional[str] = None    # linked memory slug (durable finding)
    status: str = "landed"          # "landed" (fix + test in) | "proposed" (recorded, not yet fixed)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def load_ledger(path: Path = LEDGER_PATH) -> list[HarvestEntry]:
    if not path.exists():
        return []
    out: list[HarvestEntry] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(HarvestEntry(**json.loads(line)))
    return out


def save_ledger(entries: list[HarvestEntry], path: Path = LEDGER_PATH) -> None:
    path.write_text("".join(e.to_json() + "\n" for e in entries))


def add_entry(entry: HarvestEntry, path: Path = LEDGER_PATH) -> list[HarvestEntry]:
    entries = load_ledger(path)
    if any(e.slug == entry.slug for e in entries):
        raise ValueError(f"harvest slug already recorded: {entry.slug!r}")
    entries.append(entry)
    save_ledger(entries, path)
    return entries


def _test_exists(name: str, tests_dir: Path = _TESTS_DIR) -> bool:
    """True if a `def <name>(` is defined anywhere under tests/ (the regression guard)."""
    if not tests_dir.exists():
        return False
    try:
        r = subprocess.run(["grep", "-rlE", rf"def {name}\b", str(tests_dir)],
                           capture_output=True, text=True, timeout=15)
        return bool(r.stdout.strip())
    except Exception:
        return False


def verify(path: Path = LEDGER_PATH, tests_dir: Path = _TESTS_DIR) -> list[str]:
    """Integrity check: every `landed` harvest must cite at least one pinning test, and every
    cited test must exist. Returns a list of problems ([] == clean). This is the guardrail that
    makes 'harvest' checkable rather than aspirational."""
    problems: list[str] = []
    for e in load_ledger(path):
        if e.status == "landed":
            if not e.pins:
                problems.append(f"[{e.slug}] landed harvest has no pinning test")
            for t in e.pins:
                if not _test_exists(t, tests_dir):
                    problems.append(f"[{e.slug}] pinning test not found: {t}")
    return problems


def render_markdown(path: Path = LEDGER_PATH, out: Path = MARKDOWN_PATH) -> str:
    entries = load_ledger(path)
    lines = ["# Harvest ledger — harness self-improvement",
             "",
             "Auto-rendered from `harvest_ledger.jsonl` (see `harness/learning.py`). Each entry is a",
             "gap the AI took over to fill, harvested into a harness change + a pinning test.",
             ""]
    for e in entries:
        lines += [f"## {e.id}. {e.slug}  _({e.status})_",
                  f"- **Trigger:** {e.trigger}",
                  f"- **Evidence:** {e.evidence}",
                  f"- **Root cause:** {e.root_cause}",
                  f"- **Harness change:** {e.harness_change}",
                  f"- **Pinned by:** {', '.join(e.pins) or '—'}",
                  f"- **Memory:** {e.memory or '—'}",
                  ""]
    text = "\n".join(lines)
    out.write_text(text)
    return text


def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser("harness-learning", description="Harvest ledger for harness self-improvement.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="print the ledger")
    sub.add_parser("render", help="(re)render HARVEST_LEDGER.md")
    sub.add_parser("verify", help="check every landed harvest has an existing pinning test")
    args = p.parse_args(argv)
    if args.cmd == "list":
        for e in load_ledger():
            print(f"{e.id:>2} [{e.status:>8}] {e.slug} — pins={e.pins}")
        return 0
    if args.cmd == "render":
        render_markdown()
        print(f"rendered {MARKDOWN_PATH}")
        return 0
    if args.cmd == "verify":
        problems = verify()
        if problems:
            print("HARVEST LEDGER BROKEN:")
            for pr in problems:
                print("  -", pr)
            return 1
        print(f"harvest ledger OK ({len(load_ledger())} entries, all pins present)")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
