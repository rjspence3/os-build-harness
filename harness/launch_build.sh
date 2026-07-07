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
    # THE DRIVE VEHICLE (default). A normal interactive CC session in the build root — a MAIN LOOP,
    # so its fire→poll cadence across long Mentor turns is deterministic (proven end-to-end). It is
    # interactive-AUTHENTICATED: the OutSystems MCP's OAuth token (from `/mcp`) is live, so it can drive
    # Mentor. This is the vehicle for the actual build. Under Kernel, whatever spawns a worker session
    # in this dir; standalone, an interactive `claude`.
    exec claude
    ;;
  headless)
    # Fully unattended (`claude -p`). PROVEN (2026-07-07 smoke) for the CLI + doctrine + gate half: a
    # headless build-root session runs harness-prompt-step/-gate (build-root settings.json allowlist
    # inherits) and certifies the definition of done. BUT the OutSystems MCP OAuth is INTERACTIVE — a
    # COLD headless session sees `outsystems` as UNAUTHENTICATED (only authenticate/complete_authentication
    # exposed; Mentor/build tools uncallable). So headless can drive Mentor ONLY with a PRE-PROVISIONED
    # MCP token (a tenant-signed Bearer JWT the MCP client can use without an interactive OAuth round-trip).
    # Without that, use RUN_MODE=session for the drive; headless still runs the verification/gate half.
    : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY before a headless launch}"
    : "${OUTSYSTEMS_MCP_TOKEN:?headless Mentor drive needs a pre-provisioned OutSystems MCP token — a cold headless session is UNAUTHENTICATED (OAuth is interactive). Use RUN_MODE=session, or provision a tenant JWT.}"
    # DEFINITION OF DONE is machine-checked, not self-declared: complete only when
    # `harness-gate ./spec/app_spec.json --base-url <deployed-url>` exits 0. Never stop on a green
    # publish — a no-op publish (no_changes_detected) is NOT progress. Loop build→publish→verify-at-
    # runtime until the gate is DONE or the wall cap halts. bypassPermissions (not acceptEdits) is
    # required unattended: acceptEdits auto-approves edits but still PROMPTS on Bash/MCP calls and hangs.
    exec claude -p "Build this app from ./spec per your CLAUDE.md and THE BUILD LOOP (harness/BUILD_LOOP.md). Drive ONLY the auto-emitted plan ('harness-prompt-step --plan ./spec/app_spec.json'), firing each rendered prompt VERBATIM through the OutSystems MCP; use §Turn to drive a turn and §Recovery for symptoms. After each publish, VERIFY AT RUNTIME — never trust the Mentor summary or a no_changes_detected publish. You are DONE only when 'harness-gate ./spec/app_spec.json --base-url <deployed-url>' exits 0; keep iterating until it does. Log blockers to ./WALLS.md in the required format. If the wall cap halts you, write ./HANDOFF.md and stop." \
      --output-format stream-json \
      --permission-mode bypassPermissions \
      --allowedTools "Read,Write,Edit,Bash,mcp__*"
    ;;
  *)
    echo "unknown RUN_MODE: '$RUN_MODE' (use 'session' or 'headless')" >&2
    exit 2
    ;;
esac
