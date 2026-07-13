# Modular-Build Gap Plan — to a repeatable, gate-green 5-app ODC system

**Scope:** close every gap between where the harness is now (single-app builds solid; modular
producer→consumer builds *mostly* working) and the bar: **a decomposed multi-app system builds
clean-room, first-try, gate-green on every dimension (incl. role + pixel), repeatably.** Surfaced by the
Rivian 5-app build, 2026-07-10. Companion to `GAP_CLOSURE_PLAN.md` (single-app) + `GATE_ACCURACY_PLAN.md`.

**Iron rule (carried):** a gap is CLOSED only when a clean-room from-scratch build authors it first-try
AND a verifier confirms it at runtime. "Recipe exists / unit test passes" is IN PROGRESS, not done.

---

## A. PROVEN + BANKED this session (committed, 448 tests green)

These are done — the improved iteration inherits them by construction:

- **Session reuse** (`a9d71cb`) — one Mentor slot per build (was one/step); survives the per-tenant cap.
- **Public producer entities** (`59c530a`) — `expand` sets `dataModel.public` on core-layer apps; the
  `data_model` recipe exposes them. **Proven end-to-end:** CoreV2 entities `isPublic=True`, consumer
  `app-reference` imported all 6, portal rendered Core's rows (Q-1041…Q-1044). THE modular data-flow fix.
- **Trustworthy gate** (`ea9b416`,`38beb02`) — DEFECT/UNVERIFIED taxonomy; DONE ⟺ zero of both.
- **Repeatable portal enrichment** (`9596c59`) — `gen_portal_specs.py` re-overlays rich design after `expand`.
- **create-form edit-prefill** (`78be45f`), **cap-cascade / cancel-after-publish** (`493723f`),
  **publish-failure diagnostics** (`727785c`).
- **Referenced count-aggregates COMPILE** — clean-room probe `ProbeDash` (dashboard over CoreV2's
  referenced QualificationCase+Supplier) built + published OK. Rules out the "referenced aggregate crashes"
  theory. See `memory/referenced-entity-count-aggregate-crashes-compiler.md` (now a CORRECTION note).

---

## B. OPEN GAPS (what still stands between here and the bar)

### B1 — HARNESS: in-place publish-failure retry corrupts the OML  ★ the real V4 blocker
An `OS-BEW-COMP-*` build-engine compile crash is NOT cleared by the harness re-authoring the SAME step
fresh into the SAME app — the failed publish wedges the app's compiled state, so every retry re-crashes
(proven: a plain aggregate probe into the wedged V4 crashed; the same construct in a clean app worked).
Mentor design-time validation passes throughout, so the harness can't predict it.
- **Fix:** `classify_publish` / the driver should, after N (e.g. 2) consecutive `OS-BEW-COMP` publish
  failures on a step, STOP retrying in place and signal "app wedged → rebuild fresh" (the R6→R8 fresh-name
  pattern) instead of grinding retries that deepen corruption. Distinguish `OS-BEW-COMP` (compile, sticky)
  from `OS-BEW-*` transient/`OS-DPL-*`.
- **Status:** OPEN. Highest priority — it's why every rich-portal rebuild died.

### B2 — HARNESS: seed reliability for a modular data-owner  (multi-part)
- (a) A headless Core (`screens:[]`) never runs its OnReady-triggered seed. **Fixed in spec** (add a Home
  screen) but should be a harness safeguard: `plan_from_spec` auto-synthesizes a bootstrap screen when a
  spec has `sampleData` but no screens. **Status: spec-fixed, harness-safeguard OPEN.**
- (b) The OnReady seed hits ODC's **10s screen-request limit** on a heavy graph (8 entities × FK lookups →
  `OS-CLRT-60900`). Mitigation: trim to display-critical entities (R8-proven ~5), or seed async. **OPEN.**
- (c) **Mentor's `LoadSampleData` authoring is unconfirmed** — a direct `exec_in_app` invoke inserted
  nothing verifiable (masked by B-public then never cleanly re-tested). **User decision: deterministic SQL
  seed via the ASE `db_query` harness** (bypass Mentor's flaky seed authoring). **Status: DECIDED, UNBUILT.**
  Needs: generate INSERT SQL from `sampleData` (FK via natural-key subqueries) + ODC physical column names.

### B3 — HARNESS: `classify_terminal` hard-halts a transient source-control 401
A publish/OML-download 401 (transient) is classified non-retryable "unauthorized" and HALTs, though the
token is valid (recurred on Core + V3). The external poller retries it, but the harness itself should
classify a source-control 401 as transient-retryable, not a hard auth halt. **Status: OPEN** (workaround: poller).

### B4 — PROCESS/HARNESS: producer-name alignment
`appReferences.producerApp` (from `expand`, = the domain app name e.g. `OnboardingCore`) must match the
ACTUAL tenant app name built (e.g. `RivianCoreV2`). A mismatch → the reference resolves nothing.
`gen_portal_specs.py --core <name>` patches it, but this should be one coherent step (the system builder
threads the real Core app name into the consumer specs). **Status: scripted, not integrated.**

### B5 — GATE: KPI check false-passes when everything is 0
The W5a KPI check compares rendered value vs live list count; when BOTH are 0 (empty Core), `0==0` → false
`KPI_OK`. An all-empty app agrees with itself. The gate should treat all-zero KPIs on a seeded spec as
UNVERIFIED/suspect. **Status: OPEN** (surfaced on ReviewerApp2).

### B6 — SPEC/BUILD: production-bar dimensions not yet exercised
- **role** — portals have no `auth`/`access` block, so the gate OMITs the role dimension; production bar
  needs server-side role gating (BLOCKS_ANON + ALLOWS_MEMBER). **OPEN — spec authoring.**
- **pixel** — never run green on a rich portal (the rich builds died at B1). **OPEN — needs a clean rich build.**

### B7 — BUILD: 3 of 5 apps unverified against the public Core
QualifyWorkflow, ScreeningAgent, SupplierApp built earlier against the PRIVATE OnboardingCore (pre-fix) or
not gated. Must rebuild/gate against public CoreV2. **Status: OPEN.**

### B8 — CLEANUP: misdiagnosis commit + tenant sprawl
- The "unique COUNT-aggregate name … fixes OS-BEW-COMP-50008 collision" commit — the collision theory is
  **disproven** (R8 + probe compile with duplicate/referenced aggregates). The distinct-naming is harmless
  hygiene, but the message is wrong. **Action: note the correction (keep the code).**
- **Throwaway build apps accumulate** on the tenant (no MCP app-delete exists) — manual Portal cleanup
  frees Mentor session slots. **Action: delete the disposable apps; keep the Core + the final built set.**

---

## C. The improved iteration (sequenced, once cap drains)

**Pre:** user deletes throwaway apps (frees cap) + fixes push; I fix B1 (rebuild-fresh on sticky OS-BEW)
and B3 (401 transient) so a clean build doesn't self-wedge.

1. **Fresh Core** — build `RivianCore` from `OnboardingCore.app_spec` (public entities + Home + trimmed
   seed). Verify entities `isPublic=True` + seed rows via independent read.
2. **Seed deterministically** (B2c) — generate + run INSERT SQL via the ASE harness; verify row counts.
3. **Portals** — `gen_portal_specs.py --core RivianCore`; build the RICH ReviewerApp + SupplierApp CLEAN
   (one attempt each; on sticky OS-BEW, rebuild fresh — never grind). Add `auth`/`access` for role (B6).
4. **Workflow + Agent** — build against the public Core (B7).
5. **Gate each** to DONE incl. role + pixel (B6). Iterate pixel to the design mockups.
6. **Definition of done:** every app gates DONE (spec/structural/behavioral/role/render/pixel); portals
   pixel-match the mockups + render live Core data; Workflow drives Screen→Review→Approve→Activate; audit
   immutable; integrations marked stubs.

**Sequencing:** B1 + B3 (harness) FIRST — they make a clean build possible without self-wedging. Then B2c
(deterministic seed) so data is guaranteed. Then C1→C6. B5/B4 are polish; B8 is cleanup/unblock.

## C2 — Step optimization / MCP budget (measured + decided)

`harness-build-cost` (the non-greedy diagnostic) quantifies a build's MCP load offline. Rivian 5-app,
enriched: **43 authoring turns · 43 publishes (→33 batched) · 5 cap-sessions (1/app) vs 43 greedy · ~43
reads.**

- **The greedy problem that hurt — cap saturation — is SOLVED by session-reuse** (5 vs 43 slots, 8.6×).
  The diagnostic makes that visible and is the regression guard (break reuse → cap-sessions jumps to 43).
- **Authoring turns are FIXED** — atomicity is a reliability requirement (fat turns hang/phantom;
  STEP_ATOMICITY.md). Do NOT merge authoring to save turns.
- **Publishes are the only remaining lever** (~23–30% via batching): a run of pure STRUCTURAL-UI steps
  (screen/nav/place-nav/list-screen/dashboard/detail/row-actions) doesn't gate a downstream verify, so it
  can author into the reused session and publish ONCE. But data-model/seed/write-paths/theme/app-reference
  each need their OWN publish (verify boundary) — batching them loses per-step landing granularity AND
  widens the B1 compile-wedge blast radius (a failed batch wedges several steps' authoring, un-isolatable).

**DECISION (2026-07-10): keep per-unit publish as the DEFAULT** (precise landing + tight wedge isolation
are worth more than a ~25% publish speedup now that the cap pain is gone). A `--publish-mode batched`
opt-in for trusted specs is a deferred nice-to-have, NOT a blocker. Re-open only if publish wall-clock
becomes the bottleneck.

## D. Measure of progress
Not "recipes written" but **# of distinct app SHAPES built clean-room, first-try, gate-green.** The
single-app shape is proven (R8). The **modular multi-app shape is NOT yet** — one clean rich portal
rendering live producer data, gated green incl. role+pixel, is the next milestone that closes it.
