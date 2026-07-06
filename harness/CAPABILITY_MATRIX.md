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
| Foreign key / reference (mandatory + optional, delete rule) | ~ | ✗ | ✓ | Author the FK in the same turn as its entity; default delete rule = Protect. Proven (Task.ListId). |
| Static entity (enum) | ✗ | ✗ | ~ | Manual Long PK + explicit record Ids (auto-number unsupported for static). Memory: `odc_mcp_local_entity_authoring_gotchas`. |
| Structure (non-persistent) | ✗ | ✗ | ✗ | — |
| Entity index / unique | ✗ | ✗ | ✗ | — |
| Auto entity actions (Create/Update/Get/Delete) | n/a (generated) | n/a | ✓ | Only CreateAction + DeleteAll auto-gen via Model API; Get/Update present at runtime. Memory: `odc_mcp_entity_auto_actions_incomplete`. |
| Aggregate (filter / sort / max) | ~ | ~ (list-screen) | ✓ | SINGLE-SOURCE aggregates (no FK joins on detail screens — cascades, R2). Filter by input param proven (GetTasksByList). |
| Aggregate with join | ○ | ✗ | ✗ | Avoid on detail screens (R2); resolve FK display fields separately. |
| SQL node | ○ | ✗ | ✗ | `ISQLNode.Statement` + `@Param` inputs. Memory: `odc_mcp_sql_node_api`. |

## UI layer
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Screen (route, input params) | ~ | ✗ | ✓ (context_screens) | **Bake Anonymous at creation (Roles.Clear+AnonymousAccess) or it auto-roles → _error → extra turn (seam 3d-anon/R6).** Verify `change_applied` (phantom, seam 3d-phantom). Needs `screen` recipe + plan step. |
| Default/home screen | ~ | ✗ | ~ | Set at screen-create; capture wasDefault before any delete (memory). |
| Web Block (reusable) | ✗ | ✗ | ✗ | `CreateBlock`+widgets+input params works (memory `odc_mcp_block_creation_works`). |
| Table / List bound to aggregate | ✓ (list-screen) | ✓ | ✓ | Emit `data-entity` + `data-row-id` (exact behavioral count). |
| Input / Checkbox / Dropdown bound to var | ~ (create-form widgets) | ✓ | ✓ | Bind to a screen-local var; `data-spec-id="<field>input"`. |
| Button / Link + navigation (dest + params) | ~ (list-screen Open) | ~ | ✓ (navigates) | **list-screen must emit the spec's declared nav component label+data-spec-id (seam 3e).** Link ships a default "link" text widget — delete it (R4). |
| Expression vs Text widget | ○ | ✗ | ~ | `ITextWidget.Text` literal-only; `IExpression`+SetValue for computed (memory). |
| If / conditional render | ○ | ✗ | ✗ | — |
| Layout / menu / sidebar nav | ✓ (nav-block) | ✓ | ~ | Author ONCE as a shared block; never per-screen. |
| Theme / CSS / StyleSheet | ○ | ✗ | ✓ (runtime theme) | `theme.StyleSheet` setter; verify at RUNTIME (loaded stylesheets), not in-model (memory cluster). |
| Charts (OutSystemsCharts / ECharts) | ○ | ✗ | ✗ | Native OutSystemsCharts work via MCP; data via ListAppend flow (memory). |
| Input validation (mandatory/format) | ✗ | ✗ | ✗ | — |
| Client variable | ✗ | ✗ | ✗ | — |

## Logic layer
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Server action (Public flag) | ~ (create-form action phase) | ✓ | ~ | Public=FALSE unless exposed (Public SA fails publish OS-BLD-40409). Typed local + Assign-per-attr; NEVER inline record literal. |
| Screen action (client) + OnClick wiring | ~ (create-form wire phase) | ✓ | ✓ (behavioral) | **Author widgets (OnClick empty) then RESUME session to wire; publish once (seam 3f).** Combined = 30-min cascade. |
| Client action | ✗ | ✗ | ✗ | — |
| Service action (exposed, cross-app) | ○ | ✗ | ✗ | In-app SA call needs Server Action wrapper (memory `odc_mcp_screen_action_service_action_call`). |
| Flow nodes (If/Switch/Assign/Aggregate/RunAction/ForEach/Raise/RefreshData) | ~ | ~ | ~ | `CreateNode<T>` + `ConnectedBelow`; no `.StartNode` prop (memory). Assign iteration ≠ flow order — identify by var name. |
| Exception handling (OnException) | ✗ | ✗ | ✗ | Every flow warns "No Exception Handling" until added. |
| ServerRequestTimeout on LLM calls | ○ | ✗ | ✗ | Default 10s; set 60+ on ExecuteServerAction nodes calling an LLM (memory). |

## Integration
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| REST expose (endpoint) | ○ | ✗ | ✓ (live 200) | `CreateIntegration<IRestService>`+CreateAction+HTTPMethod/URLPath; method auto-creates its Start node. Live-proven (memory `odc_mcp_rest_endpoint_authoring`). |
| REST consume | ✗ | ✗ | ✗ | — |
| External library (.NET) | ○ | ✗ | ~ | extlib_upload→status; needs .NET 8; GenerationError terminal (memory). |
| App reference (multi-app) | ○ | ✗ | ~ | `addReferenceToElements` then `applyModelApiCode AddDependency(ParseGlobalKey)`; globalKey computable (memory cluster). |

## Process / automation / AI
| Construct | Recipe | Plan | Verify | Thrash-free note |
|---|---|---|---|---|
| Timer (WhenPublished / scheduled) | ~ (seed-entity) | ~ | ✓ (runtime rows) | `CreateTimer`, `Schedule="WhenPublished"`, `Action=<serverAction>`. Proven (BootstrapData). |
| Business Process / BPT | ○ | ✗ | ✗ | `CreateBusinessProcess`+`CreateNode<IStartNode/IAutomaticActivityNode/IHumanActivityNode/IDecisionNode>`; auto-activity calls a PUBLIC Service Action (memory). **Publishing a Workflow app with 0 processes corrupts the verify cache — author refs+process in ONE turn.** |
| Global event | ○ | ✗ | ✗ | `CreateGlobalEvent` (memory). |
| Sample data / bootstrap (LoadSampleData) | ✓ (seed-entity) | ~ | ✓ | Empty-guarded LoadSampleData + WhenPublished timer. Runs once — idempotent guard, not the run-once flag (R5). |
| AI Agent (internals: CreateAgent/CallAgent/BuildMessages/AgentTask) | ~ | ✗ | ✓ (publish) | MCP authors a GOOD agent (proven); system prompt lives in BuildMessages literal. **FULLY MCP-BUILDABLE from scratch as of 2026-07-05** — see AIModel binding below. Needs an `agent` recipe + plan step. |
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
**Tier 2 — breadth the common app needs:** exception handling (OnException) · input validation · REST consume · Web Blocks · static entities · charts · client variables.
**Tier 3 — advanced:** BPT/workflows · **AI agents (NOW fully MCP-buildable incl. model bind — needs an `agent` recipe: app_create AIAgent → author agent+AgentFlow+BuildMessages+public Call service action → bind AIModel to a Trial connection → publish)** · external libraries · multi-app references · SQL nodes · SOAP.

Each tier: add the recipe (with its thrash-free note), emit it from `plan_from_spec` where the spec expresses it, add a verifier assertion, and prove it on a from-scratch build whose spec exercises it. A row is DONE only when a clean-room build authors it first-try AND a verifier confirms it at runtime.
