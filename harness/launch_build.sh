#!/usr/bin/env bash
# TARGET: harness/launch_build.sh
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

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # repo root
BUILD="$ROOT/builds/$APP"
TEMPLATE="$ROOT/builds/_template"

# 1. Scaffold the build root (idempotent, mode-independent).
mkdir -p "$BUILD/spec" "$BUILD/out"
[ -f "$BUILD/CLAUDE.md" ] || sed "s/<APP_NAME>/$APP/g" "$TEMPLATE/CLAUDE.md" > "$BUILD/CLAUDE.md"
[ -f "$BUILD/WALLS.md" ] || printf "# Walls — %s\n" "$APP" > "$BUILD/WALLS.md"
# Install the build-root permission allowlist so the launched session can actually run the harness
# CLIs (closes SEAM-001 — without this the session's Bash sandbox denies harness-gate/-verify/-capture
# and the doctrine's autonomy claim is false). Idempotent: never clobber a human-edited settings.json.
[ -f "$BUILD/.claude/settings.json" ] || { mkdir -p "$BUILD/.claude"; cp "$TEMPLATE/.claude/settings.json" "$BUILD/.claude/settings.json"; }
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
    # The DEFINITION OF DONE is machine-checked, not self-declared: the build is complete only when
    # `harness-gate ./spec/app_spec.json --base-url <deployed-url>` exits 0 (spec + structural +
    # behavioral + role + render green for every dimension the spec declares). The session must not
    # stop on a green publish — a no-op publish (no_changes_detected) is NOT progress. It loops
    # build → publish → verify-at-runtime until the gate is DONE or the wall cap halts it.
    exec claude -p "Build this app from ./spec per your CLAUDE.md and THE BUILD LOOP (harness/BUILD_LOOP.md). Drive ONLY the auto-emitted plan ('harness-prompt-step --plan ./spec/app_spec.json'), firing each rendered prompt VERBATIM through the OutSystems MCP; use §Turn to drive a turn and §Recovery for symptoms. After each publish, VERIFY AT RUNTIME — never trust the Mentor summary or a no_changes_detected publish. You are DONE only when 'harness-gate ./spec/app_spec.json --base-url <deployed-url>' exits 0; keep iterating until it does. Log blockers to ./WALLS.md in the required format. If the wall cap halts you, write ./HANDOFF.md and stop." \
      --output-format stream-json \
      --permission-mode acceptEdits \
      --allowedTools "Read,Write,Edit,Bash,mcp__*"
    ;;
  *)
    echo "unknown RUN_MODE: '$RUN_MODE' (use 'session' or 'headless')" >&2
    exit 2
    ;;
esac
