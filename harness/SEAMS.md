# SEAMS — the harness-intelligence ledger

A **seam** is any point where the harness did NOT make a build-root agent smart enough to
proceed deterministically — where it had to improvise, guess, use outside knowledge, or got
stuck. The method: run a build-specific Claude as a subagent on a real task, have it report
seams, then FIX each in the harness (a rule, a tool, a recipe, a spec field). This file is the
running record. The goal is zero open seams for arbitrary apps — that is when the harness (not
the agent) guarantees a 100%-working build.

---

## Iteration 1 — linear "New Document" write-path (subagent, 2026-07-05)
The subagent completed the write-path AND surfaced 6 seams. Fixes below.

| # | Seam | Status | Fix |
|---|------|--------|-----|
| 1 | `plan_from_spec` never reads a screen's `actions`/`does`, so the plan emits ZERO write-path steps — the one thing Phase 6 calls the definition of done. | **FIXED** | `plan_from_spec` now emits a `create-form` step for every action with `does ∈ {Create,Update,Delete}Entity`, deriving entity/fields/id_param/creator/return from the spec. |
| 2 | No `create-form` recipe existed; the agent hand-authored the write-path prompt from tribal knowledge (non-public action / typed-local+per-attr / NullIdentifier branch / identity / cast). | **FIXED** | Added the `create-form` recipe encoding all of it, emitting `data-spec-id` on inputs + save button. |
| 3 | The behavioral gate ("does it persist") was hand-rolled — `harness-capture` was structural-only (`componentPresent` is true for a dead button). | **FIXED** | `harness-capture --behavioral`: drives each spec'd create action against the live app and asserts a row persists on reload. Validated on linear (Document create → PERSISTS 8→9; correctly flagged 5/6 write-paths NOT working). |
| 4 | Meta: the spec out-expresses the tooling — `actions`/`does` are declared but no tool (plan/recipe/verify) consumed them. | **FIXED** | `actions`/`does` are now first-class across plan → create-form recipe → behavioral gate. |
| 5 | The driver could not run the harness CLIs (`harness-prompt-step`/`-verify`/`-capture`, venv python) — Bash denied by the sandbox — contradicting the doctrine's "autonomy" claim. | **CLOSED** | `builds/_template/.claude/settings.json` allowlists the harness venv bin + venv python + playwright + pytest + git, inherited by every build-root session scaffolded from `_template`. (MCP-callable tools remain a future alternative.) |
| 6 | Runtime login mechanics (localStorage session keys, a test-user identity) live in prose, not a spec field, so a generated behavioral verifier can't authenticate headlessly. | **CLOSED** | `_login_from_auth(spec)` derives a headless login from the `auth` block (quick-login by the admin test-user's label at the login-screen route) when no `--login-config` is given; the behavioral gate uses it automatically. |

### New seams found while BUILDING/TESTING the fixes (the flywheel surfaces more)
| # | Seam | Status | Fix |
|---|------|--------|-----|
| 1a | The `create-form` recipe and the behavioral gate must agree on the `data-spec-id` convention or the gate can never find the recipe-built form (recipe emitted `titleInput`, gate queried `titleinput`). | **FIXED** | Standardized both on lowercase (`<field>input`, `save<entity>btn`); a unit test now locks the contract. |
| 1b | Behavioral persistence *measurement* (row-count delta) is **contract-dependent**: exact when the list carries `data-entity="<Entity>"`, heuristic on legacy apps (linear predates it → false `0` counts). | **PARTIAL** | `list-screen`/`create-form` recipes emit `data-entity`; gate prefers it, falls back to a repeated-sibling heuristic. New builds are exact; legacy apps stay fuzzy — documented, not silent. |
| 1c | Complex create flows (a modal with FK pickers, not just text inputs — e.g. linear's issue/initiative create) aren't driven by the gate's naive text-fill → `NO_PERSIST` despite a working form. | **MITIGATED** | The gate now also selects the last real option in native `<select>` dropdowns. Fake-`<div>` OS-UI pickers (no native `<select>`) remain undriven — documented; the `data-spec-id` contract on picker options is the eventual exact fix. |
| 1d | The public venv had no browser binary (`harness-capture` needs `playwright install chromium`) — a setup seam for whoever clones the repo. | **SETUP** | Documented in README quickstart; the CLI already errors with the exact install command. |

**Net after iteration 1:** all seams from iteration 1 are CLOSED or MITIGATED. The definition-of-done thread (1–4) is closed — `actions/does` flow spec → plan → recipe → behavioral gate, and "100% working" is a machine check (`harness-capture --behavioral`). Seam 5 (build-root permissions) and Seam 6 (auth-driven headless login) are closed; Seam 1c (fake-`<div>` FK pickers) is mitigated (native `<select>` handled). The only residual is legacy-app persistence *counting* being heuristic without the `data-entity` contract — new builds emit it, so they are exact.

**Validation gate:** the true test is a from-scratch clone of the public repo running a build end-to-end. Each such run is the next iteration — its seams get logged here and fixed. Next: run a build-subagent from a clean clone on a fresh (non-linear) spec to surface seams the legacy app hides.

---

## Iteration 2 — clean-room clone E2E (2026-07-05)
Cloned the public repo from scratch to a fresh dir, set it up (venv + deps + `playwright install chromium`), and ran the pipeline. `pytest` 252 passed, `harness-verify --phase spec` PASS, and `harness-prompt-step --plan` emitted the write-path step — but on a **new, non-linear spec** (`examples/task_tracker`, which linear never exercised) the plan surfaced one seam.

| # | Seam | Status | Fix |
|---|------|--------|-----|
| 2a | Write-path **entity inference picked the wrong entity** on a list-screen create: `tasks.CreateTask` derived `TaskList` (the screen's parent-context input param `ListId`) instead of `Task` (the data-bound entity the screen lists). `_screen_write_entity` preferred the input param over the `boundTo` component — backwards for a list-screen create. The recipe would have built a form for the wrong entity. | **FIXED** | Flipped `_screen_write_entity` to prefer the screen's data-bound entity (`boundTo`), falling back to an entity-typed input param only for a pure detail/form screen with no data component (where the input IS the record). Regression test `test_write_path_entity_is_the_data_bound_one_not_the_context_input` locks it. Deeper fix logged: the spec action should name its own target entity so inference isn't heuristic at all. |

**Why linear hid it:** linear's write-path work was a *detail* screen (`documentDetail`, a `DocumentId` input, no list) — the input-param-first heuristic happened to be right there. Only a **list-screen-with-create** (task_tracker's `tasks`) exposed the wrong ordering. This is exactly the point of running the clean-room E2E on a spec the legacy app never covered: the legacy app's shape masks seams a different shape reveals.

### Live behavioral gate from the clean clone (runtime capstone)
Ran `harness-capture <linear spec> --base-url <live> --behavioral` from the fresh clone with **no `--login-config`** — the closed Seam-6 auth-driven login (`_login_from_auth`) authenticated headlessly on its own. Verdict: **6 write-paths, 0 persist** —
- `issueDetail`/`projectDetail`/`members` → `NO_CREATE_ENTRY` (no New button on the list)
- `cycleDetail` → `FORM_NOT_FOUND` (New opens no editable form — dead button)
- `initiativeDetail` (2→2) / `documentDetail` (9→9) → `NO_PERSIST` (form submits, no row appears on reload)

**Calibration (important):** the gate's *driving* dimension — auth → navigate → detect entry point → fill → submit — is fully proven here and is **contract-independent**: the 4 `NO_CREATE_ENTRY`/`FORM_NOT_FOUND` verdicts involve no row-counting and are definitively linear scaffold. The 2 `NO_PERSIST` verdicts depend on the **heuristic** row-count because **linear is a legacy app the harness did not build** — it predates the `data-entity` contract (Seam 1b), so counting there is fuzzy by design (documented, not silent). `documentDetail` persisted (8→9) in an earlier session and now reads 9→9: either a genuine regression from later Mentor work OR a Seam-1b miscount — indistinguishable *on a legacy app*, and not worth disambiguating on one.

**Consequence for the validation plan:** the definitive E2E is NOT "gate vs legacy linear" — it is **"gate vs an app THIS harness built from a spec,"** where the `create-form`/`list-screen` recipes emit `data-entity`/`data-spec-id` and every verdict (incl. persistence) is exact. Iteration 3 = run a build-subagent from the clean clone on a fresh spec (e.g. `examples/task_tracker`) through Mentor to a live app, then run `--behavioral` against it and drive to 6/6. That is the real proof of "100% working," and the harness now has every piece it needs to attempt it.

---

## Iteration 3 — FIRST from-scratch build to a live 100%-working app (2026-07-05)
Built `examples/task_tracker` from an empty `app_create` through Mentor to a live app, and the harness's OWN behavioral gate — running **exact** against a contract-emitting build — certified it:

> `harness-capture builds/task_tracker/spec/app_spec.json --base-url <live> --behavioral` → **`tasks · create Task — PERSISTS (0→2)`, 1/1, exit 0.**

The gate drove the full real user path: `/Lists` → **Open** a TaskList → `/Tasks?ListId=<real>` → fill form → **Add task** → reload → row persisted. This exercises seams 3a (mandatory parent FK `Task.ListId` wired from the screen's `ListId` context), 3b (create-only `NullIdentifier`), and 3c (gate reaches the child create via the parent nav). **This is the north-star proof: the harness builds a working app from a spec, and its own gate verifies the write-path persists — exactly.**

### Seams 3a/3b/3c (write-path master→detail) — FIXED before the build (see commit ecea67f)
Encoded so `tasks.CreateTask` authored correctly first-try: `create_form` wires the mandatory parent FK from the screen's context input param; `_screen_id_param` returns None → create-only; the gate drives child creates through the parent nav. All unit-locked; the live gate confirmed them end-to-end.

### The dominant NEW theme: REVISIONS + THRASH (the user's explicit optimization goal)
"Done" is not enough — the harness must build in the **fewest Mentor turns / publishes, with zero cascade-thrash.** This build spent turns it should not have. The accounting, and the fix each implies:

| # | Seam (thrash source) | Cost this build | Status | Fix that makes it first-try |
|---|------|------|--------|-----|
| 3d | **No data-model/screen scaffold step** — `plan_from_spec` starts at `list-screen`, which assumes the entity+screen already exist. A from-scratch build has to hand-author entities and screens. | +2 hand-authored turns | **OPEN** | Emit `entity` + `screen` scaffold steps in the plan (data model in ONE turn; screens with their input params). |
| 3d-phantom | **Screen-create phantomed**: `status=succeeded` but `change_applied=false`; `context_screens`=0. The success narrative lied. | +1 retry turn | **DOCTRINED** | BUILD_LOOP already says verify runtime not summary; the `screen` recipe must assert `change_applied` and the loop retries fresh on phantom (R7). Caught here by trusting the honest signal. |
| 3d-anon (R6) | **Auto-role on new screens**: hand-authored screens inherited the module Role despite asking for "anonymous", which renders `_error` for anon → a whole extra turn to `Roles.Clear()+AnonymousAccess`. | +1 turn +1 publish | **OPEN** | The `screen` scaffold recipe must BAKE `Roles.Clear()+AnonymousAccess` at creation for anon apps (folds the anon fix into screen-create). |
| 3e | **`list-screen` ignores the spec's explicit nav component** — it emits generic "each row links", not the spec's `openTasksBtn` label "Open" + its `data-spec-id`, which the gate's parent-nav keys on. | hand-edited the prompt | **OPEN** | `list_screen` recipe should emit the screen's declared nav component (label + `data-spec-id`) when the spec has one; and/or the gate falls back to the first `[data-row-id]` row. |
| 3f | **`create-form` cascades as ONE turn** — authoring a branching server action + form + save-wiring on a populated screen thrashed >32 min (a full cancel) then thrashed again combined. **The thrash-free path, proven live:** (1) server action `SaveTaskRecord` (fresh turn), (2) form widgets bound to a local var, OnClick left empty (fresh turn), (3) wire the button OnClick **resuming the same session as (2)** so it builds on the unpublished widgets, then publish ONCE. | 1 cancelled 32-min turn + 1 more cancel, vs the clean 3 | **OPEN (highest value)** | Expand the `create-form` plan step into these 3 ordered sub-steps, with the widgets+wire pair marked "same session, publish once". This is the single biggest thrash-killer. |
| 3g | **No seed step for display entities** — the plan seeds only the auth user entity, so a list with no create UI (`Lists`) renders empty and the gate has no parent row to open. | +1 turn +1 publish | **OPEN** | Plan should emit a `seed-entity` step for any entity bound to a list on a screen that has NO create write-path (else it can never be populated), building the LoadSampleData + `WhenPublished` timer from scratch when the app has no loader yet. |
| G-count | **Gate count heuristic double-counts** — `PERSISTS (0→2)` where one row was created; `_COUNT_JS` likely counts a row's cell + its `tr`. Harmless for `after>before` but inaccurate. | n/a (verdict correct) | **OPEN** | Tighten `_COUNT_JS` to count distinct row containers (prefer `[data-row-id]` rows, de-duped by nearest row ancestor). |

**Also confirmed:** SEAM-001 (subagent can't run the harness CLIs — a build-root permission-scope artifact, not a harness-logic gap; the main session runs them fine, which is the documented intended configuration). SEAM-002 (the screen phantom above).

### The thrash-free build playbook (what the harness should make deterministic)
For an anon master→detail app like task_tracker, the minimal clean path is **~6 committing turns, 6 publishes, zero cancels**:
1. `app_create`.
2. **Entities** — all interdependent entities in ONE turn.
3. **Screens** — all screens + input params in ONE turn, Anonymous BAKED (no separate anon turn), verify `change_applied` (retry fresh on phantom).
4. **list-screen** per data screen (emit the spec's nav component).
5. **create-form** as 3 sub-steps: server-action (fresh) → widgets (fresh) → wire-OnClick (resume) → publish once.
6. **seed-entity** for list-bound entities lacking a create UI (LoadSampleData + WhenPublished timer).
Then `--behavioral` → PERSISTS. Every OPEN seam above is a place the current harness forces a hand-step or risks a cascade; closing them turns this playbook into emitted plan steps + first-try recipes.

**Net:** iteration 3 PROVED the end goal (built + gate-certified a working app) AND produced the precise, prioritized backlog to make the next build thrash-free. 3a/3b/3c are closed in code; 3d–3g + G-count are the next code fixes, ranked by thrash cost (3f first).

---

## Phase 0.1 — clean-room re-build proving 0% thrash (2026-07-06)
Built a NEW spec of the same shape (`notebooks`: Notebook→Note master-detail CRUD) by driving ONLY the auto-emitted 8-step plan (data-model → screen(anon) → list-screen×2 → create-form action/widgets/wire → seed) via a background build subagent that fired the harness-rendered prompts VERBATIM through MCP (subagent needed only MCP — the pre-rendered prompts sidestepped SEAM-001). Result: **behavioral gate PERSISTS** (`notes · create Note`, exit 0) — the plan built a working app. Thrash tally: **0 phantoms, 1 cancel, 1 hand-step** — two real seams, both fixed:

| # | Seam | Status | Fix |
|---|------|--------|-----|
| 0.1-seed | The `seed-entity` recipe prompt said to REUSE the app's "EXISTING sample-data mechanism" — but a fresh MCP-created app has NONE (no LoadSampleData orchestrator/timer, and the sibling entity is populated via the runtime create form, not a loader). The driver had to CREATE the whole mechanism = 1 hand-step. | **FIXED** | `seed_entity` now instructs building LoadSampleData + a WhenPublished timer from scratch (empty-guarded, idempotent), reusing if present — the proven task_tracker pattern. Test locks it. |
| 0.1-introspect | Mentor repeatedly emitted `Console.WriteLine(... .Name)` on interfaces that don't expose it (IMobileWidget/ITypeSignature/IUIFlowNodeSignature/IIdentifierType/IBasicType), burning turns on compile errors before authoring; on screen-touching steps it self-recovered, but on list-screen attempt 1 it never escaped → 1 cancel. | **FIXED** | Added to the shared `_PREAMBLE`: author directly, no long read-only introspection loops, and do NOT call `.Name` on those interfaces (compile error) — reduces the diagnostic cascade across every step. |

**What the run VALIDATED (0 phantoms is the headline):** the `change_applied` gate + fresh-session-per-step killed phantoms; the screen scaffold with Anonymous baked (no separate anon turn), the `Open` nav link (3e), the create-form 3-phase resume+publish-once (no 30-min cascade), and the auto-seed all landed and produced a gate-green app. The two remaining thrash sources were a recipe-prompt premise (seed) and a Mentor read-phase foot-gun — both now closed. **Next clean-room build should approach 0/0/0; re-run to confirm.**

---

## Phase 1 — spec expressiveness + first live chart/theme/agent build (2026-07-06)
Schema v0.3 (agents/charts/design.theme/sampleData, additive) + plan emission made the orphan recipes spec-reachable. Then a clean-room build of `examples/full_app` (11 steps: CRUD + chart + theme + seed + a separate AIAgent app) driven by a subagent firing the rendered prompts verbatim through MCP returned **0 cancels · 0 phantoms · 0 hand-steps · 0 seams** — Phase 0.1's 0/0/0 CONFIRMED (the seed + introspection fixes held) AND the chart/theme/agent recipes proven live for the first time.

**Runtime-verified (not trusted):** CRUD `--behavioral` PERSISTS; `/Projects` renders the chart (`svg` present, chart element found); the theme applied (`--primary: #5E6AD2` live in the DOM); the agent app deployed + published clean (NO OS-APPS-40028). Both never-built-live recipes (chart, theme) were **buildable exactly as-written** — no seam.

**Optimization (not a seam):** the chart step took ~112 min because Mentor had to discover the block-instance `ExtendedProperties` attribute API + the DataPoint `mapTo` argument-expression shape by trial. Folded both into the `chart` recipe (name `ExtendedProperties` not `.Attributes.Create()`; `mapTo {Value: IntegerToDecimal(<value>), Label: <category>}`; quote hex colors) to shave that on the next build. 0% thrash is met; this pushes toward least-TIME.
