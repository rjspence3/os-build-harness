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

---

## Phase 2 — verification depth: render gate + full CRUD gate (2026-07-06)
The behavioral gate now verifies more than "creates persist":
- **`--render`** asserts a spec'd chart RENDERS (non-trivial svg/canvas) + `design.theme` is APPLIED (palette tokens live in the stylesheet). Proven on `full_app`: 2/2.
- **`--behavioral` covers Create/Update/Delete.** Added the `row-actions` recipe (per-row Edit link → prefill+Update via the existing Save<X>Record UpdateAction branch; per-row Delete button → DeleteAction+RefreshData; split edit/delete phases) + gate drivers `_drive_update`/`_drive_delete`. Authored Edit+Delete on the live `full_app` and the gate returned **create PERSISTS · update UPDATES · delete DELETES** (3/3). A dead Update button now FAILS — Phase 2's exit criterion.

**Two optimization findings (not seams — both authored first-try, just slow):**
- The `.Name`-property foot-gun is broader than first enumerated: Mentor also hit it on `IActionNode`/`IFlowNode` while self-verifying, burning ~15 min in an introspection loop. Broadened `_PREAMBLE` to forbid reading `.Name` off any Model-API node/widget/type interface + reiterate "don't run read-only verification loops."
- The Edit affordance's "set New<X> = the row's record" assignment is API-heavy for Mentor to discover (hit `IServerEntity.RecordType` etc.). Named the exact shape in the recipe (`New<X> = <aggregate>.List.Current.<Entity>`) to shave it next time.

**Remaining Phase-2 (build-dependent, not yet proven): role-gate enforcement (needs a non-anonymous app) + agent-reasoning-in-gate (needs the agent recipe to also emit a REST trigger).**

---

## Phase 4 — auth/login construct (2026-07-06)
Built `examples/auth_app` (Member + Home/Admin/Login + seed + login + role-gate) to prove the auth/login construct + close the Phase-2 role-gate proof. Outcome: **construct built + anon-enforcement PROVEN; member-allow blocked on a seed flakiness.**

- **`--role` result:** `admin · anon — BLOCKS_ANON` ✅ (the role-gate correctly redirects an anonymous visitor away from the gated screen — the security-critical half). `admin · member — BLOCKS_MEMBER` ❌.
- **Root cause of the member failure (debugged, NOT a logic gap):** the `login` recipe built correctly — `loginidentityinput` + `loginbtn` present, `GetMemberByName` lookup + `DoLogin` action + localStorage session all wired; it correctly shows "Invalid login" when no member matches. The failure is that **Member was never seeded** — the `WhenPublished` `BootstrapData`/`LoadSampleData` timer did NOT populate Rob/Kira (zero error logs), even though the identical seed recipe populated task_tracker, notebooks, AND full_app. So there is no member to log in as.
- **Seam A (login recipe):** Mentor set `ln_current_user` = the member's **Name** instead of its Id, wrongly concluding "Member has no Id attribute" (the auto-number Id exists). The role-gate had to be adapted to a Name lookup. Fix: the login recipe should name the Id attribute explicitly (or the session contract should standardize on a stable unique key the recipe guarantees).
- **Seam B (seed timer flakiness):** the `WhenPublished` timer silently did not seed on this app (no error). Non-deterministic across apps — a real reliability gap in the seed mechanism worth a runtime-verify + retry (or a synchronous bootstrap-on-first-load fallback).
- **Screen-scaffold cost:** step 2 (screens) phantomed once then took ~30 min of author↔validate cycling to persist; the login step ~35 min. This app was pathologically slow — the `.Name`-introspection foot-gun recurred on yet more interfaces (`IObjectSignature`) despite the broadened preamble.

**Net:** the auth/login construct is CODE-COMPLETE (login recipe + plan emission + gate driver + seed alignment; 268 tests pass) and the **role-gate anon-enforcement is runtime-proven**. The member-allow proof is blocked by seed-timer flakiness (Seam B), not by the harness's auth logic. Closing this fully needs Seam A + B fixed + a re-run.

### Phase 4 follow-up — seam B fix + deeper auth_app findings (2026-07-06)
**Seam B FIXED in the recipe (code-complete + unit-tested, 270 pass):** `seed-entity` now ALSO calls
LoadSampleData from an entry screen's OnReady (empty-guarded), so seeding no longer depends on the
flaky WhenPublished timer. The plan wires `bootstrap_screens=[loginScreen]` (authed) / `[defaultScreen]`
(display seeds). The OnReady wiring was authored + deployed on the live auth_app and validated.
**BUT the auth_app member-allow proof is STILL blocked** — even with the OnReady bootstrap firing,
Member stays unseeded. This traces the root cause PAST the timer to two deeper per-app Mentor flaws:
- **Seam C:** on auth_app, `LoadSampleData` does not actually INSERT (no error) — the same recipe seeded
  task_tracker/notebooks/full_app fine, so it is a non-deterministic Mentor authoring flaw in the
  seed action's guard/create logic, not the recipe text.
- **Seam D (login recipe):** the login lookup aggregate `GetMemberByName` is filtered by the input but
  is likely fetched at screen-start (empty) and NOT refreshed inside `DoLogin` before the lookup → even
  a seeded member would read as "Invalid login". The `login` recipe must explicitly `RefreshData` the
  lookup aggregate in the OnClick action after reading the input, before the found/not-found branch.
- auth_app is also **pathologically phantom-prone**: the screens step and the OnReady-bootstrap step each
  phantomed once (change_applied=false + confabulated success) and needed a fresh-session retry (R7); the
  screen + login steps took ~30-35 min each of author↔validate cycling.

**Net:** Seam B's fix is implemented + unit-tested; role-gate anon-enforcement is proven. Fully proving
member-allow needs Seam D fixed in the login recipe + a FRESH authed build (auth_app is too flaky to
salvage economically). The honest blocker is Mentor per-app authoring reliability, not harness logic.

### Phase 4 CLOSED — auth construct fully proven on a fresh build (2026-07-06, auth_app3)
**Seams A/B/C/D/E are RESOLVED and the member-allow proof is GREEN.** A fresh app
(`harnessbuild_authapp3`) built from the corrected recipes drove all 5 steps with **ZERO thrash**:
0 cancels, 0 phantoms, 0 hand-steps, 0 failed publishes — every step landed `change_applied=true`,
`error_count=0` on the FIRST fresh `mentor_start`. Contrast with auth_app/auth_app2, which were
pathologically phantom-prone; the difference is the fully-corrected recipe set + the tight-poll driver.

- **`--role` result: 2/2 OK — `BLOCKS_ANON` ✅ AND `ALLOWS_MEMBER` ✅.** The member-allow half that
  was blocked on auth/auth_app2 is now runtime-proven.
- **Seam E (identifier poison) — the last blocker — is FIXED and proven.** The prior cascade: login
  stored `Name` in the session key but the role-gate looked members up by `Id` (Text→Id cast), so
  Mentor silently changed Member's identifier Long→Text → OS-DPL-RDBS-40020 → undeployable. The fix
  makes `login` and `role_gate` AGREE on the identity attribute (`Name`) as the app-local session key,
  and both recipes explicitly forbid touching the entity Id/identifier. On auth_app3 step 5 published
  CLEAN — Mentor's own summary: "No platform role was added and the Member entity was not modified."
- **Seams B + D proven at runtime here too:** the OnReady bootstrap seeded Member (login succeeded for a
  real member), and the login lookup refresh resolved the member before the found/not-found branch.

**Net:** the app-local auth/login/role-gate construct is COMPLETE and END-TO-END PROVEN on a clean-room
build — data-model → screens → seed(OnReady bootstrap) → login → role-gate, 0 thrash, `--role` green.
Phase 2's last verification dimension (role-gate member-allow) is closed. The remaining honest caveat is
Mentor per-app authoring reliability (auth_app was flaky where auth_app3 was clean) — a Mentor property,
not a harness-logic gap; the tight-poll driver + corrected recipes are what made auth_app3 deterministic.

### Phase 3 CLOSED — pixel/design fidelity gate (2026-07-06)
The last missing verification pillar ("fool the head of product") is now a harness gate.
- **`harness-capture --pixel <reference>`** ports `scripts/pixel_diff.py` into the harness as
  `_pixel_compare` (pure-PIL, exact + fast: per-pixel max-channel delta via a C-speed histogram, no
  Python double-loop) + `run_pixel`. `<reference>` is EITHER a dir of `shot_<screenId>.png` (a prior
  capture / a `/design-layer` mockup export) OR a URL to capture the original from same-session/
  same-viewport (the clone-parity method: same `_apply_login`, 1440×900, full-page). Per-screen match%,
  overall **fidelity score**, `heat_<screen>.png` per screen, `--pixel-tol` (anti-alias slack),
  `--pixel-mask` (zero extension overlays), `--pixel-threshold` (default 99.0). Exits nonzero on drift.
- **`_theme_css`** now compiles the full token set — palette (unprefixed, so the `--<paletteKey>`
  runtime theme-applied check still works) + typography (`--font-*`) + spacing (`--space-*`) + fontFaces
  — deterministically (byte-identical CSS for a given token set).
- **Live proof (auth_app3):** self-vs-self → 3/3 MATCH, fidelity 100.0%, exit 0. A darkened-reference
  restyle regression → home DRIFT 0.0%, fidelity 66.67%, **exit 1** + heatmap. Both halves of the exit
  criterion demonstrated end-to-end against a deployed app.
- **Finding (not a seam — a correct null result):** a +60/channel tint of a white-dominated reference
  did NOT trip the gate, because white clamps at 255 so the visible pixels barely moved — the gate
  rightly reported no drift. A real restyle (x0.6 darken, which moves the white background too) tripped
  it. Lesson for reference authoring: a fidelity reference must differ in RENDERED pixels, not in
  clamped/no-op transforms.
- 8 browser-free unit tests (`tests/test_pixel_gate.py`) pin the discriminating core.

### Phase 5 CORE — autonomous-executor enforcement backbone + SEAM-001 closed (2026-07-06)
The autonomous run model needs a done-check a green publish can't fake, and a launched build-root
session that can actually run it. Both shipped.
- **`harness-gate <spec> --base-url <url>` (harness/gate.py, new console script)** — the single
  machine-checkable DEFINITION OF DONE. Composes spec + structural + behavioral + role + render +
  (opt-in) pixel into ONE acceptance report + exit code. Policy: a dimension the spec DECLARES is
  mandatory; a dimension it does not exercise is OMITTED (never a vacuous pass); the behavioral gate is
  the real bar; exit 0 iff DONE (no FAIL and spec+structural actually ran). This is the enforcement the
  headless executor and CI gate on — a no-op publish (no_changes_detected) never counts as done.
  Live-proven on auth_app3: ✅ DONE, exit 0 (spec ok, structural 3/3, role 2/2, pixel 100%, behavioral
  + render correctly OMITted). 9 browser-free composition tests (`tests/test_gate.py`) pin the policy
  (undeclared→OMIT, spec-gap short-circuits before live gates, any FAIL flips the verdict + exit code).
- **SEAM-001 (build-root can't run the harness CLIs) CLOSED IN PRACTICE.** Root cause found: the
  `_template/.claude/settings.json` allowlist existed but `launch_build.sh` never COPIED it into a
  scaffold — so a launched session's Bash sandbox still denied the CLIs. Fixed: the launcher now
  installs `.claude/settings.json` (idempotently, never clobbering a human edit) alongside CLAUDE.md +
  WALLS.md. Verified a fresh scaffold carries a valid 16-rule allowlist incl. harness-gate. The
  build-root permission-scope artifact is gone; a per-build session can now run the whole gate.
- **Headless launch now gates on the machine-done**, not self-declaration: the `RUN_MODE=headless`
  `claude -p` prompt drives ONLY the auto-emitted plan and is DONE only when `harness-gate` exits 0.
- REMAINING (live certification): a fully unattended headless build of a fresh spec to gate-green with
  zero human Mentor turns. The drive loop (BUILD_LOOP §Turn/§Recovery) + the machine-done are both in
  place; this is the end-to-end run, best executed as an actual dispatched per-build session.

### Seam (schema↔planner disagreement) — isDefault, surfaced by the gate_demo capstone spec (2026-07-06)
Building a FRESH CRUD spec (`gate_demo`) surfaced a real Phase-1 expressiveness gap the prior specs hid:
`plan_from_spec`'s `screen` scaffold step READS `screen.isDefault` (to mark the landing screen), but
`$defs/screen` was `additionalProperties:false` and never declared it — so `--phase spec` rejected any
spec that set it. Harmless only when the default is the FIRST screen (the planner's fallback); any
multi-screen app whose default isn't first was trapped (set it → spec-gap; omit it → wrong default).
Fixed: added `isDefault` (boolean) to the screen schema + a cross-ref guard (≤1 screen may set it) +
2 tests. This is the flywheel working — a new spec shape exposed a latent schema/consumer drift.

### Seam (create-form identifier poison) — surfaced by the gate_demo autonomous capstone (2026-07-06)
The first fully-autonomous capstone build (gate_demo: Task CRUD, driven end-to-end by a tight-poll
subagent, ZERO human Mentor turns) hard-blocked at STEP 4 (create-form :: action):
`OS-DPL-RDBS-40020: Identifier of existing Entity 'Task' cannot be changed, ''->'ID'` (deploy failed
after 3 server retries; deterministic, not transient). Steps 1-3 (data-model, screen, list-screen)
published clean.
- **Root cause (diagnosed, not guessed):** the `create_form` action turn authors `Save<Entity>Record`
  referencing `{entity}.CreateAction/UpdateAction` + a typed `{entity}` local + a `{entity}Record.Id =
  NullIdentifier()` branch. That heavy entity reference let Mentor "reconcile" by RE-KEYING the entity
  identifier — the SAME poison class as Seam E (login/role-gate), which `create_form` never got guarded
  against. Skeptical check ruled out the obvious alternative: notebooks AND task_tracker declare the
  IDENTICAL explicit `Id` attribute and passed create-form clean — so the explicit `Id` is NOT the
  trigger; they simply got lucky on Mentor's per-app nondeterminism. The guard removes the luck.
- **Fix:** `create_form`'s `action_step` (used by both `phase="action"` and the combined prompt) now
  forbids touching the entity: "do NOT rename, re-key, add, or change its identifier/Id … touch no
  entity schema", citing OS-DPL-RDBS-40020. Mirrors the proven Seam E fix (auth_app3 published clean).
  Test `test_create_form_action_phase_forbids_identifier_change`; 292 pass.
- The wedged app (harnessbuild_gatedemo, model rev 5 diverged, deploy deterministically failing) is
  unsalvageable by re-publish — the capstone re-run needs a FRESH app with the fixed recipe.

### Seam (data-model identifier partial-phantom) — gate_demo2 re-run (2026-07-06)
The create-form guard fix HELD (gate_demo2 STEP 4 hit NO OS-DPL-RDBS-40020, did not change the
identifier). But the re-run exposed the UPSTREAM cause both runs actually shared: the `data_model`
recipe DROPPED the isIdentifier attribute and PASSIVELY relied on "keep the default auto-number Id."
On gate_demo2, STEP 1 reported change_applied=true + "auto-number Id (default)" yet the Task entity
persisted with NO identifier at all (a PARTIAL phantom — Mentor confabulated the default Id). It stayed
latent through steps 2-3 (the table renders on Title/Done) and detonated at STEP 4 where
SaveTaskRecord needs Task.CreateAction + TaskRecord.Id → 4 validation errors. (Run 1's ''->'ID' rename
was the same identifier instability from the other side.)
- **Fix (root cause, not symptom):** `data_model` now SETTLES the identifier in-turn and CONFIRMS it —
  "every entity MUST end this turn with exactly ONE auto-number Long-Integer Id; do NOT assume the
  default — read each entity back and CONFIRM; create one explicitly for any entity missing it; report
  each identifier by name." Plus BUILD_LOOP §Recovery **R9**: after data-model, VERIFY via
  context_entities that every entity has an Id and re-author (fresh session) BEFORE the next publish if
  a partial phantom dropped it. Tests updated; 292 pass.
- notebooks/task_tracker/full_app passed this recipe only because Mentor's default Id happened to
  materialize for them — the passive reliance was luck, now removed. This is the deeper closure the two
  capstone runs were worth: the create-form guard AND the data-model identifier settlement together
  make the write-path deterministic.

### Phase 5 LOOP PROVEN + gate order-dependence finding (2026-07-06, gate_demo3)
**The full autonomous loop is certified end-to-end:** harnessbuild_gatedemo3 was built with ZERO human
Mentor turns (tight-poll driver firing the auto-emitted 6-step plan verbatim, 0 thrash — 0 cancels/
phantoms/re-authors/hand-steps/failed-publishes; R9 confirmed Task's Id after step 1), then
`harness-gate` certified it **✅ DONE, exit 0** (spec ok, structural 2/2, behavioral 1/1 write-path
PERSISTS; role/render/pixel correctly OMITted). This closes the two identifier seams AND proves
plan → autonomous drive → machine-checked done.

**FINDING (real wart, worth a fix): harness-gate is order-dependent on a no-seed spec.** The FIRST
gate run returned NOT DONE — structural's *binding* sub-check hard-failed because the Tasks list was
EMPTY (gate_demo's spec has no sampleData → the plan emits no seed step → cold list has 0 rows, and the
binding resolver marks an empty data-table `boundTo_unrendered`). The SECOND run passed only because the
first run's behavioral step had created a persisted row. So two identical invocations gave NOT DONE →
DONE — an enforcement tool must not do that. Two fixes on the table (neither spun yet, to respect
thrash): (a) a proper exemplar spec includes `sampleData` so the plan emits a seed step and lists render
on cold load (BUILD_LOOP §Done already requires "every list renders real seeded rows" — gate_demo's
omission is a spec-completeness gap); (b) harness-gate's structural binding check should treat a
present-but-empty bound table as INCONCLUSIVE (soft), not a hard FAIL, so the verdict is state-stable.
The app itself is correct — behavioral (the real bar) passed on both runs.
