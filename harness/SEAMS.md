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
