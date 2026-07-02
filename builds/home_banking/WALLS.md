# WALLS — home_banking build

Strategy rulings applied 2026-06-17 (see `WALL_RULINGS.md`). Live `## WALL-` headings below are the only
genuinely-open blockers (the `>5` hook counts `^## WALL-`). Accepted / resolved / handed-off items are in
the section at the bottom with `###` headings so they no longer count against the cap.

## WALL-006 [needs-human]
Visual phases need the Portal + Backoffice UI apps, which DO NOT EXIST in the tenant — scope/creation decision.
- context: visual-phase prep at rev 17. `app_config.yaml` + `--list-apps` show the clone spans 5 apps:
  core (data/logic, = `harnessbuild_hbcore` ✓ built), **HomeBankingPortal** + **HomeBankingBackoffice**
  (own ALL blocks/theme/screens/chrome + their own action layers). `app_list search=harnessbuild` returns
  ONLY `harnessbuild_hbcore` — the two UI apps were never created. The Core app has no UI recipes
  (confirmed: zero block/theme/screen recipes in the core render), so the visual phases cannot target it.
- tried: confirmed `mcp__outsystems__app_create` EXISTS and creates a blank WebApplication via MCP
  (`kind: CrossDevice`) — the old `[[odc_mcp_no_app_creation]]` Studio-gate finding is SUPERSEDED, same as
  the reference-add wall. So creation is now MCP-doable; I did NOT create anything (outward-facing, no MCP
  app-delete exists → hard to reverse; and it's a scope call).
- needs: strategy decision — create `harnessbuild_hbportal` + `harnessbuild_hbbackoffice` via `app_create`
  (driver can do it on go-ahead), confirm names, and whether to do Portal-first (Backoffice is blocked anyway,
  see WALL-008). Each is a full app build (logic → blocks → theme → screens → chrome → default), ~the bulk of
  the remaining visual fidelity work.

## WALL-007 [spec-gap]
Portal/Backoffice reference topology is not clone-ready — points at the ORIGINAL Core + 4 producer keys are TBD.
- context: `app_config.yaml` `references:` — Portal/Backoffice list `producer: HomeBankingCore,
  producer_key: 695efc5b-…` (the ORIGINAL). A self-contained clone Portal must reference the CLONE core
  `harnessbuild_hbcore` (`bf7ed15f-…`) instead — whose entities + actions were authored `Public=true`, so
  they ARE importable. Additionally 4 producer keys are blank (`producer_key: ""`): **OutSystemsCharts**
  (dashboard ECharts), **AgentsCommonResources** (Chat/ChatInput/ChatMessage AI blocks), **UltimatePDF**
  (ConfirmationPDF), **OutSystemsMaps** (branch locator). Reference-import (Phase 0) can't stage those
  producers without their keys; the dependent surfaces (charts, chat, PDF, maps) won't resolve.
- tried: none — surfaced reading the manifest before dispatch. Editing the recipe/config to redirect the
  Core key or fill producer keys is a recipe change (don't freestyle — recipes are the hardened plan).
- needs: (a) redirect Portal/Backoffice Core reference to `bf7ed15f` (clone core) — renderer/config param or
  strategy-directed config edit; (b) pin the 4 TBD producer keys (D9 per-producer: decode from the original
  Portal `fa7ab595`'s reference list, or `context_search` + disambiguate owner app). Feeds the spec factory.

## WALL-008 [spec-gap]
Backoffice block capture incomplete — Backoffice visual phase not buildable.
- context: `app_config.yaml` backoffice `blocks:` lists only `HBIcon` with comment "Phase 2 — Backoffice
  block capture pending (task #81 in SCOPE.md)". The Backoffice screens need their block family captured
  (`_raw/backoffice-*.tree.md`) before chrome-wrap can resolve. Portal capture IS complete (30+ blocks).
- tried: none — capture is upstream recipe-library work, not a driver dispatch.
- needs: spec-factory: capture the Backoffice block family (per SCOPE.md task #81). Until then only the
  Portal visual phase is buildable. Recommend: build Portal now, defer Backoffice to a later milestone.

## Resolved / accepted (not counted against the cap)

### WALL-002 — RESOLVED (rev 17, verified live)
HBAgentsProgressSteps.AgentTypeId static→static FK was dropped (renderer topo-orders server entities, not
static→static FKs, so the target wasn't present when the source was authored in `02_static_batch_01`). FIX
applied 2026-06-17 (driver): one targeted Mentor turn added `AgentTypeId` → `HBAgentType.IdentifierType`
(DeleteRule=Ignore, IsMandatory=false). Published rev 17; verified live: `AgentTypeId | HBAgentType
Identifier | mand=false | pk=false` present. Renderer-backlog item: topo-order static→static FKs.

### WALL-003 — RESOLVED (rev 17, verified live) — Id-PK accepted, parent FKs restored
The FK-as-PK identifying (1:1) shape is unattainable via MCP (publish-shape gate forbids custom PK shapes),
so the autonumber `Id` PK is ACCEPTED. The renderer had also DROPPED the parent FK entirely on all three
extension tables. FIX applied 2026-06-17 (driver): one targeted Mentor turn re-added each parent FK as a
REGULAR (non-PK) attribute, published rev 17, verified live:
  - CustomerPicture.CustomerId  → HBCustomer Identifier | mand=true | pk=false ✓
  - GoalPicture.GoalId          → Goal Identifier       | mand=true | pk=false ✓
  - HBDocumentBinary.DocumentId → HBDocument Identifier | mand=true | pk=false ✓
Id-PK + regular-FK is functionally equivalent for the screen-phase joins (dashboard avatar, goal images, loan
docs). Renderer-backlog item: demote FK-as-PK to Id-PK + regular FK — never drop the relationship.

### WALL-001 — HANDED OFF to user import (Employee FK), per D9 missing-external-dependency protocol
AssignedToEmpId FK (→ Employee producer) dropped on HBAccount + LoanRequest. The Employee entity lives in a
separate producer app `harnessbuild_hbcore` does not reference; the renderer WARN-skipped the FK. Ruling
(corrected): this is FIXABLE via MCP reference-import, but per D9 the human performs the import (the right
`Employee` producer must be pinned among look-alikes). Driver action this session: pin the producer (decode
the original Core's `AssignedToEmpId` foreignKey.globalKey/entityKey → producer app key), generate
`./IMPORT_INSTRUCTIONS.md`, and ask the user to import. Does NOT block the visual phases. On import
confirmation, re-add the `AssignedToEmpId` FK → `Employee.IdentifierType` on both entities and publish.
Status: PENDING USER IMPORT (see IMPORT_INSTRUCTIONS.md).

### WALL-004 — ACCEPTED (no action)
Is_Active/Order mandatory-flag drift on 18 statics + a few domain attrs (ChartData Income/Expenses, HBBranch
Lat/Long, Region DemoLat/Long). No functional or join impact. Accepted as a minor renderer fidelity detail.
Renderer-backlog item only.

### WALL-005 — ACCEPTED deferral for this milestone; revisit at loan-flow screens
4 action recipes (SaveRequestBasicCreditInfo, CustomerLoanCreateOrUpdateWrapper, CustLoanCreateOrUpdateWithFiles,
ServicePersonalLoanRequestCreatedOrUpdate) carry List/Structure-typed params the renderer emits
`/* unsupported */` for. Accepted as a deferral now (doesn't block the rest). KEY INSIGHT: a *renderer* gap,
not necessarily a *platform* gap — when the loan-flow screens (PersonalLoan wizard, RequestDetail) are built,
PROBE hand-authoring these 4 via Mentor natural-language before treating them as a hard cut. Renderer-backlog
item (List/Structure param support).
