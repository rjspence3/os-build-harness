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

## Phase 3 — Design / pixel fidelity (the missing pillar for "fool the head of product")
Gap: #4 — zero harness support today.
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

## Phase 5 — Autonomous executor + thrash enforcement (hand-it-to-a-stranger)
Gap: #6 — BUILD_LOOP is a doc, thrash-avoidance is doctrine, subagent path blocked.
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

## Sequencing & dependencies
- **0 → 1** first (prove current, then unlock the spec so recipes are reachable). 1 is the critical path — it gates 2/3/4.
- **2 and 3 run in parallel** after 1 (verification depth + fidelity are independent).
- **4** proceeds in batches once 1 (spec) + 2 (verify) exist, so each new construct is spec-triggered and gate-checked.
- **5** after 4 has enough breadth that autonomous runs are worthwhile; SEAM-001 sub-item can start any time.
- **6** continuous.

## The measure of progress
Not "recipes written" but **matrix rows at ✓/✓/✓/✓** and **# of distinct app shapes built clean-room, first-try, verified.** Today: 1.5 shapes (CRUD master-detail proven; agent proven; both with hand-steps that are now encoded-not-reproven). Target: arbitrary.
