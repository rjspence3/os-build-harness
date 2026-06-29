"""Normalize an OutSystems `context_graph` XRE dump into a diff-stable,
key-sorted JSON snapshot — one per app revision — so revisions can be compared
with a plain `git diff` / `diff`.

WHY THIS EXISTS
---------------
`context_graph` returns the app's full OML serialized as XRE: `{"xre": "<json>"}`
where the inner graph is index-encoded — `nodes[]` plus parallel
`edgeSrc[] / edgeDst[] / edgeAttr[]` adjacency arrays. Diffing that raw is
useless: adding one element renumbers every index, so an unrelated one-node
change shows up as a whole-file churn.

The fix: every node carries a STABLE GUID `_key` (verified: 8477/8477 nodes on
HomeBankingPortal4, including anonymous flow nodes — IStartNode/IAssignNode/
IIfNode/IForEachNode). Re-key the graph by `_key`, drop the platform builtin
catalog (huge, identical every revision), strip cosmetic position fields, and
sort. Now `diff rev_N.json rev_N+1.json` shows exactly the nodes a loop turn
added / removed / changed — at node-body granularity.

USAGE
-----
    python scripts/snapshot_app.py <context_graph_result.json> [out.json]

`context_graph_result.json` is the file the `context_graph` MCP tool writes
(shape `{"xre": "<json-string>"}`; a bare XRE object is also accepted). With no
`out.json`, writes to stdout.

LOOP WIRING (DISPATCH_PLAYBOOK beat 5): after each publish reaches Finished,
call `context_graph(key=<app>)`, then run this on the saved result into
`data/MCP_RECIPES/apps/<app>/_snapshots/rev_<N>.json`.
"""
import json
import sys

# Platform builtin catalog — stable every revision, but carries large
# Examples/Description text. Dropping it keeps snapshots lean and the diff
# focused on the app's own model. (These never change, so dropping loses
# nothing for revision comparison.)
_DROP_TYPES = {"BuiltInFunction", "BuiltInFunctionInputParameter"}

# Cosmetic per-publish fields that shift without semantic meaning — dropping
# them keeps a pure-layout move from showing up as a logic change, and stops
# audit metadata (who/when touched) from churning every revision diff.
_DROP_FIELDS = {
    # layout coordinates
    "VerticalPosition", "HorizontalPosition", "X", "Y",
    "Left", "Top", "Width", "Height",
    # audit metadata
    "CreatedBy", "CreatedDate", "LastModifiedBy", "LastModifiedDate",
    "LastMergedBy", "LastMergedDate",
}


def normalize(xre: dict) -> dict:
    """Re-key an XRE graph by stable `_key`, with outgoing edges resolved to
    `relationType->dst_key` strings (also stable, so structural changes diff
    cleanly). Returns a dict keyed by `_key`, ready for sorted JSON dump."""
    nodes = xre["nodes"]
    src, dst = xre["edgeSrc"], xre["edgeDst"]
    attr = xre.get("edgeAttr", [])

    key_of = [n.get("_key") or f"#idx{i}:{n.get('_type', '?')}" for i, n in enumerate(nodes)]

    edges_out: dict[int, list[str]] = {}
    for j, (s, d) in enumerate(zip(src, dst)):
        a = attr[j] if j < len(attr) else {}
        rel = a.get("relationType") or a.get("_type") or ""
        edges_out.setdefault(s, []).append(f"{rel}->{key_of[d]}")

    snap: dict = {}
    for i, n in enumerate(nodes):
        if n.get("_type") in _DROP_TYPES:
            continue
        entry = {k: v for k, v in n.items() if k not in _DROP_FIELDS}
        out = edges_out.get(i)
        if out:
            entry["_edges"] = sorted(out)
        key = key_of[i]
        if key in snap:
            # Defensive: stable keys should be unique. Keep both rather than
            # silently dropping one, so a collision is visible in the diff.
            existing = snap[key]
            snap[key] = existing if isinstance(existing, list) else [existing]
            snap[key].append(entry)
        else:
            snap[key] = entry
    return snap


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    raw = json.load(open(argv[1]))
    xre = json.loads(raw["xre"]) if isinstance(raw, dict) and isinstance(raw.get("xre"), str) else raw
    snap = normalize(xre)
    text = json.dumps(snap, indent=1, sort_keys=True, ensure_ascii=False)
    if len(argv) > 2 and argv[2] != "-":
        with open(argv[2], "w") as fh:
            fh.write(text + "\n")
        print(f"wrote {argv[2]}: {len(snap)} nodes (from {len(xre['nodes'])} raw)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
