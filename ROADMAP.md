# os-build-harness — ROADMAP (gap-fill plan)

Closes every gap in `STATE.md`, dependency-ordered. Each phase: **Goal · Steps · Depends · Acceptance
(validate-before-assert) · Repos**. Three keystones gate almost everything: **P1 (the actuator —
`.mcp.json`)** unblocks all live/build work; **P1.5 (ground-truth reverse-build)** empirically grounds
the schema and the channel routing; **P4 (the spec-creation phase)** unblocks the product seam. Resolved
decisions live in `HARNESS_DECISIONS.md` and are cited inline as **[HD D#]**.

Critical path to a working end-to-end build+grade:
`P0 → P1 → P1.5 → P2 → P4 → P5 → P6 → P7 → P9`, with `P3`/`P8` riding alongside once `P1`/`P1.5` land.

---

## P0 — Reconcile repo with recorded decisions (debt cleanup; ~hours)
**Goal.** Remove the contradictions STATE.md flagged so the repo stops lying about itself.
**Steps.**
1. Install the D1 launcher (the `RUN_MODE=session|headless` version) over the current `claude -p`-only
   `harness/launch_build.sh`. (`HARNESS_DECISIONS.md` is already in the repo as of the planning pass.)
2. Fix the spec factory's dangling `data/MENTOR_INDEX.md` reference — repoint to the MCP doctrine notes or
   vendor the index slice.
3. Resolve the `app_spec.v0` embedded example: either complete it (add the `transfer` screen) or label it
   "illustrative excerpt, not a conformant spec" so full-verify-fails is expected, not a bug.
4. Add a one-shot `scripts/cloneproof.sh` (clone→venv→`pip install -r`→gates) so the fresh-clone debt has
   a repeatable artifact instead of a notes claim.
**Depends.** none. **Acceptance.** `launch_build.sh` has no `claude -p` in `session` mode; grep finds no
dangling MENTOR_INDEX; `harness-verify` on the example exits as the chosen policy dictates; `cloneproof.sh`
exits 0. **Repos.** this repo, the spec factory.

## P1 — The actuator: `.mcp.json` + ODC MCP connectivity (KEYSTONE; ~1 day)
**Goal.** A real, configured ODC MCP server the harness (and `harness-verify` live) can call.
**Steps.**
1. Configure the harness against the **connected ODC MCP server** (`your-tenant.outsystems.dev`)
   per **[HD D2, revised]** — used for reads AND builds; tenant via `.env` (`OUTSYSTEMS_MCP_TENANT`).
   Apply the D2 mitigation: namespace + clean up build apps (`harnessbuild_<app>`). Gitignore the real
   `.env`. (The MCP is already connected in Claude Code; a standalone `.mcp.json` is only needed for the
   headless run mode + the harness-verify CLI's own live reads.)
2. Smoke a read (e.g. `context_entities`) against a known app to confirm auth + reachability.
3. Confirm `_mcp_configured()` in `verify.py` flips to true and the wall-cap hook still matches `mcp__.*`.
**Depends.** P0. **Acceptance.** a scripted `context_entities` read returns rows; `harness-verify --phase
live` on a spec now reports `not-implemented` (configured) rather than `unconfigured`. **Repos.** this repo.

## P1.5 — Ground-truth reverse-build + channel calibration (~3–5 days)
**Goal.** Reverse home_banking's structural spec from the live OML via the MCP, and use it to (a) find
what `app_spec` can't yet express and (b) **empirically** classify each assertion kind's read channel.
**Steps.**
1. Reverse a STRUCTURAL `app_spec` from home_banking's OML via the MCP: entities/attributes, screens/
   components, actions, navigation.
2. Produce the **SCHEMA-GAP LIST** — every field the OML expresses that `app_spec` v0 cannot represent.
   Feeds P2's v1.
3. Produce the **CHANNEL MAP** — for each assertion kind (entityExists / attribute / componentPresent /
   binding / navigates), test what actually reads back against the real app and classify it
   `mcp` / `capture` / `unverifiable` **with per-kind evidence**. This CALIBRATES (confirms or revises)
   `verify.py`'s current findings-based `LIVE_CHANNELS` scaffold — empirical result wins over the guess.
**Depends.** P1. **Acceptance.** a structural `app_spec` reversed from home_banking; the schema-gap list;
the channel map with per-kind evidence. **Repos.** this repo (+ the MCP doctrine notes, read-only, for findings cross-ref).

## P2 — app_spec v1: `integrations` + close the schema gaps (~1–2 days)
**Goal.** The spec expresses what P1.5 found the OML needs (incl. external systems), and the contract is
stable enough for P4 to target.
**Steps.**
1. Add fields from P1.5's **schema-gap list**, plus an `integrations` block — **minimal v1: only the
   connector kinds home_banking uses (likely REST)** per **[HD D3]**, derived from the MCP doctrine notes'
   `context_connections` findings. Widen later.
2. Extend cross-ref checks (integration refs resolve); classify any integration assertion's channel from
   P1.5's channel map.
3. Bump `specVersion` → `0.2`; update `harness-verify` + tests.
**Depends.** P1.5 (schema-gap list). **Acceptance.** new `test_verify.py` cases pass; an integrations-bearing
spec validates; integration-assertion channel cited to the P1.5 map. **Repos.** this repo.

## P3 — harness-verify LIVE executors, mcp channel (~2–3 days) — parallel to P4/P5
**Goal.** Actually verify the structural half against a built ODC app.
**Steps.**
1. Implement the `mcp` channel reader for **every kind P1.5's channel map marks `mcp`** (at minimum
   entityExists + attribute via `context_entities` `additionalData.attributes`; more if P1.5 shows them
   OML-readable).
2. Map assertion result → `pass`/`fail`; wire exit codes (0 all-pass / 1 any-fail / 3 inconclusive).
3. File an `mcp-wall` in the MCP doctrine notes **only for the kinds P1.5 empirically shows the platform
   cannot read** (no pre-filing — the channel map decides).
**Depends.** P1, P1.5. **Acceptance.** `--phase live` against a real app with a known entity → `pass`;
wrong-dataType spec → `fail` exit 1; behind a `@pytest.mark.live` gate (skipped without `.mcp.json`).
**Repos.** this repo (+ an MCP doctrine-notes wall entry only if P1.5 warrants).

## P4 — Spec-creation phase: interview → app_spec (KEYSTONE, long pole; ~1–2 weeks)
**Goal.** A human-approved `app_spec` produced by an interactive CC spec session **in the build root** —
the build seam (per D1). The contract allows two producers — the spec factory's cohort-specs and the harness
interview-specs; **this phase is the harness interview producer**.
**Steps.**
1. Build the interview flow (a harness command/skill run in the build root): elicit app/roles → data model
   → screens → actions/nav → acceptance assertions, **targeting app_spec v1** so output validates by construction.
2. Emit a candidate `app_spec.json`; run `harness-verify --phase spec` in-loop (validate-before-assert) so
   the interview can't produce an invalid spec.
3. Human-approval gate per **[HD D4]**: writes `builds/<app>/spec/APPROVED`; `launch_build.sh` refuses the
   build phase without it. Approved spec is the handoff.
4. Re-seed **the spec factory's** memory with the ODC-UI/theme/spec subset from the MCP doctrine notes (closes the under-seed debt).
**Depends.** P2 (schema target). **Acceptance.** an interview session produces an `app_spec` that passes
`harness-verify --phase spec` clean; approval writes the marker; `launch_build.sh <app>` honors it.
**Repos.** this repo (+ the spec factory for the P4.4 memory re-seed only).

## P5 — Design layer (FOLDED INTO SPEC CREATION per HD D10): reference → theme/mockups
**Goal.** The spec carries an intended visual layer; design tokens drive the ODC theme. **Per HD D10 this
is no longer a separate post-spec phase — it is part of spec creation (P4): a complete spec ships its design
layer.** Design SOURCE depends on app type: **known app → reference screenshots populate `screen.mockupRef`
+ theme ref** (no Figma needed); **novel app → generate via Figma → tokens → theme.** Runs in the spec session.
**Steps.**
1. Wire **`mattholihan/outsystems-figma-cli`** per **[HD D5]** (OS UI Kit aware, token export, CDP-to-
   Figma-Desktop; Desktop-open caveat is fine — the spec phase is interactive). Instantiate the UI Kit per screen.
2. Map Figma design tokens → `theme`/`portal.css` for the build.
3. Link each `screen.mockupRef` to its Figma frame (the advisory-diff reference for P6).
**Depends.** P4 step 1 (the structural spec exists to lay out). **Acceptance.** a spec's screens have Figma
frames + a generated `portal.css`; tokens round-trip to ODC theme variables on a test build. **Repos.**
this repo (+ tooling).

## P6 — harness-capture: CDP visual diff vs Figma frame (~3–4 days)
**Goal.** Implement the advisory (non-gating) visual channel.
**Steps.**
1. `harness-capture`: drive `harness/cdp_helpers.py` to screenshot built screens (auth, viewport per the
   parity method); diff vs the Figma frame using `scripts/pixel_diff.py`; emit a match% (advisory).
2. Honest exit semantics: visual is NEVER gating (structure-first per harness doctrine).
**Depends.** P1 (built app reachable) + P5 (frames). **Acceptance.** capture a known screen → match% vs its
frame, written as advisory; no exit-1 on visual mismatch. **Repos.** this repo.

## P7 — harness-verify LIVE executors, capture channel (~2–3 days; may shrink)
**Goal.** Close whatever gating assertion kinds P1.5 routed to `capture`.
**Steps.**
1. Take `componentPresent` and `navigates` channels **from P1.5's map** — do not assume capture. **Any kind
   P1.5 shows OML-readable moves to the P3 mcp executor and is dropped here** (P7 shrinks accordingly).
2. For kinds that remain `capture`: `componentPresent` via rendered-DOM observation (mapping per **[HD D6]**,
   itself contingent on P1.5); `navigates` via CDP click→observe-navigation.
**Depends.** P1.5 (routing) + P6 (for any capture-routed kind). **Acceptance.** for each capture-routed kind,
built screen with the feature → `pass`, without it → `fail`. **Repos.** this repo.

## P8 — harness-prompt-step (~2–3 days; anytime after P1)
**Goal.** Bounded, templated MCP build sub-steps (cheaper than free-form for repetitive work).
**Steps.** Harvest the recurring build steps that emerge from P1.5/P3 builds; template them against the MCP;
expose as `harness-prompt-step <template> <args>`. **Depends.** P1 + some build experience. **Acceptance.**
one real templated step (e.g. create-entity-from-spec) runs deterministically against the MCP. **Repos.** this repo.

## P9 — Grading test: Mentor × Figma on home_banking (CAPSTONE; ~1 week)
**Goal.** Prove the full loop on a known-good target, graded honestly against the P1.5 ground truth.
**Steps.**
1. Reverse the UI from home_banking **captures → Figma** frames (the structural spec already exists from P1.5).
2. Extract a stakeholder-altitude **brief** (the "spec input prompt") from {P1.5's reversed structural spec +
   the UI artifacts}.
3. Run the P4 interview answered from that brief → a fresh `app_spec`.
4. Build a **FRESH** app from that spec via `launch_build.sh`.
5. Grade the fresh build: structure via `harness-verify` against **P1.5's OML-reversed spec** (the rubric);
   visuals via `harness-capture` against the captures. **Do NOT grade the existing clone against its own
   derived spec.**
**Depends.** P1.5 (rubric), P3, P4, P5, P6, P7. **Acceptance.** a fresh build scores against the reversed
spec; a written grade report (structural pass-rate + advisory visual match); blockers logged as WALLS.
**Repos.** all.

---

## Cross-cutting (slot into the phases above)
- **Memory re-seed** for the spec factory → folded into P4.4.
- **Fresh-clone CI** (`cloneproof.sh`) → created in P0, run on every change to this repo.
- **mcp-wall filings** → driven by P1.5's channel map: file in the MCP doctrine notes only the kinds P1.5
  empirically shows the platform can't read. No pre-filing.
- **Wall-cap + WALLS.md feedback to spec factory** — when builds hit `spec-gap` walls (P1.5/P3/P9), route
  them back to P4's interview as spec-quality signal (the doctrine already says spec-gap walls are factory signal).

## Decisions (resolved — see HARNESS_DECISIONS.md)
- **[HD D1]** Run mode — build is a normal CC session (not `claude -p`); `RUN_MODE` toggle for future headless.
- **[HD D2, revised]** ODC MCP server/tenant — the **connected `your-tenant` server**, used for reads AND builds (revised from sandbox-only; accepted-risk mitigation: namespace + clean up build apps).
- **[HD D3]** `integrations` taxonomy — minimal v1, only home_banking's connector kinds (likely REST); widen later.
- **[HD D4]** Approval UX — marker file `builds/<app>/spec/APPROVED`; launcher refuses the build without it.
- **[HD D5]** Figma tool — `mattholihan/outsystems-figma-cli` (Desktop-open caveat acceptable; spec phase is interactive).
- **[HD D6]** `componentId→DOM` mapping — contingent on P1.5; only needed if `componentPresent` is NOT OML-readable.

## Sequencing summary (longest pole wins)
- **Now-ish, unblock everything:** P0 (~hours), P1 (~1 day), then **P1.5 (~3–5 days)** — P1.5's schema-gap
  list and channel map feed P2/P3/P7, so it precedes them.
- **Quick after P1.5:** P2 (schema v1).
- **The two-week investments:** P4 (spec interview, now in the harness) + P5 (Figma) — the actual product.
- **Then:** P6 → P7 (P7 shrinks by whatever P1.5 routed to mcp); P3/P8 land in parallel once P1/P1.5 are up.
- **Capstone:** P9 grades a FRESH build against P1.5's reversed spec. The end-to-end isn't real until P9.
