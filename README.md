# os-build-harness

A build harness for **cloning and regenerating OutSystems apps end to end** via the
OutSystems **Mentor MCP** server. It drives a recipe runner against a fresh ODC app, then
**verifies the result against a known-good source of truth** — structural conformance first,
visual/pixel parity second.

The harness encodes a *proven method*, not just code: a hard-won set of recipes, an MCP
authoring loop (turn-size limits, publish-per-turn, cap hygiene, read-back-lag polling), a
wall/escalation protocol, and a runtime pixel-parity verification procedure. Those are the
parts that took the longest to get right — they live in the doctrine docs and recipe library,
which are as important as the runner.

> Extracted from a working lab and curated for reuse. The **`home_banking`** build is the
> complete worked example / benchmark (build #0); it clones an OutSystems first-party demo app.

## What's here

```
harness/
  banking_runner/    # the recipe runner — renders recipes → Mentor MCP batches, tracks state
  schemas/           # app_spec.v0.json — the spec schema for spec-driven builds
  cdp_helpers.py     # CDP (Chrome DevTools) connection helpers for runtime capture
  capture.py verify.py prompt_step.py   # harness-capture / harness-verify / harness-prompt-step
  CLAUDE.md          # SHARED DOCTRINE — the build loop, walls protocol, authoring patterns
builds/
  home_banking/      # build #0 — the reference clone (OutSystems demo app)
    MCP_RECIPES/     # the recipe library + DISPATCH_PLAYBOOK + RUNBOOK + per-app captures
    theme/
  _template/         # starting point for a new build root
assets/              # shared OutSystems UI / FontAwesome / ECharts bundle (vendored, see LICENSEs)
scripts/             # build_banking.py (entrypoint) + render/diff/capture tooling
tests/               # banking_runner unit tests
HARNESS_DECISIONS.md # the architectural decision log
ROADMAP.md           # where this is headed (generalizing the runner into a spec-driven harness)
```

## Two build modes

The harness supports two ways of defining "the source of truth" — a build root's own
`CLAUDE.md` declares which applies:

- **recipe / clone** — the source of truth is a hardened recipe library **plus the original
  app**. Recipes drive Mentor; fidelity is verified by **`pixel_diff`** against the original's
  runtime captures. `home_banking` is this mode.
- **spec-driven** — the source of truth is an `app_spec` (see `harness/schemas/app_spec.v0.json`);
  structure is verified with `harness-verify`. (This is the direction the roadmap generalizes toward.)

## Requirements

- Python 3.10+
- An **OutSystems ODC tenant** with the **Mentor MCP** server available, and authority to
  create/modify apps in it. The harness is the *only* actuator — it builds entirely through the MCP.
- `node`/`npx` (the runner spawns `mcp-remote` to reach the tenant MCP endpoint).
- For runtime/pixel capture: Google Chrome reachable on `--remote-debugging-port=9222`, plus
  `playwright` (imported lazily by the CDP scripts).

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# No tenant needed for these — they exercise the runner offline:
pytest tests/ -q
python scripts/build_banking.py --list-apps
python scripts/build_banking.py --app core --dry-run --out /tmp/hb_run
#   → rendered Mentor batches land under /tmp/hb_run/core/batches/
```

Configure your tenant before any **live** run:

```bash
cp .env.example .env
# edit .env → set OUTSYSTEMS_MCP_TENANT=<your-tenant>.outsystems.dev
```

Then authenticate the `outsystems` MCP server in your session and drive a build following the
loop in **`harness/CLAUDE.md`** + **`builds/home_banking/MCP_RECIPES/DISPATCH_PLAYBOOK.md`**.

## The method, in one breath

Build the next unit of work via the MCP → **verify against live system state** (never trust that
a step worked because a doc said it would) → pass and continue, or log a **wall** and attempt one
bounded recovery. Keep Mentor authoring turns small (≤ ~1 screen-section) and **publish per turn**;
**cancel every Mentor session after publish** (cap hygiene); treat read-back lag as *minutes* and
poll `context_entities` rather than sleeping. Seed realistic data before chasing pixels — parity is
meaningless on empty screens. The full doctrine is in `harness/CLAUDE.md`.

## Caveats

- **7 unit tests fail and are pre-existing** (test-vs-code API drift inherited from the original
  monorepo, e.g. a renderer returning a 3-tuple while a test unpacks 2). They are not setup
  artifacts; fixing them is open work.
- `banking_runner` was built around the `home_banking` clone and is **not yet generalized** — paths
  resolve to `builds/home_banking/`. Mirror that layout under `builds/<name>/` and parameterize when
  adding a build (see `ROADMAP.md`).
- Captures, snapshots, and tenant/app identifiers in `builds/home_banking/` are example artifacts
  from the reference build; point the harness at your own tenant and apps.

## License

MIT — see [LICENSE](LICENSE). Vendored assets under `assets/` carry their own upstream licenses
(OutSystems UI, Font Awesome, ECharts); see the `LICENSE`/`VERSION` files in each.
