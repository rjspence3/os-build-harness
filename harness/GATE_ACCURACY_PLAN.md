# Gate-Accuracy Build Plan — make `harness-gate` a trustworthy definition-of-done

**Scope:** HARNESS-GENERAL. Every change is to core modules (`harness/gate.py`, `harness/capture.py`,
`harness/prompt_recipes.py`) that gate **every** app the harness builds — not Rivian-specific. Rivian is
only the reproduction case that surfaced these bugs and the live-verification vehicle; the fixes (verdict
taxonomy, action-screen anchoring, edit-via-nav driver, KPI assertion, reliable count authoring) apply to
any spec.
**Status:** ready for `/build` (plan → implement-with-tests → review). Drive from the harness session.
**Branch:** `feat/autonomous-harness-and-rivian`. Keep the 418-suite green; add tests per workstream.
**Origin:** surfaced by the RivianReviewer4/R7 gate review, 2026-07-09.

---

## Problem statement

The gate's verdict is **inverted**: it hard-fails three things that work, and is blind to the one
thing that is broken. A harness that ships *production* apps cannot rest on a verdict that is strict
where it shouldn't be and silent where it must be loud. This plan makes `DONE` actually mean done.

The "accept it as-is vs chase literal green" decision is a false binary — both assume the verdict is
meaningful. The fix is neither: make the verdict trustworthy, then let the loop run to green.

### Evidence (verified against current code)

| # | Symptom | Root cause | Location |
|---|---------|-----------|----------|
| 1 | Supplier-intake create marked failing though it works | driver measures on `_list_screen_for_entity(entity)` = **first** entity-bound screen (screening), not the action's own screen (intake) | `prompt_recipes.py:1365`, consumed at `capture.py:397` |
| 2 | Part-edit marked failing though it works | `_drive_update` only finds an **inline** `Edit` row-action on the entity's own list; no edit-via-navigation mode — even though the create path already models nav-context (`_parent_context_nav`) | `capture.py:531`, cf. `capture.py:405` |
| 3 | `addSupplierBtn` flagged | create-form recipe authored `Add Supplier` instead of the spec's declared `+ New Supplier`/`addSupplierBtn` — recipe ignores `component.id`/label | create-form recipe in `prompt_recipes.py` |
| 4 | **Real defect: KPI shows `1`** | Mentor bound `.kpi-value` to `.List.Length` despite the recipe forbidding it **twice**; and **the gate never asserts KPI value**, so it would ship the bug | recipe prose ceiling `prompt_recipes.py:784-788`; no KPI check in `run_render` `capture.py:608` |

Net: the gate false-**fails** on 1/2/3 (working UX) and false-**passes** on 4 (broken app). Both are
gate-accuracy failures.

---

## Design: a two-class verdict taxonomy (the spine)

Today every failure is an undifferentiated verdict string, so "the checker couldn't reach the button"
is indistinguishable from "the app is broken." Split every behavioral/render verdict into two classes:

- **DEFECT** — the app is genuinely wrong. `NO_PERSIST`, `NO_UPDATE`, `NO_DELETE`, theme `NOT_APPLIED`,
  `NO_CHART`, and the new **KPI mismatch**. → contributes to a **HALT** (exit nonzero). Never accepted,
  never overridden.
- **UNVERIFIED** — the checker could not drive the app (wrong screen, no edit-via-nav path, no list
  found). → does **not** count as DEFECT (kills the false-fails), but does **not** vacuously pass
  either. It **blocks `DONE`** and routes the fix to the *driver/gate*, not the app.

`DONE` ⟺ **zero DEFECT and zero UNVERIFIED** (plus the existing "spec+structural actually ran" guard at
`gate.py:212`). This is what makes "accept R7" structurally impossible and makes the harness HALT hard
on real defects.

**Implementation note for the coder:** each driver already returns a `verdict` string. Add a
`verdict_class` field (`"ok" | "defect" | "unverified"`) derived from a single classifier map so the
taxonomy lives in one place. Then find where `run_acceptance` (`gate.py:80`, `capture.build_runtime_snapshot`
`capture.py:267`) folds per-dimension results into pass/fail and make: any `defect` → dimension FAILED;
any `unverified` with none `defect` → dimension `INCOMPLETE` (new state, blocks DONE, distinct from
FAILED in the report + JSON). Keep `--json` back-compatible by adding fields, not renaming.

---

## Workstreams

### W1 — Verdict taxonomy + `INCOMPLETE` state  *(do first; the rest depend on it)*
- Add `_classify_verdict(verdict:str) -> str` in `capture.py` mapping verdict prefixes to
  `ok|defect|unverified`. Map (initial):
  - `defect`: `NO_PERSIST`, `NO_UPDATE`, `NO_DELETE`, `NOT_APPLIED`, `NO_CHART`, `KPI_WRONG` (new).
  - `unverified`: `NO_LIST_SCREEN`, `NO_CREATE_ENTRY`, `NO_EDIT_ENTRY`, `NO_PARENT_CONTEXT`,
    `FORM_NOT_FOUND`, `SAVE_NOT_FOUND`, `NO_ROWS`, `ERROR *`.
  - `ok`: `PERSISTS`, `UPDATES`, `DELETES`, `APPLIED`, `RENDERS`, `KPI_OK` (new).
- Thread `verdict_class` onto every driver result dict.
- Update the acceptance aggregation + report/JSON to surface DEFECT / INCOMPLETE / OK counts and set
  `DONE` only when zero DEFECT **and** zero INCOMPLETE.
- **Rationale to preserve:** UNVERIFIED must not silently vanish — it is a signal to improve the gate,
  and it must block DONE.

### W2 — Anchor behavioral checks to the action's own screen  *(fixes #1)*
- `run_behavioral` (`capture.py:579`) already holds `screen` (the screen that declares the action).
  Pass it as the **measurement anchor** into `_drive_create`/`_drive_update`/`_drive_delete` and prefer
  it when it carries a data component for the entity.
- Extend `_list_screen_for_entity(spec, entity, exclude=None)` → add `prefer:str|None`: return `prefer`
  when it is entity-bound; else first non-excluded match. Fallback only when the action screen has no
  list.
- **Guard:** if neither the action screen nor any list screen can measure the entity, verdict
  `NO_LIST_SCREEN` → **UNVERIFIED** (not DEFECT).

### W3 — Edit-via-navigation driver  *(fixes #2)*
- Add an edit path to `_drive_update`: when the entity's own list has no inline `Edit` row-action but an
  edit screen exists whose input param references the entity, reach it the way the create path does —
  navigate from the parent/source row (reuse `_parent_context_nav` at `capture.py:405`), open the row,
  then drive the edit form + save + assert the marker persists.
- Selection rule: prefer inline edit; else nav-to-edit; else `NO_EDIT_ENTRY` → **UNVERIFIED**.

### W4 — Recipe fidelity: honor the declared button  *(fixes #3)*
- The create-form recipe must author the spec-declared button `id` + label (e.g. `addSupplierBtn` /
  `+ New Supplier`) rather than inventing `Add Supplier`. Emit `data-spec-id="<component.id>"` and the
  declared label verbatim so the structural check matches without loosening it.

### W5 — KPI-correctness assertion + reliable count authoring  *(catches AND fixes #4)*
**W5a — Catch it (gate gets stricter):** add a KPI check to `run_render` (`capture.py:608`). For each
dashboard card bound to a COUNT aggregate, read the rendered `.kpi-value` for that card
(`[data-spec-id="kpi<slug>"] .kpi-value`) and compare to the **true** row count (from the entity's
`sampleData` length, or a live list count on the entity's list screen, or a REST read). Verdict
`KPI_OK` / `KPI_WRONG (shows N, expected M)` → **DEFECT** on mismatch. A `.List.Length`-bound "1" now
FAILS loudly.

**W5b — Fix it reliably (stop trusting prose):** split the `dashboard` recipe emission in
`plan_from_spec` (~`prompt_recipes.py:1660`) into **two atomic steps** per your proven
one-step-per-unit tactic (commit `654f038`):
  1. author the `Count{Ent}` screen aggregate (data-only turn);
  2. a **bind-only** turn that sets the KPI Expression Value to `Count{Ent}.Count` and nothing else.

**W5c — Fallback if the split still flakes:** a deterministic Model-API corrective recipe
(`applyModelApiCode`) that locates the KPI Expression and rebinds it to the aggregate's `.Count`,
bypassing NL authoring for the one pattern Mentor won't do. Gated behind a config flag; only fires when
W5a reports `KPI_WRONG` after the split. W5a proves whichever mechanism landed.

---

## Test specifications (add alongside existing suite; keep 418 green)

- **T-W1 taxonomy:** unit-test `_classify_verdict` over every verdict string → correct class. Acceptance
  aggregation test: a run with one `NO_CREATE_ENTRY` and zero defects → verdict `NOT_DONE` with dimension
  `INCOMPLETE` (not FAILED); a run with one `NO_PERSIST` → `NOT_DONE` FAILED; an all-`ok` run → `DONE`.
- **T-W2 anchor:** given a spec where entity `Supplier` is bound on both `screening` (first) and
  `intake` screens and the create action lives on `intake`, `_list_screen_for_entity(..., prefer="intake")`
  returns `intake`. Driver-selection unit test asserts the create measures on the action screen.
- **T-W3 edit-nav:** spec fixture where `partEdit` is reachable only via a `release` row; assert the
  update driver selects the nav-to-edit path (mock the page eval calls; assert the parent-nav branch is
  taken, not `NO_EDIT_ENTRY`).
- **T-W4 button fidelity:** render the create-form recipe for a screen whose declared button is
  `+ New Supplier`/`addSupplierBtn`; assert the emitted prompt names that id + label and does **not** emit
  `Add Supplier`.
- **T-W5a KPI check:** unit-test the KPI comparison logic — rendered value `1` vs expected `4` →
  `KPI_WRONG` (DEFECT); `4` vs `4` → `KPI_OK`.
- **T-W5b split:** `plan_from_spec` on a spec with a dashboard COUNT card emits a `dashboard`/aggregate
  step **and** a distinct bind step (two steps, ordered aggregate-before-bind).

**Live-verification (manual, in the harness session, not CI):** rebuild `RivianReviewer5` and run
`harness-gate` — expect the three false-fails gone (INCOMPLETE→resolved or genuinely OK) and the KPI
either `KPI_OK` (W5b worked) or a loud `KPI_WRONG` DEFECT (then W5c).

---

## Acceptance criteria (definition of done for THIS plan)
1. Full suite green, including the new T-W1..T-W5 tests.
2. A behavioral verdict is classified DEFECT vs UNVERIFIED; `DONE` requires zero of both.
3. `harness-gate --json` emits per-dimension DEFECT / INCOMPLETE / OK counts (additive fields).
4. On `RivianReviewer5`: Supplier-intake create and Part-edit no longer report as app defects; the
   `addSupplierBtn` structural flag is gone; the dashboard KPI is asserted (OK, or a real DEFECT that
   HALTs).
5. No recipe loosens a structural check to pass — fidelity comes from authoring the declared artifact.

## Out of scope / follow-ups
- Spec actions naming their target entity/screen explicitly (the seam logged at `prompt_recipes.py:1316`)
  — would retire the `_list_screen_for_entity` heuristic entirely; do as a separate schema change.
- Pixel-dimension tightening against the staged screenshots.
- Applying the taxonomy to the Path-B multi-app `system_gate`.

## Sequencing
W1 → (W2, W3, W4 in parallel) → W5a → W5b → W5c only if W5a still red. Land W1 first: every other
workstream reports through the taxonomy.
