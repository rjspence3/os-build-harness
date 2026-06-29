#!/usr/bin/env python3
# TARGET: buildHarness/.claude/hooks/walls-cap.py   (chmod +x)
#
# PreToolUse hook, registered against the ODC MCP tools in .claude/settings.json.
# Halts a build session once ./WALLS.md accumulates MORE THAN 5 OPEN walls, so the loop
# stops for human review instead of grinding on.
#
# Contract:
#   - Reads the hook event JSON from stdin; uses its `cwd` (= the build root).
#   - Counts ONLY OPEN walls: a "## WALL-" block is CLOSED (not counted) when its heading
#     line, or a `status:` line in its body, contains RESOLVED / ACCEPTED / CLOSED. So a
#     build that resolves walls regains headroom instead of asymptoting to the cap.
#   - exit 0  -> allow the tool call.
#   - exit 2  -> BLOCK the call; stderr is surfaced to the agent as the reason.
#
# The block fires on the MCP actuator only, so the agent can still Read/Write/Edit
# to produce HANDOFF.md and end the session. A PreToolUse deny also fires under
# bypassPermissions / --dangerously-skip-permissions, so the cap can't be skipped.

import json
import re
import sys
from pathlib import Path

CAP = 5  # "more than 5" -> block at 6 or more


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never block on a malformed event

    cwd = event.get("cwd") or "."
    walls = Path(cwd) / "WALLS.md"
    if not walls.exists():
        sys.exit(0)

    try:
        text = walls.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        sys.exit(0)

    closed_re = re.compile(r"\b(resolved|accepted|closed)\b", re.I)
    parts = re.split(r"(?m)^(## WALL-.*)$", text)
    total = open_count = 0
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        total += 1
        if closed_re.search(head):
            continue  # heading marks it resolved/accepted/closed
        if any(re.search(r"status\s*:", ln, re.I) and closed_re.search(ln)
               for ln in body.splitlines()[:8]):
            continue  # a `status:` line marks it closed
        open_count += 1

    if open_count > CAP:
        sys.stderr.write(
            f"WALL CAP REACHED: {open_count} OPEN walls (of {total} logged; cap {CAP}). "
            f"Stop building now — do not call the MCP again. "
            f"Write ./HANDOFF.md summarizing the open walls by category, with a recommendation "
            f"for each, then end the session for human review. "
            f"(To free the cap, mark resolved/accepted walls — append ' — RESOLVED' to the heading "
            f"or add a 'status: resolved' line.)\n"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
