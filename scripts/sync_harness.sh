#!/usr/bin/env bash
# Sync the canonical harness engine + docs from THIS repo (public os-build-harness) to the
# private lab and any clean clones, then run the test suite in each to catch drift.
# Closes gap #7 (3-repo hand-sync drift). Usage: scripts/sync_harness.sh [target_dir ...]
# With no args, syncs the default targets below (edit to taste). Canonical source = this repo.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"

# Curated canonical file list (the engine + tests + docs I hand-sync). Add rows as the harness grows.
FILES=(
  harness/prompt_recipes.py
  harness/capture.py
  harness/verify.py
  harness/prompt_step.py
  harness/schemas/app_spec.v0.json
  harness/BUILD_LOOP.md
  harness/SEAMS.md
  harness/CAPABILITY_MATRIX.md
  harness/GAP_CLOSURE_PLAN.md
  harness/reference/BANKING_MINED.md
  tests/test_prompt_step.py
  tests/test_capture.py
)

# Default targets: the private lab, and a clean clone if present.
DEFAULT_TARGETS=(
  /Users/rob/Development/buildHarness
  /tmp/obh_clean_e2e
)
TARGETS=("${@:-}")
[ -z "${TARGETS[0]:-}" ] && TARGETS=("${DEFAULT_TARGETS[@]}")

echo "== sync_harness: source = $SRC"
for T in "${TARGETS[@]}"; do
  [ -d "$T" ] || { echo "  SKIP $T (not present)"; continue; }
  echo "== target: $T"
  for f in "${FILES[@]}"; do
    if [ -f "$SRC/$f" ]; then
      mkdir -p "$T/$(dirname "$f")"
      cp "$SRC/$f" "$T/$f"
      echo "   synced $f"
    fi
  done
  # Parity check: run the prompt/capture tests in the target's own venv if it has one.
  if [ -x "$T/.venv/bin/python" ]; then
    echo "   pytest (target venv):"
    ( cd "$T" && .venv/bin/python -m pytest tests/test_prompt_step.py tests/test_capture.py -q 2>&1 | tail -1 )
  fi
done
echo "== done. Review + commit each target repo."
