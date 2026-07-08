# Step Atomicity — how the planner decomposes work into Mentor turns

Every plan step from `plan_from_spec` maps to exactly **one Mentor turn**. The single biggest
reliability lever, learned live across the Rivian build, is keeping each turn **atomic**: one concern,
few authored elements. Overloaded turns **hang** (recovery R1: cancel + fresh session), **fail**, or
**phantom** (report success, persist nothing). Atomic turns land.

> Evidence: a 3-button `action-button` turn failed after 3 retries; split to one button per turn it
> succeeds. A 22-record seed choked at 14 min; a lean seed authored fine. `create-form` phantomed as
> one turn; split to *action* then *form+wire* it persists.

## The rule
**Split multi-element work into one-concern steps.** The planner does this by construction:

| Recipe | Atomic decomposition |
|---|---|
| `create-form` | *action* (author Save server action) → *combined* (Form + inputs + wire) — two turns |
| `row-actions` | *edit* and *delete* are separate turns |
| `action-button` | one **button** per turn, and each split *action* (author the non-public server action) → *wire* (add + wire the button) — so N buttons = 2N atomic turns |
| `seed-entity` | one entity per turn; each row-count kept lean (~10–12 max) |
| `list-screen` / `dashboard` / `detail` | one screen region per turn |

## The exceptions — recipes that MUST be one turn
Some elements are interdependent *within a single Model-API transaction*; a later separate turn would
roll them back or couldn't share locals. These are exempt from the split rule (`_ATOMIC_UNIT_RECIPES`):

- **`data-model`** — interdependent entities (a FK to a not-yet-created entity fails); author all in one turn.
- **`seed-graph`** — the captured parent-Id locals are shared across the child creates; one action.

They can't be split, so the mitigation is to **keep them lean** (fewer attributes/rows) and let the
recovery loop absorb an occasional hang. The planner still surfaces their load (see below) so the
heaviness is honest, not hidden.

## Making load visible — `_step_weight` / `annotate_weights`
Each step carries a `weight` = a rough count of the elements Mentor must author in that turn. Steps
over `MAX_STEP_WEIGHT` (~14) are flagged:

- **`atomicity_warning`** (⚠) on a *splittable* heavy step — the planner should be taught to split it.
- **`atomicity_note`** (·) on an *exempt* heavy step (`data-model`/`seed-graph`) — can't split; keep lean.

`python -m harness.run_build <spec> --plan-only` prints the weight and any ⚠/· per step, so an
overloaded turn is visible **before** it fails, not after. This is the seam where the future
gate-driven loop plugs in: a step that fails as too-heavy becomes a signal to split it finer.
