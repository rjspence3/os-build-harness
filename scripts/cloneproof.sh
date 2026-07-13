#!/usr/bin/env bash
#
# cloneproof.sh — Prove the os-build-harness repo is clone-clean.
#
# Clones the repo into a fresh temp dir under a DIFFERENT name (a different
# path surfaces hardcoded absolute paths), builds a fresh venv, installs deps,
# runs the test suite + the banking CLI, and greps the cloned *.py/*.md for
# hardcoded host paths and private sibling-repo names. Prints a PASS/FAIL
# summary and exits nonzero on any defect.
#
# The full suite is expected GREEN. A pytest result of "N passed" (0 failed)
# is SUCCESS; any failure, error, or collection error is a DEFECT.
#
# SOURCE_REPO can be overridden (e.g. to point at a scratch clone) via env:
#   SOURCE_REPO=/path/to/repo scripts/cloneproof.sh
# It defaults to the repo this script lives in.
#
# Usage: scripts/cloneproof.sh
#
set -uo pipefail

# --- Configuration -----------------------------------------------------------

# Default the source to the repo this script lives in (portable — no hardcoded
# host path). Override with the SOURCE_REPO env var when needed.
readonly SOURCE_REPO="${SOURCE_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
readonly CLONE_DIRNAME="os-build-harness_cloneproof"
readonly EXPECTED_FAILS=0
# The absolute home path of whoever runs this; any occurrence in *.py is a leak.
# Override with CLONEPROOF_FORBIDDEN_PATH to check a specific author path.
readonly FORBIDDEN_PATH="${CLONEPROOF_FORBIDDEN_PATH:-$HOME}"
# Generic host-path fragments that must never ship in the public repo's *.py/*.md.
# Absolute home dirs (macOS /Users/<user>/, Linux /home/<user>/) and their
# path-slug form (-Users-<user>-). Add project-private names via CLONEPROOF_LEAK_EXTRA.
readonly LEAK_PATTERN="/Users/[^/ ]+/|/home/[^/ ]+/|-Users-[^-/ ]+-${CLONEPROOF_LEAK_EXTRA:+|}${CLONEPROOF_LEAK_EXTRA:-}"

# --- State -------------------------------------------------------------------

TMP_ROOT=""        # mktemp -d parent; cleaned up on exit
CLONE_DIR=""       # the actual clone path (TMP_ROOT/os-build-harness_cloneproof)
declare -a DEFECTS=()   # accumulated defect messages

# --- Helpers -----------------------------------------------------------------

step() { printf '\n=== %s ===\n' "$1"; }
ok()   { printf '  [OK]   %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; DEFECTS+=("$1"); }

cleanup() {
    if [[ -n "${TMP_ROOT}" && -d "${TMP_ROOT}" ]]; then
        rm -rf "${TMP_ROOT}"
        printf '\n[cleanup] removed %s\n' "${TMP_ROOT}"
    fi
}
trap cleanup EXIT

# --- Stage 1: clone into a fresh, differently-named temp dir -----------------

step "1. Clone ${SOURCE_REPO} into a fresh temp dir (different name)"

if [[ ! -d "${SOURCE_REPO}/.git" ]]; then
    fail "source repo is not a git repository: ${SOURCE_REPO}"
    printf '\nFATAL: cannot proceed without a source git repo.\n'
    exit 1
fi

TMP_ROOT="$(mktemp -d)"
CLONE_DIR="${TMP_ROOT}/${CLONE_DIRNAME}"

if git clone --quiet "${SOURCE_REPO}" "${CLONE_DIR}"; then
    ok "cloned to ${CLONE_DIR}"
else
    fail "git clone failed"
    printf '\nFATAL: clone failed; nothing else can run.\n'
    exit 1
fi

# --- Stage 2: fresh venv -----------------------------------------------------

step "2. Create fresh venv (.venv)"

VENV_PY="${CLONE_DIR}/.venv/bin/python"
VENV_PIP="${CLONE_DIR}/.venv/bin/pip"

if python3 -m venv "${CLONE_DIR}/.venv"; then
    ok "venv created"
else
    fail "python3 -m venv failed"
    printf '\nFATAL: no venv; cannot install or run.\n'
    exit 1
fi

# --- Stage 3: install requirements + editable package ------------------------

step "3. Install requirements.txt then editable package (-e .)"

if "${VENV_PIP}" install --quiet --upgrade pip >/dev/null 2>&1; then
    ok "pip upgraded"
else
    # non-fatal: an old pip can still install
    printf '  [warn] pip upgrade failed; continuing with bundled pip\n'
fi

if "${VENV_PIP}" install --quiet -r "${CLONE_DIR}/requirements.txt"; then
    ok "requirements.txt installed"
else
    fail "pip install -r requirements.txt failed"
fi

# Run editable install from inside the clone so setuptools resolves correctly.
if ( cd "${CLONE_DIR}" && "${VENV_PIP}" install --quiet -e . ); then
    ok "editable package installed (-e .)"
else
    fail "pip install -e . failed"
fi

# --- Stage 4: pytest ---------------------------------------------------------

step "4. Run pytest tests/ -q (expect: N passed, ${EXPECTED_FAILS} failed)"
# EXPECTED_FAILS is 0 — the suite is green. Any failure/error is a DEFECT.

PYTEST_OUT="$( cd "${CLONE_DIR}" && "${VENV_PY}" -m pytest tests/ -q 2>&1 )"
PYTEST_RC=$?
printf '%s\n' "${PYTEST_OUT}" | sed 's/^/  | /'

# Parse the pytest summary line. Examples:
#   "120 passed, 7 failed in 3.21s"
#   "127 passed in 3.21s"
#   "errors during collection" / "ERROR" / "no tests ran"
SUMMARY_LINE="$(printf '%s\n' "${PYTEST_OUT}" | grep -E '(passed|failed|error|no tests ran)' | tail -n 1)"

extract_count() {
    # extract_count <regex-with-capture-group> -> number or 0
    printf '%s\n' "${SUMMARY_LINE}" | grep -oE "[0-9]+ $1" | grep -oE '^[0-9]+' | head -n1
}

PASSED_COUNT="$(extract_count 'passed')"; PASSED_COUNT="${PASSED_COUNT:-0}"
FAILED_COUNT="$(extract_count 'failed')"; FAILED_COUNT="${FAILED_COUNT:-0}"
ERROR_COUNT="$(extract_count 'error(s)?')"; ERROR_COUNT="${ERROR_COUNT:-0}"

if printf '%s\n' "${PYTEST_OUT}" | grep -qiE 'errors? during collection|no tests ran'; then
    fail "pytest collection error or no tests collected (clone is broken)"
elif [[ "${ERROR_COUNT}" -gt 0 ]]; then
    fail "pytest reported ${ERROR_COUNT} error(s) — not an expected banking failure"
elif [[ "${PASSED_COUNT}" -eq 0 ]]; then
    fail "pytest reported 0 passed (suite did not run as expected)"
elif [[ "${FAILED_COUNT}" -eq "${EXPECTED_FAILS}" ]]; then
    ok "pytest: ${PASSED_COUNT} passed, ${FAILED_COUNT} failed (== ${EXPECTED_FAILS} expected banking failures)"
elif [[ "${FAILED_COUNT}" -lt "${EXPECTED_FAILS}" ]]; then
    # Fewer failures than the known baseline: surprising, flag it for review.
    fail "pytest: ${FAILED_COUNT} failed, FEWER than the ${EXPECTED_FAILS} expected — baseline drift, review"
else
    fail "pytest: ${FAILED_COUNT} failed, MORE than the ${EXPECTED_FAILS} expected — NEW failures present"
fi

# --- Stage 5: banking CLI smoke ---------------------------------------------

step "5. Run scripts/build_banking.py --list-apps (expect exit 0)"

LISTAPPS_OUT="$( cd "${CLONE_DIR}" && "${VENV_PY}" scripts/build_banking.py --list-apps 2>&1 )"
LISTAPPS_RC=$?
printf '%s\n' "${LISTAPPS_OUT}" | sed 's/^/  | /'

if [[ "${LISTAPPS_RC}" -eq 0 ]]; then
    ok "build_banking.py --list-apps exited 0"
else
    fail "build_banking.py --list-apps exited ${LISTAPPS_RC} (expected 0)"
fi

# --- Stage 6: grep for leaked host paths + private repo names ----------------

step "6. Grep clone *.py/*.md for host paths + private repo names (expect zero)"

# 6a. Hardcoded absolute home path in *.py (original guard).
HITS="$(grep -rIn --include='*.py' "${FORBIDDEN_PATH}" "${CLONE_DIR}" \
            --exclude-dir='.venv' 2>/dev/null)"

if [[ -z "${HITS}" ]]; then
    ok "no hardcoded ${FORBIDDEN_PATH} found in *.py"
else
    HIT_COUNT="$(printf '%s\n' "${HITS}" | grep -c .)"
    fail "found ${HIT_COUNT} hardcoded ${FORBIDDEN_PATH} reference(s) in *.py"
    printf '%s\n' "${HITS}" | sed 's/^/    > /'
fi

# 6b. Absolute host-home paths (/Users/<user>/, /home/<user>/, -Users-<user>-)
#     in *.py, *.md AND *.js — so this whole class of leak cannot regress.
LEAK_HITS="$(grep -rInE --include='*.py' --include='*.md' --include='*.js' "${LEAK_PATTERN}" "${CLONE_DIR}" \
            --exclude-dir='.venv' --exclude-dir='node_modules' 2>/dev/null)"

if [[ -z "${LEAK_HITS}" ]]; then
    ok "no host-path fragments or private repo names found in *.py/*.md/*.js"
else
    LEAK_COUNT="$(printf '%s\n' "${LEAK_HITS}" | grep -c .)"
    fail "found ${LEAK_COUNT} host-path / private-repo-name leak(s) in *.py/*.md/*.js"
    printf '%s\n' "${LEAK_HITS}" | sed 's/^/    > /'
fi

# --- Stage 7: cleanup is handled by the EXIT trap ----------------------------

# --- Stage 8: summary --------------------------------------------------------

step "SUMMARY"

if [[ "${#DEFECTS[@]}" -eq 0 ]]; then
    printf '  RESULT: PASS — repo is clone-clean.\n'
    exit 0
else
    printf '  RESULT: FAIL — %d defect(s):\n' "${#DEFECTS[@]}"
    for d in "${DEFECTS[@]}"; do
        printf '    - %s\n' "${d}"
    done
    exit 1
fi
