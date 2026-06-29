#!/usr/bin/env python3
"""Merge N already-rendered recipe prompt files into ONE Mentor prompt that
authors all N in a SINGLE applyModelApiCode call.

WHY: the OutSystems tenant has a hard, low, slow-draining per-tenant Mentor
session-concurrency cap. Each recipe = one session = one cap slot, so a
hundreds-of-recipes rebuild is impractical one-at-a-time. Merging ~10 recipe
bodies into one session collapses the session count ~10x.

HOW (safe merge): each source body is `eSpace => { <statements> }`. We strip the
`eSpace => {` / `}` wrapper, re-wrap the inner statements in their OWN `{ }`
block, and concatenate the blocks inside a single outer `eSpace => { ... }`.
C# scopes local functions (AddInput/AddOutput) and locals (var a, FK vars, rp)
per-block, so they do NOT collide across recipes. Imports are unioned.

Caveat: a batch compiles all-or-nothing — one bad body fails the whole batch.
Use known-good recipes and keep batch size modest (≈8-12).

Usage:
    python scripts/batch_recipes.py --out /tmp/r12_core/core/batches/batch_a.prompt.txt \
        /tmp/r12_core/core/04_serveraction_029_*.prompt.txt \
        /tmp/r12_core/core/04_serveraction_030_*.prompt.txt ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CSHARP_FENCE = "```csharp"
FENCE = "```"
IMPORTS_MARKER = "Required imports for the `imports` array on the applyModelApiCode call:"


def parse_recipe(text: str) -> tuple[str, str, list[str]]:
    """Return (preamble, inner_body_statements, imports) for one recipe prompt.

    inner_body_statements is the code BETWEEN the outer `eSpace => {` and its
    closing `}` (the wrapper itself stripped)."""
    if CSHARP_FENCE not in text:
        raise ValueError("no ```csharp fence found")
    preamble, after = text.split(CSHARP_FENCE, 1)
    # after begins with "\n eSpace => { ... }\n```\n\nRequired imports...\n  - X"
    body_part, _, imports_part = after.partition("\n" + FENCE)
    body = body_part.strip()
    if not body.startswith("eSpace =>"):
        raise ValueError(f"body does not start with 'eSpace =>': {body[:40]!r}")
    # strip "eSpace => {" prefix and trailing "}"
    open_brace = body.index("{")
    inner = body[open_brace + 1:]
    inner = inner.rstrip()
    if not inner.endswith("}"):
        raise ValueError("body does not end with '}'")
    inner = inner[:-1].rstrip("\n")  # drop the final closing brace of the lambda

    imports: list[str] = []
    if IMPORTS_MARKER in imports_part:
        _, _, imp_lines = imports_part.partition(IMPORTS_MARKER)
        for line in imp_lines.splitlines():
            line = line.strip()
            if line.startswith("- "):
                imports.append(line[2:].strip())
    return preamble, inner, imports


def merge(files: list[Path]) -> str:
    preamble0 = None
    blocks: list[str] = []
    union_imports: list[str] = []
    names: list[str] = []
    for f in files:
        text = f.read_text()
        preamble, inner, imports = parse_recipe(text)
        if preamble0 is None:
            preamble0 = preamble
        for imp in imports:
            if imp not in union_imports:
                union_imports.append(imp)
        # label the block with the source file stem for readability + diagnostics
        label = f.stem.replace(".prompt", "")
        names.append(label)
        block = f"    // ═══ {label} ═══\n    {{\n{inner}\n    }}"
        blocks.append(block)

    assert preamble0 is not None
    # Replace the singular "Now execute the following recipe:" trailer with a
    # batch-aware instruction (the rest of the preamble's constraints still hold).
    batch_instruction = (
        f"Now execute the following BATCH of {len(files)} recipes. They are merged "
        f"into a SINGLE applyModelApiCode call: each recipe is wrapped in its own "
        f"`{{ }}` block scope (so per-recipe helpers/locals do not collide). Run "
        f"the WHOLE block as ONE applyModelApiCode call — do not split it. Each "
        f"block prints its own 'Status: OK' line; expect {len(files)} such lines:"
    )
    pre = preamble0.rstrip()
    if "Now execute the following recipe:" in pre:
        pre = pre.replace("Now execute the following recipe:", batch_instruction)
    else:
        pre = pre + "\n\n" + batch_instruction

    merged_body = "eSpace => {\n" + "\n\n".join(blocks) + "\n}"
    imports_lines = "\n".join(f"  - {i}" for i in union_imports)
    return (
        pre
        + "\n\n"
        + CSHARP_FENCE
        + "\n"
        + merged_body
        + "\n"
        + FENCE
        + "\n\n"
        + IMPORTS_MARKER
        + "\n"
        + imports_lines
        + "\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path, help="recipe .prompt.txt files to merge (in order)")
    ap.add_argument("--out", type=Path, required=True, help="output merged prompt path")
    args = ap.parse_args()

    files = [f for f in args.files if f.exists()]
    missing = [str(f) for f in args.files if not f.exists()]
    if missing:
        print(f"WARNING: skipping missing files: {missing}", file=sys.stderr)
    if not files:
        print("ERROR: no input files exist", file=sys.stderr)
        return 1

    merged = merge(files)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(merged)
    print(f"merged {len(files)} recipes -> {args.out} ({len(merged)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
