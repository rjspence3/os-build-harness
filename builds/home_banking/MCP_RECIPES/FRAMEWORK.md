# MCP Recipe Framework

A grammar + recipes + tooling for cloning OutSystems apps via the Mentor MCP. Validated on Home Banking Portal (in progress); designed to generalize.

## Mental model

```
[Source OutSystems app]
        │
        ▼
[CAPTURE] — Mentor probes pull entity / action / screen / block / theme trees
        │
        ▼
[MANIFEST] — YAML grammar describing the app's structure
        │
        ▼
[RECIPES] — C# templates per element type (entity, action, screen, block, theme, ...)
        │
        ▼
[RENDERER] — Python that fills recipes from manifest + captures, produces dispatchable prompts
        │
        ▼
[DISPATCH] — Foreground driver executes prompts via MCP (warm-session, verify between phases)
        │
        ▼
[CLONE] — Working OutSystems app on the tenant
```

## The four layers

### 1. Grammar — `data/MCP_RECIPES/apps/<app>/*.yaml`

Per-app manifest files describing structure:

| File | Describes |
|---|---|
| `entities.yaml` | Server entities + static entities + identifiers + FKs |
| `actions.yaml` | Service actions + server actions + inputs/outputs + body capture refs |
| `screens.yaml` | Screens + uiflow + inputs + roles + anonymous flag + aggregates + navigation |
| `roles.yaml` | App roles |
| `library_element_keys.yaml` | Producer + element UUIDs for `addReferenceToElements` |
| `SCOPE.md` | Discovery output — what's in the source app |
| `GAPS.md` | Known gaps + walls |

App-level wiring (theme, default screen, layout) lives in build_banking.py constants today; P2 migrates these to per-app `<app>.app.yaml`.

### 2. Recipes — `data/MCP_RECIPES/*.md`

C# template per element type. Each recipe is a self-contained Mentor prompt that authors one element via `applyModelApiCode`.

| Recipe | Element |
|---|---|
| 00_app_shell | Composite: theme + Login + DefaultScreen wired at app birth |
| 01_entity_server | Server entity with Public=true |
| 02_entity_static | Static entity with records |
| 03_role | App role |
| 04_action | Service action stub (Start→End) |
| 05_action_sql_update | SQL-update action body |
| 05a_action_body | Real action body from capture |
| 06_action_workflow | Workflow action |
| 08_screen_aggregate | Screen aggregate (data fetcher) |
| 09_screen_dashboard | Dashboard screen pattern |
| 10_theme | Theme CSS slot |
| 11_default_screen | Set eSpace.DefaultScreen |
| 16_action_foreach_list | ForEach loop action body |
| 18_agent_memory_entity | Agent memory entity |
| 20_agent_tool_wiring | Agent tool wiring |
| 22_block_create | Custom block from widget tree |
| 23_chrome_wrap | Replace dechromed Containers with BlockInstance widgets |
| 24_navigation | Wire screen-to-screen routing |
| 99_verify_phase | Inter-phase state verification |

Recipes use `{{TEMPLATE_VAR}}` substitution. Renderer fills them.

### 3. Renderer — `pipeline/banking_runner/*.py`

Python that:
- Loads recipe templates
- Loads manifests + captures
- Substitutes template vars
- Writes dispatchable `.prompt.txt` files
- Batches per phase via `scripts/batch_recipes.py`

Module map:

| Module | Role |
|---|---|
| `recipe.py` | Generic per-element renderer (entities, actions, theme, default screen) |
| `screen_renderer.py` | Dechromed screen authoring from widget tree |
| `block_renderer.py` | Block authoring from widget tree |
| `chrome_wrap.py` | Chrome wrap (BlockInstance replacement of placeholder Containers) |
| `library_keys.py` | Library element UUID lookup + IMPORT PREREQUISITES emit |
| `tree_parser.py` | Captured widget tree parser |
| `app_block_whitelist` (in build_banking.py) | Per-app block name enumeration |

Generalization (P2): rename `banking_runner` → `app_runner`, replace banking-hardcoded constants with manifest-driven defaults.

### 4. Dispatch — playbooks + MCP tools

| Doc | When |
|---|---|
| `WARM_SESSION_DISPATCH.md` | First — covers session resume + mentor_cancel-immediately patterns |
| `DISPATCH_PLAYBOOK.md` | During dispatch — step-by-step with halt conditions |
| `CAPTURE_PLAYBOOK.md` | Before dispatch — how to pull captures from any source app |
| `FRAMEWORK_REVIEW.md` | Periodic — health check on framework completeness |

Dispatch is FOREGROUND-DRIVEN in main context, NOT autonomous subagent. Subagents drift (verified 4× this session); foreground driver verifies state between every batch.

## Patterns (load-bearing for any build)

These are the three big Mentor cost workarounds discovered during Banking. ALL builds must use them:

### Pattern 1: Warm-session dispatch

`mentor_start` always runs `get_app_summary` on fresh sessions (3-5 min cost). Resume turns via `mentor_session_id` + `mentor_session_token` SKIP this. Use ONE fresh session per build; resume for every subsequent batch.

Source: bug B1, memory `[[odc_mcp_warm_session_dispatch]]`.

### Pattern 2: mentor_cancel-immediately-after-tool_end

After Mentor's `applyModelApiCode` returns `tool_end`, Mentor's narrative synthesis phase runs 60-180s before status flips terminal. Calling `mentor_cancel(runId)` immediately after tool_end SKIPS the synthesis phase while keeping the session alive.

Discovery: 2026-06-09 capture run 2. Biggest cost win after warm-session.

### Pattern 3: reference-add is a TWO-step contract (CORRECTED 2026-06-10)

`addReferenceToElements({elementKey, producerKey})` returning `null` is EXPECTED — it stages the import. The reference only materializes after a follow-up `applyModelApiCode` call runs `eSpace.AddDependency(Services.ModelServices.ParseGlobalKey("<globalKey>"))` per element. globalKey (NOT the elementKey UUID — different format) comes from `getWebBlock(objectName)`, which returns the verbatim AddDependency stub. Verify via `app_refs` after.

Source: MCP retest B2-rerun (2026-06-09), corrected. Baked into chrome_wrap v11 IMPORT PREREQUISITES (5-step). The earlier "cache-warm" hypothesis is superseded.

## Anti-patterns (NEVER do these)

1. **Subagent autonomy for build dispatch.** Subagents skip phases for "budget" or improvise when given goal-framed prompts. Use the foreground driver.

2. **Trust Mentor's "Status: OK" without verification.** Mentor reports wrapped=3/3 while OML fails to publish. Verify via `context_search` after every batch.

3. **Skip phases.** "We'll come back to that" leads to broken builds. Phase order is dependency order; skipping cascades.

4. **Goal-framed prompts at scale.** Goal-framing works for one-off probes. For builds, give Mentor verbatim recipe C# and instruct "execute exactly as written."

5. **Reflection on `SourceWebBlock`** for chrome wraps. Works in-session, fails OML serialization. Use typed `bi.SourceBlock = (IMobileBlock|IMobileBlockSignature)blockSig` (v10 bake).

6. **Setting `IServerAction.Public = true`**. Removed feature in ODC (`OS-BLD-40409`). Use `IServiceAction` for cross-app exposure.

7. **getScreen on complex screens.** Returns 277K-char dumps that crash Mentor synthesis. Use direct `applyModelApiCode` walk via `IMobileScreen` + `IMobileWidgetSignature`.

## Known walls (from this session, documented in bug_reports/)

14 confirmed MCP bugs + 3 behavior-changed memories. The framework's patterns work around these. See `data/bug_reports/INDEX.md`.

## How to validate the framework on a new app

1. **Source identification**: pick an existing OutSystems app. Capture its assetKey.
2. **Discovery**: run the SCOPE.md context_search enumeration. Determine total scope (screens, blocks, actions, refs).
3. **Capture**: follow `CAPTURE_PLAYBOOK.md` to pull `.tree.md` files. Per-block-per-turn pattern.
4. **Manifest**: derive `<app>.yaml` manifests from the captures.
5. **Render**: run `python scripts/build_banking.py --app <app>` (or the generalized `build_app.py` post-P2).
6. **Dispatch**: follow `DISPATCH_PLAYBOOK.md` phase by phase with verification.
7. **Verify runtime**: open the runtime URL — should match the source app's behavior.

If steps 1-6 succeed but step 7 reveals visual gaps, file them in `GAPS.md` — each becomes a framework feature, not a one-off fix.

## Validation state — Home Banking Portal (forcing function)

| Phase | Status |
|---|---|
| Source identification | ✅ Original at `fa7ab595…` |
| Discovery | ✅ SCOPE.md complete: 8 screens, 29 blocks, refs identified |
| Capture | ✅ 8/8 screens, 30/29 blocks (1 truncated AccountCard), theme CSS |
| Manifest | ✅ Banking-hardcoded; P2 generalizes |
| Render | ✅ 69 prompts, 55 batches |
| Dispatch | ⏳ Multiple attempts; subagent drift caused incomplete builds |
| Runtime verification | ⏳ Pending disciplined foreground dispatch |

## Related

- `[[FRAMEWORK_REVIEW]]` — gap analysis + adjustments
- `[[DISPATCH_PLAYBOOK]]` — execution rules
- `[[CAPTURE_PLAYBOOK]]` — capture rules
- `[[WARM_SESSION_DISPATCH]]` — session resume pattern
- `[[GAPS]]` — known visual + functional gaps in Banking clone
- `[[bug_reports/INDEX]]` — 14 confirmed MCP bugs + workarounds
