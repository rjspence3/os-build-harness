# ODC production gotchas — the walls this harness already handles

OutSystems Developer Cloud (ODC) has a set of non-obvious rules that only surface at
**publish** or **runtime** — never at design-time validation. Every item below cost a live
build to discover; the recipes in `harness/prompt_recipes.py` encode the fix so you don't
re-hit it. This doc is the map: what the wall is, how it shows up, and which recipe handles it.

If you author ODC apps by hand (not through this harness), read this as a checklist. If you
drive the harness, this is *why* the generated prompts say the things they say.

> Provenance: mined from the harness **harvest ledger** (`harness/HARVEST_LEDGER.md`) — each
> entry was found by a real failed build, fixed in a recipe, and pinned by a test.

---

## Data model & cross-app references

**1. A consumer can only reference a PUBLIC producer entity.**
Referencing a `Public=false` entity across apps compiles clean in the IDE but the **build
engine rejects it at publish with `OS-BEW-COMP-50008`** ("An internal server error occurred!" —
no per-element detail). The first thing that compiles a *use* of the entity (an aggregate, a
query, an identifier) is where it blows up, so the crash *looks* like it's about the aggregate.
It isn't. → A data-owning Core must mark its entities `Public=Yes`.

**2. Never create duplicate entities on a rebuild.**
Re-running entity creation on an app that already has the entities makes ODC **auto-suffix a
name collision to `<Name>2`** — leaving a private original + a public duplicate. Consumers
reference the private original → gotcha #1. Any recipe re-run on a reused app must be
**idempotent** (find-or-create; update in place; flip `Public` on the existing entity, never a
copy). *(harness: `data_model` recipe is idempotent.)*

**3. `Entity.Update` wipes unset columns.**
A bare `{Id, ChangedField}` record blanks every other column. Always **fetch-then-modify**:
read the record, set only the changed field, then Update. Caught only by running the app, never
by validation.

---

## Public/exposed surface (`OS-DPL-50205` at publish)

**4. A public/exposed action may not write entities.** A Service Action that does any
Create/Update/Delete/CreateOrUpdate fails publish with `OS-DPL-50205` "Model features validation
failed" (0 errors in-session). Keep writes in a **NON-public `*Internal` Server Action**; the
public action delegates to it. (A Server Action also can't be Public at all — `OS-BLD-40409`.)

**5. A public Web Block that navigates trips `OS-DPL-50205`.** If a public block's internal
action performs a navigation (a `DestinationNode`), the platform can't guarantee the target
screen exists in a consuming app. Keep app-shell blocks **`Public=false`**.

**6. Consuming a screen-bearing (CrossDevice) app's Service Actions cross-app** also throws
`OS-DPL-50205` at deploy. Co-locate orchestration in the producer so the calls stay local.

---

## Build-engine crashes — rebuild fresh, don't grind

**7. `OS-BEW-*` / `OS-APPS-40028` are corruption, not transient.** `OS-BEW-COMP-50008`,
`OS-BEW-50000`, and `OS-APPS-40028` ("Input binary does not contain a valid OML") are
build-engine/OML-corruption failures. **Retrying in place deepens the corruption** (the working
OML wedges; a later resume then fails on a step that already succeeded). After 2, **rebuild
fresh** (new app), don't grind. *(harness: `run_build` halt-fasts on these codes.)*

**8. Publishes are per-step, so the deployed app is safe at the last good revision** even when a
later step wedges the Mentor working copy. A fresh session forks the clean deployed revision.

---

## UI / theming

**9. ODC charts are NATIVE toolbox widgets — not a referenced `OutSystemsCharts` block** (that's
classic O11). There are **exactly 7**: Area, Bar, Column, Line, Pie, Donut, Radar. Data wires
via `DataPointList` of `{Label, Value}` + `SeriesName`, bound to an **aggregate** (inline
`ListAppend` throws). Anything else (gauge/scatter/…) needs the `SetHighcharts*Configs` escape
hatch.

**10. A theme must RESET OutSystemsUI defaults or the class contract loses.** A styled
`.nav-item` container still renders its inner `<a>` as default blue+underline unless the theme
includes `.nav-item a { color: inherit; text-decoration: none }`. Set the exact CSS class on a
widget **at creation** (the class attribute is client-reactive; the inline-style attribute is
only honored at creation).

**11. Mentor drops container widgets.** Ask for "a value inside a `.kpi-card` Container" and it
may author the value and skip the container, rendering it bare. **Force the container** as its
own structural step and verify it exists post-author.

**12. Author dashboard COUNT aggregates BEFORE the kpi-card widgets.** Adding aggregates to a
screen that already has the card widgets can crash the compiler; author aggregates onto a clean
screen first, then the widgets.

---

## Runtime / orchestration

**13. ODC has no `IsInDevStage()` built-in.** A phantom stage-detection call authors clean but
fails publish `OS-DPL-50205` (model-features validation runs only at publish). Gate dev-only
seeds on an explicit `Confirm` Boolean **input parameter** instead.

**14. A headless Core can't seed itself.** An app with `screens: []` never fires `OnReady`, so
its seed never runs and consumers show 0 rows. Give it a minimal bootstrap screen.

**15. BPT (BusinessProcess) apps can't contain Structures**, and node-heavy processes time out
(900s). Put JSON/parse/transform logic (with a Structure) in a Core and reference it; keep the
process thin; stage complex processes across small turns.

---

## Working with the platform

**16. Read-back lags minutes.** `context_*` reads can show a stale snapshot after a publish.
Trust **`app_info.revision`** (+ a new `modelDigest`) as the persistence oracle; poll
`context_entities` until the entity `timestamp` advances past your publish.

**17. `no_changes_detected: true` on a `succeeded` publish is an ambiguous dedup signal**, not
proof nothing deployed. Verify the deployed inventory (or `app_info.revision` + `modelDigest`)
rather than trusting the flag either way.

**18. The Mentor session cap is 100 per tenant, cluster-wide.** Reuse ONE session across a
build's steps (`mentor_start` with `session_id` + `fresh_context=True`) instead of opening one
per step; a heavy day otherwise saturates the cap for ~24h (sessions reap on 24h inactivity;
cancel is a no-op on a terminal run). *(harness: `run_build`'s `SpecDriver` reuses the session.)*

---

*This list grows as the harness harvests new walls. See `harness/HARVEST_LEDGER.md` for the
authoritative, test-pinned record, and `harness/RECIPE_GAPS.md` for capabilities not yet covered.*
