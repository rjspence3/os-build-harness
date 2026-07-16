<!-- The authoritative coverage map for "the harness can build ANY ODC app, first-try."
     Two axes of DONE: (1) 0% THRASH — every unit lands first-try, and (2) FULL COVERAGE —
     a recipe + plan-rule + verifier for every ODC construct. Drive every row to ✓/✓/✓.
     Sources: live osMCP capability retests + the from-scratch task_tracker build (iteration 3).
     Keep in lockstep with harness/prompt_recipes.py (RECIPES), plan_from_spec, and verify/capture. -->

# ODC CAPABILITY MATRIX — brains + wiring for everything, zero thrash

**Status legend**
- Recipe: ✓ first-try recipe in `prompt_recipes.py` · ~ proven inline in a build (no recipe yet) · ○ doctrine/notes only · ✗ none
- Plan: ✓ `plan_from_spec` emits it from the spec · ~ partial · ✗ not emitted (hand-driven)
- Verify: ✓ structural (`--assert`/`--phase live`) or behavioral (`--behavioral`) check · ~ partial · ✗ none
- Thrash: the PROVEN first-try authoring note (decomposition / `change_applied` gate / bake-in). ⚠ = known to cascade/phantom until the note is followed.

**The 0%-thrash invariants (apply to EVERY row).** These are the discipline half of "done":
1. **Trust `change_applied`, not the narrative.** A turn is a no-op unless `change_applied=true`; on `false`, re-author in a FRESH session (phantom/wedge — R7). Verify the artifact at runtime, never the summary.
2. **One concern per committing turn.** Never combine structural-create with per-element edits, or seed with UI — that cascades 25–45 min (R1).
3. **Author interdependent things together, dependent things in sequence.** All entities in ONE turn; a screen's widgets before its wiring.
4. **Bake required properties at creation** (Anonymous, `data-spec-id`, pinned aggregate names) so no second "fix-up" turn is ever needed.
5. **Publish once per logical group**, at a VALID model; resume a session to finish a multi-turn unit before publishing (widgets→wire).
6. **Mentor MCP authoring auto-deploys**; an explicit publish then reads `no_changes_detected` — verify the deployed inventory, don't report the no-op as a landed change.

---

## Data layer
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Local entity + attributes (Text/Int/Decimal/Bool/DateTime/Identifier/Email/Phone) | ~ | ✗ | ✓ (context_entities) | All entities of an app in ONE turn; auto-number Id; length/mandatory/default inline. **Needs a `entity`/`data-model` recipe + plan step (seam 3d).** |
| Array/list-valued attribute (`Text[]`, `Image[]`, `List<T>`) | n/a (NOT REPRESENTABLE) | ✓ (fail-closed) | ✓ (`--phase spec` lint) | **RECIPE_GAPS B1 — a hard ODC constraint, not a recipe.** Attributes are scalar (basic types + Identifier). `_datamodel_lint` (verify.py) flags an array attr with actionable "promote to child entity + FK / CSV" guidance BEFORE the enum failure; `plan_from_spec` raises fail-closed. Model as a child entity (one row per element). Tests: test_verify (6) + test_prompt_step (1). Live-CLI-proven 2026-07-14. |
| Foreign key / reference (mandatory + optional, delete rule) | ~ | ✗ | ✓ | Author the FK in the same turn as its entity; default delete rule = Protect. Proven (Task.ListId). |
| Static entity (enum) | ✓ (static-entity) | ✓ | ✓ (context_entities) | Manual Long PK + explicit record Ids (auto-number unsupported for static). Recipe emits records w/ explicit Long Ids + create-once guard; plan emits it BEFORE data-model. **Runtime-proven 2026-07-07 (batcha): ContactStatus deployed isStatic+isPublic+Long PK+records[Active,Archived].** Memory: `odc_mcp_local_entity_authoring_gotchas`. |
| Structure (non-persistent) | ✓ (structure) | ✓ | ✓ (context_structures) | No identifier — a plain typed record shape for action/agent signatures. Plan emits top-level `structures` before data-model. **Runtime-proven 2026-07-07 (batcha): ResultDTO deployed.** |
| Entity index / unique | ✓ (entity-index) | ✓ (entity.indexes) | ✓ (mentor read-back) | Add-only index over attribute(s), optionally UNIQUE; do not touch the identifier. **Runtime-proven 2026-07-07 (batchb): CustomerId_Idx on Order.** (context_entities omits index metadata; read-back authoritative.) |
| Auto entity actions (Create/Update/Get/Delete) | n/a (generated) | n/a | ✓ | Only CreateAction + DeleteAll auto-gen via Model API; Get/Update present at runtime. Memory: `odc_mcp_entity_auto_actions_incomplete`. |
| Aggregate (filter / sort / max) | ~ | ~ (list-screen) | ✓ | SINGLE-SOURCE aggregates (no FK joins on detail screens — cascades, R2). Filter by input param proven (GetTasksByList). |
| Aggregate with join | ✓ (aggregate-join) | ✓ (screen.aggregateJoin) | ✓ | Additive join on a LIST screen's aggregate (CreateJoin; wrong ns=CS0234); shows related display fields vs raw FK Id. Avoid on DETAIL screens (R2). **Runtime-proven 2026-07-07 (batchb): GetOrders LEFT JOIN Order.CustomerId=Customer.Id + Customer.Name.** |
| SQL node | ✓ (sql-action) | ✓ (spec.logic sqlAction) | ✓ (context_actions) | `ISQLNode.Statement` with {Entity}/[Attr]/@Param + declared+bound inputs. **Runtime-proven 2026-07-07 (batchb): RecentOrders ServerAction w/ SQL node, out Order List.** Memory: `odc_mcp_sql_node_api`. |

## UI layer
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Screen (route, input params) | ~ | ✗ | ✓ (context_screens) | **Bake Anonymous at creation (Roles.Clear+AnonymousAccess) or it auto-roles → _error → extra turn (seam 3d-anon/R6).** Verify `change_applied` (phantom, seam 3d-phantom). Needs `screen` recipe + plan step. |
| Default/home screen | ~ | ✗ | ~ | Set at screen-create; capture wasDefault before any delete (memory). |
| Web Block (reusable) | ✗ | ✗ | ✗ | `CreateBlock`+widgets+input params works (memory `odc_mcp_block_creation_works`). |
| Table / List bound to aggregate | ✓ (list-screen) | ✓ | ✓ | Emit `data-entity` + `data-row-id` (exact behavioral count). |
| Input / Checkbox / Dropdown bound to var | ✓ (create-form combined) | ✓ | ✓ (behavioral) | Inputs live INSIDE a Form container widget (bare Inputs phantom — R10); bound to a screen-local var; `data-spec-id="<field>input"`. Runtime-proven (cfwall 2026-07-07). |
| Button / Link + navigation (dest + params) | ~ (list-screen Open) | ~ | ✓ (navigates) | **list-screen must emit the spec's declared nav component label+data-spec-id (seam 3e).** Link ships a default "link" text widget — delete it (R4). |
| Expression vs Text widget (derived/computed field) | ✓ (derived-field) | ✓ (component.computed) | ✓ (DOM-verified) | **M1 Wave 1 (B2-5) — ✓/✓/✓/✓ RUNTIME-PROVEN 2026-07-15 (w1probe rev 8).** `derived-field` authored a `NetWorthExpr` Expression (`Value=Assets-Liabilities`); live DOM rendered **"60"** (100−40) — a computed formula, not a literal. |
| If / conditional render | ✓ (conditional) | ✓ (component.visibleWhen) | ✓ (DOM-verified) | **M1 Wave 1 (B2-4) — ✓/✓/✓/✓ RUNTIME-PROVEN 2026-07-15 (w1probe rev 8).** `conditional` set `EmployerBlock` Container `Visible=ShowDetails`; live DOM showed it visible ("Details are visible"). |
| Layout / menu / sidebar nav | ✓ (nav-block) | ✓ | ~ | Author ONCE as a shared block; never per-screen. |
| Theme / CSS / StyleSheet | ○ | ✗ | ✓ (runtime theme) | `theme.StyleSheet` setter; verify at RUNTIME (loaded stylesheets), not in-model (memory cluster). |
| Charts (OutSystemsCharts / ECharts) | ○ | ✗ | ✗ | Native OutSystemsCharts work via MCP; data via ListAppend flow (memory). |
| Input validation (mandatory/format) | ✓ (input-validation) | ✓ (opt-in `action.validate`) | ~ (model-authored; behavioral blocked by create-form widgets seam) | Validation gate SHORT-CIRCUITS the save before Save<Entity>Record. **Runtime 2026-07-07 (batcha): gate authored + published (Trim/EmailValidate/short-circuit/Mandatory). End-to-end behavioral drive blocked by the create-form WIDGETS phantom wall + data-spec-id drift (Tier-1 seam, not this recipe).** |
| Client variable | ✗ | ✗ | ✗ | — |

## Logic layer
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Server action (Public flag) | ~ (create-form action phase) | ✓ | ~ | Public=FALSE unless exposed (Public SA fails publish OS-BLD-40409). Typed local + Assign-per-attr; NEVER inline record literal. |
| Screen action (client) + OnClick wiring | ✓ (create-form combined) | ✓ | ✓ (behavioral) | **Revised seam 3f: action (own turn) → Form+inputs+wire in ONE turn (`combined`).** The bare-widgets-only turn phantomed (R10); the combined shape is proven-persist + keeps the contract data-spec-ids through a phantom+retry. Runtime-proven (cfwall 2026-07-07). |
| Client action | ✓ (client-action) | ✓ (spec.logic clientAction) | ✓ (context_actions) | Browser-side reusable logic (no DB round-trip). **Runtime-proven 2026-07-07 (batchb): FormatCode ClientAction, in Code/out Display.** |
| Service action (exposed, cross-app) | ✓ (service-action) | ✓ (spec.logic serviceAction) | ✓ (context_actions) | Public=TRUE (a Server Action can't be Public — OS-BLD-40409); may wrap a server action. **Runtime-proven 2026-07-07 (batchb): GetOrderCount ServiceAction isPublic=true.** In-app SA call still needs a Server Action wrapper (memory `odc_mcp_screen_action_service_action_call`). |
| Flow nodes (If/Switch/Assign/Aggregate/RunAction/ForEach/Raise/RefreshData) | ~ | ~ | ~ | `CreateNode<T>` + `ConnectedBelow`; no `.StartNode` prop (memory). Assign iteration ≠ flow order — identify by var name. |
| Exception handling (OnException) | ✓ (exception-handler) | ✓ (opt-in `action.guardExceptions`) | ✓ (authored + published) | AllExceptions handler → graceful failure (server: Success=False output; screen: feedback msg). **Runtime-proven 2026-07-07 (batcha): handler authored change_applied=true, published rev 9, happy path intact.** |
| ServerRequestTimeout on LLM calls | ○ | ✗ | ✗ | Default 10s; set 60+ on ExecuteServerAction nodes calling an LLM (memory). |

## Integration
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| REST expose (endpoint) | ○ | ✗ | ✓ (live 200) | `CreateIntegration<IRestService>`+CreateAction+HTTPMethod/URLPath; method auto-creates its Start node. Live-proven (memory `odc_mcp_rest_endpoint_authoring`). |
| REST consume | ✓ (rest-consume) | ✓ (integration.direction=consume + methods) | ~ (deploy-proven; live-call pending) | **M1 Wave 1 (B2-1) — DEPLOY-PROVEN 2026-07-15 (w1probe rev 4).** `BureauAPI` consumed integration + `GetInfo` GET @ httpbin authored clean + deployed. Recipe FIXED post-run: the RESPONSE structure is AUTO-GENERATED by the integration (don't pre-map an app Structure — SEAM W1-restresp). Residual: a live 2xx call not separately exercised. |
| Excel bulk import (Excel→entity) | ✓ (excel-import) | ✓ (logic.kind=excelImport) | ~ (deploy-proven; import-run pending) | **M1 Wave 1 (B2-3) — DEPLOY-PROVEN 2026-07-15 (w1probe rev 3).** `ImportCodes` (`Excel to Record List`→ForEach→CreateRawCode + RowsInserted) authored clean + deployed; built-in resolved. Residual: an actual .xlsx import run not exercised. |
| External library (.NET) | ✓ (external-library) | ✓ (spec.externalLibraries) | ~ (extlib_status) | NOT a Mentor turn — the recipe emits the extlib_* lifecycle (upload→poll→publish). Needs .NET 8; GenerationError TERMINAL; publish on non-ReadyForReview = HTTP 500. *(runtime pending — needs a real .NET 8 assembly)* |
| App reference (multi-app) | ✓ (app-reference) | ✓ (spec.appReferences) | ~ (event+SA deploy-proven; static-entity FK authors-clean, deploy-walls) | `addReferenceToElements` (does the dependency wiring) + AddDependency/RefreshDependencies; globalKey = producerKey*elementKey (asterisk). **event + PUBLIC SA: deploy-proven (wfprobe rev 2).** **static entity + FK: authors clean in-model — full import, NOT a hidden Id-only stub — but consumer DEPLOY fails OS-DPL-50205 'Model features validation failed' (open; not app-shape, not OS-APPS-40028; likely producer-state or a static cross-app deploy constraint — SEAMS 2026-07-07).** |

## Process / automation / AI
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Timer (WhenPublished / scheduled) | ✓ (seed-entity WhenPublished) · ⚠ (scheduled-timer recurrent) | ✓ (spec.timers) | ✓ WhenPublished · ✗ recurrent DEPLOY-WALL | `CreateTimer`, `Action=<serverAction>`. WhenPublished proven (BootstrapData; + w1probe rev 8). **M1 Wave 1 (B2-2) `scheduled-timer`: authors clean but a RECURRENT (cron) schedule FAILS deploy `OS-DPL-50205` — LIVE-PROVEN 2026-07-15 (w1probe, 3× incl. a parameterless target; the SAME timer as WhenPublished deployed clean → the recurrent schedule is the trigger).** New OS-DPL-50205 cause (single app, none of the 3 known causes). WALL open (SEAM W1-timer); memory `odc-recurrent-timer-deploy-wall-os-dpl-50205`. Root cause platform-vs-Model-API-authoring unresolved. |
| Business Process / BPT | ✓ (workflow) | ✓ (spec.processes) | ✓ (publish + validation) | **RUNTIME-PROVEN from scratch (wfprobe 2026-07-07):** producer app holds the Global Event + PUBLIC SA; `app_create kind=BusinessProcess` does NOT auto-publish (safe window); ONE turn references the producer's event+SA cross-app AND authors the process (Start.StartProcessOn=referenced event, auto-activity ActionToTrigger=referenced public SA — both bind; 0 errors); publish ONCE with the process present (rev 2, real deploy, no corruption). **Landmine: a 0-process Workflow app publish corrupts the verify cache — the create→author→publish order avoids it structurally (§Workflow).** |
| Global event | ✓ (global-event) | ✓ (spec.logic globalEvent) | ✓ (change_applied + publish) | `CreateGlobalEvent` (THROWS in a Workflow-kind app). **Runtime-proven 2026-07-07 (batchb): OrderPlaced event, payload OrderId; did not throw (not a Workflow app).** (Events don't surface in context reads.) |
| Sample data / bootstrap (LoadSampleData) | ✓ (seed-entity) | ~ | ✓ | Empty-guarded LoadSampleData + WhenPublished timer. Runs once — idempotent guard, not the run-once flag (R5). |
| AI Agent (internals: CreateAgent/CallAgent/BuildMessages/AgentTask) | ~ | ✗ | ✓ (publish) | MCP authors a GOOD agent (proven); system prompt lives in BuildMessages literal. **FULLY MCP-BUILDABLE from scratch as of 2026-07-05** — see AIModel binding below. Needs an `agent` recipe + plan step. |
| Agent structured / typed output (Structure w/ Decimal confidence + rationale) | ✗ | ✗ | ✗ | **RECIPE_GAPS B2-17 (PCM).** Native: Call Agent → Structured output tab → a Structure the caller reads. The `agent` recipe emits a **Text-only** `Response` — no confidence field. Blocks any confidence-routing / structured-extraction agent. |
| Batch agentic loop (agent called per row over a batch) | ✗ | ✗ | ✗ | **RECIPE_GAPS B2-18 (PCM).** Timeout-bound (60s client / 300s BPT activity / ≤30min Timer + auto-retry) → must loop async in a chunked idempotent Timer, not synchronously. `agent` recipe's `ServerRequestTimeout=120` exceeds the 60s client max — review. |
| AI Model binding (agent AIModel slot ← AIModelConnection) | ~ | ✗ | ✓ (publish) | **WALL LIFTED 2026-07-05 (live-proven).** Bind the agent's AIModel to a **Trial** AIModelConnection (`TrialClaudeHaiku4_5`) in the same Mentor turn that authors the agent; publishes clean (rev 1→2, NO OS-APPS-40028). The old Portal-only step is gone. (Customer/non-Trial connection bind untested — use a Trial model.) |
| AI Model connection asset | n/a (tenant) | n/a | ✓ (context_connections) | Trial models (`TrialClaudeHaiku4_5`/`TrialGPT5`/`TrialAmazonNovaPro`) exist tenant-wide, reference-able + bindable via MCP. app_create kind=AIAgent still ships a blank shell (author internals via MCP). |

## Security / identity / app-level
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Roles + app-local auth gate | ✓ (role-gate) | ✓ | ~ | Keep screens Anonymous; gate app-locally (OnReady localStorage→GetUserById→redirect). NO platform role on anon apps (R6). |
| Anonymous access | ~ | ~ | ✓ (anon render) | Bake at screen-create (seam 3d-anon). Verify with an unauthenticated headless load (no _error/login). |
| End-user / test users | ✓ (seed-entity from auth.testUsers) | ✓ | ~ | ODC end-users are STAGE-WIDE (memory `odc_mcp_user_provider_settable_via_reflection`). |
| App properties / site settings | ✗ | ✗ | ✗ | — |

---

## Roadmap to both-axes DONE (drive rows to ✓/✓/✓, thrash-note followed)
**Tier 1 — close the proven thrash seams (make the CRUD slice 0%-thrash), then every task_tracker-shaped app is first-try:**
- `entity`/`data-model` recipe + plan step (3d) · `screen` recipe with Anonymous baked + change_applied gate (3d/anon/phantom) · list-screen emits the spec nav component (3e) · seed step for list-bound entities lacking a create UI (3g) · create-form 3-phase — **DONE (3f)**. Tighten `_COUNT_JS` (G-count).
**Tier 2 — breadth the common app needs:** ~~exception handling (OnException)~~ ✓recipe · ~~input validation~~ ✓recipe · ~~static entities~~ ✓recipe · ~~structures~~ ✓recipe · REST consume · Web Blocks · charts · client variables. *(Batch A recipes+plan+tests landed 2026-07-07; each still needs a runtime-exercised build to reach ✓/✓/✓/✓.)*
**Tier 3 — advanced:** BPT/workflows · **AI agents (NOW fully MCP-buildable incl. model bind — needs an `agent` recipe: app_create AIAgent → author agent+AgentFlow+BuildMessages+public Call service action → bind AIModel to a Trial connection → publish)** · external libraries · multi-app references · SQL nodes · SOAP.

Each tier: add the recipe (with its thrash-free note), emit it from `plan_from_spec` where the spec expresses it, add a verifier assertion, and prove it on a from-scratch build whose spec exercises it. A row is DONE only when a clean-room build authors it first-try AND a verifier confirms it at runtime.
