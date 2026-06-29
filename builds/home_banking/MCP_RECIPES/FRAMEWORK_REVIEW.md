# Framework Review — 2026-06-09

Honest examination of what we've built, what's missing, what's broken. Goal: identify what to adjust before the next dispatch attempt.

The framework should answer: **"Given a source OutSystems app + the MCP tools, produce a working clone."** Banking is the test case; generality is the deliverable.

---

## Inventory

| Layer | Files | Status |
|---|---|---|
| Recipes (C# templates) | 29 markdown files | Per-element, no composite recipes |
| Python renderer modules | 12 (.py) | Banking-specific in places, generic in others |
| App manifests | 5 YAML files (entities/screens/actions/roles/library_keys) | Element-scattered, not app-scoped |
| Widget tree captures | 44 (.tree.md) | Quality varies; some truncated |
| Bug reports | 42 markdown files | Comprehensive; needs filing |
| Doctrine docs | WARM_SESSION_DISPATCH, GAPS, SCOPE | Scattered |

---

## Grammar — what manifests describe today

### What works
- Entity declarations (server + static + identifier + FKs)
- Action declarations (name, inputs, outputs, public/private)
- Role declarations
- Screen declarations (name, uiflow, inputs, roles)
- Theme declarations (CSS file path)
- Library element keys (UUID cache for cross-app references)
- Block whitelist (per-app block name → render)

### What's MISSING from the grammar

| Gap | Why critical | Workaround today |
|---|---|---|
| **Screen aggregates** (data fetching per screen) | Without these, every screen renders empty containers | Manual / not done |
| **Action bodies** (real logic, not stubs) | Apps can't function — buttons fire empty actions | Manual / not done |
| **Navigation routing** (screen-to-screen) | Apps can't be navigated | Hardcoded in screen widget tree |
| **Anonymous access flag** per screen | Mentor auto-applies role gate; we fix after | Manual Mentor turn after publish |
| **Reference manifest** (what producers + element keys an app needs) | We hardcoded OS UI; HBCore + others not in YAML | Goal-framed Mentor prompts |
| **Default screen target** per app | Hardcoded in build_banking.py per-app | Per-app override constant |
| **App shell** (theme + layout + menu + default screen as composite) | These must wire together at app birth | Dispatched individually |
| **Seed data / sample records** | Apps render empty without it | Skipped |

### What the grammar should look like (proposal)

One `<app>.app.yaml` per app being cloned, indexing into sub-manifests:

```yaml
# home_banking_portal.app.yaml
app:
  name: HomeBankingPortal
  source_asset_key: fa7ab595-...
  kind: CrossDevice

references:
  - producer: HomeBankingCore
    producer_key: 695efc5b-...
    elements_to_import: [entities, service_actions]  # or explicit list
  - producer: OutSystemsUI
    producer_key: 8be17f2a-...
    elements_to_import: [Tag, Counter, Card, Section, Columns2, Columns3, ...]
  - producer: OutSystemsCharts
    producer_key: <UUID>
    elements_to_import: [Column, Line, Pie]

theme:
  name: HomeBankingPortal
  css_capture: theme-portal.css
  layout_block: LayoutTopMenu
  grid: Fluid
  max_width: 1280

screens:
  - name: Dashboard
    uiflow: MainFlow
    capture: portal-dashboard.tree.md
    aggregates:                  # NEW
      - name: GetAccounts
        source: HBAccount
        order_by: AccountName Ascending
    actions_referenced: [GetSettings, FormatCurrencyCustom]  # NEW — wires action calls
    is_default: true             # NEW — replaces per-app constant
    anonymous: false
  - name: Login
    uiflow: Common
    capture: portal-login.tree.md
    anonymous: true              # NEW — clears roles, sets AnonymousAccess
    roles: []

blocks:
  - name: HBIcon
    capture: HBIcon.block.tree.md
  - name: LayoutTopMenuLeftSide
    capture: LayoutTopMenuLeftSide.block.tree.md
    is_layout: true              # NEW — layout blocks render first, wrap screens

action_bodies:                   # NEW — capture-driven real logic
  - name: SubmitTransfer
    capture: SubmitTransfer.action.tree.md
    # Renderer reads the captured action body and emits the C# logic
```

Single source of truth per app. Other manifests can be derived from it.

---

## Recipes — what C# templates do today

### What works
- `01_entity_server`, `02_entity_static` — emit entities with Public=true (v2 verified)
- `03_role` — role creation
- `04_action_crud`, `05_action_sql_update`, `06_action_workflow`, `16_action_foreach_list` — action stubs (no real body)
- `10_theme_replace` — CSS slot
- `11_default_screen` — DefaultScreen setter
- `22_block_create` — block from widget tree
- `23_chrome_wrap` — wrap dechromed containers with BlockInstance widgets
- `99_verify_*` — probes

### What's MISSING in recipes

| Gap | Impact |
|---|---|
| **00_app_shell.md** — composite: theme + layout + default screen + first screen, all wired | Without it, dispatched fragments don't form a working app |
| **05a_action_body.md** — author action bodies from capture (not stubs) | Buttons fire but do nothing |
| **08_screen_aggregate.md** — author screen aggregate with WHERE/ORDER BY | Screens render empty |
| **09_screen_anonymous.md** — anonymous-friendly screen (clears auto-role) | Auth wall after every publish |
| **24_navigation.md** — wire screen-to-screen routing | Can't navigate the app |
| **25_seed_data.md** — populate entities with realistic test data | App is empty even when working |

### Recipe-level issues

- **No recipe composition** — each runs in isolation; you can't say "build this screen WITH its aggregate AND its action body" as one dispatch
- **Reflection-heavy code** — chrome_wrap uses reflection that fails OML serialization (V14)
- **Recipes hardcode `Public = true`** even for intra-app helpers (architectural impurity accepted, but should be manifest-driven)

---

## Tooling — what Python does today

### What works
- `recipe.py` — generic per-element renderer (entities, actions, theme, default screen)
- `screen_renderer.py` — dechromed screen from widget tree
- `block_renderer.py` — block from widget tree
- `chrome_wrap.py` — chrome wrap recipe with import prerequisites (v9/v10)
- `library_keys.py` — library_keys YAML loader + import emit
- `tree_parser.py` — captures parser
- `batch_recipes.py` — merge multiple recipes into one mentor turn

### What's HARDCODED to banking

- `build_banking.py::APP_BLOCK_WHITELIST` — per-app block names
- `build_banking.py::DEFAULT_SCREEN_PER_APP` — per-app default screen target
- `SCREEN_CAPTURES_DIR` — points to `apps/home_banking/_raw/`
- Phase ordering — Banking-specific
- Logical app slot names (`portal`, `backoffice`, `core`)

### What the tooling is MISSING

- **No generic "render any app" entrypoint** — only `--app portal|backoffice|core`
- **No capture playbook tool** — manual Mentor probes only
- **No verification harness between phases** — Console.WriteLine trust
- **No reference resolver** — UUIDs are hand-pasted into YAML
- **No "dispatch in foreground with verification" driver** — relies on subagents which drift
- **No idempotency check before dispatch** — re-running a batch silently re-creates entities (cascade failures)

---

## Patterns / doctrine — what's documented today

### Documented
- `WARM_SESSION_DISPATCH.md` — session resume to skip get_app_summary
- `library_keys` cache-warm + verify (B2 workaround)
- v2 ServiceAction + entity.Public requirement
- v9 IMPORT PREREQUISITES emit pattern
- 14 bug reports + 30+ memory entries

### Discovered today but NOT yet documented
- **`mentor_cancel` immediately after `tool_end`** skips 60-180s narrative synthesis (biggest cost win after warm-session)
- **Per-block-per-turn capture** avoids stdout truncation
- **`IMobileWidgetSignature`** is the correct interface name (NOT `IMobileWidget`)
- **`.DisplayName`** reflection on ParsedExpression for clean source-text values
- **Sandbox imports allowlist** narrower than thought (System.Collections.Generic BLOCKED)

### Anti-patterns observed but NOT enforced anywhere

- Subagents skipping phases for "budget" → produces broken builds with success reports
- Trusting Mentor's stdout "Status: OK" without context_search verification → false positives
- Per-screen role gate fix after publish → should be in renderer
- Mentor improvisation when given goal-framed prompts at scale → loses determinism

---

## Where the framework BREAKS

Concrete failure modes from this session:

1. **Subagent autonomy drift** — given "dispatch these 13 batches," subagent dispatched 3 + improvised the rest. **Fix**: foreground driver, no autonomous subagent for build dispatches.

2. **State desync between Mentor stdout and OML** — Mentor says wrapped=3/3, OML rejects at publish. **Fix**: verify state via context_search after every batch BEFORE proceeding.

3. **Auto-applied role gates** — Mentor adds role to every new screen, we fix after. **Fix**: bake role-clear + AnonymousAccess into screen recipe based on manifest's `anonymous: true` flag.

4. **Chrome wrap reflection vs typed setter** — V14 bug. **Fix**: v10 baked typed setter; needs validation on real dispatch.

5. **Captures incomplete** — Dashboard truncated, AccountCard truncated, source_block resolution returns null. **Fix**: capture playbook with per-block-per-turn + retry-on-null pattern.

6. **No app shell** — theme + layout + default screen never wired together. **Fix**: 00_app_shell composite recipe.

7. **No aggregates / action bodies / navigation** — screens render but don't function. **Fix**: 3 new recipes + 3 manifest grammar additions.

---

## Recommended adjustments (priority order)

### P0 — framework spine (~2-3 hours)

1. **Bake the role-clear + AnonymousAccess pattern into `screen_renderer.py`** — driven by manifest's `anonymous: true` flag. Eliminates the post-publish auth fix.

2. **Add `00_app_shell.md` composite recipe** — theme + layout + default screen + Common Login as a coherent first publish. Subsequent dispatches build INTO this shell.

3. **Add foreground dispatch driver** — replaces autonomous subagents. Drives batch-by-batch with verification between each. Per-batch failure stops the build with a clear failure mode.

4. **Add verification recipes** between phases — `context_screens` / `context_search` to confirm published state matches expected state. If not, halt + report.

### P1 — close the missing grammar (~3-4 hours)

5. **Aggregate authoring** — `08_screen_aggregate.md` + manifest `screen.aggregates:` block

6. **Action body authoring** — `05a_action_body.md` + per-action capture from source app + manifest `actions[].body_capture:` reference

7. **Navigation wiring** — `24_navigation.md` (screen OnClick → Screen.Goto)

### P2 — generalize beyond banking (~2-3 hours)

8. **Replace banking-hardcoded constants in `build_banking.py`** with manifest-driven defaults

9. **Capture playbook tool** — given a source app key, dump all captures into `_raw/` programmatically (using the patterns we discovered today)

10. **Rename `pipeline/banking_runner` → `pipeline/app_runner`** + generic `scripts/build_app.py --manifest <path>`

### P3 — doctrine

11. **Write FRAMEWORK.md** — the spine doc tying grammar + recipes + tooling + patterns together. Becomes the project's README.

12. **Refresh memory entries** — add the mentor_cancel-immediately pattern, IMobileWidgetSignature interface name, sandbox import allowlist narrowing, ParsedExpression.DisplayName.

13. **Document anti-patterns** as explicit rules in PROMPT_PREAMBLE.md — subagents see them, can't skip them.

---

## What I'd adjust BEFORE the next dispatch attempt

Minimum to make the next dispatch likely to succeed:

- P0 #1 (anonymous bake) — keeps us out of the auth wall hole we've fallen into 3 times
- P0 #3 (foreground driver) — eliminates subagent drift
- P0 #4 (verification recipes) — catches state desync before it cascades

Optional but high-leverage:

- P0 #2 (app shell) — gives the dispatch a coherent first phase

Total ~1-2 hours of focused renderer work. Then the dispatch has a real chance of producing a working clone.

---

## Open question for the user

The recipes + grammar are mostly there. The biggest gap is **discipline at dispatch time**. Should we:

**A.** Bake P0 #1, #3, #4 first (~90 min), THEN dispatch — disciplined path  
**B.** Acknowledge the framework + dispatch as-is foreground with discipline (no subagent) — accept some patches mid-build  
**C.** Take the framework as a deliverable AS-IS — write FRAMEWORK.md from what works, ship the bug reports, retire the banking goal as "test case showed walls and wins"  

The framework deliverable doesn't require Banking running to be valuable. Banking just stress-tested it.
