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
| 5 | The driver could not run the harness CLIs (`harness-prompt-step`/`-verify`/`-capture`, venv python) — Bash denied by the sandbox — contradicting the doctrine's "autonomy" claim. | **OPEN** | Build-root permission set must allowlist the harness venv bin + venv python, OR expose plan/verify/capture as MCP-callable tools so a Bash-restricted driver can still reach them. (Doctrine's autonomy claim corrected to not assume CLI access.) |
| 6 | Runtime login mechanics (localStorage session keys, a test-user identity) live in prose, not a spec field, so a generated behavioral verifier can't authenticate headlessly. | **PARTIAL** | `auth.sessionKeys` + `auth.testUsers` exist in the spec (v0.2); the behavioral gate accepts a login config. TODO: derive headless login from `auth` directly (no `--login-config`), incl. a resolvable test-user id. |

### New seams found while BUILDING/TESTING the fixes (the flywheel surfaces more)
| # | Seam | Status | Fix |
|---|------|--------|-----|
| 1a | The `create-form` recipe and the behavioral gate must agree on the `data-spec-id` convention or the gate can never find the recipe-built form (recipe emitted `titleInput`, gate queried `titleinput`). | **FIXED** | Standardized both on lowercase (`<field>input`, `save<entity>btn`); a unit test now locks the contract. |
| 1b | Behavioral persistence *measurement* (row-count delta) is **contract-dependent**: exact when the list carries `data-entity="<Entity>"`, heuristic on legacy apps (linear predates it → false `0` counts). | **PARTIAL** | `list-screen`/`create-form` recipes emit `data-entity`; gate prefers it, falls back to a repeated-sibling heuristic. New builds are exact; legacy apps stay fuzzy — documented, not silent. |
| 1c | Complex create flows (a modal with FK pickers, not just text inputs — e.g. linear's issue/initiative create) aren't driven by the gate's naive text-fill → `NO_PERSIST` despite a working form. | **OPEN** | Gate v1 handles single-form (text) creates. TODO: pick/dropdown handling + required-field inference from the spec's mandatory attributes. |
| 1d | The public venv had no browser binary (`harness-capture` needs `playwright install chromium`) — a setup seam for whoever clones the repo. | **SETUP** | Documented in README quickstart; the CLI already errors with the exact install command. |

**Net after iteration 1:** the definition-of-done thread (Seams 1–4) is closed — `actions/does` now flow spec → plan → recipe → behavioral gate, and "100% working" is a machine check (`harness-capture --behavioral`). Open: driver permissions (5), auth-driven headless login (6), complex-modal create driving (1c). Next iteration: run a subagent on a fresh (non-linear) spec to surface seams a legacy app hides.
