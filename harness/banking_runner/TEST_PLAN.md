# Banking Runner — Test Plan

A sequenced plan to validate every recipe + the orchestrator end-to-end before
running the full rebuild. Each tier depends on the previous tier passing.

## Test target

Primary: **TestRunnerSandbox** (`6d7a3257-4a75-4341-92ed-c9f7efc40584`) on
Development env (`3ba8afaa-fc56-4c7a-8704-939086449c7c`). Already has:
- ChartDataOption (static, 3 records)
- HBBranch (server, 7 attrs)
- HBCustomer (server, 21 attrs + 2 FKs)
- TestRoleRunnerSmoke (role — session-scoped, not persisted)

Currently at revision 5.

## Pass/fail criteria — universal

A test PASSES iff all of:
1. `compilationErrors: []` in the `applyModelApiCode` tool_end
2. Expected `Recipe NN: <Name> | Status: OK` line in stdoutOutput
3. No `validationOutput` errors (warnings OK)
4. `publish_status: Finished` within 90s
5. `app_info.revision` bumped
6. `context_search` confirms the artifact exists with expected properties
7. **Structural diff** (for screens, blocks, themes): the rebuilt artifact's
   author-controlled properties match the captured original — see T4.3 for
   what counts vs is ignored

Failure on any of these → STOP, record verbatim error, do not proceed to next tier.

---

## Tier 1 — Already-authored recipes, untested live (~30 min)

### T1.1 — Action recipe (Recipe 04 stub)

**What**: Dispatch `render_action_stub` output for one simple action against
TestRunnerSandbox.

**Action target**: `CheckAndGrantRole` (Portal — User Identifier input only,
no outputs, no producer call). Already rendered to `/tmp/check_grant_role.prompt.txt`.

**Steps**:
1. `mentor_start` with the rendered prompt + TestRunnerSandbox app_key
2. Wait 60s
3. `mentor_get_run` → verify `Recipe 04: CheckAndGrantRole | Created: action (...)` in stdout
4. Capture mentor_session_id + mentor_session_token from terminal payload
5. `publish_start` with those creds + Dev env_key
6. Wait 90s
7. `publish_status` → `Finished`
8. `context_search` query="CheckAndGrantRole" objects=["Actions"] scoped to TestRunnerSandbox
9. Verify the result contains the action with: Public=False, 1 input (UserId: User Identifier), 0 outputs

**Pass criteria**: All universal criteria + action's IsPublic + parameter types match.

**Likely failures**:
- "Action with name X already exists" → action got created in earlier test; pick a different name
- Compile errors on the User Identifier resolver → indicates the FK auto-inject still has bugs

**Time**: ~5 min

### T1.2 — Recipe 10 (theme replace)

**What**: Replace TestRunnerSandbox's theme with HomeBankingPortal's `theme-portal.css`.

**Steps**:
1. `render_theme(theme_name="CustomStyleTheme", css_path="data/MCP_RECIPES/apps/home_banking/theme-portal.css", is_default=True)`
2. Dispatch via `mentor_start` (prompt is ~40 KB — large but well under per-call limit)
3. Wait 60s, poll, verify stdout
4. publish_start + publish_wait
5. `context_themes` (need to load the tool) → verify theme exists with the expected stylesheet length

**Pass criteria**: Theme created, `IsDefault=true`, stylesheet length matches input within ±100 bytes.

**Likely failures**:
- CSS @import rules stripped by publish (per `[[odc_publish_strips_css_import]]`) — acceptable, recipe docs this
- Theme name conflict — pick a unique test name like `TestThemeRunnerSmoke`

**Time**: ~5 min

### T1.3 — Recipe 99 (verification probe)

**What**: Dispatch the read-only verify probe against TestRunnerSandbox to
confirm it correctly reports counts.

**Steps**:
1. `render_verify_probe(expected_entities=3, expected_screens=0, expected_actions=0)` — counts based on what's actually there now
2. Dispatch via mentor_start
3. Wait 30s, poll
4. Verify stdout includes:
   ```
   Recipe 99 — Post-publish verification:
     Entities: 3 (server=2, static=1) — expected 3 — OK
     ...
   ```

**Pass criteria**: All count comparisons report OK (matches reality).

**Failure handling**: If counts mismatch, that's actually useful info — tells us what's drifted.

**Time**: ~3 min (no publish needed — read-only probe)

### T1.4 — Recipe 11 (DefaultScreen) — DEFERRED

**Blocker**: TestRunnerSandbox has no screens. Recipe 11 requires a target
screen to exist. Test in Tier 3 after a screen recipe runs.

---

## Tier 2 — Author + test missing recipes (~6-8 hours)

**Status (2026-05-27)**: T2.1 + T2.2 complete (48 unit tests, all passing).
T2.3 + T2.5 pending. Live dispatch of T2.2 deferred to T4 (TestRunnerSandbox
lacks the prereq entities DataSettings/Region for ManageSettings).

### T2.1 — Tree parser (`tree_parser.py`) — prerequisite for T2.2 + T2.3 — ✅ COMPLETE

Read `.tree.md` files → typed AST. Same parser powers screen authoring AND
structural-diff verification. Build first.

Schema:
```python
@dataclass
class WidgetNode:
    type: str               # "Container" | "Text" | "Button" | "BlockInstance" | "If" | "Placeholder" | ...
    name: str | None        # author-set name; None if unnamed
    properties: dict[str, str]  # Text, Style, CustomStyle, Source, Condition, Visible, Width, OnClick, ...
    source_block: str | None    # for BlockInstance
    block_params: dict[str, str]  # for BlockInstance — block input parameter bindings
    children: list[WidgetNode]
    placeholder_fillings: dict[str, list[WidgetNode]]  # for BlockInstance — placeholder content
    true_branch: list[WidgetNode] | None  # for If
    false_branch: list[WidgetNode] | None
```

**Test**: Parse one of each (small + large + If-branch + BlockInstance-heavy)
and verify round-trip equality with a printer.

**Time**: 2-3 hours

**Delivered**: `pipeline/banking_runner/tree_parser.py` + 24 tests in
`tests/test_tree_parser.py`. Parses all 10 captured `.tree.md` files
(`backoffice-*` + `portal-*`); per-screen smoke (name, inputs, locals,
aggregates, top-level widgets); If branch detection; quote-escape handling;
2-space vs 4-space indent tolerance; `PLACEHOLDER` vs `Placeholder` variance;
T/F branch path segments. Bonus: `diff_screens(expected, actual) → list[Difference]`
covers all author-visible deltas (widget_type, name, source_block, condition,
SIGNIFICANT_PROPERTIES, events, child_count) — wired for T4.3 structural diff.

### T2.2 — Screen dechromed renderer (STRUCTURE phase) — ✅ COMPLETE (unit-tested; live dispatch deferred to T4)

**Inputs**: A `.tree.md` AST + manifest entry → applyModelApiCode prompt that
authors the screen WITHOUT custom-block dependencies.

**Transform applied to the AST**:
- BlockInstance to a custom block (Menu, Header, HBIcon, AlignCenter, etc.) →
  replace with the OS UI default equivalent + a `// CHROME: <BlockName>`
  marker. Examples:
  - `BlockInstance 'LayoutSideMenu'` → keep (it's OS UI standard)
  - `BlockInstance 'Menu'` → comment + skip
  - `BlockInstance 'HBIcon'` → replace with `Text` widget bearing the icon text
  - `BlockInstance 'AlignCenter'` → wrap children in `Container Style="display-flex justify-content-center"`
- BlockInstance to OS UI standard block (Wizard, Carousel, Chart, etc.) →
  keep verbatim
- Everything else → emit verbatim

**Output**: An applyModelApiCode prompt that creates the dechromed screen.
Plus a side-output: the original AST nodes that got replaced, dumped as
`chrome_wrap_<screen>.json` for use by T2.5.

**Test target**: Smallest screen first — `backoffice-managesettings.tree.md`
(15 widgets). Dechrome it, dispatch, verify.

**Pass criteria**: Screen creates with the right widget hierarchy minus the
custom-block chrome, publishes clean, data bindings work.

**Time**: 3-4 hours

**Delivered**: `pipeline/banking_runner/screen_renderer.py` + 24 tests in
`tests/test_screen_renderer.py`. Renders all 10 captured trees without
crashing. Coverage: screen + role + flow setup; inputs (mandatory + identifier
types); locals (defaults + Boolean/Integer/Text); aggregates (source entity
resolver across local IServerEntitySignature / IStaticEntitySignature /
references); widget types (Container, Text, Button, If, Dropdown, Input,
Image, Expression); BlockInstance dispatch (`OS_UI_STANDARD_BLOCKS` kept;
custom blocks stripped to placeholder Container with `// CHROME-STRIPPED:`
marker for T2.5 chrome-wrap); screen action stub creation (only for OnClick
handlers, NOT for `Destination=` navigation); diagnostic line.

**Live dispatch deferred**: ManageSettings depends on DataSettings + Region
entities not present in TestRunnerSandbox. Live test moves to T4 (full rebuild
where prereq entities are created first).

### T2.3 — Custom Block authoring recipe (CHROME phase)

After dechromed screens land, author the custom blocks they would have used.

Per `[[odc_mcp_block_creation_works]]`: `IMobileFlow.CreateBlock(name)`
creates new blocks. Need a recipe template that authors:
- Block name + IsPublic flag
- Input parameters (with default values)
- Placeholders (via `CreateWidget<IPlaceholderWidget>`)
- Internal layout (Container + Text + chrome)
- Block style sheet
- Screen actions (event handlers)
- OnEvent input parameters (for parent-child event flow)

**Capture phase**: For each custom block referenced by `_raw/*.tree.md`,
dispatch a Mentor probe to extract the block's structure (similar to screen
captures but using `getWebBlock` instead of `getScreen` per `[[odc_ui_mcp_surface]]`).

**Author phase**: New recipe `22_block_create.md` + Python renderer
`render_block_from_capture(block_ast)`.

**Test target**: HBIcon (smallest custom block — single placeholder + 1
inline-styled text).

**Pass criteria**: Block creates + publishes + visible in Studio.

**Time**: 2-3 hours

**Delivered**: `pipeline/banking_runner/block_renderer.py` (BlockAST +
BlockParam + BlockEvent dataclasses, `render_block(ast) → C#`, plus a
speculative `parse_block_tree()` for future `.block.tree.md` captures);
`data/MCP_RECIPES/22_block_create.md` recipe template doc; 16 tests in
`tests/test_block_renderer.py`. Coverage: idempotent re-run guard
(`Status: ALREADY_EXISTS` short-circuit), input parameters with mandatory +
default value, Action-typed event input parameters with output params,
widget tree (reuses screen_renderer dispatcher), block style sheet emitted
as C# verbatim string, custom flow_name override, nested custom-block
stripping via shared `OS_UI_STANDARD_BLOCKS` set. Live capture deferred to
T4 (need `.block.tree.md` captures from a Mentor probe — billable). Renderer
ready to consume them when they exist.

### T2.5 — Chrome Wrap recipe (CHROME phase) — wires dechromed screens to custom blocks — ✅ COMPLETE

Takes the `chrome_wrap_<screen>.json` from T2.2 + the now-published custom
blocks from T2.3, replaces the dechromed widget shells with BlockInstance
references.

Recipe 23 mutates an existing published screen — it doesn't recreate from
scratch. Pattern: find the dechromed shell by Name or position in the
hierarchy, replace via `parent.RemoveWidget(shell) + parent.CreateBlockInstance(...)`,
populate parameter bindings + placeholder fillings.

**Test target**: Wrap the dechromed ManageSettings screen from T2.2 with the
HBIcon + Menu + Header blocks from T2.3.

**Pass criteria**: Structural diff (T4.3 tool) vs original
`backoffice-managesettings.tree.md` → zero significant differences.

**Delivered**: `pipeline/banking_runner/chrome_wrap.py` (ChromeWrapManifest +
`extract_chrome_wrap_manifest(ast)` + `render_chrome_wrap(manifest)`);
`data/MCP_RECIPES/23_chrome_wrap.md` recipe template doc; 27 tests in
`tests/test_chrome_wrap.py`. Coverage: OS UI vs custom-block filter, deep
walk (children + If true/false branches), end-to-end against real
ManageSettings capture, full wrap emission (flow + screen lookup, marker
discovery, BlockInstance creation, parameter binding via name lookup, marker
RemoveWidget, status diagnostic), layout-only-property filter (Width/Style/
Visible NOT bound as block parameters), no-entries diagnostic. **Critical
symmetry tests**: `strip_marker_name()` is deterministic; T2.2's emitted
marker Names match T2.5's lookup Names for every chrome site in every real
capture (10 captures × ~4 sites each = ~40 marker pairs validated).

**Updates to T2.2**: `screen_renderer._render_block_instance` now sets a
stable `.Name = strip_marker_name(source_block, path)` on stripped
placeholder Containers. This is the contract that lets T2.5 find what T2.2
set without any coordination state.

**PLAN_GAPs**: CW-A (children of stripped Containers discarded — fine for
Banking recreate since they were synthetic). CW-B (block parameter values
with runtime expressions passed as literal strings to SetValue). CW-C (no
cross-check between Recipe 22's declared inputs and Recipe 23's parameter
bindings — name drift silently drops bindings).

**Time**: 3-4 hours

### T2.3 — AI Agent recipes (5 new)

Per the deferred R10:

- `17_agent_app_create.md` — needs Portal-only gate; document the manual step
- `18_agent_memory_entity.md` — memory entity authoring
- `19_agent_system_prompt.md` — 3 variant patterns (inline / composed / param-description)
- `20_agent_tool_wiring.md` — CreateActionHandler + IsFilledByAI markers
- `21_agent_multitenancy.md` — AgentsConsumerApp Identifier wiring

**Capture phase**: For each of the 5 existing banking agents (CallIntakeAgent,
EnrichmentAgent, CommunicatorAgent, UnderwriterAgent, OfferAgent), Mentor
probe to extract:
- System prompt content
- Memory entity schema
- Tool list (Server Actions with IsFilledByAI)
- Inputs/outputs
- AgentsConsumerApp Identifier value

**Test target**: Simplest agent first. Per the corpus, OfferAgent looks like
the simplest (per `[[odc_agent_architectures]]` data).

**Pass criteria**: Agent app authors + publishes + tools callable + memory
entity persists records.

**Blocker check**: Does the agent backend have its required plugin loaded?
Mobile had a plugin failure — verify Agent works before investing time.

**Time**: 3-4 hours

### T2.4 — Action body capture + Recipe 06 (workflow) integration

Per the deferred R13: capture flow bodies for the 95 actions we don't have
bodies for, then author Recipe 06 instances for each.

This validates Recipe 06 (workflow with branches + aggregates + ExecuteAction
nodes) which we wrote but haven't tested live.

**Test target**: One action with a captured body — `Sidebar_ChangeStatus`
(Backoffice). Has 8 inputs, 5 nodes including an If branch. Already captured
in `actions-bodies.md`.

**Pass criteria**: Recipe runs, action creates with correct flow, publish
succeeds, action callable.

**Time**: 2 hours for the test path; 4+ hours to capture the remaining 94.

---

## Tier 3 — Integration tests (~4 hours)

**Status (2026-05-27)**: T3.4 (code change) complete + wired. T3.1 / T3.2 /
T3.4 simulated via FakeMentorMCP unit tests (12 tests, all passing) —
exercises orchestrator multi-recipe flow, halt-on-failure, resume-after-
interrupt, verify-phase wiring. T3.3 (live mcp-remote subprocess) deferred to
Tier 4. Live Mentor dispatch of T3.1+T3.2 also deferred — the FakeMentorMCP
scripts validate the orchestrator's state-machine paths, so the only thing
the live test adds is real-MCP behavior validation which Tier 4 will cover
holistically.

### T3.1 — Multi-recipe phase

**What**: Dispatch 5 recipes in sequence against a fresh sandbox, with
publish-per-recipe. Validates the orchestrator's loop + state DB transitions.

**Recipe set** (against `TestRunnerSandbox2` — Portal-create a fresh one):
1. Static entity: ChartDataOption (3 records)
2. Static entity: HBAgentType (5 records)
3. Server entity: DataSettings (1 attr)
4. Server entity: HBBranch (7 attrs)
5. Role: HomeBankingCore

Run via:
```bash
python scripts/build_banking.py --app core --run --app-key <TestRunnerSandbox2-key>
```

**Pass criteria**:
- All 5 recipes show status=succeeded in state DB
- Each has a unique publication_id
- App revision = original + 5
- context_search confirms all 5 artifacts

**Failure mode to watch**: cascading failure where recipe N's compile error
brings down N+1 (which should be skipped due to halt-on-failure).

**Time**: ~15 min runtime + setup

### T3.2 — Resume after interrupt

**What**: Validate state DB-based resume.

**Steps**:
1. Start T3.1's build
2. Kill the process after recipe 3 succeeds (Ctrl-C or SIGTERM)
3. Re-run the same command
4. Verify only recipes 4-5 dispatch (recipes 1-3 should be skipped)

**Pass criteria**: No double-creation errors. Final state matches T3.1.

**Time**: ~10 min

### T3.3 — Python orchestrator end-to-end (mcp-remote subprocess)

**What**: Run the actual Python `MentorMCP` client (not Claude Code's MCP)
end-to-end against an app.

**Setup**: First run will pop browser OAuth via `mcp-remote`. User completes
the flow. mcp-remote caches token at `~/.mcp-auth/`.

**Test**: Dispatch one Recipe 02 (small, fast) via the Python client.

**Pass criteria**:
- mcp-remote spawns + initializes
- Mentor tools callable via the stdio JSON-RPC bridge
- mentor_get_run cursor pagination works
- publish_start/wait via Python returns Finished
- No subprocess hangs or zombie processes

**Likely failures**:
- mcp-remote npm package missing → `npx -y mcp-remote` should auto-install
- OAuth callback timeout → user has to finish browser flow
- JSON-RPC message format mismatch → would need to adapt the Python client

**Time**: ~15 min if smooth; ~1 hour if OAuth + serialization issues

### T3.4 — Recipe 99 dispatch from orchestrator — ✅ COMPLETE

**What**: After phase completes, orchestrator should dispatch Recipe 99 to
verify counts. Currently not wired.

**Code change needed**: Add `_verify_phase()` call at the end of `build_app()`
in orchestrator.py that uses `render_verify_probe` + dispatches it.

**Pass criteria**: Verify probe runs, reports counts matching the recipes that
just landed.

**Time**: ~30 min code + test

**Delivered**: `Orchestrator._verify_phase(config) -> VerifyResult` wired
into `build_app()`. Reads succeeded-recipe counts from state DB via
`_compute_expected_counts()` (phase-prefix-based bucketing: `01_server` +
`02_static` → entities, `07_*` → screens, `04_*` → actions). Renders
Recipe 99 prompt via `render_verify_probe()`, persists to
`prompts_dir/99_verify_<app>.prompt.txt`, dispatches via mentor_start +
mentor_poll (NO publish — verify is read-only), parses stdout for
`Recipe 99 ... Status: OK|DRIFT`. `VerifyResult` carries status/stdout/
expected/compile_errors. DRIFT is non-fatal (count mismatch expected because
Mentor Web auto-CRUDs inflate counts per `[[odc_mcp_mentor_path_differs_from_studio]]`).

Coverage in `tests/test_orchestrator.py` (12 tests):
- T3.1 simulation: 5-recipe sequence, all succeed → 5 succeeded rows
- T3.1 halt: middle recipe compile error → phase halts at that target
- T3.1 mentor_start failure: error propagates to state row
- T3.2 resume: pre-marked succeeded rows skipped on re-run
- T3.4 verify: skipped without app_key / dispatched with app_key / drift
  detected / compile errors / expected-counts math / prompt persisted to
  disk / read-only (no publish call)
- Session credentials carried from poll to state row (required for
  publish_start binding)
- Failed rows do NOT trigger publish_start

---

## Tier 4 — Full rebuild dry run (~2-3 hours wall time)

### T4.1 — Core rebuild against fresh sandbox

**Setup**: Portal-create `HomeBankingCoreSandbox` (manual). Get the asset_key.

**Run**:
```bash
python scripts/build_banking.py --app core --run --app-key <key>
```

**Expected**:
- ~138 recipe calls (35 entities + 3 roles + 100 actions)
- 138 publish cycles (publish-per-recipe)
- ~2 hours wall time with 3-concurrent dispatch
- Resume-safe if interrupted

**Pass criteria**:
- All 138 recipes succeed
- Final `context_search` confirms 35 entities + 3 roles + 100 actions
- `app_info.revision` bumped by ~138
- Recipe 99 verify reports counts match

**Likely failures**:
- Mentor session-context wall on big entities (already validated HBCustomer's 21 attrs; LoanRequest has 30 — possible boundary case)
- Rate-limiting from OutSystems on 138 sequential publishes
- Network blips → orchestrator should retry once per recipe

**Time**: ~2-3 hours (mostly waiting on Mentor + publish)

### T4.2 — Portal + Backoffice rebuild

**Prereq**: T4.1 done. Cross-app Manage Dependencies (Studio gate) added
manually.

**Run**:
```bash
python scripts/build_banking.py --app portal --run --app-key <portal-key>
python scripts/build_banking.py --app backoffice --run --app-key <backoffice-key>
```

**Per app**: ~26 recipe calls (actions, themes, screens — when screen renderer exists).

Without screen renderer: just actions + theme will run. Screens stay missing.

**Pass criteria**: Same as T4.1 scaled to each app's count.

**Time**: ~30 min per app

### T4.3 — Structural equivalence diff against originals

**What**: For each rebuilt screen, diff its widget tree + screen action set +
data bindings against the original.

**Why structural, not pixel**: OS rendering is deterministic from a known
component palette. Two screens with the same widget hierarchy + same
properties + same theme will render to byte-identical HTML/CSS at runtime —
regardless of which internal widget IDs Mentor assigns to each node. Pixel
diffing is the wrong verification because it conflates real differences
(missing widget, wrong style) with non-differences (widget ID `b3-Container`
vs `b7-Container`).

**Diff procedure**:
1. Capture the rebuilt screen's widget tree via the same R8 process
   (`getScreen` + Mentor synthesis → `.tree.md`)
2. Diff it against the original capture (already in `_raw/`)
3. Walk both trees in parallel, comparing at each node:
   - Widget **type** (`Container`, `Text`, `Button`, `BlockInstance`, `If`, etc.)
   - Widget **Name** (where set by the author — these ARE intentional)
   - Block instance **SourceBlock** reference
   - Properties: `Text`, `Value`, `Style`, `CustomStyle`, `Source`,
     `Condition`, `Visible`, `Width`, `OnClick`, `IList Source`, `Variable`,
     `List`, `Labels`, `Values`
   - For BlockInstances: parameter bindings + placeholder filling
   - Child count + child ordering
4. **Ignore** (non-significant differences):
   - Mentor's auto-generated widget IDs (`b3-Container` etc.)
   - Studio canvas position metadata (`HorizontalPosition`, `VerticalPosition`)
   - OML XML node ordering within a same-parent set (Mentor may reorder)
   - Empty/null property defaults that one side omits and the other emits

**Pass criteria**: Structural diff returns zero significant differences per
the rules above. Authoring-level identity = runtime visual identity (per the
OS rendering contract).

**Tooling**: Python script using the same tree-parser written for R9
(`pipeline/banking_runner/tree_diff.py` — to be written).

**Time**: ~1 hour for the diff tool + ~5 min per screen comparison

**Status (2026-05-27)**: Diff TOOL complete + tested. The diff algorithm is
`tree_parser.diff_screens()` (built in T2.1, 8 tests). CLI wrapper is
`scripts/tree_diff.py` — supports `<expected> <actual>` pair mode and
`--rebuild-dir <dir>` batch mode (diffs every `_raw` capture against a
same-named re-capture). Self-diff → zero differences; cross-screen diff →
differences reported with path + kind + expected/actual. **Coverage gate**:
a capture below 0.9 parse coverage is reported UNVERIFIABLE (exit 1) rather
than producing a misleading diff against a half-parsed tree. Live use waits
on the actual rebuild (T4.1/T4.2) + a re-capture of the rebuilt screens.

**R8 capture-format non-determinism (discovered during this work)**: the
existing `_raw/*.tree.md` captures came from free-form Mentor synthesis and
landed in 3 incompatible dialects (A/B/C — see
`data/MCP_RECIPES/R8_CAPTURE_PROMPT.md` + memory
[[odc_mcp_r8_capture_dialect_drift]]). The parser now handles A + B cleanly
(8 of 10 captures, coverage ≥ 0.96). Two Dialect-C captures
(`portal-personalloan` 0.04, `backoffice-personalloanofferletter` 0.70) are
narrative-format and need re-capture with the strict prompt before they can
feed the rebuild. `tree_parser.parse_coverage()` + the two guard tests
(`test_clean_captures_high_coverage`, `test_dialect_c_captures_documented_low`)
lock this in so the silent under-parse bug can't recur.

### Bridge: render all screens to MCP-ready prompts

`scripts/render_all_screens.py` walks `_raw/*.tree.md`, runs each clean
capture through the dechromed renderer (T2.2) + chrome-wrap renderer (T2.5),
and writes per-screen `.dechromed.prompt.txt` + `.chrome_wrap.prompt.txt` to
`_rendered/`. Coverage-gated (skips sub-0.9 captures with a re-capture
pointer). Current run: **8 dechromed + 8 chrome-wrap prompts, 141 chrome
sites**; 2 Dialect-C screens skipped. These prompt files are what the
orchestrator dispatches in T4.1/T4.2.

---

## Pre-flight checklist before T1

- [ ] State DB clean (`rm data/runner_state.db` if doing fresh test)
- [ ] mcp-remote installed (`npx -y mcp-remote --version`)
- [ ] OutSystems MCP server reachable (`claude mcp list` shows ✓)
- [ ] TestRunnerSandbox still at revision 5 + has ChartDataOption + HBBranch + HBCustomer
- [ ] Latest renderer code (manifest.py, recipe.py) loads without import errors
- [ ] pytest suite green (`pytest tests/test_banking_runner_smoke.py`)

## Pre-flight checklist before T4

- [ ] All T1, T2, T3 tests pass
- [ ] PLAN.md reviewed for known constraints
- [ ] Fresh sandbox apps Portal-created (Core + Portal + Backoffice; Mobile + 5 agents deferred)
- [ ] Studio open for each — first-publish warmup done
- [ ] `~/.mcp-auth/` populated (mcp-remote previously authenticated)

## Tier-level time budget

| Tier | Wall time | Mostly |
|---|---|---|
| Tier 1 | ~30 min | Mentor calls |
| Tier 2 | 6-8 hours | Recipe authoring + screen parser |
| Tier 3 | ~4 hours | Orchestration tests |
| Tier 4 | ~3 hours | Full rebuild + visual diff |
| **Total** | **~14 hours** | |

## Out-of-scope for testing

- **Mobile screens** — backend `MobileUI 1.2.1.0` plugin missing per R8
  finding. No path to test until OutSystems restores the plugin.
- **LoanRequest BPM workflow** — user excluded from rebuild scope.

## What "identical" means here

OS apps render deterministically from a known component library. If the
rebuilt app has the same widget tree + properties + theme + entity
schemas as the original, **it will render and behave identically at
runtime**. The success criterion is **structural equivalence** — not OML
byte-equivalence (Mentor assigns its own internal widget IDs, doesn't matter)
and not pixel diffing (a brittle proxy for the real thing).

Structural equivalence = the things the author actually controls match:
widget types, named widgets, block-instance references, property values,
expression strings, screen-action wiring, data-binding sources. Mentor's
internal bookkeeping IDs and Studio canvas position metadata are not part of
the contract.

## Failure escalation

If a tier fails persistently after 2 retries:
1. Document the verbatim error in `_raw/test-failures-<phase>.md`
2. Identify whether it's: my code bug / recipe bug / OutSystems platform issue
3. If platform: file ticket with OutSystems support, mark as blocked
4. If recipe: fix recipe template, re-test
5. If code: fix Python, rerun test suite, re-test
