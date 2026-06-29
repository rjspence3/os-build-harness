#!/usr/bin/env bash
# TARGET: buildHarness/harness/launch_build.sh
#
# Scaffolds builds/<app>/ and starts the build. The build runs as a normal Claude Code session
# in the build root — the same operational pattern banking_runner ran under — with CC as the
# orchestrator in the slot the runner used to hold. See HARNESS_DECISIONS.md (D1).
#
# RUN_MODE:
#   session  (default, current) — start a normal CC session in the build root. Supervision comes
#            from Kernel (tiered autonomy + audit) plus the wall-cap hook. No `claude -p`.
#   headless (future)           — `claude -p` for unattended/CI builds. Flip RUN_MODE=headless when
#            ready; everything else is identical.
#
# Inheritance is mode-independent: cwd pickup of CLAUDE.md + .mcp.json and the wall-cap PreToolUse
# hook fire the same way in both modes.
#
# Usage:  harness/launch_build.sh <app-name> [spec-path]
#         RUN_MODE=headless harness/launch_build.sh <app-name> [spec-path]

set -euo pipefail

RUN_MODE="${RUN_MODE:-session}"

APP="${1:?usage: launch_build.sh <app-name> [spec-path]}"
SPEC_SRC="${2:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # buildHarness/
BUILD="$ROOT/builds/$APP"
TEMPLATE="$ROOT/builds/_template"

# 1. Scaffold the build root (idempotent, mode-independent).
mkdir -p "$BUILD/spec" "$BUILD/out"
[ -f "$BUILD/CLAUDE.md" ] || sed "s/<APP_NAME>/$APP/g" "$TEMPLATE/CLAUDE.md" > "$BUILD/CLAUDE.md"
[ -f "$BUILD/WALLS.md" ] || printf "# Walls — %s\n" "$APP" > "$BUILD/WALLS.md"
[ -n "$SPEC_SRC" ] && cp -R "$SPEC_SRC"/. "$BUILD/spec/"

cd "$BUILD"

# 2. Start the build per RUN_MODE.
case "$RUN_MODE" in
  session)
    # Clone-style: a normal CC session in the build root. Under Kernel this is whatever spawns a
    # worker session in this dir; standalone it's an interactive `claude` session.
    exec claude
    ;;
  headless)
    # Future: fully unattended. ANTHROPIC_API_KEY (+ MCP tenant creds) must be in the environment.
    : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY before a headless launch}"
    exec claude -p "Build this app from ./spec per your CLAUDE.md. Verify each step against the spec with harness-verify. Log blockers to ./WALLS.md in the required format. If the wall cap halts you, write ./HANDOFF.md and stop." \
      --output-format stream-json \
      --permission-mode acceptEdits \
      --allowedTools "Read,Write,Edit,Bash,mcp__*"
    ;;
  *)
    echo "unknown RUN_MODE: '$RUN_MODE' (use 'session' or 'headless')" >&2
    exit 2
    ;;
esac
