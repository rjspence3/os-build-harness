<!-- The systematic program to close every gap between "builds one CRUD app + one agent" and
     "builds ANY ODC app, 0% thrash, fully verified, pixel-faithful." Companion to
     CAPABILITY_MATRIX.md (the what) and SEAMS.md (the thrash ledger). The discipline is the
     whole point: a gap is CLOSED only when a clean-room from-scratch build authors it first-try
     AND a verifier confirms it at runtime — encoded ≠ done. -->

# GAP CLOSURE PLAN — to a harness that builds any ODC app, 0% thrash, verified

## The two axes and the definition of done
- **Axis 1 — 0% thrash:** every build unit lands first-try (no phantom, cascade, retry, or hand-step).
- **Axis 2 — full coverage + fidelity:** every ODC construct is `recipe · spec-field · plan-emission · verifier` = ✓/✓/✓/✓, and the output matches the intended design.
- **Program DONE:** a stranger clones the repo, points it at a spec (and optionally a reference app), runs one command, and gets a 100%-working, pixel-faithful ODC app that the harness itself verifies — for an ARBITRARY app.

**Iron rule for every item below:** DONE = a clean-room from-scratch build authored it first-try AND a verifier confirmed it at runtime. "Unit tests pass / recipe exists" is IN PROGRESS, not done. Track each construct's four checkmarks in `CAPABILITY_MATRIX.md`; log every new seam in `SEAMS.md`.

---

## Phase 0 — Prove the current state (cheap, high-signal, unblocks confidence)
Gaps: #1 (0%-thrash unproven), #7 (gate count, repo sync).
1. **Re-prove 0% thrash.** Clean-room from-scratch build of `task_tracker` (or a second small spec) driving ONLY the auto-emitted plan (data-model → screen(anon) → list-screen(+nav) → write-path 3-phase → seed) with **zero hand-steps**. Exit: app built with **0 cancels/phantoms** and `--behavioral` = PERSISTS. Any hand-step needed → new seam → fix → repeat.
2. **Tighten the behavioral gate count** (`_COUNT_JS`): count distinct row containers (de-dupe cell vs `tr`) so `PERSISTS` reports the true delta (fix the `0→2`).
3. **Automate 3-repo sync.** One canonical (public) + a `sync` script mirroring to private + clean-clone, with a test-parity check. Removes hand-sync drift.
**Exit criteria:** a second app is built entirely from the emitted plan, zero cancels, gate green — 0%-thrash is now a RESULT for the CRUD slice.

## Phase 1 — Spec expressiveness (the enabler; everything else depends on it)
Gap: #2 — recipes exist but the spec can't trigger them, so the plan can't emit them.
1. **Schema v0.3** — add first-class blocks to `app_spec`: `sampleData` (per entity), `agents` (name/systemPrompt/model/tools), `charts` (per screen: type/category/series/source), `design` (theme tokens: palette/typography/spacing, or a `reference` product URL), `workflows` (BPT), `integrations` (REST consume/expose), `validation` (per field/action), `access`/`exceptionHandling`.
2. **`harness-verify --phase spec`** validates every new block + cross-refs (fail closed).
3. **`plan_from_spec`** emits the existing orphan recipes (`agent`, `chart`, `theme`, plus seed) from the new fields, in the right order.
4. **One example spec** (`examples/full_app`) exercising an entity + list + write-path + agent + chart + theme + seed.
**Exit criteria:** the full example spec produces a plan that emits agent+chart+theme steps, and a clean build authors all of them first-try + each is verified (Phase 2). Recipes stop being orphans.

## Phase 2 — Verification depth (make "verified" mean it)
Gap: #3 — gate is create-only + structural.
1. **Behavioral gate beyond create:** Update persistence (edit a row → reload → changed), Delete (remove → gone), navigation (click nav → correct route + context), role-gate enforcement (anon blocked / member allowed), and **agent invocation** (wire the REST-trigger-invoke recipe into `--behavioral` so an agent's reasoning is auto-checked).
2. **Construct-render asserts:** chart rendered real values; theme applied (loaded stylesheet / computed style); block instantiated.
3. **`--phase live` breadth:** extend structural asserts to blocks, charts, input params.
**Exit criteria:** `--behavioral` covers Create/Update/Delete + nav + role + agent, each proven on a build; a dead Update button or an unbound chart FAILS the gate.

## Phase 3 — Design / pixel fidelity (the missing pillar for "fool the head of product") — DONE (2026-07-06)
Gap: #4 — CLOSED. `harness-capture --pixel <reference>` ports the pixel gate into the harness:
per-screen match% + overall fidelity score, heatmap per screen, same-session auth + masked viewport,
exits nonzero below `--pixel-threshold`. `_theme_css` now compiles the full token set
(palette/typography/spacing + fontFaces) deterministically. **Exit criteria met + live-proven** on
`harnessbuild_authapp3`: self-vs-self → 3/3 MATCH, fidelity 100.0%, exit 0; a darkened-reference
restyle regression → home DRIFT 0.0%, fidelity 66.67%, **exit 1** + heatmap. Browser-free unit tests
(`tests/test_pixel_gate.py`, 8) pin the discriminating core (identical=PASS, restyle=FAIL, tolerance
absorbs anti-alias noise, mask neutralizes overlays, size-mismatch reported).
1. **Reference capture:** ingest either a live original (headless screenshot + DOM/theme capture) or a `/design-layer` token set into `design`.
2. **Theme from tokens:** `theme` recipe consumes the token set (palette/typography/spacing/fonts) deterministically.
3. **Pixel-diff gate:** port `pixel_diff.py` into the harness as `harness-capture --pixel <reference>` — match%/heatmap/bbox, exits nonzero below threshold, same-session auth + masked viewport (per the clone-parity method).
4. **Fidelity score** in the acceptance report next to the behavioral verdict.
**Exit criteria:** a clone build emits a pixel-diff score vs a reference and gates on it; a restyle regression fails the gate.

## Phase 4 — Coverage breadth (Tier-2/3 recipes; banking has the proven approach for most)
Gap: #5. Each construct follows recipe·spec·plan·verify and is DONE only when a build authors it first-try + a verifier confirms it. Use `BANKING_MINED.md` for the working Model-API approach + thrash note.
- **Batch A (common app needs):** exception handling (`OnException`), input validation, static entities, structures, web blocks, REST consume.
- **Batch B (logic/data depth):** service actions, client actions, SQL nodes, aggregate joins, global events, indexes.
- **Batch C (advanced):** BPT/workflows (author refs+process+publish in ONE turn — avoids the verify-cache corruption), external .NET libraries, multi-app references (element-import every touched entity incl. static).
**Exit criteria per row:** its four matrix checkmarks are ✓ and a clean build exercised it. Program-level exit: a "kitchen-sink" spec exercising Batches A–C builds first-try, fully verified.

## Phase 5 — Autonomous executor + thrash enforcement (hand-it-to-a-stranger) — CORE DONE (2026-07-06)
Gap: #6. **Enforcement backbone shipped + proven:** `harness-gate <spec> --base-url <url>` is the
single machine-checkable DEFINITION OF DONE — it composes spec+structural+behavioral+role+render+pixel
into one verdict and exits 0 only when every DECLARED dimension is runtime-green (undeclared = omitted,
never vacuously passed; a no-op publish never counts). Live-proven on auth_app3 (✅ DONE, exit 0; 9
browser-free composition tests). **SEAM-001 closed in practice:** `launch_build.sh` now installs the
build-root `.claude/settings.json` allowlist (harness CLIs incl. harness-gate) into every scaffold —
verified a fresh scaffold carries it — so a launched per-build session can actually run the gate. The
headless launch prompt now gates on `harness-gate` exit 0, not self-declaration. REMAINING: a fully
unattended `RUN_MODE=headless` end-to-end run (claude -p building a fresh spec to gate-green with zero
human turns) — the drive loop + machine-done are both in place; this is the live certification.
1. **The runner:** a program that executes `plan_from_spec` steps through Mentor with §Turn/§Recovery ENCODED — one-poll-per-heartbeat, `change_applied=false` → auto re-author in a fresh session (phantom retry), publish-once grouping for `create-form` widgets→wire, cancel-and-split on a cascade timer, verify-at-runtime between phases.
2. **Enforce, don't advise:** the runner refuses to advance a unit that didn't land; it never reports a no-op publish (`no_changes_detected`) as success.
3. **Resolve SEAM-001:** expose the harness CLIs as MCP tools the driver is already authorized to call (or ship the build-root launch as the one-line documented path), so a subagent CAN drive.
**Exit criteria:** `harness build <spec>` takes an arbitrary in-scope spec to gate-green (behavioral + pixel) with **no human Mentor turns**, from a clean clone.

## Phase 6 — Hardening + continuous flywheel
Gap: #7 + sustainability.
1. Role-gated-screen demo path (a real end-user login flow, banking Wall-02).
2. The flywheel as standing practice: every real build logs seams → fixes → matrix update; periodic clean-room builds on new spec shapes to surface shape-specific seams (as iteration 2/3 did).
3. Keep `CAPABILITY_MATRIX.md`/`SEAMS.md`/this plan in lockstep with the code.

---

## Phase 7 — Real-spec coverage breadth (close every RECIPE_GAP; milestones M1→M2→M3)
Source: `RECIPE_GAPS.md` — gaps surfaced by three real BRDs (Trust Banking / Credit Decisioning /
Lifecycle Management) and classified vs **ODC-native capability** (verified against ODC docs, not O11).
Those three BRDs are the **acceptance specs**: Phase 7 is done when they build clean-room, first-try.

**The closing template (every gap = 5 artifacts; DONE only at runtime proof).** For each gap: add the
`RECIPES` function in `prompt_recipes.py` (ODC gotcha baked in + `Do not publish` tail) · a first-class
`app_spec` block · `plan_from_spec` emission in dependency order · a `harness-verify --phase live` and/or
`harness-capture --behavioral` assertion + unit tests · then a from-scratch build authors it first-try and
the verifier confirms it at runtime. Matrix row → ✓/✓/✓/✓. Log each new thrash note in `SEAMS.md`.

**Milestone gate rule:** do NOT start a milestone until the prior one is matrix-green (every row ✓/✓/✓/✓
+ a clean-room build proved it). Each milestone has its own exit gate.

### M1 — ODC-native recipes, no external dependency (RECIPE_GAPS B1 + B2). Highest value/risk ratio.
- **Wave 0 (pure Python; no Mentor/tenant) — DONE 2026-07-14:**
  - B1-1 array-attribute **lint** — **DONE**. `_datamodel_lint` (verify.py) runs ALONGSIDE the schema layer
    (the array dataType also fails the odcDataType enum, which short-circuits cross-ref) so the actionable
    "promote to a child entity + FK / CSV column" message always surfaces; `plan_from_spec` raises fail-closed;
    schema `odcDataType.$comment` documents the constraint for the spec factory. 7 tests, full suite 352 green,
    live-CLI-proven on an `Image[]` spec (exit 1, actionable message first). Matrix row added (✓/✓/✓).
  - **Schema audit (findings, drives M1/M2/M3 emission):**
    - `integrations` EXISTS but is thin: `kind` enum = `RestApi` only, fields = name/baseUrl/description; NO
      operations, auth, or consume-vs-expose distinction. **B2-1 REST-consume needs this widened** (add
      `direction: consume|expose`, `operations[]`, `auth`). Not a blocker for authoring, but the plan can't
      emit a consume step from today's block.
    - `capabilities` is the USER-FLOW layer (roles→screens→actions→entities), NOT device capabilities —
      unrelated to B2-8 mobile plugins. **A new `capabilities`/`plugins` block is needed for M3** (name collision
      to avoid: call it `devicePlugins`).
    - Timers: no timer/schedule block at all today (seed-entity hardcodes WhenPublished). **B2-2 needs a
      `timers[]` block** (`{name, action, schedule: whenPublished|daily|weekly|interval, at?}`).
    - MISSING blocks to add as their wave lands (all additive, backward-compatible): `settings[]` (B2-10),
      `notifications[]` email/sms (B2-6/B3-6), field-level `masking` (B2-14), `offline`/`sync` + `devicePlugins`
      (M3), `derivedFields`/`conditional` (B2-4/B2-5 — may ride on existing component `props`).
    - Confirmed already-present + reusable: `structures` (Core-hosted parse DTOs for B2-3 Excel),
      `logic[]` (service/client/SQL actions), `appReferences` (Forge-component references for M2), `processes`
      (maker-checker B2-16), `design.theme` (unaffected). No schema change needed for those.
  - **Net:** Wave 0 closes the one true platform gap and yields a concrete per-wave schema-change list, so each
    M1/M2/M3 recipe lands with its spec block already scoped. Blocks are added JUST-IN-TIME per wave (not all now)
    to keep every intermediate schema shape valid + tested.
- **Wave 1 (native, 2–3 specs each — do first) — OFFLINE HALF DONE 2026-07-15:** `rest-consume` (B2-1) ·
  `scheduled-timer` recurrent (B2-2) · `excel-import` (B2-3, `ExcelToRecordList`+ForEach insert; Structure in a
  normal app/**Core**, [[odc-bpt-app-cannot-contain-structures]]) · `conditional` If-render (B2-4) ·
  `derived-field` Expression (B2-5). **All 5 recipes + schema blocks (integration.direction/methods, top-level
  `timers`, logic.kind=excelImport, component.visibleWhen/computed) + `plan_from_spec` emission + unit tests
  landed; full suite 365 green; CLI-visible.** REMAINING = the runtime proof (below) to reach ✓/✓/✓/✓ per row.
  - **Runtime-proof strategy (Mentor-optimal):** prove all 5 in ONE consolidated probe app, NOT five apps —
    the harness leaks a Mentor session per committing step and the tenant caps at 100 sessions/24h
    ([[harness-leaks-mentor-session-per-step]]), so minimize `app_create` + session count. One normal app
    (Structures + a target entity + a screen) exercises `excel-import`, `scheduled-timer` (Timer→the import
    action), `rest-consume`, `conditional` + `derived-field` (on the screen). Drive it per doctrine: one
    committing concern per fresh Mentor session, publish once per logical group from the main loop, cancel
    after publish. rest-consume needs a real reachable base URL (a public echo/test API) for a live 2xx.
  - **RUNTIME PROOF DONE 2026-07-15 (w1probe rev 8, https://robertjspencedemos-dev.outsystems.app/w1probe):**
    **4/5 proven, 1 deploy-wall** (full ledger in SEAMS.md §"M1 Wave 1 runtime proof"). ✅ **conditional (B2-4)**
    + **derived-field (B2-5)**: DOM-verified (EmployerBlock visible; NetWorthExpr renders "60"=100−40). ✅
    **rest-consume (B2-1)** + **excel-import (B2-3)**: authored clean + deployed (live 2xx / .xlsx-run are the
    only residuals). ⚠ **scheduled-timer (B2-2): DEPLOY-WALL** — a recurrent (cron) Timer authors clean but
    fails deploy `OS-DPL-50205`; the SAME timer as WhenPublished deploys → the recurrent schedule is the
    trigger (a 4th distinct OS-DPL-50205 cause; memory [[odc-recurrent-timer-deploy-wall-os-dpl-50205]]).
    Recipe fixes applied from the run: `rest-consume` response is auto-generated (not pre-mapped). Doctrine
    learned: [[mentor-fresh-session-forks-from-model-not-deployed]] (a broken undeployed rev poisons
    downstream publishes). **M1 Wave 1 exit-gate status: 4/5 ✓/✓/✓/✓; B2-2 blocked on the timer wall.**
- **Wave 2 (native app-level):** `native-email` (B2-6; Email element, SMTP is external Portal config) ·
  `web-block` (B2-9) · `settings` (B2-10) · `audit-log` (B2-11, append-only entity + write-on-mutate) ·
  `role-limit` (B2-12, extend `role-gate` with a numeric threshold) · `draft-resume` (B2-13) · `field-mask`
  (B2-14) · `org-scope` RLS (B2-15) · maker-checker breadth (B2-16, generalize `workflow`).
- **Wave 3 (agentic depth — PCM brief; the agentic slice is the most under-served):** extend the `agent`
  recipe with a **structured-output** variant (B2-17 — Structured output tab → a Structure with a Decimal
  confidence field + rationale, the field downstream logic reads) · a **batch-agentic-loop** recipe (B2-18 —
  chunked idempotent Timer loop calling the agent per row, respecting the 60s client / 300s BPT-activity /
  ≤30min Timer limits; fix the `agent` recipe's 120s `ServerRequestTimeout` vs the 60s client max) · a thin
  `guardrail`/decision recipe if warranted (B2-19 — service-action + If/Switch; low priority, buildable today).
- **M1 exit gate:** slimmed TBS + Credit + PCM specs build clean-room first-try; every B1/B2 row ✓/✓/✓/✓;
  behavioral gate proves over-limit blocked, draft reloads, cross-org blocked, a mutation writes an audit row,
  AND (PCM) an agent returns a typed confidence score that a deterministic guardrail routes on over a batch.

### M2 — Forge / external-component recipes (RECIPE_GAPS B3). Gate: M1 green.
- **Shared infra FIRST:** a Forge-dependency `IMPORT_INSTRUCTIONS` generator (a `needs-human` wall per
  `harness/CLAUDE.md` fall-out): Forge component name → tenant-install steps → `addReferenceToElements`.
  Every B3 recipe gates on the component being installed + referenced — that human step is part of the plan,
  never silently assumed.
- **Per-component recipes:** Data Grid (B3-1) · Maps/heatmap (B3-2) · PDF/Ultimate PDF (B3-3) · QR-gen/QRCoder
  (B3-4) · CSV/CsvToolkit (B3-5) · SMS via external REST (B3-6). Verify = component instantiated + its behavior
  renders at runtime.
- **M2 exit gate:** a spec exercising each B3 component builds clean-room (with the documented install step
  performed once), each verified at runtime; install-wall instructions proven executable.

### M3 — Mobile / offline cluster (RECIPE_GAPS B2-7, B2-8). Gate: M2 green. Highest uncertainty.
- **Spike FIRST (research, not a recipe):** (a) is ODC mobile/offline authoring even MCP-reachable? — no
  evidence in the matrix today; (b) a mobile verification channel — `harness-capture` is headless web and
  cannot exercise a native mobile/offline app. Resolve the PWA path (IndexedDB, partially headless-testable)
  vs native (SQLite + device plugins → structural-only verify + documented manual runtime).
- **Recipes (post-spike):** offline local-entities + `OnSync` + a conflict pattern (B2-7) · device-plugin
  references — camera / barcode-scan / GPS (B2-8, OS-supported plugins referenced into the app).
- **M3 exit gate:** the LMS field-app spec builds clean-room; offline-sync + device-plugin rows verified by
  the chosen channel (PWA behavioral where possible; structural + a logged manual-runtime step otherwise —
  no silent pass).

**Phase 7 program exit:** all three source BRDs build clean-room, first-try, gate-green — the harness now
covers the real-world app shapes that motivated the gap review.

---

## Sequencing & dependencies
- **0 → 1** first (prove current, then unlock the spec so recipes are reachable). 1 is the critical path — it gates 2/3/4.
- **2 and 3 run in parallel** after 1 (verification depth + fidelity are independent).
- **4** proceeds in batches once 1 (spec) + 2 (verify) exist, so each new construct is spec-triggered and gate-checked.
- **5** after 4 has enough breadth that autonomous runs are worthwhile; SEAM-001 sub-item can start any time.
- **6** continuous.

## The measure of progress
Not "recipes written" but **matrix rows at ✓/✓/✓/✓** and **# of distinct app shapes built clean-room, first-try, verified.**
- **2026-07-06:** `full_app` (CRUD + chart + theme + seed + a separate AIAgent) built clean-room in **0/0/0** (0 cancels/phantoms/hand-steps/seams), runtime-verified (CRUD PERSISTS, chart renders, theme applied, agent publishes clean + reasons). This is the first **multi-construct, first-try, verified** shape — and it confirms Phase 0.1's 0/0/0 for the CRUD slice. `chart`/`theme`/`agent` are now spec-reachable + live-proven.
- **2026-07-06:** `harnessbuild_authapp3` (data-model → screens → seed → login → role-gate) built clean-room in **0/0/0** and proved the app-local auth construct end-to-end: `--role` → BLOCKS_ANON + **ALLOWS_MEMBER** green (Seam E identifier-poison fix held; step 5 published clean, no OS-DPL-RDBS-40020). Closes Phase 2's last verification dimension.
- **2026-07-06:** Phase 3 pixel/fidelity gate shipped + live-proven on auth_app3 (self=100%/PASS, restyle regression=DRIFT/exit 1). `harness-capture --pixel`.
- **2026-07-06:** Phase 5 loop PROVEN. `harnessbuild_gatedemo3` (fresh Task CRUD spec) built FULLY AUTONOMOUSLY — a tight-poll driver fired the auto-emitted 6-step plan verbatim through the MCP with ZERO human Mentor turns, 0 thrash — then `harness-gate` certified ✅ DONE, exit 0 (structural 2/2, behavioral write-path PERSISTS). The two capstone runs before it each closed a real recipe seam (create-form identifier guard; data-model identifier settlement + R9) and a gate order-dependence wart (empty bound table = inconclusive) — the flywheel working. `harness-gate` = the machine-checked definition of done; SEAM-001 closed; headless launch gates on it.
- **2026-07-07:** Phase 5 FULLY CLOSED. Headless smoke proved a `claude -p` build-root session runs the harness CLIs + certifies `harness-gate` unattended (SEAM-001 holds headless). Defined the auth boundary: OutSystems MCP OAuth is interactive → `RUN_MODE=session` is the Mentor DRIVE vehicle (inherits the live token); `RUN_MODE=headless` drives Mentor only with a pre-provisioned tenant JWT (a cold headless session is unauthenticated). launch_build.sh encodes it (OUTSYSTEMS_MCP_TOKEN preflight + bypassPermissions).
- **2026-07-07:** Phase 4 breadth — Batch A (static entity, structure, input-validation, exception-handler) + Batch B (service/client/SQL actions, aggregate join, global event, index) BOTH recipe·spec·plan·tests + RUNTIME-PROVEN (batcha, batchb — batchb 0-thrash). Batch C: **workflow/BPT RUNTIME-PROVEN from scratch** (wfprobe — cracked the multi-app + verify-cache-corruption problem); app-reference event+SA deploy-proven, static-entity FK authors-clean but deploy-walls OS-DPL-50205 (open); external-library recipe-complete, prereq-blocked (.NET assembly). The create-form widgets phantom wall was closed en route (cfwall). 316 tests.
- **Phase 0, 1, 2, 3, 5 = DONE. Phase 4 substantially DONE** (13 constructs recipe·plan·verify; the standout: workflows now build from scratch). Remaining: 1 open Batch-C deploy wall (OS-DPL-50205) + 1 prereq-blocked (external .NET), and Phase 6 (hardening/flywheel).
- **2026-07-14:** Phase 7 PLANNED. Reviewed three real BRDs (Trust Banking / Credit Decisioning / Lifecycle Management) for recipe gaps and classified each vs **ODC-native capability** (verified against ODC docs — `RECIPE_GAPS.md`): only ONE true platform constraint (array-valued attributes, B1); ~16 ODC-native-but-unrecipe'd gaps (B2 — REST-consume, scheduled timer, Excel-import, If/Expression, email, offline+sync, device plugins, Web Blocks, Settings, audit-log, role-limit, draft/resume, masking, org-scope, maker-checker); 6 Forge/external (B3). Folded into three gated milestones: **M1** native (Waves 0–2), **M2** Forge (install-wall infra + per-component), **M3** mobile/offline (spike-first — MCP-authorability + a mobile verify channel are unproven). The three BRDs are the acceptance specs. NOT STARTED — this is the plan, not built.
