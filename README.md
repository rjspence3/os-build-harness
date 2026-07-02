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

**New here? Read [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md).** It takes you from
clone → install → your first build, and explains the one thing the rest of this README assumes:

## How it works (read this first)

This is **not** a `python build.py` that emits an app. The harness is a *tool belt* driven by an
orchestrator, and **the orchestrator is a [Claude Code](https://claude.com/claude-code) session
running inside a build root** (`builds/<app>/`). That session is the CPU; the harness pieces are
its program:

- the **OutSystems Mentor MCP** is the *only* actuator — every entity, screen, and action is
  authored by the session calling the MCP;
- the **recipes / app spec** are the source of truth for what to build;
- **`harness-verify`** / **`pixel_diff`** are the judge — they confirm built state against that
  source of truth.

The Python CLIs (`scripts/build_banking.py`, `harness-verify`, …) **prepare and check** work; they
don't author the app. So there's an important boundary:

- **Offline** (runs anywhere, no tenant): render recipe batches (`--dry-run`), validate a spec
  (`harness-verify --phase spec`), run the unit tests.
- **Live** (needs your ODC tenant + an authenticated MCP session in Claude Code): actually build,
  publish, and verify.

## What's here

```
harness/
  banking_runner/    # the recipe runner — renders recipes → Mentor MCP batches, tracks state
  schemas/           # app_spec.v0.json — the spec schema for spec-driven builds
  cdp_helpers.py     # CDP (Chrome DevTools) connection helpers for runtime capture
  capture.py verify.py prompt_step.py   # harness-capture / harness-verify / harness-prompt-step
  CLAUDE.md          # SHARED DOCTRINE — the build loop, walls protocol, authoring patterns
  launch_build.sh    # scaffolds builds/<app>/ from _template and starts a build session
builds/
  home_banking/      # build #0 — the reference clone (OutSystems demo app)
    MCP_RECIPES/     # the recipe library + DISPATCH_PLAYBOOK + RUNBOOK + per-app captures
    theme/
  _template/         # starting point for a new build root (see its README)
docs/                # GETTING_STARTED.md — the onboarding walkthrough
examples/            # task_tracker/app_spec.json — a complete, validated example spec
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

- **Python 3.11+**
- **[Claude Code](https://claude.com/claude-code)** — the orchestrator that drives the build loop.
  *(The offline commands below need none of the items past this point.)*
- An **OutSystems ODC tenant** with the **Mentor MCP** server available, and authority to
  create/modify apps in it. The harness is the *only* actuator — it builds entirely through the MCP.
- `node`/`npx` (the runner spawns `mcp-remote` to reach the tenant MCP endpoint).
- For runtime/pixel capture: Google Chrome reachable on `--remote-debugging-port=9222`, plus
  `playwright` (imported lazily by the CDP scripts).

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .          # installs the harness-verify / harness-capture / harness-prompt-step CLIs

# No tenant needed for these — they exercise the harness offline:
pytest tests/ -q                                                  # → 173 passed
python scripts/build_banking.py --list-apps                       # the home_banking manifest
python scripts/build_banking.py --app core --dry-run --out /tmp/hb_run
#   → rendered Mentor batches land under /tmp/hb_run/core/batches/
harness-verify examples/task_tracker/app_spec.json --phase spec   # validate a spec, offline
```

To go **live** you need an OutSystems ODC tenant with the **Mentor MCP** enabled
(it may be in preview — confirm on your tenant). Register the MCP once, then run one
build session per app:

```bash
# 1. register the OutSystems Mentor MCP (user scope); endpoint = your tenant's host:
claude mcp add --transport http outsystems https://<your-tenant>.outsystems.dev/mcp -s user

# 2. scaffold builds/my_app/ from the example spec and start a build session IN it:
harness/launch_build.sh my_app examples/task_tracker
```

Inside that session run `/mcp` to complete the OAuth login, then drive the loop per
**`harness/CLAUDE.md`** + **`builds/home_banking/MCP_RECIPES/DISPATCH_PLAYBOOK.md`**.
**Run model:** one Claude Code session per build, cwd = `builds/<app>/` — that's where
the doctrine, the wall-cap, your MCP auth, and the captured run all apply; no central
orchestrator needed. **See [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) for
the full walkthrough** (incl. the Mentor-MCP access caveat).

## The method, in one breath

Build the next unit of work via the MCP → **verify against live system state** (never trust that
a step worked because a doc said it would) → pass and continue, or log a **wall** and attempt one
bounded recovery. Keep Mentor authoring turns small (≤ ~1 screen-section) and **publish per turn**;
**cancel every Mentor session after publish** (cap hygiene); treat read-back lag as *minutes* and
poll `context_entities` rather than sleeping. Seed realistic data before chasing pixels — parity is
meaningless on empty screens. The full doctrine is in `harness/CLAUDE.md`.

## Caveats

- The full unit suite passes (`pytest tests/ -q` → 173 passed). The renderers are pure
  (AST → C# string), so the tests run offline with no tenant or live Mentor dispatch.
- `banking_runner` was built around the `home_banking` clone and is **not yet generalized** — paths
  resolve to `builds/home_banking/`. Mirror that layout under `builds/<name>/` and parameterize when
  adding a build (see `ROADMAP.md`).
- The `home_banking` build is a worked example to **study**, not a push-button reproducible build:
  its live verification compares against the original Home Banking app and tenant-specific app keys
  that exist only in the author's tenant. The recipes, doctrine, and offline `--dry-run` are fully
  usable; the exact live clone is not re-runnable without that original app present.
- Captures, snapshots, and tenant/app identifiers in `builds/home_banking/` are example artifacts
  from the reference build; point the harness at your own tenant and apps.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, keeping the suite green, where doctrine vs
build-specific notes belong, and how to add a build.

## License

MIT — see [LICENSE](LICENSE). Vendored assets under `assets/` carry their own upstream licenses
(OutSystems UI, Font Awesome, ECharts); see the `LICENSE`/`VERSION` files in each.
