# Getting Started

This guide takes you from `git clone` to driving your first build. Read the
[mental model](#mental-model) first — it's the thing most newcomers miss, and
everything else depends on it.

---

## Mental model

**This is not a `python build.py` that emits an app.** The harness is a *tool belt*
driven by an orchestrator. The orchestrator is a **Claude Code session running
inside a build root** (`builds/<app>/`). That session is the CPU; the pieces below
are its program:

| Piece | Role | Analogy |
|---|---|---|
| **Claude Code session** | the orchestrator that reads the doctrine and drives the loop | the CPU |
| **OutSystems Mentor MCP** | the *only* actuator — every entity/screen/action is authored through it | the hands |
| **recipes / app spec** | the source of truth for what to build | the program |
| **`harness-verify` / `pixel_diff`** | the judge — confirms built state against the source of truth | the test oracle |

The Python CLIs (`scripts/build_banking.py`, `harness-verify`, etc.) **prepare and
check** work; they do not author the app. Authoring happens when the Claude Code
session calls the MCP. Keep this offline-vs-live boundary in mind:

- **Offline** (no tenant, runs anywhere): render recipe batches (`--dry-run`),
  validate a spec (`harness-verify --phase spec`), run the unit tests.
- **Live** (needs your ODC tenant + an authenticated MCP session): actually build,
  publish, and verify against live state.

---

## Prerequisites

- **Python 3.11+**
- **[Claude Code](https://claude.com/claude-code)** — the orchestrator. (A different
  MCP client could work, but the doctrine, hooks, and `launch_build.sh` assume Claude Code.)
- An **OutSystems ODC tenant** with the **Mentor MCP** server, and authority to
  create/modify apps in it. *(Everything in the [Offline](#1-offline-no-tenant-needed)
  section works without this.)*
- **node / npx** — the runner spawns `mcp-remote` to reach the tenant MCP endpoint.
- *(Optional, for runtime/pixel capture)* Google Chrome on `--remote-debugging-port=9222`.

---

## Install

```bash
git clone https://github.com/rjspence3/os-build-harness.git
cd os-build-harness
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .          # installs the harness-verify / harness-capture / harness-prompt-step CLIs
```

---

## 1. Offline — no tenant needed

Get a feel for the harness before wiring up a tenant. All of this runs anywhere:

```bash
# Run the unit suite (pure AST → C# renderers; no live calls)
pytest tests/ -q                                   # → 173 passed

# Inspect the home_banking reference build's manifest
python scripts/build_banking.py --list-apps

# Render the Mentor authoring batches for one app, WITHOUT building anything
python scripts/build_banking.py --app core --dry-run --out /tmp/hb_run
#   → batches land under /tmp/hb_run/core/batches/ — open one to see the C# the MCP would run

# Validate the example app spec (schema + cross-references)
harness-verify examples/task_tracker/app_spec.json --phase spec
#   → PASS — app_spec.json conforms to app_spec.v0 (schema + cross-refs).
```

If those four work, your install is good.

---

## 2. Connect the OutSystems Mentor MCP

The harness authors your app through OutSystems' **Mentor MCP** — an ODC-hosted
remote MCP server that is the *only* thing that writes to your app. To use it you
need **(a)** an OutSystems ODC tenant and **(b)** the Mentor MCP enabled on it.
(The Mentor MCP is an ODC capability; confirm it is available on your tenant — it
may be in preview / limited release.)

Its endpoint is your tenant's control-plane host,
`https://<your-tenant>.outsystems.dev/mcp`. Register it once at **user scope** so
every build session can see it:

```bash
claude mcp add --transport http outsystems https://<your-tenant>.outsystems.dev/mcp -s user
```

Then, **inside a Claude Code session, run `/mcp`** and complete the OAuth login in
your browser (against your tenant). Confirm it connected:

```bash
claude mcp get outsystems   # → Status: ✔ Connected · Type: http
```

Optionally, for the `banking_runner` / CDP-capture scripts, also set the tenant in `.env`:

```bash
cp .env.example .env
# edit .env → OUTSYSTEMS_MCP_TENANT=<your-tenant>.outsystems.dev
```

**How you run a build (the model):** **one Claude Code session per build, with its
cwd inside `builds/<app>/`** — exactly what `launch_build.sh` (next section) gives you.
You do **not** need a central orchestrator: the build's doctrine
(`builds/<app>/CLAUDE.md` → `@import harness/CLAUDE.md`), the wall-cap safety hook,
your authenticated MCP, and the run's captured state all key off that working
directory. See [`harness/CLAUDE.md`](../harness/CLAUDE.md) for the loop mechanics
(turn size, publish-per-turn, cap hygiene, read-back-lag polling).

---

## 3. Pick a path

The harness supports two ways of defining "the source of truth."

### Path A — spec-driven (build your own app)

Best starting point for a brand-new app. The flow:

1. **Write a spec** conforming to [`harness/schemas/app_spec.v0.json`](../harness/schemas/app_spec.v0.json).
   Start by copying the validated example:
   ```bash
   mkdir -p builds/my_app/spec
   cp examples/task_tracker/app_spec.json builds/my_app/spec/app_spec.json
   # edit it, then validate offline as you go:
   harness-verify builds/my_app/spec/app_spec.json --phase spec
   ```
2. **Scaffold + launch** the build root (creates `builds/my_app/` from `builds/_template/`,
   copies your spec, and starts a Claude Code session in it):
   ```bash
   harness/launch_build.sh my_app builds/my_app/spec
   ```
3. **Drive the loop.** Inside that session, Claude Code follows the doctrine in
   `builds/my_app/CLAUDE.md` (which `@import`s `harness/CLAUDE.md`): take the next
   unit of work from the spec → build it via the MCP → verify with
   `harness-verify <spec> --phase live` → continue or log a wall.
   *(Note: the `--phase live` executors and `harness-capture` are honest stubs today —
   they report `not-implemented` rather than silently passing. Until they land, verify
   built state at runtime yourself: query the MCP / inspect the published app / eyeball
   the screen. Offline `--phase spec` validation is fully implemented.)*

> The spec-driven runner is still being generalized (see [`ROADMAP.md`](../ROADMAP.md));
> the doctrine and verifier are the mature parts. Expect to drive more of the loop by
> hand than the recipe/clone path.

### Path B — recipe/clone (study the worked example)

`builds/home_banking/` is the fully worked reference build (build #0): a hardened
recipe library (`MCP_RECIPES/`) that clones an OutSystems first-party demo app and
verifies fidelity with `pixel_diff` against the original's captures.

It is the best place to learn the *method* — read `MCP_RECIPES/DISPATCH_PLAYBOOK.md`
and `MCP_RECIPES/RUNBOOK.md`. **Note it is not push-button reproducible** in your
tenant: verification compares against the original Home Banking app and tenant-specific
app keys that only exist in the author's tenant. You can study every recipe, run the
offline `--dry-run`, and adapt the pattern — but you can't re-run the exact live clone
without that original app present.

---

## 4. When you hit a wall

Builds log blockers to `./WALLS.md` in the build root using the format in
`harness/CLAUDE.md`. A PreToolUse hook (`.claude/hooks/walls-cap.py`) halts the
session at more than 5 open walls — that's the safety brake, not a bug. Resolve or
accept walls to free the cap. The doctrine's "validate before you assert" rule is the
core discipline: never record a step as done until verification against live state
confirms it.

---

## Where to read next

- [`harness/CLAUDE.md`](../harness/CLAUDE.md) — the shared build-loop doctrine (start here for the loop).
- [`builds/home_banking/MCP_RECIPES/DISPATCH_PLAYBOOK.md`](../builds/home_banking/MCP_RECIPES/DISPATCH_PLAYBOOK.md) — the canonical turn loop.
- [`builds/home_banking/MCP_RECIPES/RUNBOOK.md`](../builds/home_banking/MCP_RECIPES/RUNBOOK.md) — cap hygiene + known walls and fixes.
- [`HARNESS_DECISIONS.md`](../HARNESS_DECISIONS.md) — why the architecture is the way it is.
- [`ROADMAP.md`](../ROADMAP.md) — where the harness is headed.
