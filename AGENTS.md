# AGENTS.md — instructions for an AI agent using this repo

You are an AI coding agent (Claude Code, Cursor, etc.) helping a user build **production
OutSystems Developer Cloud (ODC) apps** with this harness. This file tells you how to set the
repo up and how to guide the user. Read it fully before acting. Human-oriented docs:
[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) and [`docs/ODC_GOTCHAS.md`](docs/ODC_GOTCHAS.md).

## What this is (say this to the user in one breath)

A harness that turns an **app spec** into a built, published ODC app. It does *not* generate code
you paste; it drives OutSystems' **Mentor MCP** (the only thing that writes to the tenant) with
**recipes** — prompt builders that encode hard-won ODC corrections — and verifies the result
against the spec. The authoring engine is an LLM, so this is *deterministic orchestration over a
stochastic actuator*: fast, pre-corrected, but the output still deserves a review.

## Step 1 — set up (do this before anything live)

Run these and report results to the user; stop and ask if a prerequisite is missing.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .   # installs harness-verify / -capture / -prompt-step
pytest tests/ -q                                       # sanity: the suite must pass offline
```

Then the **live** prerequisites (the harness can't build without these — confirm each with the user):
1. An **ODC tenant** with the **Mentor MCP** available (it may be preview/limited on their tenant).
2. `node`/`npx` (the runner spawns `mcp-remote` to reach the tenant MCP).
3. Tenant configured: `export OUTSYSTEMS_MCP_TENANT=<their-tenant>.outsystems.dev` — there is **no
   working default** (`your-tenant.outsystems.dev` is a placeholder; a build will fail to connect
   until this is set).
4. MCP auth: register once (`claude mcp add --transport http outsystems
   https://<tenant>.outsystems.dev/mcp -s user`) and complete the OAuth login (`/mcp`). Tokens
   expire (~24h) — if a build errors on "connection closed / re-authorize," have the user re-auth.

Everything that doesn't touch the tenant (validate a spec, `--plan-only`, `--dry-run`, the tests)
works with no tenant — use it to make progress and to show the user results before spending sessions.

## Step 2 — guide the user (the recommended workflow)

Don't ask the user to write a spec cold. Drive this loop:

1. **Understand the app.** Ask what they want (entities, screens, roles, one clear user flow). Keep
   the first app **small** — one Core or one CrossDevice app. Modular multi-app comes later.
2. **Write the spec together.** Copy a validated example (`examples/task_tracker/app_spec.json`) and
   adapt it to their domain. Validate offline continuously: `harness-verify <spec> --phase spec`.
   The schema is `harness/schemas/app_spec.v0.json`.
3. **Preview offline before spending a live session.** `python -m harness.run_build <spec>
   --plan-only` prints the step plan; `--dry-run` renders the prompts. Show the user what will be
   built.
4. **Build.** `python -m harness.run_build <spec> --create --name <App> --kind CrossDevice --tenant
   $OUTSYSTEMS_MCP_TENANT --state /tmp/<app>.state.json`. It's resumable (re-run to continue) and
   cap-aware. For a modular producer+consumers system, use `python -m harness.build_system` with a
   `domain_spec` (see GETTING_STARTED "Path A+"). Drive long builds in the background and watch the
   StateDB, not the noisy MCP log.
5. **Verify, don't assume.** After it publishes, confirm against LIVE state — never report "done"
   because a step *said* it succeeded (`no_changes_detected` and success flags are unreliable; trust
   `app_info.revision` + a new `modelDigest`, and `context_*`/a browser screenshot). Open the app.
6. **When it falls short, fix it — then harvest.** If you hand-fix a recipe gap, feed it back:
   change the recipe + add a pinning test + record it (`python -m harness.learning`). That loop is
   the point — the harness improves and never silently regresses.

## Rules you must follow

- **Read [`docs/ODC_GOTCHAS.md`](docs/ODC_GOTCHAS.md) before the first live build.** It lists the ODC
  walls that only surface at publish/runtime (cross-app entity publicity → `OS-BEW-COMP`,
  `OS-DPL-50205` on public writes/block-nav, native chart widgets, theme resets, `IsInDevStage`
  doesn't exist, BPT limits, read-back lag, the 100-session cap). The recipes encode these; know them.
- **Session cap is 100/tenant, cluster-wide.** Don't spawn one session per step by hand — the runners
  reuse one session per build. A heavy day saturates the cap for ~24h. If a build halts on
  `per_tenant_cap_reached`, it's resumable; wait or pause other Mentor work.
- **On a build-engine crash (`OS-BEW-*`, `OS-APPS-40028`), rebuild fresh — do not retry in place**
  (retries corrupt the OML). The runner halts fast with this guidance; heed it.
- **Never fabricate success.** Verify against live state. Surface failures with the real error code.
- **Don't push to a remote or delete apps without the user asking.** Disposable dev apps are fine to
  create; deletes and deploys are the user's call.

## Where to look

- [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) — install, MCP setup, the build paths.
- [`docs/ODC_GOTCHAS.md`](docs/ODC_GOTCHAS.md) — the ODC production walls + how the recipes handle them.
- [`harness/RECIPE_GAPS.md`](harness/RECIPE_GAPS.md) — what the recipes cover vs. don't (ODC REST, chart types, forms).
- [`harness/HARVEST_LEDGER.md`](harness/HARVEST_LEDGER.md) — the harness's self-improvement log.
- [`harness/prompt_recipes.py`](harness/prompt_recipes.py) — the recipe catalog (the `RECIPES` dict).
- [`harness/CLAUDE.md`](harness/CLAUDE.md) — the build-loop doctrine (turn size, verify-before-assert, cap hygiene).
