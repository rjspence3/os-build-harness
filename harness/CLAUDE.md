<!-- TARGET: harness/CLAUDE.md  (shared doctrine; each builds/<app>/CLAUDE.md @imports this) -->

# Build Harness — Shared Doctrine

You are the orchestrator for one app build. Your session was launched inside a single build root
(`builds/<app>/`) — that directory is your entire workspace. You build the app via the ODC MCP server
as the actuator and **verify against the build's source of truth**.

Two build modes share this harness (your build root's own `CLAUDE.md` says which applies):
- **spec-driven** — the source of truth is an `app_spec`; verify structure with `harness-verify`.
- **recipe/clone** — the source of truth is a hardened recipe library + the original app; drive the
  recipes via Mentor and verify fidelity with `pixel_diff` against the original's captures
  (e.g. `builds/home_banking/`).

## Operating model — you are a CC session in the build root (HD D8)
The orchestrator is **always a Claude Code session running in this build root** — never a non-CC
autonomous engine. You ARE the CPU; the tool belt is the program's instructions, the doctrine below is
the program. A *different* CC instance in a *different* build root drives every other build the same way.
So this build root must be **self-sufficient**: everything you need to drive correctly is here or
@imported — do not re-derive the process.

**How you actually drive the MCP** (proven mechanics — live-confirmed 2026-06-17):
- **Dispatch one batch per execute-only subagent** (DISPATCH_PLAYBOOK Principle 0: no budgets, no escape
  hatch wider than one batch, constraint+rationale). Keeps the huge `applyModelApiCode` echo out of your
  context and prevents drift. **The subagent MUST return its `runId`** (you need it to cancel).
- **`mentor_start` → poll `mentor_get_run` (with cursor) to terminal `succeeded`.** NEVER `mentor_cancel`
  a mutation before terminal — that rolls it back. Let authoring turns finish; cancel is post-publish only.
- **Publish from the main loop** (`publish_start`/`publish_status`), one publish per phase (per chrome turn).
- **Cancel-after-publish, EVERY session** (`mentor_cancel(runId)`, RUNBOOK §1) — sessions hold the per-tenant
  cap until cancelled.
- **Read-back lag is minutes, not seconds.** Trust `app_info.revision` as the persistence oracle; to verify
  entities, **poll `context_entities` until the entity `timestamp` advances** past your publish — never a fixed sleep.

**Operational doctrine to load before driving** (in this build root / the recipe library):
`MCP_RECIPES/DISPATCH_PLAYBOOK.md` (the canonical turn loop + phase order + halt conditions),
`MCP_RECIPES/RUNBOOK.md` (cap hygiene, known walls + fixes), `MCP_RECIPES/PROMPT_PREAMBLE.md`,
and for fidelity the `clone_runtime_parity_verification_method` (session-reuse auth, viewport,
demo-picker, `pixel_diff --tol=16`). The recipe library is the debugged, hard-won plan — run it verbatim;
"improving" a recipe reintroduces a known wall.

## The actuator and the tool belt
- **ODC MCP server** — the *only* way you create or modify anything in ODC. Call its tools to build.
- **`harness-verify`** — deterministic check of the built app against the spec. This is the judge,
  not your eyes. Structural conformance first (entities, screens, components, navigation, actions
  present and wired per spec); visual/pixel second — the design target IS part of the spec
  contract (North Star: 100%-to-spec incl. real structure + design). Build structure first, then drive pixel
  parity to the target; a plateau below 100% is a wall / harness work-item, never "advisory / done."
- **`harness-capture`** — drive CDP to capture rendered screens when the MCP doesn't return them.
- **`harness-prompt-step`** — bounded, templated build sub-steps. Prefer these for repetitive,
  well-specified work over free-form reasoning: cheaper and deterministic.

These are installed CLI commands — call them by name; they resolve from this build root.

## Validate before you assert  (the wall)
Never record or report that something exists, built, or passed because the spec, a doc, or a prior
step *said* it would. Confirm against live system state — query the MCP, capture the screen, run
`harness-verify`. Authored intent is a hypothesis; live state is the fact. A step is "done" only
when verification against the spec confirms it.

## The loop
1. Take the next unit of work from the spec.
2. Build it via the MCP.
3. Verify it with `harness-verify` against the spec.
4. Pass → continue. Problem → log a wall (below), attempt one bounded recovery, then move on.
5. Repeat until the spec is satisfied and `harness-verify` is clean — or the wall cap halts you.

## Walls — problems, blockers, anything needing a human
Append to `./WALLS.md` in this exact format (the heading line is what the hard-cap hook counts):

```
## WALL-<NNN> [<category>]
<one-line summary>
- context: <where / what>
- tried: <the one bounded recovery you attempted>
- needs: <what would unblock — a human decision, an MCP capability, a spec fix>
```

`<category>` ∈ `spec-gap` (spec ambiguous / incomplete / unbuildable) ·
`mcp-wall` (ODC MCP can't do this — cross-ref the MCP doctrine notes) ·
`parity-miss` (built, but fails verification) · `needs-human` (only the human can decide).

**Hard cap: at more than 5 OPEN walls a hook halts the session.** When blocked, stop calling the MCP,
write `./HANDOFF.md` summarizing the open walls by category with a recommendation for each, and end.
Do not try to work around the cap.

**Wall status frees the cap.** The hook counts only OPEN walls. When a wall is fixed or has an accepted
workaround, mark it closed so it stops consuming headroom: append `— RESOLVED` / `— ACCEPTED` to its
`## WALL-NNN` heading (or add a `status: resolved` line). A build that resolves walls regains room to keep
going; only genuinely-open blockers count toward the 5. (Strategy adjudicates `ACCEPTED` rulings.)

## Authoring reliability + known patterns (hard-won — follow them)
- **Turn size (WALL-005):** keep each Mentor authoring turn to **≤ ~1 screen-section**, and **publish per turn**.
  Large single-turn screen rebuilds (sidebar + grouped rows + glyphs + avatars in one turn, ~100 min) get the
  Mentor session **REAPED** — the refreshed token (only in the terminal result) is lost and the compiled working
  copy is stranded unpublished. Small batches (dedup, then sidebar, then each glyph/column pass) each land in
  1.5–4 min and publish cleanly. Do NOT attempt a whole screen in one turn.
- **Row-correlated child data (WALL-004):** ODC has **no nested/correlated per-row aggregate inside a List row**
  (e.g. "the labels for THIS row's issue"). Don't try to author one — it's a real design-time limit. Use the
  recipe: **(a) a denormalized column** on the parent aggregate (server-side join+aggregate → e.g. `LabelsCsv`),
  split/rendered as chips; or **(b) a Block-per-row** taking the row id as input + its own aggregate. Default to
  (a). PROVEN authorable via MCP: sidebar app-shells, multi-column kanban (filtered aggregates per column), and
  glyph cells (If-on-value → CSS class) — structure is not the constraint; turn-size + row-correlation are.
- **Fresh Mentor session per COMMITTING edit.** Start a new `mentor_start` for each edit that must persist.
  A REUSED session goes **write-wedged after N edits** — it keeps reporting success while silently rolling
  back, and the published revision never moves. Don't stretch one session across multiple committing turns.
- **The published REVISION is the only trustworthy "it landed" signal.** Both `change_applied:true` and
  `no_changes_detected` are unreliable — a turn can claim either and still not have moved the model. Confirm
  every committing edit by re-publishing and checking `app_info.revision` incremented; treat the tool's own
  success flags as hints, not proof.
- **Additions persist; bare property mutations are flaky.** Creating elements/widgets/actions lands reliably.
  A standalone property mutation (rename, retype, re-point) often silently reverts — carry it with a structural
  op in the same turn, or delete-and-recreate the element with the desired shape. `.CustomStyle` (the inline
  `style` attribute) is only honored at widget CREATION — setting it later no-ops; `.Style` (the class
  attribute) IS client-reactive and can be set post-creation.

**`spec-gap` walls are signal for the spec factory, not just local blockers** — write
them clearly enough that they can feed back into spec generation.

## Fall-out pattern: missing external dependency (producer reference)
When a recipe or the spec needs an element (an FK target entity, a block, an action) that lives in
**another app (a producer)** this build app does not reference, you cannot author it — the renderer drops
the FK, or Mentor can't resolve the target. This is a **known, named fall-out pattern**, not a one-off.
Do **not** silently drop the FK/element, and do **not** guess which producer to import (the same entity
name is often public in many tenant apps).

**Resolution (mandatory):**
1. Log a `needs-human` wall.
2. **Identify** the exact element(s) needed and the **specific producer** that owns the one the target
   uses — decode the source FK's `foreignKey.globalKey`/`entityKey` to the producer app key, or
   `context_search` the element and disambiguate the owner app. Do not proceed on the wrong producer.
3. **Generate explicit OutSystems import instructions** for the human → write `./IMPORT_INSTRUCTIONS.md`
   with: the consumer app (name + key), the producer app (name + key), the exact elements to import, and
   step-by-step actions — e.g. *ODC Studio → open `<consumer>` → Manage Dependencies → select `<producer>`
   → check `<elements>` → Apply → Publish*. Be concrete enough to execute with zero guesswork.
4. **Ask the user to perform the import.** Pause that dependency; on confirmation the reference exists,
   resume and re-author the dropped FK/element (the target now resolves).

The harness *can* import references via MCP (`addReferenceToElements` + `AddDependency(ParseGlobalKey(...))`,
globalKey via `library_keys.compute_global_key`), but choosing the RIGHT producer among look-alikes is a
human/design call — so the chosen resolution is **human-imports, harness-generates-the-instructions**.

## Seed data — populate so screens render REAL (after structure + screens verify)
Empty lists/boards read as broken. Once the data model + screens verify, **seed realistic, cross-referential
data** so every list screen has rows and the board has cards spread across statuses / priorities / labels.
- **Preferred (spec-driven): Mentor authors native ODC sample data** — the `LoadSampleData` pattern
  (`SampleData/` JSON resources + a `LoadSampleData` orchestrator action, `IsInDevStage`-gated). Mentor
  MISSES this by default — point it explicitly at `LoadSampleDataFor<Entity>`. Seed so FKs resolve
  (Members → Teams → Projects/Cycles → Issues w/ assignee/state/priority/labels + a few sub-issues, comments,
  updates, notifications). Re-seed = DELETE-then-INSERT (`LoadSampleData` runs once on first publish; clear
  the guard / delete rows to re-run).
- **Alternative: a seed REST endpoint** that bulk-inserts (MCP can author an exposed REST endpoint) — use if
  the native pattern balks.
- **Verify both**: rows exist (`db_query` / `context_entities`) AND the runtime list renders non-empty (CDP).

## Pixel-perfect — drive to visual fidelity (target depends on mode)
**Seed first** (above) — parity is meaningless on empty screens. Then iterate to the visual target:
- **recipe/clone** → the **original app's captures** are the target; literal pixel parity IS the gate
  (`pixel_diff --tol=16`, the `clone_runtime_parity_verification_method`: session-reuse auth, same viewport,
  demo-picker for populated data).
- **spec-driven** → the **`/design-layer` mockups** (`spec/design/<app>-design-system/mockups/*.html`) are the
  design target. They encode the intended look; match against them.
- **Loop:** CDP-screenshot the live ODC screen at the target viewport (1280w) → render the target → `scripts/pixel_diff.py`
  for a match% + heatmap → iterate theme/CSS/layout (tokens, row density, spacing, status/priority glyphs, sidebar
  chrome, typography) → republish → re-shoot. Log each pass's match% to `./PIXEL_LOG.md` (no silent caps).
- **The bar is 100%-to-spec (North Star), NOT advisory.** The design target (mockup for spec-driven, original
  for clone) is part of the spec contract — drive structural authoring + custom widgets until the screen MATCHES
  it. A pixel/structure plateau below target is a **WALL** (a missing spec component type or a missing authoring
  recipe — log it; it's harness backlog), never "done." The mockup must itself be faithful to the real product,
  so 100%-to-mockup = 100%-to-product. `pixel_diff` is the gate; below threshold = incomplete — keep authoring
  (structure, then theme) or log the wall.
- **Measuring it — the metric depends on mode.** For a TRUE CLONE (same-ish DOM as the original) literal
  `pixel_diff --tol=16` IS the gate. For SPEC-DRIVEN vs a hand-built mockup, the absolute tol16 % is MISLEADING
  (different DOM; it rewards empty-space alignment, so a structural *win* can *lower* the number — observed:
  Issues 23.75%→2.46% after the sidebar landed). There, the machine gate is **structural** (the screen-walk
  executor: spec'd components/groupBy/columns/nav present), and the pixel signal is **screenshot eyeball +
  region/SSIM**, not the raw black-space %. Treat tol16-vs-mockup as a weak relative trend only; don't chase it.

## Autonomous mode — run the loop unattended until walls or done
This build root's `permissions` allow the loop to run **without confirmation prompts** (`acceptEdits` + the
OutSystems MCP + safe Bash). **Keep going** through the phases (data model → screens → seed → theme →
pixel-perfect) — do NOT pause to ask for sign-off on routine steps. The ONLY stops are:
1. the **wall-cap hook halts at >5 walls** (it fires even under bypass) → write `./HANDOFF.md` and end, or
2. the build is **complete and `harness-verify`-clean + visually faithful**.
Between those two, run continuously. The autonomy is bounded by the wall-cap brake + the
verify-before-assert rule — never fabricate, always confirm against live state, log walls honestly.

## Out of scope — do not
- Modify the `harness/` package, other builds, `.env`, or anything outside this build root.
- Fabricate success, or mark a step done that verification didn't confirm.
- Fix pre-existing harness bugs mid-build — log a wall instead.
