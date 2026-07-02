# Banking Rebuild — Multi-Session Plan

**Goal** (locked-in 2026-05-27): Recreate the Home Banking suite — Core +
Portal + Backoffice + Mobile + 5 AI Agents — with **structurally identical
UI/UX**. The LoanRequest BPM workflow is the ONLY out-of-scope app.

## Methodology — dechromed → chromed phasing

The recipe library is a **defined methodology**, not a script collection.
Build in deterministic phase order (see `data/MCP_RECIPES/README.md`):

1. **STRUCTURE**: entities, statics, roles, dechromed screens (standard OS
   UI widgets only, no custom blocks), default screen
2. **LOGIC**: server/service/client actions wired against the entities
3. **CHROME**: custom blocks, theme, chrome-wrap (replace bare widget shells
   with custom-block instances)
4. **VERIFY**: read-only structural diff vs original captures

"Identical UI/UX" = author-controlled state matches: widget types + names +
properties + block-instance bindings + screen-action wiring + theme content.
NOT: Mentor's internal widget IDs, OML XML node ordering, Studio canvas
position metadata. OS rendering is deterministic from the author surface, so
same author surface = same runtime output.

## Completion Plan (authoritative, 2026-05-28)

Supersedes the per-phase status notes below (kept as historical detail). Open
work in strict dependency order. Phase 2 is the gate: do NOT start Phase 4
until the renderers are proven live.

### Scope decision (decide first)
**Mobile is descoped for v1.** Tenant is missing the `MobileUI 1.2.1.0` plugin;
~27 Mobile screens are uncapturable via MCP. Achievable suite = **Core + Portal
+ Backoffice + 5 AI agents** (LoanRequest BPM workflow also out of scope).
Revisit only if OutSystems restores the plugin. This drops "all pieces" to 5/6
apps — accept and proceed, or escalate the plugin restore before R12.

---

### Phase 1 — Close screen capture (task #57)
Re-capture the 2 Dialect-C screens so all in-scope screens parse cleanly.
- For `portal-personalloan` and `backoffice-personalloanofferletter`:
  `mentor_start` against the source app (HomeBankingPortal `fa7ab595…` /
  HomeBankingBackoffice `555cac1f…`) using the strict
  `data/MCP_RECIPES/R8_CAPTURE_PROMPT.md`. Write stdout → overwrite the
  `_raw/*.tree.md`.
- Verify `parse_coverage(text)["coverage"] >= 0.9`; move both from
  `DIALECT_C_CAPTURES` → `CLEAN_CAPTURES` in `tests/test_tree_parser.py`.
- Re-run `python scripts/render_all_screens.py` → expect 10/10 dechromed +
  chrome-wrap prompts.
- **Deliverable**: all in-scope screens rendered. **Acceptance**:
  `test_clean_captures_high_coverage` green for all; `_rendered/` complete.
- **Cost**: ~2 billable Mentor calls, ~20 min.

### Phase 2 — Live-validate the renderers (task #67) ← CRITICAL GATE
The R9 renderers emit Model-API C# inferred from memory; never dispatched.
Prove them on ONE screen before trusting the full run.
- Target: `ManageSettings` (smallest; needs `DataSettings` + `Region` entities).
- Steps:
  1. On a sandbox (reuse TestRunnerSandbox `6d7a3257…` or a fresh
     HomeBankingBackofficeSandbox), create prereq entities `DataSettings` +
     `Region` via Recipe 01/02; publish.
  2. Dispatch `_rendered/backoffice-managesettings.dechromed.prompt.txt` via
     `mentor_start` → poll → `publish_start`. Triage `compilationErrors`.
  3. Fix `screen_renderer.py` emitters for each bad Model-API call
     (`CreateScreenAggregate`, `CreateContainer/Text/Button`,
     `CreateScreenAction`, `SetValue`, data-type resolvers). Re-render,
     re-dispatch. **Budget 2–4 iterations.** Record each API correction as a
     memory entry (mirror the entity-recipe fixes).
  4. Dispatch Recipe 22 for the 4 custom blocks (Menu, Header, AlignCenter,
     HBIcon) → fix `block_renderer.py` (`CreateBlock`, `CreateInputParameter`,
     `StyleSheet.SetText`).
  5. Dispatch Recipe 23 chrome-wrap → fix `chrome_wrap.py`
     (`CreateBlockInstance`, `Parameters` binding, `RemoveWidget`).
  6. Re-capture the rebuilt ManageSettings (Phase-1 strict prompt) →
     `python scripts/tree_diff.py _raw/backoffice-managesettings.tree.md
     <rebuilt>.tree.md` → drive to **zero significant diffs**.
- **Deliverable**: 1 screen rebuilt + structurally verified; 3 renderers
  hardened against the real Model API.
- **Acceptance**: emitted C# compiles clean; `tree_diff` zero significant
  diffs. **Risk: HIGH** — this is where the unknowns live. If renderers need
  heavy rework, STOP and reassess R12 cost before proceeding.
- **Cost**: ~15–30 Mentor calls (iteration), 2–4 h.

### Phase 3 — AI Agent recipes (task #59) — parallelizable with Phase 2
Author offline, then validate ONE agent live.
- Write recipes `17_agent_app_create` (Portal-create gate +
  `[[odc_mcp_agent_app_authoring_wall]]`), `18_agent_memory_entity`,
  `19_agent_system_prompt` (3 variant patterns), `20_agent_tool_wiring`
  (`CreateActionHandler` + `IsFilledByAI`), `21_agent_multitenancy`
  (`AgentsConsumerApp Identifier`).
- Write 5 per-agent manifests (CallIntake, Enrichment, Communicator,
  Underwriter, Offer): name, system prompt, memory entity, tool list,
  consumer app key.
- Validate CallIntakeAgent live on a fresh agent sandbox.
- **Deliverable**: 5 templates + 5 manifests + 1 validated agent.
- **Acceptance**: agent has memory entity + system prompt + ≥1 tool, confirmed
  via `context_agents`/`context_search`. **Cost**: ~3–4 h + ~10 Mentor calls.

### Phase 4 — Full orchestrated rebuild (task #61) — blocked by #67 + #59
- **User gates (~30 min)**: Portal-create 8 sandbox apps (Core, Portal,
  Backoffice, 5 agents); Studio-warmup each; Manage-Dependencies for consumers.
- Run `python scripts/build_banking.py --app <name> --run --app-key <key>` in
  dependency order: Core → 5 agents → Portal + Backoffice. Orchestrator does
  publish-per-recipe + state-DB resume + Recipe 99 verify.
- **Deliverable**: 8 apps with entities + roles + action-stubs + screens +
  blocks + theme. **Acceptance**: per-app `context_search` counts match
  manifests; Recipe 99 OK or explained DRIFT. **Cost**: ~95 min Mentor +
  gate time; resume-safe.

### Phase 5 — Real action bodies (task #62) — after/interleaved with Phase 4
- For ~95 stub actions: Mentor-probe flow → Recipe 06 form → re-dispatch.
  Prioritize the demo critical path (login, loan wizard, underwriter sidebar).
- **Acceptance**: Playwright smoke of main flows passes. **Cost**: ~4 h.

### Phase 6 — Final structural verification (task #66)
- Re-capture every rebuilt screen → `tree_diff.py --rebuild-dir <dir>` vs
  `_raw/` originals → zero significant diffs across all in-scope screens.
- Manual login + click-through smoke per app.
- **Acceptance**: structural identity proven; smoke flows green.

### Critical path & checkpoints
`#57 → #67 → (#59 ∥) → #61 → #62 → #66`. Two hard checkpoints:
- **After #67**: renderers proven (or reworked) — decision point for R12 go/no-go.
- **After #61**: app shells exist — decision point for how deep #62 goes.

---

## Current state (after R7)

✅ banking_runner Python orchestrator scaffolded (Phases A + B)
✅ Recipes 01–16 + 99 authored
✅ Manifest YAML loaders working
✅ Recipe 02 (static entity) validated E2E on TestRunnerSandbox: published, persisted, verified via context_search
✅ Recipe 01 (server entity) validated E2E for HBBranch + HBCustomer: AutoNumber.Yes fix, Email/PhoneNumber type fix, FK resolution working
✅ Recipe 03 (role) validated E2E
✅ publish-per-recipe architecture wired in orchestrator

## R8 partial completion

**Captured (Mentor synthesis path, `.tree.md` format)**:
- Portal: Dashboard (R5), Transfer, PersonalLoan, Requests, Confirmation
- Backoffice: Dashboard, RequestDetail, Customers, CustomerDetail, ManageSettings, PersonalLoanOfferLetter

That's 11 of 16 originally-planned in-scope screens. Each `.tree.md` is 3-37 KB of clean indented widget tree from Mentor's synthesis.

**Blocked on backend infrastructure**:
- HomeBankingMobile (29 screens): Mentor MCP returns `agent serve error: Unable to find the following required model plugins: MobileUI (1.2.1.0): Unable to locate plugin binaries` for every Mobile screen capture. Not a refusal — backend plugin loader failure. Cannot proceed via MCP until OutSystems restores the MobileUI plugin in this tenant.

**Scope decision pending**: with Mobile blocked by backend, the achievable rebuild is Core + Portal + Backoffice + 5 AI agents = **5 of 6 in-scope apps**. Loss of Mobile (~27 screens) reduces "all pieces" coverage by ~30%.

## Open phases

### R8 — Full screen capture (UI/UX foundation)

Problem: MCP wrapper truncates `tool_end.result` at ~8 KB. `getScreen`
output for a Mentor-Web Dashboard is ~280 KB. Need to extract the full C#
reconstruction source per screen.

**Approach**: Mentor session chunking
1. Dispatch ONE mentor_start per screen with this code:
   ```csharp
   eSpace => {
       var raw = /* call getScreen-equivalent, get the full C# source */;
       // store raw in module-level so subsequent applyModelApiCode in same
       // session can read it
       Console.WriteLine($"CAPTURED:{raw.Length}");
   }
   ```
2. Then chain applyModelApiCode calls in the same session that print chunks:
   ```csharp
   eSpace => {
       var chunk = raw.Substring(offset, Math.Min(7500, raw.Length - offset));
       Console.WriteLine($"CHUNK[{idx}]:{chunk}");
   }
   ```
3. Python-side: reassemble chunks per screen.

**Caveat**: Mentor sessions don't persist state across applyModelApiCode
calls by default (each call is independent). We may need to capture the
ENTIRE source in one call's stdout, even if truncated. If truncated, fall
back to multiple `mentor_start` sessions, each grabbing a different
substring range using `getScreen` then printing only the slice.

Target screens (16):
- Portal: Dashboard, Transfer, PersonalLoan, Requests, Confirmation, WakeUp + Login (auto) + InvalidPermissions (auto)
- Backoffice: Dashboard, RequestDetail, Customers, CustomerDetail, ManageSettings, PersonalLoanOfferLetter + Login + InvalidPermissions
- Mobile: TBD — manifest doesn't list Mobile screens yet

Out-of-scope: LoanRequest screens

**Deliverable**: `data/MCP_RECIPES/apps/home_banking/_raw/*.full.cs` per screen,
~280 KB each, complete reconstruction-style C# source.

### R9 — Screen recipe authoring (STRUCTURE phase output)

Take each captured `.tree.md` and produce TWO outputs:

**R9a — Dechromed renderer**: parse the tree, strip BlockInstance references
to custom blocks (Menu, Header, HBIcon, AlignCenter, etc.), replace with
standard OS UI shells (default Layout, plain Container, default text icon).
Result: a working screen with all data bindings + logic + correct layout
hierarchy, but rendered with the OS UI default look. This is the STRUCTURE
phase output — Recipes 07/08/09/12/13/14/15 emit this.

**R9b — Chrome wrap manifest**: a parallel file noting, per screen, which
custom block replacements need to happen + their placeholder fillings + their
parameter bindings. This drives the CHROME phase's Recipe 23.

Why this split: a dechromed screen can be published + functionally tested
BEFORE its custom blocks exist. The chrome wrap recipe then "promotes" the
screen to its final visual state once blocks + theme are in place.

Build infrastructure:
- `pipeline/banking_runner/tree_parser.py` — reads `.tree.md` → AST (also
  powers the verification structural-diff)
- `render_screen_dechromed(manifest_entry, ast)` in recipe.py
- `render_chrome_wrap(manifest_entry, ast)` in recipe.py
- `apps/home_banking/screens.dechromed.yaml` — auto-generated from captures
- `apps/home_banking/screens.chrome.yaml` — auto-generated from captures

### R10 — AI Agent recipes

Author new recipes:
- `17_agent_app_create.md` — Portal-only gate (`[[odc_mcp_no_app_creation]]`) + scaffolding via Mentor MCP. Per `[[odc_mcp_agent_app_authoring_wall]]` MCP can author agent internals after the app exists.
- `18_agent_memory_entity.md` — uniform Memory entity (UUID 984d4abd in template-clones per `[[odc_agent_architectures]]`)
- `19_agent_system_prompt.md` — handle 3 variant patterns (inline literal / composed-from-struct / param-description-embedded)
- `20_agent_tool_wiring.md` — Server Action + `CreateActionHandler` + `IsFilledByAI` markers per `[[odc_mcp_agent_app_authoring_wall]]`
- `21_agent_multitenancy.md` — `AgentsConsumerApp Identifier` wiring (the universal multi-tenancy key)

Per-agent manifests for 5 banking agents:
- CallIntakeAgent
- EnrichmentAgent
- CommunicatorAgent
- UnderwriterAgent
- OfferAgent

Each needs: name, system prompt, memory entity, tool list, consumer app key.

### R11 — Theme + DefaultScreen + Recipe 99 renderers — ✅ DONE

Three small Python renderers in `recipe.py`:
- `render_theme(theme_name, css_path) -> str` — CHROME phase, slot CSS into Recipe 10
- `render_default_screen(screen_name, flow_name) -> str` — STRUCTURE phase
- `render_verify_probe(expected_counts) -> str` — VERIFY phase

### R11b — Custom Block authoring + Chrome Wrap (NEW)

Two new recipes for the CHROME phase:

**Recipe 22 — Custom Block** (`22_block_create.md`): authors a reusable
block (Menu, Header, HBIcon, AlignCenter, etc.). Capture phase: probe each
custom block referenced by `_raw/*.tree.md` via Mentor's `getWebBlock` tool
per `[[odc_ui_mcp_surface]]`. Author phase: Python renderer
`render_block_from_capture` emits Mentor prompt that creates the block via
`IMobileFlow.CreateBlock(name)` per `[[odc_mcp_block_creation_works]]`.

**Recipe 23 — Chrome Wrap** (`23_chrome_wrap.md`): takes a published
dechromed screen + the chrome wrap manifest from R9b + the now-published
custom blocks, replaces placeholder/shell widgets with BlockInstance
references, sets block-instance parameter bindings + placeholder fillings.
Re-publishes the screen.

Recipe 23 is the BRIDGE between dechromed STRUCTURE state and final visual
state. Without it, screens stay generic-looking even after blocks + theme
exist.

### R12 — Full orchestrated rebuild

Portal-create 9 new apps:
- HomeBankingCoreSandbox
- HomeBankingPortalSandbox
- HomeBankingBackofficeSandbox
- HomeBankingMobileSandbox
- CallIntakeAgentSandbox
- EnrichmentAgentSandbox
- CommunicatorAgentSandbox
- UnderwriterAgentSandbox
- OfferAgentSandbox

Run banking_runner against each in dependency order:
1. AppsCommonCore (if not already present) — Employee entity
2. AgentsCommonResources (if not already present) — AgentsConsumerApp static
3. HomeBankingCoreSandbox (entities + actions + roles)
4. 5 agent apps (in parallel, each gets data refs to Core)
5. HomeBankingPortalSandbox + HomeBankingBackofficeSandbox + HomeBankingMobileSandbox (each consumes Core + agents via Manage Dependencies)

Manual gates: ~9 Portal-creates + ~9 Studio warmups + ~9 Manage Dependencies = ~30 min user labor.

Wall time: with 3-concurrent dispatch + publish-per-recipe (~60s each):
- ~138 Core recipes × 60s ÷ 3 = ~46 min
- ~52 Portal/Backoffice action stubs × 60s ÷ 3 = ~17 min
- ~16 screens × 60s = ~16 min
- 3 themes × 60s = ~3 min
- ~25 agent recipes × 60s ÷ 3 = ~8 min
- Per-phase verification = ~5 min
- **Total: ~95 min of pure Mentor calls + user gate time**

### R13 — Action body capture (95 remaining actions)

For each of the 95 Core/Portal/Backoffice actions we don't have captured bodies for:
1. Mentor probe to dump the action's flow nodes
2. Author Recipe 06 (workflow) form with the captured flow
3. Re-dispatch via banking_runner

This is the "make actions actually work, not just stubs" phase.

Wall time: ~95 actions × 90s capture + 90s recipe build + 60s dispatch = ~4 hours.

### R14 — Final verification

Per app, run Recipe 99 probe + manual smoke (login + click through main flows).

## What "complete" looks like

| Criterion | Status check |
|---|---|
| Core has all 35 entities + 100 actions + 3 roles | context_search count match |
| Portal has all 8 user screens + role + 26 actions | context_search count match |
| Backoffice has all 8 user screens + role + 26 actions | context_search count match |
| Mobile has all screens (TBD count) + role | context_search count match |
| 5 agent apps each have memory entity + system prompt + tools | per-agent context_search |
| Portal Dashboard renders identically | manual visual diff |
| Login flow works on Portal | Playwright smoke test |
| Loan application wizard works on Portal | Playwright smoke test |
| Underwriter sidebar actions work on Backoffice | Playwright smoke test |

## Session-survival notes

If a session ends mid-phase, resume by:
1. Reading this PLAN.md
2. Checking `data/runner_state.db` for last completed recipe per app
3. Re-running `python scripts/build_banking.py --app <name> --run --app-key <key>` (idempotent — skips already-succeeded recipes)

Cross-references that must NOT be lost:
- TestRunnerSandbox asset_key: `6d7a3257-4a75-4341-92ed-c9f7efc40584`
- TestRunnerSandbox currently has: HBBranch + HBCustomer + ChartDataOption (already validated via Recipes 01/02)
- Env keys: Dev = `<your-dev-env-key>`
- HomeBankingCore source asset_key (original): `695efc5b-8f39-4a53-8d71-35c59097d245`
- HomeBankingPortal source: `fa7ab595-f8cd-4140-8826-2acc484727b6`
- HomeBankingBackoffice source: `555cac1f-af92-4461-9750-b635d6570495`
