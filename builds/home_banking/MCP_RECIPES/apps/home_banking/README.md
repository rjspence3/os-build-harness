# Home Banking — App Rebuild Playbook

A from-scratch rebuild plan for the Home Banking suite, driven by the MCP recipe
templates in `data/MCP_RECIPES/`. Goal: hit "Portal create new app" → run this
playbook → end with a working replica of the original.

## Suite architecture (as observed in the OutSystems tenant)

| App | Asset Key | Role | What lives here |
|---|---|---|---|
| Home Banking Core | `695efc5b-8f39-4a53-8d71-35c59097d245` | Data layer | 35 entities (14 static + 21 server). All other apps reference these. |
| Home Banking Portal | `fa7ab595-f8cd-4140-8826-2acc484727b6` | Customer Web UI | Owns Easing static + customer-facing screens (Login/UserProfile/Common come for free). |
| Home Banking Backoffice | `555cac1f-af92-4461-9750-b635d6570495` | Admin Web UI | Owns SidebarAction + AgentsProgressSteps statics + admin/underwriter screens. |
| Home Banking Loan Request | `4b4c5f81-d528-41dd-a5a6-3d75367f74d3` | Workflow (BPM) | Loan approval state machine, calls Core entities. |
| Home Banking Mobile | `03466756-800d-40d5-954a-394a99473f48` | Mobile UI | Customer-facing mobile screens, references Core. |

Build order for a from-scratch rebuild: **Core first** (entities), then Portal +
Backoffice + Loan Request + Mobile in parallel (they only consume Core; no
inter-dependencies between them).

## Required referenced entities (NOT created by this manifest)

Core's `LoanRequest` and others reference an `Employee` entity whose
`fk_target_entityKey` (`86dabd64-5219-49da-8965-8535260ab309`) isn't owned by any of
the 5 Home Banking apps. This is likely a shared "Bank Employee Directory" core that
also feeds Backoffice's underwriter assignment logic.

Before running this rebuild, identify and stand up that producer app **first** (or
mock it with a minimal `Employee` entity in Core itself; both paths work).

Other referenced types resolve to standard ODC built-ins:
- `User Identifier` → `(System).User` (auto-available in every ODC app)
- `Binary Data` → built-in primitive
- All static-entity identifier types → produced by Recipe 02 below

## Build sequence

Run each phase as one or more MCP recipe calls, then publish before moving on.
Do not bundle phases.

### Phase 0 — Portal create empty app

Manual gesture. There is no MCP path to create new apps (per
`[[odc_mcp_no_app_creation]]`). In ODC Portal:

1. Apps → New App → Web Application
2. Name: `HomeBankingCore` (or your chosen name)
3. Wait for Studio warmup; do not skip — per `[[odc_mcp_publish_studio_warmup]]`
   the first MCP publish after Portal-create requires one Studio publish first
4. Note the new `assetKey` from `app_list` — it goes into every subsequent recipe call

### Phase 1 — Static entities (14 entities)

Drive `entities.yaml :: static_entities` through `data/MCP_RECIPES/02_entity_static.md`.

One recipe call per entity. Publish after every 5 or so to keep blast radius small.
Build order doesn't matter for statics — they don't reference each other.

Expected:
- 14 static entities created
- Each has Id (Integer or Text) + Label + Order + Is_Active + domain extras
- Records pre-loaded (between 1 and ~14 each)

### Phase 2 — Server entities (21 entities)

Drive `entities.yaml :: server_entities` through `data/MCP_RECIPES/01_entity_server.md`.

Build in dependency order. Entities whose FKs target other server entities must
be built AFTER their FK targets exist. Approximate order:

1. `DataSettings`, `Region`, `HBBranch` — no inter-entity FKs (besides User)
2. `HBCustomer`, `HBDocument`, `HBDocumentBinary`, `HBUpload`, `Transaction`, `HistoryLog`, `ChartData` — reference statics + maybe Branch
3. `HBAccount` — references HBCustomer + HBBranch
4. `CustomerLoan`, `CustomerGoal`, `CustomerPicture`, `GoalPicture` — reference HBCustomer
5. `HAgentsResponse` — references LoanRequest, agents
6. `LoanRequest` (last — 30 attrs including FKs to Customer/Account/CustomerLoan/CustomerGoal/Status/Employee/InfoOption) — depends on most of the above

**Critical**: per [[odc_db_upgrade_pk_change_blocked]] the PK MUST be set in the same
applyModelApiCode call as `CreateServerEntity`. The recipe handles this — do not
break the pattern.

**Critical**: every FK attribute has `DeleteRule = Ignore` per
[[odc_db_upgrade_pk_change_blocked]] (Protect is deprecated; OS-BLD-40409 at publish).

Expected:
- 21 server entities created
- Each has Long Integer auto-number Id PK
- All FKs declared with DeleteRule = Ignore
- Catalog (`context_entities` with `owned_only=true`) returns all 21

### Phase 3 — Roles

Drive `roles.yaml` (TBD — extract from app_info / roles inventory) through
`data/MCP_RECIPES/03_role.md`.

### Phase 4 — Server actions

Drive `actions.yaml` (TBD — extract from Core's user actions inventory) through
`data/MCP_RECIPES/04_action_crud.md` and `05_action_sql_update.md`.

### Phase 5 — Theme

Drive `theme.css` (TBD — extract via `context_themes`) through
`data/MCP_RECIPES/10_theme_replace.md`.

### Phase 6 — Screens

Drive `screens.yaml` (TBD — extract from Portal + Backoffice screens inventory + widget trees)
through `data/MCP_RECIPES/07_screen_table.md`, `08_screen_detail.md`, `09_screen_dashboard.md`.

### Phase 7 — Default screen + post-build verification

Drive through `data/MCP_RECIPES/11_default_screen.md` and `99_publish_verify.md`.

## What's complete in this manifest (status as of authoring)

| Phase | Status | File | Detail |
|---|---|---|---|
| 1 — Static entities | ✅ Complete | `entities.yaml :: static_entities` | 14 entities, all records captured |
| 2 — Server entities | ✅ Complete | `entities.yaml :: server_entities` | 21 entities, FK targets resolved |
| 3 — Roles | ✅ Complete | `roles.yaml` | 3 roles (Core owns all; Portal/Backoffice consume Public ones) |
| 4 — Server actions (signatures) | ✅ Complete | `actions.yaml` | 152 signatures total: Core 100, Portal 26, Backoffice 26 |
| 4b — Server actions (bodies, priority 5) | ✅ Complete | `actions-bodies.md` | 5 sample bodies covering 5 distinct flow patterns (CRUD wrapper, multi-output projection, ForEach list, multi-step workflow, AI pipeline) |
| 4c — Server actions (bodies, remaining 147) | 🚧 Deferred | — | Sample patterns above are sufficient to author recipes 04/05/06 + foreach_list |
| 5 — Theme | ✅ Complete | `theme-portal.css`, `theme-backoffice.css`, `theme-email.css` | Full CSS captured |
| 6 — Screens (signatures) | ✅ Complete | `screens.yaml` | 16 user-authored screens (8 Portal + 8 Backoffice), 0 Core. Plus 4 auto-generated (Login/InvalidPermissions × 2 apps) excluded from rebuild. |
| 6b — Screens (widget trees, P0) | ✅ All 5 captured (partial depth) | `_raw/*.flat.txt` + `_raw/portal-dashboard.summary.md` | Portal: Dashboard (26KB clean, full hierarchy), Transfer (61 widgets), PersonalLoan (134 widgets, wizard pattern w/ StepNo + DocumentStructure locals). Backoffice: Dashboard (109 widgets), RequestDetail (124 widgets, master-detail w/ IsSidebarOpen). All `.flat.txt` files truncated at ~8KB MCP wrapper cap. |
| 6c — Screens (widget trees, P1+P2) | 🚧 Deferred | — | 4 P1 (Requests, Customers, CustomerDetail, PersonalLoanOfferLetter) + 3 P2 (Confirmation, WakeUp, ManageSettings) |

## What still needs deeper discovery

### Action BODIES (Phase 4b)

`actions.yaml` captures every action's name, type, params, and description — enough
to RE-CREATE the signature in a recipe call. But the flow logic inside each action
(SQL queries, Assign nodes, ExecuteAction wiring, exception handlers) requires
one Mentor `applyModelApiCode` call per action to inspect.

Highest-priority action bodies for pattern extraction:
- `LoanRequestCreate`, `LoanRequestUpdate`, `LoanRequestDelete` — canonical entity CRUD
- `Sidebar_ChangeStatus` — multi-input state-mutation pattern (8 input parameters)
- `RequestAssignEmployeeBulk` — list-input batch pattern
- `ValidateDocument` — server action consuming a Binary + returning a complex Structure
- `Get_Settings` / `GetSettingsAndPicture` — typical "load app config" pattern

These five patterns alone would inform recipes 04 (CRUD), 05 (SQL update),
06 (workflow w/ exception handler), plus document/upload and read-only-aggregate
variants.

### Screen widget trees (Phase 6b)

`context_screens` returns screen names + layout slot info but NOT the widget tree.
For widget-tree-level fidelity, a Mentor read per screen is required. Highest priority
screens to inspect:
- Portal: `Dashboard`, `Transfer`, `LoanRequest` (the wizard) — covers dashboard, form, wizard patterns
- Backoffice: `RequestList`, `RequestDetail`, `CustomerProfile` — covers table-list, master-detail, profile patterns

## Pulling the remaining specs (cheap, read-only)

```bash
# Screens — pull all per app (only Portal + Backoffice have non-Common screens)
mcp__outsystems__context_screens --app fa7ab595-... --limit 100  # Portal
mcp__outsystems__context_screens --app 555cac1f-... --limit 100  # Backoffice
mcp__outsystems__context_screens --app 695efc5b-... --limit 100  # Core (likely zero owned)
```

For action BODIES and screen WIDGET TREES, one Mentor `applyModelApiCode` per
element. Pace these per-session to avoid the session-context-wall — see
`[[odc_mcp_session_context_wall]]`.
