# Banking app rebuild runner

Drives `data/MCP_RECIPES/` against fresh OutSystems apps to reconstruct the
Home Banking suite (Core + Portal + Backoffice + LoanRequest + Mobile) from
the per-app YAML manifests at `data/MCP_RECIPES/apps/home_banking/`.

## Status

| Phase | What it does | State |
|---|---|---|
| A | Manifest loader + recipe renderer + dry-run CLI | ✅ Done |
| B | MCP client + SQLite state DB + orchestrator + manual gates | ✅ Wired (untested e2e) |
| C | End-to-end run against fresh apps; iterate on Mentor edge cases | 🚧 Pending — needs user to Portal-create empty apps |

## Phase A — what works today

```bash
python scripts/build_banking.py --list-apps
python scripts/build_banking.py --app core --dry-run
python scripts/build_banking.py --app all --dry-run --out /tmp/run
```

Renders 190 prompts to disk (Core 138 + Portal 26 + Backoffice 26). Each prompt
is a paste-ready Mentor MCP `applyModelApiCode` body wrapped with
`PROMPT_PREAMBLE`. Filenames are sortable by recipe stage so the orchestrator
can drive them in order.

**Verified against `HBCustomer`**: 21 attributes in manifest → 21 AddX call
sites in rendered C# (AddText for Email/Phone Number, AddCurrency for
AnnualIncome, AddDate for BirthDate/EmploymentStartDate, AddIdentFk for User /
HBBranch / HBCustomer / Employee, etc.).

## Architecture

```
pipeline/banking_runner/
├── __init__.py
├── manifest.py        ← YAML loaders for entities, roles, actions, screens
├── recipe.py          ← recipe template loader + C# block generators
├── mcp_client.py      ← (Phase B) HTTP client for OutSystems MCP
├── state.py           ← (Phase B) SQLite state DB for resume / idempotency
├── gate.py            ← (Phase B) manual-gate UX for Portal/Studio steps
└── orchestrator.py    ← (Phase B) phase coordinator + parallel dispatch

scripts/build_banking.py   ← CLI entry point

data/banking_runner_out/   ← rendered prompts (gitignored)
data/runner_state.db       ← (Phase B) SQLite state file
```

## Phase A gaps to close before Phase B

Documented here so they're not forgotten when wiring MCP:

1. **Action-stub FK resolution**: Recipe 04 template only pre-declares
   `userIdentType`. Other FK types referenced by action params currently render
   with undeclared variables. Fix: auto-inject FK resolution block at the top
   of render_action_stub like render_server_entity does.

2. **Screen renderers (Recipes 07-09, 12-15)**: not implemented. Highest
   complexity due to widget tree generation. Reference: `_raw/*.flat.txt` for
   per-screen widget inventories.

3. **Theme renderer (Recipe 10)**: not implemented. Trivial — read CSS file +
   slot into `{{CSS_CONTENT}}`.

4. **Default screen renderer (Recipe 11)**: not implemented. Trivial — needs
   target screen name + flow name.

5. **Publish verify renderer (Recipe 99)**: not implemented. Needs expected
   counts per phase, pulled from manifest totals.

## Phase B — what works today

```bash
# Render prompts to disk + queue in state DB + drive MCP
python scripts/build_banking.py --app core --run

# Check state DB at any time
python scripts/build_banking.py --status --app core

# Resume after crash — the state DB skips already-succeeded calls
python scripts/build_banking.py --app core --run --app-key <existing-key>
```

The runner spawns `npx -y mcp-remote https://your-tenant.outsystems.dev/mcp`
as a stdio subprocess. First run pops a browser for OAuth (handled by
mcp-remote); subsequent runs reuse the cached token.

Modules:
- `state.py` — SQLite DB with `recipe_calls` + `gates` tables, idempotent
  upserts, per-status counts. Tested independently.
- `gate.py` — terminal-prompt UX for the 4 manual-gate kinds: portal_create,
  studio_warmup, manage_deps, role_assign. Pre-built gate factories for the
  banking suite.
- `mcp_client.py` — `MentorMCP` async context manager wrapping mcp-remote.
  Exposes mentor_start / mentor_poll / publish_start / publish_wait /
  context_entities + 4 other context_* tools.
- `orchestrator.py` — `Orchestrator.build_app(AppConfig)` drives one app end
  to end: pre-flight gates → phase 1 (statics) → publish → phase 2 (server
  entities) → publish → ... → phase 6 (verify). Halts on first failure to
  avoid cascading bad state. Default 3-concurrent within a phase.

## Phase B — open questions before implementation

1. **MCP transport + auth**: OutSystems MCP server URL? Bearer JWT obtained
   how (OAuth flow? export from existing Claude Code session)? Python `mcp`
   package vs raw httpx?

2. **Parallelism limits**: per `[[odc_mcp_app_refs_parallel_wall]]` only
   `app_refs` was rate-limited; `context_*` and `mentor_*` tolerate at least
   parallel-5. Runner should default to 3 concurrent Mentor sessions to leave
   headroom.

3. **State recovery**: on restart, query the live app via `context_entities`
   + `context_actions` + `context_screens` and reconcile against the state DB.
   Items present in app but not in state → add to state (someone built them
   externally). Items in state but not in app → mark for rebuild.

4. **Manual gates UX**: terminal prompt `Please do X in Portal/Studio, then
   press Enter` is the simplest. Could be a TUI later but not v1.

5. **Recipe call failure recovery**: per `[[odc_mcp_cascading_validation_auto_fix]]`
   Mentor sometimes auto-fixes compile errors with 3-4 same-turn iterations.
   The runner should let those play out before deciding "failed". Decision
   tree: succeeded → next; transient compile error → retry once; runtime
   error → pause + ask user.

## Phase C — what "identical" looks like at the end

Per the spec the user set: **structurally identical** (same entity/action/role/
screen names + types + signatures), not byte-equivalent OML.

Verification gates:
- Per-app `context_*` counts match manifest totals (`Recipe 99`).
- Spot-check 5 entities + 5 actions via `getEntity` / `getAction` Mentor reads;
  compare attribute set and parameter list against manifest.
- Login + click through (via Playwright per project's existing
  `test_prototype_production.py` pattern) to verify the app actually works.

## Cost / time estimate

Per phase A's 190 prompts + future screens (16) + themes (3) + default screens
(per-app) + publish verify (per-phase) ≈ ~215 Mentor calls total. At ~2 min
per call serial, ~17 hours. With 3-concurrent parallelism, ~6 hours.
