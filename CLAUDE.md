# buildHarness

Build harness for cloning/regenerating OutSystems apps via the Mentor MCP. Consumes app specs
(today: hand-authored recipe libraries; future: specs produced by the `kyleCohorts` spec factory)
and drives a recipe runner against fresh ODC apps, diffing the result against a known-good original.

Split out of the former `kyleAccounts` monorepo on 2026-06-16. Sibling repos:
`kyleCohorts` (spec factory) and `mentorMCP` (MCP doctrine / findings).

## Layout

```
harness/
  banking_runner/    # the recipe runner (relocated from pipeline/banking_runner; NOT generalized)
  CLAUDE.md          # harness-level doctrine + follow-on phase notes
builds/
  home_banking/      # build #0 — the home_banking clone benchmark (the known-good original)
    MCP_RECIPES/     # recipe library + manifests + _raw screen captures
    theme/ banking_runner_out/ compare/
assets/              # SHARED OutSystems UI / FontAwesome / ECharts bundle (harness-level)
scripts/             # build_banking.py + render/diff tooling + CDP capture scripts
tests/               # banking_runner unit tests
```

## Path convention (IMPORTANT — changed during the split)

`banking_runner` resolves recipes/manifests via `Path(__file__).resolve().parents[2] / "builds" /
"home_banking" / "MCP_RECIPES"` (was `…/ "data" / "MCP_RECIPES"` in the monorepo). `build_banking.py`'s
`--out`/`--state-db`/theme paths default under `builds/home_banking/` too. If you add a new build,
mirror this layout under `builds/<name>/` and parameterize the dirs (don't hardcode home_banking).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # pyyaml, mcp, Pillow, playwright, python-dotenv, pytest
pytest tests/ -q                  # banking_runner unit tests
python scripts/build_banking.py --list-apps
python scripts/build_banking.py --app core --dry-run
```

Note: 7 tests fail and are PRE-EXISTING (inherited from the monorepo — test-vs-code API drift, e.g.
`render_fk_resolution_block` returns a 3-tuple while a test unpacks 2). They are NOT migration
artifacts; fixing them is follow-on work, not part of the split.

## Vendored helper — `cdp_helpers`

The `cdp_*` capture scripts import `connect_with_retry` + `is_chrome_available` from
`harness/cdp_helpers.py`, **vendored** (2026-06-16) from the canonical `kernel/scripts/cdp_helpers.py`
so the repo is clone-clean with no off-repo path. The vendored file carries a provenance header; sync
it manually if the kernel original changes. The scripts add the repo root to `sys.path` and import
`from harness.cdp_helpers import ...`. They still need Chrome on `--remote-debugging-port=9222` and
`playwright` in the venv (playwright is imported lazily inside `cdp_helpers`).

## Follow-on (next phase — see harness/CLAUDE.md)

Generalizing `banking_runner` into a spec-driven harness, the spec schema, the build→check-against-spec
loop, and `WALLS.md` escalation. Not implemented in the split.
