# home_banking build — DRIVER STATE & NEXT STEPS

You are the **driver** CC session for the home_banking clone (HD D8: a CC in this build root drives;
the strategy/context session is separate). Read this, then `MCP_RECIPES/DISPATCH_PLAYBOOK.md` +
`MCP_RECIPES/RUNBOOK.md`. Don't re-derive the process — it's all here.

## Setup (do first)
- **cwd** = this dir (`builds/home_banking/`).
- **Tool belt:** `source ../../.venv/bin/activate` (harness-verify / build_banking resolve from the
  repo venv; `pip install -e .` already done there). Scripts live at `../../scripts/`.
- **MCP auth:** run `/mcp` to authenticate the `outsystems` server in THIS session (per-session, expected).
  Confirm with `auth_status` → tenant `your-tenant`.
- **Re-render the prompts** (the `/tmp` output is ephemeral):
  `python ../../scripts/build_banking.py --app core --dry-run --out /tmp/hbcore_run`
  → batches at `/tmp/hbcore_run/core/batches/` (15 batches), 4 parked in `_deferred/`.

## Keys
- **Target app** (the clone being built): `harnessbuild_hbcore` = `bf7ed15f-1819-4a65-a6f6-4b5d8528bfd4`
- **Env**: Development = `<your-dev-env-key>`
- **Fidelity reference (the ORIGINAL — do NOT build from it, verify against it):**
  Home Banking Core = `695efc5b-8f39-4a53-8d71-35c59097d245`; Portal = `fa7ab595-f8cd-4140-8826-2acc484727b6`.
  Visual captures: `MCP_RECIPES/apps/home_banking/_raw/` + `compare/`.

## State (as of 2026-06-17, DRIVER session — data model + logic COMPLETE; wall fixes applied @ rev 17)
- `harnessbuild_hbcore` is at **rev 17**. Data model + roles + ALL action batches + the WALL-002/003 FK
  fixes published clean. Strategy rulings (`WALL_RULINGS.md`) applied; `WALLS.md` re-triaged → 0 live walls.
- **rev 17 fixes (verified live):** WALL-002 `HBAgentsProgressSteps.AgentTypeId`→HBAgentType; WALL-003 parent
  FKs restored as regular attrs (`CustomerPicture.CustomerId`, `GoalPicture.GoalId`, `HBDocumentBinary.DocumentId`).
- **WALL-001 (Employee FK)** PENDING USER IMPORT — producer pinned = `AppsCommonCore` (`4ba075ee-…`); see
  `IMPORT_INSTRUCTIONS.md`. On "Employee imported", re-add `AssignedToEmpId`→Employee on HBAccount+LoanRequest.
- WALL-004 accepted (no-op); WALL-005 accepted deferral (probe Mentor for the 4 List/Structure actions at the loan screens).
- (history) rev 16 reached after: data model + roles + 96 actions across 10 batches.
- **Done (DO NOT re-dispatch any of these — re-authoring collision-renames `*2`):**
  - `02_static_batch_01` (rev 2, pre-session) → 10 statics.
  - `02_static_batch_02` (rev 3) → 8 statics. `03_role_batch_01` (rev 4) → 3 roles.
  - `01_server_batch_01` (rev 5) + `01_server_batch_02` (rev 6) → 17 server entities. **35 entities total.**
  - `04_serveraction_batch_01..06` (rev 7–12) → 59 service actions.
  - `04_serviceaction_batch_01..04` (rev 13–16) → 37 service actions. **96 actions total.**
- **Data model VERIFIED** structurally vs original Core (695efc5b): 35/35 entities present; 4 isolated
  attribute divergences → `WALLS.md` WALL-001..004 (Employee FK cut, AgentTypeId FK, FK-as-PK→Id on 3
  entities, static mandatory drift). None block the action phase (verified against the rendered batches).
- 4 action recipes deferred (List/Structure params) → WALL-005. Action surface short by those 4 vs original.
- Every Mentor session was published then `mentor_cancel`'d (cap clean). One transient "run lost" on the
  first serveraction_01 dispatch (server-side run-registry hiccup, nothing published) → clean re-dispatch.

## Next phase = VISUAL — BLOCKED on prerequisites (escalated 2026-06-17, see WALL-006/007/008)
The visual phases (blocks/theme/screens/chrome) live in the **Portal + Backoffice UI apps**, NOT in Core.
Core (`harnessbuild_hbcore`) is data/logic only. Topology (from `app_config.yaml` + `--list-apps`): 5 apps —
core ✓, HomeBankingPortal, HomeBankingBackoffice. Prerequisites NOT met → cannot dispatch yet:
- **WALL-006:** `harnessbuild_hbportal` / `harnessbuild_hbbackoffice` DO NOT EXIST. `app_create` works over MCP
  now (Studio-gate finding superseded) — driver can create on strategy go-ahead.
- **WALL-007:** `app_config.yaml` references point Portal/Backoffice at the ORIGINAL Core (695efc5b) — must
  redirect to the CLONE core (bf7ed15f, elements are Public). 4 producer keys TBD (OutSystemsCharts,
  AgentsCommonResources=Chat, UltimatePDF, OutSystemsMaps) — pin via the original Portal `fa7ab595` refs.
- **WALL-008:** Backoffice blocks uncaptured (only HBIcon) — Backoffice not buildable; do Portal first.

Recommended path once unblocked (Portal first):
1. `app_create(name=harnessbuild_hbportal, kind=CrossDevice)`; manual warm publish if needed.
2. Import refs (Phase 0): clone core `bf7ed15f` (all_public) + OutSystemsUI elements + the pinned charts/
   agents/PDF/maps producers + AppsCommonCore. Verify with `app_refs`.
3. Portal logic (portal: 10 server + 16 client actions) → publish.
4. **Blocks** LAYOUT FIRST (LayoutBase/TopMenu families before screens) → **Theme** (theme-portal.css) →
   **Screens** (dechromed; Login/InvalidPermissions anonymous) → **Chrome wrap** (PUBLISH-GATE PER TURN) →
   **DefaultScreen=Dashboard**.
5. CDP runtime gate + `pixel_diff --tol=16` vs original Portal captures (`_raw/portal-*`,
   `clone_runtime_parity_verification_method`).
WALL-003 is now NEUTRALIZED (parent FKs restored @ rev 17) so screen-phase joins won't break on it.

## Per-batch loop (the proven mechanics — HD D8 / DISPATCH_PLAYBOOK)
1. **Dispatch via an execute-only subagent** (Principle 0: no budgets, no escape hatch wider than one
   batch, ship constraints+rationale). Subagent: load `mentor_start`+`mentor_get_run`, read the batch file,
   `mentor_start(app_key=bf7ed15f…, prompt=<file verbatim>)`, poll with cursor to terminal `succeeded`,
   read EVENTS (the `applyModelApiCode` tool_end: `compilationErrors`, `stdoutOutput`).
   **Subagent MUST return: `runId`, `mentor_session_id`, `mentor_session_token`, compilationErrors, what-it-built.**
   (The runId is required for cancel — last session it was omitted and had to be transcript-grepped.)
2. **Never cancel a mutation before terminal** (rolls it back). Let authoring finish `succeeded`.
3. **Publish from here:** `publish_start(session_id, token, env_key=<your-dev-env-key>)` → poll `publish_status` to `Finished`.
4. **`mentor_cancel(runId)`** — EVERY session, after publish (RUNBOOK §1 cap hygiene). Bulk-cancel on `per_tenant_cap_reached`.
5. **Verify** before advancing (validate-before-advance).

## Verification (fidelity = vs the ORIGINAL, not a reversed spec)
- **Persistence oracle:** `app_info(bf7ed15f…)` revision bumped = committed.
- **Read-back lag is MINUTES** (saw ~4.5 min): **poll `context_entities(app=bf7ed15f…)` until the entity
  `timestamp` advances** — never a fixed sleep.
- **Structural fidelity:** snapshot `context_entities` for BOTH the clone (`bf7ed15f`) and the original Core
  (`695efc5b`); diff entity + attribute sets (names, dataType, mandatory). Same set = structural parity.
  (`harness-verify --phase live --entities <clone-snapshot>` checks a clone snapshot against a spec; for
  clone fidelity the direct rebuild-vs-original diff is the gate.)
- **Visual fidelity (screen phases, later):** `pixel_diff` vs the original captures per
  `clone_runtime_parity_verification_method` (session-reuse auth, viewport, demo-picker, `--tol=16`).

## Walls / escalation
- `WALLS.md` here, format per the shared doctrine; the `>5` PreToolUse hook halts the session.
- Known walls + fixes: RUNBOOK §5. `spec-gap`/decision walls → escalate to the human (who relays to the
  strategy session). Do not improvise around a recipe — recipes are the hard-won plan; run verbatim.

## Cleanup debt
- No MCP app-delete. `harnessbuild_hbcore` (and `harnessbuild_looptest` from the loop test) persist on Dev —
  manual Portal cleanup. Namespace `harnessbuild_` marks them.
