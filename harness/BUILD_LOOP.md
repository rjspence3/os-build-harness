<!-- The operating procedure a build-root Claude Code session EXECUTES to produce a
     100%-WORKING OutSystems app. The intelligence lives here, not in the agent:
     follow this loop literally, react to tool output per the rules, do not improvise.
     harness/CLAUDE.md is the doctrine; THIS is the step-by-step program. -->

# THE BUILD LOOP — execute this, don't improvise

## RUN MODEL (read first) — one Claude session PER BUILD, IN the build root
This loop is meant to be executed by a **dedicated Claude Code session launched from inside the
build root** (`cd builds/<app>/ && claude`) — ONE session per app. That session IS the builder and
the orchestrator. This is not incidental; it is what makes the loop work:
- It is a **main loop**, so its fire→poll→publish cadence across long Mentor turns is reliable — the
  harness re-invokes it deterministically on background-task completion. (A *nested subagent* driving
  the same loop stalls: its background-sleep→re-wake handshake is unreliable and parks it. If you ever
  MUST drive from a subagent, never `sleep`/yield — TIGHT-POLL the status tool to terminal, cap ~500.)
- Launched in the build root, it **loads that root's `.claude/settings.json`**, which allowlists the
  harness venv CLIs (`harness-verify`/`-prompt-step`/`-capture`/`-gate`) — without that, Bash denies
  them (closes SEAM-001). Verified headless too (2026-07-07): a `claude -p` build-root session runs the
  CLIs and certifies `harness-gate` unattended.
- **Interactive vs headless — the auth boundary (2026-07-07).** The OutSystems MCP's OAuth is
  INTERACTIVE. An interactive `RUN_MODE=session` inherits the live `/mcp` token, so it can drive Mentor
  — this is THE drive vehicle. A COLD `RUN_MODE=headless` (`claude -p`) session sees `outsystems` as
  UNAUTHENTICATED (only authenticate/complete_authentication exposed; Mentor/build tools uncallable), so
  it can drive Mentor ONLY with a pre-provisioned tenant JWT. Headless still runs the whole
  verification/gate half unattended; the Mentor DRIVE half needs interactive auth (or a provisioned token).
Mission-control (the hub repo) **DISPATCHES** a build to such a session (`/dispatch-build <app>`); it
does NOT hand-drive Mentor turns from the hub, nor orchestrate the build via subagents.

You are the **executor**. The harness is the intelligence. Your job is to run the
phases below in order, drive each step with the harness-rendered prompts, and react
to tool output using the deterministic rules here. Every rule below exists because a
prior build discovered it the hard way — you do **not** need to rediscover it.

**Done means WORKING, not present.** A screen that renders but whose buttons do nothing
is NOT done. The behavioral gate (Phase 6) is the definition of done; structural gates
are necessary but not sufficient.

---

## Phases (run in order; each has a harness command)

0. **Gate the spec.** `harness-verify <spec> --phase spec` → exit 0 or fix the spec-gaps first.
1. **Plan.** `harness-prompt-step --plan <spec>` → the ordered build steps. You execute this
   plan; you do not invent one. Each step names a recipe + params.
2. **Data model + screens present.** For each plan step, render its prompt
   (`harness-prompt-step <recipe> --params '…'`), fire it via `mentor_start`, drive the turn
   (§Turn), publish, and verify structurally (`harness-capture <spec> --base-url <url> --assert`
   → then `harness-verify <spec> --phase live --screens <snapshot>`).
3. **Shared chrome once.** Nav/sidebar/menu is the `nav-block` step — author it ONCE as a
   reusable block; never fan it out per screen.
4. **Auth + access.** `role-gate` steps; keep screens Anonymous, gate app-locally (§Recovery R6).
5. **Seed.** `seed-entity` steps so every list renders real rows (§Recovery R5).
6. **WRITE-PATHS + BEHAVIORAL GATE — the definition of done.** For every mutating action in the
   spec (`capabilities`/`actions` with `does` ∈ {CreateEntity, UpdateEntity, DeleteEntity}):
   wire it to persist, then PROVE it: drive the action in the browser, confirm the row is
   created/updated/deleted AND survives a reload. A create button that opens no form, or a form
   that doesn't persist, is a FAIL — fix it. The app is not done until every write-path passes.
   *(Structural passes do not count here; `componentPresent` is true for a dead button.)*
7. **Pixel/design** parity last (see CLAUDE.md §Pixel-perfect). Seed before pixels. Machine check:
   `harness-capture <spec> --base-url <clone-url> --pixel <reference>` where `<reference>` is a
   directory of `shot_<screenId>.png` (a prior capture or a `/design-layer` mockup export) OR a URL
   to capture the original from same-session/same-viewport. It screenshots every spec screen, emits a
   per-screen match% + an overall **fidelity score**, writes a `heat_<screen>.png` per screen, and
   **exits nonzero when any screen falls below `--pixel-threshold`** (default 99.0; `--pixel-tol` for
   anti-alias slack, `--pixel-mask` to zero out extension overlays). A restyle regression fails it.

Between phases, verify at runtime; never advance on "publish succeeded" alone.

---

## §Turn — how to drive one Mentor turn (deterministic)

1. Render the prompt with `harness-prompt-step` (pre-corrected) — do not hand-write it.
2. `mentor_start` (fresh session per committing edit; resume only for a dependent follow-up
   that must see turn-1's *unpublished* work — then publish once).
3. Poll `mentor_get_run` **once per wake**, paced by a background `sleep` heartbeat. Do NOT
   tight-poll or re-read empty output between wakes — one poll per heartbeat notification.
4. On terminal `succeeded`: check `change_applied` + `validation.error_count == 0`. Then
   **publish** (`publish_start`/`publish_status`).
5. **Verify at RUNTIME**, not by the model or by Mentor's summary. `no_changes_detected:true`
   is NOT proof of anything; `mentor_get_run` summaries lie (they claim "clean"/"stale view"
   when the model still has the defect). CDP/`harness-capture` is the only truth.

---

## §Recovery — symptom ⇒ action (do this, don't deliberate)

- **R1 Cascade/hang.** Turn sits at `applyModelApiCode` past ~2× a normal turn (i.e. >~15 min for
  a screen edit) ⇒ **cancel + split** into single-concern turns. NEVER combine structural-create
  with per-element cleanup, or seed with UI, in one instruction — it cascade-hangs 25–45 min.
- **R2 Detail-screen joins.** A detail/aggregate turn that joins FK entities cascades ⇒ use a
  **single-source aggregate** (parent entity only, no joins); resolve FK display fields separately.
- **R3 Row→detail navigation.** Only works cheaply when the cell is ALREADY a Link ⇒ surgically
  **set OnClick on the existing Link**. Asking Mentor to *create/wrap* a Link cascades — if there's
  no link, that's a heavier, separate turn; don't fold it into other work.
- **R4 Link "linkX" prefix.** Mentor's Link ships a default literal "link" ITextWidget; delete it
  (an Expression-only scan reports "clean" and misses it — see CLAUDE.md).
- **R5 Empty-after-seed.** `LoadSampleData` runs once; a newly-wired `LoadSampleDataFor<X>` is
  skipped by the run-once guard ⇒ add an **idempotent pre-guard block** at the START of
  `LoadSampleData` (count<X> = 0 ⇒ seed) so it inserts only when empty, independent of the guard.
- **R6 Auth.** Ask for "role access" and Mentor auto-adds a platform Role that breaks anon apps ⇒
  instruct "NO platform role, keep Anonymous"; gate app-locally (OnReady localStorage → GetUserById
  → If not admin → home). Seed a test user per role.
- **R7 Stuck cancel / wedged session.** A cancel can hang in `cancelling`, and a session whose last
  run was cancelled is UNPUBLISHABLE ⇒ **re-author the change in a FRESH session** against the last
  published rev. Don't wait on a wedged session.
- **R8 Big-table screens** (many rows) cascade on any edit ⇒ instruct "do NOT touch the table/rows/
  aggregate, only add X"; expect ~15–25 min even so.
- **R9 Entity has no identifier (partial phantom).** After the data-model step, VERIFY via
  `context_entities` that every entity actually persisted an `Id` identifier attribute — a data-model
  turn can report `change_applied=true` + "auto-number Id (default)" yet silently drop the identifier
  (gate_demo2, 2026-07-06). It stays LATENT (list screens render fine on other columns) and only
  detonates at the first write-path, where `Save<Entity>Record` needs `<Entity>.CreateAction` + `.Id`
  (Invalid Expression × N). ⇒ re-author data-model in a FRESH session to settle the identifier BEFORE
  the next publish — never after (changing an identifier post-publish is the irreversible
  OS-DPL-RDBS-40020). Do this check between data-model and the first create-form step, not later.

---

## §Done — completion criteria (all required)

**One machine check enforces all of it:** `harness-gate <spec> --base-url <url>` runs every applicable
gate (spec, structural, behavioral, role, render, and — with `--pixel <ref>` — fidelity) and exits 0
ONLY when every dimension the spec DECLARES is runtime-green. A dimension the spec doesn't exercise is
omitted, never vacuously passed. This is the "am I done?" the executor gates on — a green publish does
not count; a no-op publish (`no_changes_detected`) is not progress. The individual gates below are what
it composes:

- `harness-verify --phase spec` → exit 0.
- `harness-capture --assert` (structural: componentPresent/binding/navigates) → pass, verified at runtime.
- **Behavioral gate: every spec'd write-path drives + persists.** ← the real bar.
- Role gate (`--role`) for gated screens; render gate (`--render`) for charts/theme; pixel gate
  (`--pixel`) for fidelity.
- Every list renders real seeded rows; no dead buttons; 0 console errors.
- Design parity per the spec's `design` target.

If any write-path is a dead button or doesn't persist, the app is a scaffold, not done —
regardless of how many structural assertions pass. `harness-gate` refuses to call it done.

---

## Status of the harness's own intelligence (be honest with whoever runs this)

- **Encoded + usable now:** the plan incl. write-paths (`plan_from_spec` reads `actions/does`), the
  pre-corrected prompts incl. `create-form` (`prompt_recipes`/`harness-prompt-step`), structural
  verification (`harness-capture --assert` + `harness-verify --phase live`), the **behavioral gate**
  (`harness-capture --behavioral` — drives each spec'd create and asserts a row persists on reload),
  the **role gate** (`--role` — anon-blocked + member-allowed), the **render gate** (`--render` —
  chart paints + theme applied), the **pixel/fidelity gate** (`--pixel <reference>` — per-screen
  match% + fidelity score, exits nonzero on a restyle regression), and §Recovery above.
- **Run the behavioral gate as Phase 6's machine check:** `harness-capture <spec> --base-url <url>
  --login-config <json> --behavioral`. It is EXACT when the build emits the contract (`data-entity`
  on list containers, `data-spec-id="<field>input"`/`save<entity>btn"` on the form — the `create-form`
  recipe emits these); on legacy apps that predate the contract, persistence counting is heuristic
  (documented, never silent).
- **Known-open seams (see `harness/SEAMS.md`):** complex-modal creates (FK pickers) aren't yet
  driven by the gate's text-fill; auth-driven headless login is partial; and the build-root driver
  needs its permission set to allowlist the harness venv (or the tools exposed via MCP) — the doctrine
  does NOT guarantee CLI access. Track + close these via the run-subagent → document-seams → fix loop.
