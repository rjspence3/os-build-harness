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

### Autonomous mode — `python -m harness.run_build <spec> --create` (harness = brain AND hands)
The build-root session above puts the harness in the *brain* seat and a Claude agent in the *hands*
seat (firing each rendered prompt, reacting per §Recovery). `harness/run_build.py` collapses both into
the harness: it runs `plan_from_spec`, fires each step through the harness's OWN MCP client
(`harness/mcp_client.py`, via `mcp-remote`), publishes per unit, and — crucially — **codifies the
§Recovery rules that only surface at terminal/publish/verify** so it self-heals reproducibly with NO
agent in the loop (`classify_terminal`/`classify_publish` + `_verify_step`):
- **R1 hang / R7 wedged** → cancel the hung run, re-author in a FRESH session (each attempt is a fresh
  `mentor_start`), up to `--max-attempts` (default 3), then halt.
- **R9 data-model phantom / missing identifier** → an independent `context_entities` read confirms every
  entity landed WITH an identifier before the step is trusted; a phantom re-authors fresh.
- **R11 OS-DPL-50205 at publish** → HALT with the diagnosis (deterministic build-rule — a re-publish
  won't fix it; it's a recipe/spec gap to fix, not a transient).
- **R12 cancel-rollback / §Turn 5** → nothing is trusted on Mentor's word or a `no_changes_detected`
  publish; the `_verify_step` read is the truth.

Division of labor (be honest about it): the **recipes PREVENT** the rules that are pre-correctable
(R2/R3/R4/R5/R6/R8/R10 are baked into `prompt_recipes.py`), and the **driver RECOVERS** the residual
deterministic failures that only appear after the turn (R1/R7/R9/R11/R12). What the driver canNOT do is
invent a fix for a recipe/spec gap — those HALT with a diagnosis for a human/recipe change. Use this
mode for unattended/reproducible builds; use the session mode when you want an agent's adaptive judgment
on a novel failure. Both are public: a fresh clone has `pip install` (`mcp>=1.0`) + `npx mcp-remote`.

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
- **R10 Create-form widgets phantom.** A form's Inputs must live INSIDE a **Form container widget**; a
  BARE Input added straight onto the screen is the shape that intermittently phantoms — the turn reports
  `change_applied=true` but nothing persists (batcha, 2026-07-07, 4× fresh). The **positive detector**
  is phase-specific: a widgets turn that leaves OnClick empty MUST raise the "On Click must be set"
  validation error; if that error is ABSENT, the widgets did NOT persist ⇒ re-author FRESH; do NOT wire
  against widgets that aren't there (proceeding drifts the `data-spec-id` contract on the recovery →
  behavioral gate NO_CREATE_ENTRY). The plan's default create-form is now **action (own turn) → Form +
  inputs + wire in ONE turn** (`phase="combined"`, the proven-persist shape) — the old bare-widgets-only
  turn is retired as the plan default (still available as `phase="widgets"/"wire"` if a screen needs the
  split).
- **R11 OS-DPL-50205 at publish (0 errors in-session).** "Model features validation failed" is a build-time
  rule the TrueChange validator does NOT catch — deterministic (3 retries), so it's real, not transient.
  It is a GENERIC bucket; diagnose the specific element read-only (ask Mentor to compare the failing
  element to a known-good sibling). Three confirmed causes: (a) a local entity **FK to a cross-app
  referenced entity** (cross-app entities are consume-only, never FK targets); (b) a **public/exposed
  action that RAISES a Global Event** (raise-event actions must be non-public); (c) a **public/exposed
  Server Action that WRITES entities** (Create/Update/Delete/DeleteAll) OR **carries an Entity Record /
  Entity Identifier parameter in its signature** (live SLATracker 2026-07-07 — a public `SeedData` that
  wrote, and a public Tool whose input was an Application identifier; fixes: make the writer non-public,
  and take entity keys as Long Integer + `LongIntegerToIdentifier()` internally). An AI agent's Tools ARE
  public Service Actions, so they must be read-only with portable signatures — keep seed/write logic in a
  separate non-public action. **(d) a PUBLIC Web Block whose internal screen action performs a navigation**
  (`DestinationNode`) — the platform can't guarantee the target screen exists in a consuming app (live
  Rivian 2026-07-08 — `SidebarNav` was `Public=true` and its `DoLogout` navigated). Fix: author app-shell /
  internal blocks **Public=false** (they are not shared cross-app). The `nav-block` recipe now bakes this
  (Public=false + logout link only when the app has a login screen).
- **R12 Cancel rolls back UNCOMMITTED same-session edits (not just the cancelled turn).** A `mentor_cancel`
  (e.g. on an over-large seed turn) can discard EARLIER edits from the same session that had not yet
  committed — even ones whose turn reported `change_applied=true` (live SLATracker: entities from turn 1
  persisted but the Tool actions from turn 2 were gone after cancelling turn 3). Trust an INDEPENDENT
  inventory read (context reads / a read-only Mentor walk), never the success signal. Mitigate: keep
  turns small, publish/commit per logical unit, and re-verify the model after any cancel (ties to R7).

---

## §Workflow — building a Business Process (BPT) from scratch (RUNTIME-PROVEN, wfprobe 2026-07-07)

A workflow is the one construct that is **inherently multi-app** and has a **destructive landmine**, so it
does NOT build like a normal app. Follow this sequence exactly — it is proven end-to-end:

1. **Producer app (a NORMAL, non-Workflow app)** holds the trigger **Global Event** and the **PUBLIC Service
   Action(s)** the activities call. `CreateGlobalEvent` THROWS in a Workflow app, and an auto-activity can
   call ONLY a Public Service Action — so both live in the producer and are referenced cross-app. (Any app
   with a global event + a public SA works as the producer.)
2. **`app_create kind=BusinessProcess`** registers the Workflow app at rev 1 but does **NOT auto-publish it**
   (`deploy_list` = 0 deployments — verified). THIS IS THE SAFE WINDOW: the app is not yet bricked.
3. **ONE Mentor turn** (the `workflow` recipe): reference the producer's event + PUBLIC service action(s)
   cross-app (addReferenceToElements + AddDependency(ParseGlobalKey) + RefreshDependencies) AND author the
   process — Start(`StartProcessOn` = the referenced event, `TriggerMode` = Event) → auto-activities
   (`ActionToTrigger` = the referenced public SAs) → End. A referenced (cross-app) event binds to
   `StartProcessOn` and a referenced public SA binds to `ActionToTrigger` — both confirmed. Expect **0
   errors** (a "missing event handler" + "no User Provider" warning are benign for a consume-only workflow).
4. **Publish ONCE, with the process present.** Never publish before step 3 lands — a **0-process Workflow app
   publish CORRUPTS the verify cache** and bricks the app (recover only via delete/recreate). A valid
   1-process publish is clean (proven: rev 2, `no_changes_detected:false` = real deploy, no corruption).

The landmine is avoided **structurally** by the order: create (no publish) → author refs+process → publish.
Never a bare publish in between.

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
