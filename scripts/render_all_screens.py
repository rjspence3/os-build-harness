#!/usr/bin/env python3
"""Render all captured screens to MCP-ready .prompt.txt files.

Walks `data/MCP_RECIPES/apps/home_banking/_raw/*.tree.md`, runs each through
the dechromed renderer (T2.2) + chrome-wrap renderer (T2.5), and writes the
output to `data/MCP_RECIPES/apps/home_banking/_rendered/`:

    backoffice-managesettings.dechromed.prompt.txt
    backoffice-managesettings.chrome_wrap.prompt.txt

The orchestrator picks up these files during Tier 4 dispatch.

Usage:
    python3 scripts/render_all_screens.py [--dry-run]

`--dry-run` prints what would be rendered without writing files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from harness.banking_runner.chrome_wrap import (
    extract_chrome_wrap_manifest,
    render_chrome_wrap,
)
from harness.banking_runner.recipe import load_preamble
from harness.banking_runner.screen_renderer import render_screen_dechromed
from harness.banking_runner.tree_parser import parse_coverage, parse_tree_file

# Captures below this parse coverage are in a dialect the parser can't fully
# read (narrative Dialect C). Rendering them would emit an incomplete screen,
# so they're skipped with a pointer to the strict re-capture prompt.
MIN_COVERAGE = 0.9


RAW_DIR = REPO / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw"
OUT_DIR = REPO / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_rendered"
RECIPES_DIR = REPO / "builds" / "home_banking" / "MCP_RECIPES"


# ─── App + flow + role mapping (per app's manifest) ─────────────────────────

# Maps the filename prefix to (app_name, flow_name, role_name). Roles come from
# the manifest — Portal uses HomeBankingPortal, Backoffice uses
# HomeBankingBackoffice. Mobile is out of scope for v1 (backend block).
PREFIX_TO_CONTEXT: dict[str, tuple[str, str, str | None]] = {
    "portal-":     ("HomeBankingPortal",     "MainFlow", "HomeBankingPortalCustomer"),
    "backoffice-": ("HomeBankingBackoffice", "MainFlow", "HomeBankingBackofficeEmployee"),
}


def _context_for(filename: str) -> tuple[str, str, str | None]:
    for prefix, ctx in PREFIX_TO_CONTEXT.items():
        if filename.startswith(prefix):
            return ctx
    return ("unknown", "MainFlow", None)


def _wrap_with_preamble(body: str) -> str:
    """Wrap a raw `eSpace => { ... }` lambda in the standard PROMPT_PREAMBLE
    + ```csharp fence + imports declaration. Mirrors `_assemble_prompt` in
    recipe.py for consistency."""
    preamble = load_preamble(RECIPES_DIR).strip()
    imports = [
        "System.Linq",
        "OutSystems.Model",
        "OutSystems.Model.Data",
        "OutSystems.Model.Logic",
        "OutSystems.Model.Logic.Nodes",
        "OutSystems.Model.UI.Mobile",
        "OutSystems.Model.UI.Mobile.Widgets",
        "OutSystems.Model.Enumerations",
        "ServiceStudio.Plugin.NRWidgets",
    ]
    imports_lines = "\n".join(f"  - {i}" for i in imports)
    return (
        preamble
        + "\n\n```csharp\n"
        + body.strip()
        + "\n```\n\n"
        + f"Required imports for the `imports` array on the applyModelApiCode call:\n{imports_lines}\n"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without writing files")
    args = parser.parse_args(argv)

    captures = sorted(RAW_DIR.glob("*.tree.md"))
    if not captures:
        print(f"FAIL: no captures in {RAW_DIR}")
        return 1

    if not args.dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    dechromed_count = 0
    chrome_wrap_count = 0
    skipped_no_chrome = 0
    skipped_low_coverage = 0
    total_chrome_sites = 0

    for capture in captures:
        # Coverage gate — skip narrative Dialect-C captures the parser can't
        # fully read (rendering them would author an incomplete screen).
        cov = parse_coverage(capture.read_text())
        if cov["coverage"] < MIN_COVERAGE:
            print(f"  SKIP (low coverage {cov['coverage']:.2f}, "
                  f"{cov['parsed_nodes']}/{cov['widget_lines']}): {capture.name} "
                  f"— re-capture via data/MCP_RECIPES/R8_CAPTURE_PROMPT.md")
            skipped_low_coverage += 1
            continue

        ast = parse_tree_file(capture)
        app_name, flow_name, role_name = _context_for(capture.name)

        # ─── Dechromed render ─────────────────────────────────
        dechromed_body = render_screen_dechromed(ast, role_name=role_name, flow_name=flow_name)
        dechromed_prompt = _wrap_with_preamble(dechromed_body)

        dechromed_path = OUT_DIR / f"{capture.stem}.dechromed.prompt.txt"
        if args.dry_run:
            print(f"  [DRY] write {dechromed_path.relative_to(REPO)} ({len(dechromed_prompt)} bytes, app={app_name}, role={role_name})")
        else:
            dechromed_path.write_text(dechromed_prompt)
        dechromed_count += 1

        # ─── Chrome wrap render ───────────────────────────────
        manifest = extract_chrome_wrap_manifest(ast, flow_name=flow_name)
        if not manifest.entries:
            skipped_no_chrome += 1
            continue

        chrome_body = render_chrome_wrap(manifest)
        chrome_prompt = _wrap_with_preamble(chrome_body)

        chrome_path = OUT_DIR / f"{capture.stem}.chrome_wrap.prompt.txt"
        if args.dry_run:
            print(f"  [DRY] write {chrome_path.relative_to(REPO)} ({len(chrome_prompt)} bytes, {len(manifest.entries)} sites)")
        else:
            chrome_path.write_text(chrome_prompt)
        chrome_wrap_count += 1
        total_chrome_sites += len(manifest.entries)

    print()
    print(f"Rendered:")
    print(f"  Dechromed screens:     {dechromed_count}")
    print(f"  Chrome wraps:          {chrome_wrap_count} ({total_chrome_sites} total sites)")
    print(f"  No chrome needed:      {skipped_no_chrome}")
    print(f"  Skipped (low coverage): {skipped_low_coverage}")
    if not args.dry_run:
        print(f"  Output dir:            {OUT_DIR.relative_to(REPO)}/")
    print()

    if dechromed_count + skipped_low_coverage != len(captures):
        print(f"WARN: rendered {dechromed_count} + skipped {skipped_low_coverage} "
              f"!= {len(captures)} captures")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
