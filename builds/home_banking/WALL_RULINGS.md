# Strategy rulings — home_banking walls (2026-06-17)

Rulings from the strategy session on WALLS.md 001–005. Driver: apply these, re-triage WALLS.md so the
LIVE `## WALL-` count drops below the cap (move accepted/resolved entries to the RESOLVED section at the
bottom with a non-`## WALL-` heading so the hook stops counting them), then proceed to the visual phases.

## WALL-001 (Employee FK on HBAccount + LoanRequest) → CORRECTED: FIXABLE via MCP reference-import (NOT a scope cut)
**Earlier ruling was WRONG** — it cited `odc_mcp_reference_add_studio_only`, which is **SUPERSEDED**: the
the 2026-06-09 MCP retest RETIRED the reference-add wall. This is the **producer-reference-import pattern**,
and the MCP can do it (the same flow the chrome_wrap recipes + DISPATCH_PLAYBOOK Phase 0 use):
`addReferenceToElements` STAGES the import (returns null), then `applyModelApiCode` materializes it with
`eSpace.AddDependency(Services.ModelServices.ParseGlobalKey("<globalKey>"))` per element; the `globalKey`
is computable via `harness/banking_runner/library_keys.py::compute_global_key(producerKey, elementKey)`.
Verified 2026-06-17: `Employee` exists as a **public** entity importable from a producer (it's public in
many tenant apps). So this is a **harness/process gap** (the Core rerun skipped Phase-0 reference-import),
NOT an MCP ceiling.
**FIX — follow the D9 missing-external-dependency protocol (do NOT auto-import):**
(1) Identify the producer the ORIGINAL Core's `AssignedToEmpId` FK points at — decode the original's
`foreignKey.globalKey`/`entityKey` (`695efc5b`) to the producer app key (several public `Employee` entities
exist across apps, so pin the exact one). (2) **Generate `./IMPORT_INSTRUCTIONS.md`** with explicit OutSystems
steps for the human (consumer `harnessbuild_hbcore` + the producer app name/key, the `Employee` entity,
Manage-Dependencies → check → Apply → Publish). (3) **Ask the user to import it.** (4) On confirmation,
add the `AssignedToEmpId` FK on HBAccount + LoanRequest → `Employee.IdentifierType` and publish. Doesn't
block the visual phases; recoverable fidelity. See `harness/CLAUDE.md` "Fall-out pattern: missing external
dependency" + HD D9.

## WALL-002 (HBAgentsProgressSteps.AgentTypeId static→static FK dropped) → FIX (cheap, do now)
Both entities are in-app statics; the FK dropped only because the renderer's topo-ordering covers SERVER
entities, not static→static FKs, so the target wasn't present when the source was authored. **Fix now**
with a targeted Mentor turn: add the `AgentTypeId` FK attribute to `HBAgentsProgressSteps` referencing
`HBAgentType` (both already exist → no ordering problem now). Low cost, restores real structure. Doesn't
block visual, but do it in the data-model phase while you're here. → also a RENDERER bug (see findings).

## WALL-003 (FK-as-PK identifying relationships → standalone Id) → ACCEPT shape, but RESTORE the FK first
The FK-as-PK (identifying 1:1) shape is unattainable via MCP — the publish-shape gate forbids custom PK
shapes (`osmcp` #1 scale blocker). **Accept** the autonumber-`Id` PK. BUT the fidelity-and-screen-critical
question is whether the PARENT FK survived as a regular attribute. CustomerPicture/GoalPicture/HBDocumentBinary
are 1:1 extension tables the UI joins on (avatar on dashboard, goal images, loan docs — recipe 14). 
**ACTION (do now, before visual):** for each of the 3, check the live entity — does it still carry its
parent FK as a regular (non-PK) attribute (`CustomerId` / `GoalId` / `DocumentId`)? If the renderer DROPPED
the FK with the PK, add it back as a regular FK attribute via a targeted Mentor turn. Id-PK + regular-FK is
functionally equivalent for joins; FK-missing breaks the screen-phase aggregates. This is the wall that
"bites in the screen phase" — neutralize it in the data-model phase. → also a RENDERER bug (demote, don't drop).

## WALL-004 (Is_Active/Order mandatory-flag drift on statics) → ACCEPT (minor)
Mandatory-flag drift on static housekeeping columns has no functional or join impact. **Accept.** Not worth
a fix. (Minor renderer fidelity-detail; tighten later if ever.)

## WALL-005 (4 List/Structure-param actions deferred) → ACCEPT deferral for the milestone; probe Mentor for the loan phase
These 4 are loan-flow actions (SaveRequestBasicCreditInfo, CustomerLoanCreateOrUpdateWrapper,
CustLoanCreateOrUpdateWithFiles, ServicePersonalLoanRequestCreatedOrUpdate) — the RENDERER emits
`/* unsupported */` for List/Structure-typed params. KEY INSIGHT: that's a *renderer* gap, not necessarily
a *platform* gap — Mentor natural-language authoring may handle List/Structure params fine (it authored
Widget-style turns cleanly). **Accept the deferral now** (don't block the rest), and when the loan-flow
screens (PersonalLoan wizard, RequestDetail) are built, **probe hand-authoring those 4 via Mentor** before
treating them as a hard cut. The loan screens depend on them, so they matter for loan-flow fidelity — but
they're not needed for the rest of the visual phases.

## Meta — proceed order
1. Do the two data-model fixes NOW: WALL-002 FK; WALL-003 FK-restore (the join-critical one).
2. Re-triage WALLS.md: 001/004/005 → RESOLVED/ACCEPTED section (drop the live count under cap); 002/003 →
   RESOLVED once the fixes publish + verify.
3. Then start the visual phases per DISPATCH_PLAYBOOK (blocks LAYOUT-FIRST → theme → screens → chrome →
   default + CDP/pixel-diff). With 003 neutralized up front, no known wall should bite the screen phase.

## Renderer-improvement findings (harness work — the REAL fix vs per-build patches)
These three should be fixed in `harness/banking_runner/recipe.py` so future builds don't re-hit them:
- **Static→static FK ordering** (WALL-002): topo-order statics for FKs to other statics, not just server entities.
- **FK-as-PK demotion** (WALL-003): when the publish-shape gate forbids a custom PK, render as autonumber-Id
  PK **+ keep the parent FK as a regular attribute** — never drop the relationship.
- **List/Structure-typed action params** (WALL-005): renderer support (or a Mentor-handoff path) for these.
Log these for the strategy backlog; they don't block this build once the per-build patches above are applied.
