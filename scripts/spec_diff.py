"""Cross-app "distance from spec" diff between two snapshot_app.py outputs.

Same-app rev-to-rev diff uses node `_key` (stable GUID) — a plain `git diff`.
But two DISTINCT apps (the clone vs the original) give the same logical element
different `_key`s, so a `_key` diff is meaningless across apps. This compares by
STRUCTURAL IDENTITY instead: `<_type>::<Name>` for every NAMED element node.

Reports, for the clone vs the original spec baseline:
  - MISSING   — named elements in the original but not the clone (distance from spec)
  - EXTRA     — named elements in the clone but not the original
  - CHANGED   — matched elements whose salient scalar props differ (e.g. a local
                typed Text in the clone but List in the original — surfaces V19)
The build is DONE (for the in-scope surface) when MISSING + CHANGED are empty.

Usage: python scripts/spec_diff.py <original.json> <clone.json>
"""
import json
import sys

# Node types that represent NAMED, cross-app-comparable elements. Anonymous
# nodes (flow nodes, expressions, literals — Name is null) have no stable
# cross-app identity and are excluded from the named-element diff.
_ELEMENT_TYPES = {
    "IMobileScreen", "IClientScreenAction", "IClientAction", "IServerAction",
    "IServiceAction", "IEntityAction", "ILocalVariable", "IInputParameter",
    "IOutputParameter", "IAggregate", "IScreenAggregate", "IMobileBlock",
    "IEntity", "IStaticEntity", "IStructure", "IReference", "IMobileTheme",
}
# Salient scalar props worth comparing on matched elements (skip noisy/structural).
_SALIENT = {"DataType", "IsPublic", "Public", "Function", "IsMandatory", "AggregationType"}


def _index(snap: dict) -> dict:
    """Map `<_type>::<Name>` -> {salient props} for every named element node."""
    out = {}
    for entry in snap.values():
        nodes = entry if isinstance(entry, list) else [entry]
        for n in nodes:
            t, name = n.get("_type"), n.get("Name")
            if t not in _ELEMENT_TYPES or not name:
                continue
            key = f"{t}::{name}"
            out[key] = {k: n[k] for k in _SALIENT if k in n}
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    orig = _index(json.load(open(argv[1])))
    clone = _index(json.load(open(argv[2])))

    missing = sorted(set(orig) - set(clone))
    extra = sorted(set(clone) - set(orig))
    changed = sorted(
        f"{k}  spec={orig[k]}  clone={clone[k]}"
        for k in set(orig) & set(clone)
        if orig[k] != clone[k]
    )

    print(f"=== distance from spec ===")
    print(f"named elements: original={len(orig)}  clone={len(clone)}")
    print(f"MISSING (in spec, not clone): {len(missing)}")
    for m in missing:
        print(f"  - {m}")
    print(f"CHANGED (prop mismatch): {len(changed)}")
    for c in changed:
        print(f"  ~ {c}")
    print(f"EXTRA (in clone, not spec): {len(extra)}")
    for e in extra:
        print(f"  + {e}")

    distance = len(missing) + len(changed)
    print(f"\nDISTANCE = {distance} (MISSING + CHANGED); build is spec-complete at 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
