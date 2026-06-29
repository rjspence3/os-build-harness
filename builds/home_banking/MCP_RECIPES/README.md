# MCP Recipe Library

A **defined methodology** for building OutSystems Developer Cloud apps via the
Mentor MCP. Not a script collection — a standardized vocabulary that codifies
how to drive Mentor toward deterministic, reproducible OML output.

## The methodology

Every recipe **defines as much as possible explicitly**. Mentor never guesses,
never explores, never improvises. Each call is one `applyModelApiCode`
invocation with pre-resolved API surface, pre-validated patterns, and a STOP
protocol on any deviation. The result: same manifest + same recipes = same
app, every time.

Recipes **compose** in a deterministic build order:

```
  STRUCTURE PHASE        →   LOGIC PHASE        →   CHROME PHASE
  (the skeleton)             (what it does)         (what it looks like)
  ───────────────────        ──────────────         ──────────────────
  01 server entity           04 action (CRUD)       10 theme (CSS/fonts)
  02 static entity           05 action (SQL)        22 custom block
  03 role                    06 action (workflow)   23 chrome wrap
  07 screen (dechromed)      16 action (foreach)
  08 screen (detail)
  09 screen (dashboard)
  11 default screen
  17–21 AI agents (parallel: agent app + memory + prompt + tools + multitenancy)
```

**Dechromed first**: a screen is authored as a bare functional skeleton using
standard OutSystemsUI components (default Container, default Layout, default
widgets) with working data bindings + logic wired. It's *correct* but
*generic-looking*.

**Then chrome**: custom blocks (Menu, Header, brand-specific icons) get
authored separately. The theme (CSS + brand vars) gets applied. A final
"chrome wrap" recipe replaces dechromed placeholders with their custom-block
counterparts.

The split matters because:
- Dechromed screens are simpler to author + verify (just OS UI standard library)
- Chrome is reusable across many screens (one HBIcon block instantiated 12 times)
- Theme is independent (swap brand = replace one CSS + a few blocks)
- Build order is deterministic (no chicken-and-egg between screens and the blocks they use)

## Why this exists

After a day of MCP-driven OS app builds (see corpus memories), the cost of letting Mentor
"figure things out" became clear:

- Mentor's `get_app_summary` boilerplate consumes ~15% of the session-context budget
  before any user code runs
- Discovery probes (e.g. inspecting a layout block) can blow another ~70%
- One unexpected error and Mentor begins regenerative rewrites that drift from spec
- Cancelled sessions lose all their work (publish gate requires `succeeded` terminal)

Recipes flip the model: every recipe is a paste-ready prompt that pre-resolves the API
surface, names the exact patterns to use, and instructs Mentor to STOP on any error
rather than iterate. Mentor becomes a deterministic compiler for OML, not an
exploratory agent.

## Layout

```
data/MCP_RECIPES/
├── PROMPT_PREAMBLE.md      ← prepend to every recipe call
├── README.md               ← (this file)
├── 01_entity_server.md             ← server entity w/ PK + typed attrs + FK delete rules
├── 02_entity_static.md             ← static entity + records
├── 03_role.md                      ← role w/ Public flag
├── 04_action_crud.md               ← thin wrappers + multi-output projections
├── 05_action_sql_update.md         ← SQL UPDATE/INSERT/DELETE w/ parameter binding
├── 06_action_workflow.md           ← multi-step branching + aggregate-then-If + AI pipeline
├── 07_screen_table.md              ← table-pattern screen w/ pagination
├── 08_screen_detail.md             ← master-detail w/ N child aggregates
├── 09_screen_dashboard.md          ← dashboard (KPIs + chart + activity feed)
├── 10_theme_replace.md             ← full stylesheet swap + dark mode + custom fonts
├── 11_default_screen.md            ← eSpace.DefaultScreen setter (avoids redirect loop)
├── 12_screen_wizard.md             ← multi-step wizard, StepNo-gated containers
├── 13_screen_modal.md              ← Popup w/ Show*:Boolean local + open/close actions
├── 14_screen_document_upload.md    ← per-doc-type slot w/ DocumentStructure + AI validator
├── 15_screen_master_detail_sidebar.md  ← admin work surface w/ collapsible action sidebar
├── 16_action_foreach_list.md       ← bulk per-item Service Action via ForEach
├── 99_publish_verify.md            ← publish_start + post-publish verification probe
│
└── apps/                            ← per-app manifests + build playbooks
    └── home_banking/                ← reconstruct Home Banking from scratch (35 entities, 152 actions, 16 screens)
        ├── README.md                ← build sequence, expected revisions
        ├── entities.yaml            ← spec for all 35 entities (Core)
        ├── actions.yaml             ← spec for 152 action signatures
        ├── actions-bodies.md        ← 5 captured action body samples
        ├── screens.yaml             ← spec for 16 screens (Portal + Backoffice)
        ├── roles.yaml               ← 3 roles
        ├── theme-portal.css         ← Portal stylesheet (~28KB)
        ├── theme-backoffice.css     ← Backoffice stylesheet (~30KB)
        ├── theme-email.css          ← shared transactional email styles
        └── _raw/                    ← Mentor probe outputs feeding recipes 12–15
```

## How to use a recipe

For each recipe you want to run:

1. **Open `PROMPT_PREAMBLE.md`** and copy its paste-block content (everything inside
   the triple-backtick block under "Paste verbatim, prefixed to the recipe body").

2. **Open the recipe file** and copy its `## Mentor prompt (paste verbatim)` block.

3. **Substitute the `{{PLACEHOLDERS}}`** with concrete values for your app.

4. **Send to Mentor MCP** via `mentor_start` with:
   - `app_key` = your target app
   - `prompt` = preamble + (substituted) recipe body

5. **Poll `mentor_get_run`** until `status: succeeded`. Verify the diagnostic stdout
   matches the recipe's "Expected stdout" section.

6. **Publish immediately** via `publish_start` + `publish_status` poll. Verify
   `revision` bumped and `status: Finished` (NOT `FinishedWithError`).

7. **Verify via `context_*` REST API** (per `99_publish_verify.md`) that the catalog
   sees the new element.

8. Move to the next recipe. Each recipe = one publish cycle. Do not bundle.

## How to rebuild an app from scratch

Per-app manifests live in `apps/<app_name>/`. To rebuild:

1. Portal-create the app (manual gesture — no MCP path to create new apps; see
   `[[odc_mcp_no_app_creation]]`)

2. Run the manifest's build sequence in **phase order** (publish after each
   recipe; structural equivalence is the final gate, not OML byte-equivalence):

   **Phase 1 — Structure (the skeleton)**:
   - Static entities (typically 5–15 enums)
   - Server entities (typically 5–30 domain records)
   - Roles
   - **Dechromed screens** — bare functional skeletons using standard OS UI
     components only. Data bindings + logic wired but no custom theming.

   **Phase 2 — Logic (what it does)**:
   - Server actions (CRUD wrappers, SQL actions, workflows, foreach loops)
   - Service actions (cross-app callable)
   - Default screen wiring

   **Phase 3 — Chrome (what it looks like)**:
   - Custom blocks (Menu, Header, app-specific icons + helpers)
   - Theme stylesheet
   - Chrome wrap — replace dechromed widget shells with custom-block instances

   **Phase 4 — Verify**: Recipe 99 against the published OML, structural diff
   against the captured original.

3. Publish after each recipe. The build is **idempotent** — recipes that
   would no-op on re-run (entity already exists, etc.) report `Status: OK
   (no change)` rather than fail.

### What "identical" means here

OS rendering is deterministic. Two apps with the same widget tree + same
properties + same theme will produce **byte-identical rendered HTML/CSS** at
runtime, regardless of which internal widget IDs Mentor assigned to each
node during authoring. Pixel diffing is the wrong verification — it
conflates real differences (missing widget, wrong style) with non-differences
(widget ID `b3-Container` vs `b7-Container`).

The verification surface is **author-controlled state**:
- Widget types + author-set names
- BlockInstance SourceBlock refs + parameter bindings + placeholder fillings
- Property values (Style, CustomStyle, Source, Condition, Visible, OnClick…)
- Screen action wiring + data-binding sources
- Theme stylesheet content + entity schemas

The verification ignores:
- Mentor's auto-generated bookkeeping IDs
- Studio canvas position metadata (HorizontalPosition, VerticalPosition)
- OML XML node ordering within sibling sets
- Default property emissions that one capture omits and the other includes

## Hard rules baked into every recipe

| Rule | Why |
|---|---|
| One applyModelApiCode call per recipe | Prevents session-context exhaustion |
| No reflection, no probing in production recipes | Discovery is done in this library, not at use-time |
| All FKs use `DeleteRule.Ignore` | `Protect` is deprecated (OS-BLD-40409) |
| PK set in same call as entity creation | Cannot be added post-publish (OS-RDBS-GEN-40003) |
| Mentor STOPS on first error | No regenerative drift; caller decides recovery |
| Publish happens between recipes, not inside them | Each recipe is atomic + rollback-friendly |
| Diagnostic output is one line, machine-checkable | Enables programmatic build pipelines |

## Versioning

- Recipes are versioned by file name (`01`, `02`, …) for stability.
- Per-app manifests are versioned by directory + a manifest version header.
- When the underlying ODC platform changes (e.g. new deprecation), recipes get a
  patch update with the date and a `corpus_ref` to a memory documenting the change.

## Corpus references — load these before authoring new recipes

- `[[odc_mcp_entity_auto_actions_incomplete]]`
- `[[odc_db_upgrade_pk_change_blocked]]`
- `[[odc_mcp_sql_node_api]]`
- `[[odc_mcp_publish_terminal_success_gate]]`
- `[[odc_mcp_screen_creation_broken_complianceops]]`
- `[[odc_mcp_record_literal_via_typed_local]]`
- `[[odc_long_integer_to_identifier_cast]]`
- `[[odc_mcp_assign_node_iteration_not_flow_order]]`
- `[[odc_mcp_session_context_wall]]`
