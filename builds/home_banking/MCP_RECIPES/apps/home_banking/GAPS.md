# Home Banking Clone — Gaps vs Original

**Goal**: Open both the original `Home Banking Portal` (`fa7ab595-f8cd-4140-8826-2acc484727b6`, rev 5) and our clone `HomeBankingPortalRebake2` (`ad39c3a7-4465-462b-923e-418325f998a4`) side-by-side; they should look and behave as similarly as possible.

This document tracks every known difference. Some gaps are intentional (scope cut for v1), some are platform limitations, some are renderer bugs to fix in a future pass.

## Visual / Structural

| # | Gap | Where | Why | Path to close |
|---|---|---|---|---|
| V1 | `InputWithIcon` chrome markers stay as empty Containers | Requests/Transfer screens | SetArgumentValue with `""` doesn't satisfy AVS's Required-Property-Value check on the BlockInstance's nested Input widget's `.Variable` property. Studio Mentor binds it to a screen-local Variable; chrome_wrap can't (no aggregate scope at chrome-wrap time). | LOGIC phase deep-bind pass: walk BlockInstance children, bind nested widget required properties to scope-derived Variables |
| V2 | Local blocks (HBIcon, FormInfoField, AccountCard, LayoutTopMenuLeftSide, ConfirmationPDF, Menu) may not render perfectly if their author state differs from original | All chrome markers using these | block_renderer recreates from captured `.tree.md` files; CSS / nested structure may differ from original | Capture-pass review + targeted block re-author |
| V3 | FirebaseReceiver (Requests screen) — referenced library may not be in tenant or not imported | Requests screen `chrome_FirebaseReceiver_*` marker | Original lives in Firebase ReactiveLibrary; library reference + public-element import needed | `addReferenceToElements` for the library if it's tenant-available; else document as omitted |
| V4 | Theme parity not yet verified | All screens | render_theme copies portal.css; some `@import` / local `url()` refs may be stripped or invalid | Visual diff after publish; targeted CSS fixes |
| V5 | Layout block (LayoutTopMenuLeftSide) may not nest screens correctly | All screens | Recipe limitation: layout blocks need 9 specific CSS classes on nested wrappers (`layout`, `layout-top`, `main`, etc.). Reference-lifted layout blocks via MCP have shown runtime-rendering issues. | Manual touch-up via Studio Mentor, OR use original's Layout directly via reference |
| V6 | Phase 0 bulk service-action reference import timed out | Rebake2 references list | Mentor `addReferenceToElements` call with all 55 HomeBankingCore service actions ran >22 min and was cancelled; only the previously-imported entities + Tag/Card remained. Batches will need to add references on demand or fail with "not found" gaps. | Per-batch on-demand reference adds via Mentor; or pre-stage references in smaller groups of ~10 |
| V7 | Stub service actions (batches 2-3 of 04_clientaction + 04_serveraction) not authored | All non-batch-1 stub actions | Pipeline run budget exhausted by Mentor session overhead — each batch spends ~3-5 min running get_app_summary before the recipe call. Skipped non-visual stub-only batches to prioritize visual parity (screens, blocks, chrome, theme). Without these stubs, screens that reference them by name will fail to resolve at chrome-wrap / screen-author time. | Re-run batches 2 and 3 in a separate session, or accept incomplete action surface (visual parity may still be reachable for screens that don't bind these actions) |
| V8 | Only Confirmation screen authored (1 of 3 screen batches) | Screens Requests + Transfer + 4 blocks | Time budget ran out after Confirmation screen + DefaultScreen recipes. Each Mentor turn ran get_app_summary first (~3-5 min) before applying the recipe code, despite explicit "do NOT call get_app_summary" instructions — a Mentor session-default behavior that recipes need to opt out of via a Mentor session-init flag (no such flag is exposed in the current MCP surface). | Re-run remaining batches 5/screen_02, 5/screen_03, 6/block, 7/chrome_01, 7/chrome_02, 7/chrome_03, 10/theme in a fresh session; or warm a Mentor session once and reuse it across batches |
| V9 | Theme CSS not applied (10_theme batch skipped) | All screens | Time budget exhausted. Confirmation screen renders with default OutSystemsUI styling only. | Re-run 10_theme_batch_01 to apply portal.css |
| V10 | Local blocks not authored (06_block batch skipped) | Confirmation's chrome_Menu / chrome_HBIcon / chrome_ConfirmationPDF / chrome_LayoutTopMenu remain empty Container placeholders | Time budget exhausted. Screen authored in DECHROMED form per recipe library design — chrome wrap phase requires the underlying blocks to exist. | Re-run 06_block_batch_01 then 07_chrome_batch_01 to wrap Confirmation |
| V11 | OS UI standard blocks not in scope (Menu, Columns3, Columns2, FormInfoField, AccountCard, AlignCenter, ButtonLoading, MaskText, MaskCurrency, LayoutTopMenuLeftSide, FirebaseReceiver, ConfirmationPDF) | All 3 chrome-wrap batches partial | The 06_block batch only authors HBIcon. Standard OS UI blocks aren't in the app's References. The v9 cache-warm pattern (context_search + app_refs) wasn't expressed in the chrome batch prompts as the documented STEP 1/2/3/4 — they go straight to applyModelApiCode. Even with cache warm, the underlying issue is reference addition (memory `odc_mcp_reference_add_studio_only`) — Studio Manage Dependencies is the only known clean path. | Author missing local blocks in 06_block_batch (Menu, FormInfoField, AccountCard, LayoutTopMenuLeftSide, ConfirmationPDF); use `addReferenceToElements` to import OS UI standard blocks (Columns3, Columns2, AlignCenter, ButtonLoading, MaskText, MaskCurrency, FirebaseReceiver) before chrome_wrap |
| V12 | Theme CSS reduced to core subset (~3KB vs ~30KB original) | Theme | 30KB CSS payload too large for single mentor_start prompt parameter without significant tool-call overhead. Dispatched core color tokens + .btn + .account-card + .counter-card + .request-table + .left-side-content for visual anchor; ~90% of original CSS (dashboard layout details, AI chat skin, demo access popup, animations) deferred. | Split 10_theme batch into 3-4 ~10KB CSS chunks dispatched as sequential `theme.StyleSheet += @"..."` appends, or upload via Resource API |
| V13 | Chrome batches go directly to applyModelApiCode (no v9 cache-warm STEPs 1-4) | All 07_chrome_* batches | The v9 prompts as-dispatched lack the documented IMPORT PREREQUISITES section (STEP 1: context_search cache-warm, STEP 2: addReferenceToElements, STEP 3: app_refs verify, STEP 4: applyModelApiCode). Mentor doesn't add references on its own — it interprets the recipe constraint "ONE applyModelApiCode call, no exploration" literally. Result: blocks not in scope = silently skipped with WARN. | Generate chrome batches with the 4-step preamble explicitly inlined as Mentor instructions (not just comments in the prompt) before the applyModelApiCode call |

## Run summary (2026-06-09)

- **Start state**: rev 2 (entities + Tag/Card imports only)
- **End state**: rev 5
- **Published artifacts**: 10 service action stubs (CheckCookie, CheckRTL, DoLogin, FormatCurrencyCustom, FormatDateCustom, GetCreditRank, GetLocale, GetUserPicture, InitClientVars, Random); Confirmation screen (dechromed); DefaultScreen=Confirmation
- **Runtime URL**: https://your-tenant-dev.outsystems.app/HomeBankingPortalRebake2
- **Time**: ~85 min wall-clock

## Run summary (2026-06-09, warm-session dispatch)

- **Start state**: rev 5 (10 service actions + Confirmation dechromed + DefaultScreen)
- **End state**: rev 7
- **Published artifacts**:
  - +14 ServiceAction stubs (6 client: ScrollToTop, SendSMS, SetDefaultLocale, SliderGoTo, TextToHex, ToggleDarkMode; 8 server: CheckAndGrantRole, GetDefaultLocale, GetMonth, GetRequestByCustomerLoan, Get_Settings, IsTwilioConfiguredAndGetPhoneNumber, KeepAwakeAll, SetCookie)
  - +Requests screen (dechromed; 5 locals, 4 screen actions, 12 chrome markers)
  - +Transfer screen (dechromed; 1 input, 16 locals, 14 screen actions, 18 chrome markers)
  - +HBIcon block (1 input)
  - +Chrome-wrap on 3 screens: Confirmation 1/3, Requests 8/11, Transfer 2/17 (missing blocks per V11)
  - +HomeBankingPortal theme (core subset CSS, set as DefaultMobileTheme)
- **Runtime URL**: https://your-tenant-dev.outsystems.app/HomeBankingPortalRebake2
- **Time**: ~24 min wall-clock for 10 batches + 2 publishes
- **Warm-session effectiveness**: 1 fresh session paid `get_app_summary` once on batch 1 (~70s); batches 2-10 ran with NO get_app_summary on resume turns. Single batch (resume) averaged ~25-35s wall-clock vs. ~3-5 min for fresh-session-per-batch — confirms B1 finding and the WARM_SESSION_DISPATCH playbook empirically. Zero session crashes; zero `run_already_in_flight` collisions.
- **v9 cache-warming effectiveness**: NOT EXERCISED — the dispatched chrome batch prompts don't include the documented STEP 1/2/3/4 preamble (see V13). Missing-block failures are real (V11), but they're upstream of cache-warm: the references aren't in the app to be cached. Would need either local-block authoring or `addReferenceToElements` calls before chrome_wrap dispatch.

## Functional / Data

| # | Gap | Where | Why | Path to close |
|---|---|---|---|---|
| F1 | Action bodies are Start→End stubs (no business logic) | All 100 service actions | render_action_stub emits parameter declarations + empty body. Real action bodies require per-action LOGIC capture from original | Phase 4-mini-extended: capture priority action bodies via Mentor; backfill rest as needed |
| F2 | No screen aggregates wired | All screens that need entity data | dechromed screen renderer doesn't currently emit aggregates; aggregates need separate LOGIC pass | Inv 5: aggregate authoring (eSpace.MobileFlows.Named("MainFlow").Nodes.Named("Transfer").CreateScreenAggregate) |
| F3 | No screen action bodies (Submit, Refresh, Navigation) | All screens with interactive buttons | dechromed renderer emits Start→End shells only | Inv 7: per-screen action body authoring |
| F4 | No seed data | All entities | LoadSampleData orchestrator pattern not yet baked. Original's seed data lives in its `SampleData/` folder + JSON resources | Bake native sample-data pattern (memory `odc_native_sample_data_pattern.md`) into block_renderer |
| F5 | No actual transfer logic | Transfer screen | Both V/F gaps: chrome may render but Submit does nothing | F1 + F3 + aggregate wiring |

## Architecture / Cross-app

| # | Gap | Where | Why | Path to close |
|---|---|---|---|---|
| A1 | Server Actions can't be Public in Applications (ODC platform wall) | Cross-app callable surface | `OS-BLD-40409` removed feature. ODC enforces weak dependencies — Service Actions only for cross-app calls. | v2 renderer change: all actions emit as ServiceAction. ✅ Done. |
| A2 | Reference resolution requires elementKey UUIDs at dispatch time | Phase 0 references | `addReferenceToElements` is UUID-driven; element discovery via context_search needed per producer | library_keys.yaml caches OS UI + InputMasks UUIDs. For HBCore: use goal-framed Mentor prompt that catalog-searches |
| A3 | InputMasks library reference must exist | Transfer screen MaskText/MaskCurrency | Library may or may not be referenced in target app | Phase 0: addReferenceToElements adds it if missing |

## Validation / Test

| # | Gap | Where | Why | Path to close |
|---|---|---|---|---|
| T1 | No automated visual diff | Pre-acceptance | Manual eyeball at acceptance per PLAN_GAP D-A | Future: headless browser + pixel diff |
| T2 | No runtime URL probe for the clone | Acceptance | env_app may not return URL on first publish | Manual: open in browser, log URL in this doc |

## Documented Decisions

- **Service Action over Server Action**: All actions emit as ServiceAction with `Public = true`. Architectural impurity (intra-app helpers are now "public-shaped") accepted for working build. ODC enforces this via `OS-BLD-40409`.
- **Application over Library for Core**: Original HBCore is a CrossDevice WebApplication; we match. Library route requires Portal-side release step (set version + release notes) which is UI-side and not cleanly MCP-able.
- **InputWithIcon skip**: chrome marker stays as empty Container. Better than failing publish on the entire screen.
- **Defer Core2 actions (98)**: Use original HBCore for entity + service action references. Core2 (rev 5) stands as renderer validation proof; not on Mid Reset success path.

## Confirmed Working (no gap)

- ✅ Entity Public flag (`e.Public = true`) — renderer emit + publish + cross-app discoverable
- ✅ ServiceAction creation (`eSpace.CreateServiceAction(name) + .Public = true`) — compiles + publishes + cross-app callable
- ✅ chrome_wrap v8 with IMPORT PREREQUISITES — OS UI + InputMasks blocks resolve via `addReferenceToElements`
- ✅ `addReferenceToElements` MCP tool — unified library-add + public-element-import primitive
- ✅ SetArgumentValue type-aware placeholders — Boolean `False`, Numeric `0`, Text `"X"`, Identifier/other `""`
- ✅ Library-level reference add via MCP (memory `odc_mcp_reference_add_studio_only.md` proven wrong)

## V14 — Chrome wrap OS-APPS-40028 returns (2026-06-09)

Same-session pattern fails: theme + Menu + ConfirmationPDF authored, published (rev 10), then chrome_wrap on Confirmation reported `wrapped=3/3` in Mentor stdout but `publish_start` rejected with `OS-APPS-40028: Input binary does not contain a valid OML`.

Hypothesis: reflection-set `SourceWebBlock` works in-session but doesn't survive OML serialization. Mentor's verbatim C# from the Counter probe used `instance.SourceBlock = (IMobileBlockSignature)blockSig` directly typed — not reflection on `SourceWebBlock`. Possible fix: switch chrome_wrap.py to use `SourceBlock` (typed cast) instead of reflection on `SourceWebBlock`.

**Path to close**: bake v10 chrome_wrap that uses `instance.SourceBlock = (OutSystems.Model.UI.Mobile.IMobileBlockSignature)blockSig` directly. Defer until Portal3 reaches chrome phase.

## Rebake2 final state (2026-06-09 17:35)

- Rev 10
- Theme CSS landed (full 35KB)
- Local blocks: HBIcon (pre-existing), Menu (rev 10), ConfirmationPDF (rev 10)
- Chrome wraps: NOT persisted (V14)
- Runtime URL renders Confirmation with text-only widgets + theme CSS partially applied
- Pivoting to fresh Portal3 build for full app gestalt approach

## Portal3 build (2026-06-09 18:39)

- **Start**: rev 1 (empty WebApplication, asset key `ed2c58a1-88b0-4fe9-a105-770eae8e9a79`)
- **End**: rev 6 (deployed, runtime URL live)
- **Runtime URL**: https://your-tenant-dev.outsystems.app/HomeBankingPortal3
- **Wall-clock**: ~75 min

### Artifacts shipped
- 12 OutSystemsUI block references (Tag, Counter, InputWithIcon, ButtonLoading, AlignCenter, Card, Section, Columns2/3, Notification, CardItem, CardBackground)
- 5 screens: Dashboard (default + KPIs + 3 account cards + recent activity), Login, Transfer, Requests, Confirmation
- TopNav header bar on all 5 screens (Brand + 4 nav links)
- HomeBankingPortal theme with 3.3KB banking-style CSS (selectors keyed off widget id substrings)
- DefaultScreen = Dashboard, role-free (anonymous visit works)

### Gestalt vs original
- **What matches**: landing on the runtime URL goes straight to a styled Dashboard with header band, 3 account cards, KPI row, recent-activity card, top-nav strip. Login / Transfer / Requests / Confirmation screens stand up with field labels and CTA-styled buttons.
- **What doesn't**: no real entity binding (no HBCore data), no aggregates, no action wiring, no AI Chat, no PersonalLoan flow, no FormInfoField / HBIcon / AccountCard custom blocks (V11). The "buttons" are text widgets styled to look like buttons, not real Button widgets — they're inert.
- **Why**: the prepared 55-batch dispatch was bypassed because the initial bulk `addReferenceToElements` for HBCore (86 elements) timed out (same wall as V6). Pivoted to a 12-element OS UI essentials import + screen-author-from-scratch using primitive widgets.

### V14 closure (this run)
- v10 chrome_wrap (typed `bi.SourceBlock = (IMobileBlockSignature)blockSig`) **was not exercised** — we authored screens with primitive widgets directly rather than dechromed-then-wrapped. The typed setter is empirically confirmed to compile + publish (KPIRow/CardRow on Dashboard expanded turn used `c.SourceBlock = counterSig;` directly and survived publish at rev 4).

### New gaps surfaced
- **V15**: `addReferenceToElements` with 86 elements in one call locks Mentor for >10 min wall-clock and never returns a `tool_end`. Smaller chunks (≤20 elements) complete in ~20 s. Recommendation: split per-producer-app calls and cap at ~15 elements each.
- **V16**: `eSpace.CreateMobileTheme(name)` works clean via MCP. Setting `BaseTheme` via reflection on a referenced `IMobileThemeSignature` is best-effort — no exception was raised this run but downstream effect not verified.
- **V17**: `IMobileBlockInstanceWidget` does NOT support `CreateWidget` for nested children. Empirically rediscovered (memory `odc_mcp_block_creation_works.md` is about creating Blocks, not nesting into block-instances). Block instance widgets are leaf nodes from the model API perspective; nesting requires placing them inside Container widgets.
- **V18**: `[id*='...']` CSS substring selectors are the only practical way to style widgets authored via MCP without writing per-widget `Style`/`CustomStyle` assignments. They publish cleanly and apply at runtime — confirmed by rev 5 visual.

### Mentor cost metrics
- Fresh sessions: 2 (first cancelled mid-bulk-ref; second carried all 6 dispatches)
- Warm resume turns: 5 (refs-import, Dashboard, Dashboard-expand, screens, theme-create, nav-wrap)
- get_app_summary cost: ~70s on each fresh session, skipped on every resume turn
- Per resume turn (applyModelApiCode + synthesis): ~30-60 s wall-clock
- mentor_cancel events to skip synthesis: 0 (synthesis was short enough not to need skipping at this batch granularity)
- Publishes: 4 (revs 2, 3, 4, 5, 6) — each ~50-80 s

### Renderer-fidelity gaps surfaced (2026-06-12, Portal4 action-bodies pass)

Surfaced while authoring the Dashboard action bodies onto `HomeBankingPortal4`
(rev 33→34). Both block faithful reproduction of the data layer; both are
framework bugs, not app-specific. Root-caused with file:line evidence.

- **V19 — Local-variable type fidelity: List/Structure/Record locals silently become Text.**
  `screen_renderer.py::_resolve_data_type` (lines 937-959) maps only scalar
  types (`_TYPE_MAP`) and `"<Entity> Identifier"` types. Every other `data_type`
  string returns `eSpace.TextType /* unmapped: ... */`. So List-of-record locals
  (`Accounts`, `DeptList`) and anonymous-record locals (`ChartCardsValue`) are
  authored as **Text**, not their real types. Consequence on Portal4: the
  `GetAccountsOnAfterFetch` (ListClear/ListAppend to `Accounts`) and
  `ConsolidatedPositionSidebarOpen` (ListAppend to `DeptList`) bodies cannot be
  authored as specified — the AVS publish validator rejects List ops on a Text
  local. The renderer already KNOWS this is lossy (it tracks the names in
  `ctx.unmapped_locals` to defer `<local>.Field` expressions, lines 107-117,
  259-262) but never emits the correct type. **Path to close:** extend
  `_resolve_data_type` to resolve `"<X> List"` and Structure/Record types to a
  real List/Structure IDataType (harvest the verified Model API call for
  List-typed local creation from Mentor first — first-of-kind code). In-place
  on Portal4 needs a Mentor patch that retypes the existing Text locals (a
  re-bake would destroy the screen-scoped aggregates).

- **V20 — Action references never collected into the import manifest.**
  `library_element_keys.yaml` catalogs **Blocks only** (discovered via
  `context_search objects=["Blocks"]`). Producer ACTIONS are never collected, so
  Phase 0 never imports them. Confirmed on Portal4 via `app_refs`: every producer
  reference is `kinds:["entities"]` — `GetLabelByLocale` (AgentsCommonResources,
  globalKey `2A5uDfh5wkKmZLRlbbGH6w*RqhsG84kiECGEOl_4g_2_Q`) and
  `ServiceFormatCurrencyCustom` (HomeBankingCore) are unavailable. Any action
  body that calls them re-stubs the call site (the "2 re-stubbed GetLabelByLocale
  expressions" at rev 33 trace here). **Path to close:** collect producer action
  elementKeys into the manifest (a parallel `actions:` block per library) and
  extend Phase 0 to import them via the two-step contract (addReferenceToElements
  stages; `eSpace.AddDependency(ParseGlobalKey(globalKey))` materializes).

- **V21 — `GetChartSampleData` data action absent on Portal4.**
  The INFRA pass (revs 30-32) authored the 7 **screen aggregates** but not the
  `GetChartSampleData` **data action** (a separate element with its own embedded
  aggregates — capture line 248). So `SetChartCards` /
  `GetChartSampleDataOnAfterFetch` have no `GetChartSampleData.ChartDataList`
  to reference. Not strictly a renderer bug — the INFRA scope simply didn't
  include data actions. **Path to close:** add a data-action recipe + include
  `GetChartSampleData` in the data-layer pass.

- **V22 — `AgentsCommonResources` under-import: names + icons both broken by one root cause.**
  Runtime DOM probe of Portal4 rev 35 (logged in as demo-user): 0 icons rendered,
  8 leaked icon-name texts (`transfer`, `eyeshow`, `columnchart`…), 7 literal
  "text" name stubs. All trace to `app_refs` showing `AgentsCommonResources`
  imported for `kinds:["entities"]` only. That library gives the original four
  things; the clone took one: `Locale2` entity (yes); `GetLabelByLocale` action
  (no → the 7 name stubs); `HBIcon` block (no — but NOT required, see below);
  the `hb-icons` icon font + `.hb-icon` CSS (no → 8 icon-name leaks, 0 glyphs).
  **Icon mechanism (confirmed from the original app's live CSS):** a custom TTF
  font `hb-icons` (`@font-face`) + a `.hb-icon` class with
  `font-feature-settings:"liga"`. `<span class="hb-icon">eyeshow</span>` renders
  the ligature as a glyph. So HBIcon-the-block is just a font wrapper — the glyph
  is pure font+class. **The block import is a red herring for rendering;** the
  fix is font + class, not the block.
  **Two-part fix (refined):**
  1. *Names* — import `GetLabelByLocale` (action) via the two-step contract
     (elementKey `1b6ca846-24ce-4088-8610-e97fe20ff6fd`, producer `0d6e0ed8-…`,
     globalKey `2A5uDfh5wkKmZLRlbbGH6w*RqhsG84kiECGEOl_4g_2_Q`) and wire the 7
     stubbed name expressions to `GetLabelByLocale(LabelLocale, Client.LocaleId)`.
  2. *Icons* — add the `hb-icons` `@font-face` + `.hb-icon` rule to Portal4's
     theme (font URL, same host so no CORS:
     `https://your-tenant-dev.outsystems.app/HomeBankingPortal/hb-icons__sNxxkmeqyW4BB9jTQaUAZA.ttf`
     — deploy-hash-specific per [[odc_resource_url_uuid_unstable]]; re-host later
     for stability), and apply class `hb-icon` to the icon text widgets (a
     renderer/block_renderer fix so future bakes carry it). No block import needed.
  **Framework generalization:** the import manifest + Phase 0 must collect a
  library's BLOCKS and THEME/FONT assets, not just entities (V20 added actions).


## CORRECTED BUILD ORDER — validated on Portal5 (2026-06-13)

The dechrome-then-chrome-wrap order was the structural mistake (web-search confirmed
the canonical ODC order). Rebuilt fresh as `HomeBankingPortal5` (dccd3c27, rev 7)
in the correct order: data → THEME (active) → LAYOUT block with placeholders →
SCREEN on the layout, content authored INTO MainContent/SideContent via
`layoutInstance.PlaceholdersContent.FirstOrDefault(p=>p.Placeholder?.Name=="SideContent").CreateWidget<T>()`.
Result: CDP gate GREEN (dark_mode=1, right_sidebar=1, leaked_icons=0, text_stubs=0,
inline_colored=0); sidebar renders RIGHT by construction; real account+txn data.
The old order's failure (empty SideContent, left-stacked) cannot occur. "Chrome
wrap" should be DELETED as a phase — chrome is the frame you build into.

### New generalizable platform walls/fixes (apply to renderer/recipes)
- **V23: never `block.Public=true` on a layout/UI block** → publish fails
  `OS-BLD-40409`/`OS-DPL-50205` (deprecated ModelFeature_UIPublicProperty). Same-module
  blocks don't need Public. Set `Public=false`.
- **V24: `IsDesktop()`/`IsTablet()`/`IsPhone()` are REJECTED in Web-app Style
  expressions** (`Unknown function 'IsDesktop'`). The responsive `If(IsDesktop(),…)`
  anchors can't be authored verbatim via the guided path — use the static
  desktop-equivalent classes (acceptable at desktop width; verbatim responsive parity
  is a wall).
- **V25: referenced entities live under `eSpace.References.Named("X").Entities`,
  NOT `eSpace.Entities`** (which is local-only). Renderer entity lookups for
  referenced data must use the References path.
- **V26: a fresh MCP-created theme is wired to NOTHING** — setting `theme.StyleSheet`
  does nothing until the theme is assigned active at app/flow level
  (`eSpace.DefaultMobileTheme` / `MainFlow.Theme` / `Layouts.Theme`). Renderer must
  ACTIVATE the theme, not just set its CSS.
- **V27: role-gated screen + no Login screen → `_error.html`** on anonymous hit.
  Open-demo screens need `AnonymousAccess=true` + cleared roles.
- **card_columns still 1 on Portal5**: data exists + cards render, but the
  `dashboard-card-list` grid container isn't the direct flex parent of the cards —
  a CSS-selector refinement, not a data gap.

## BREADTH RESULT — 8/8 Portal screens cloned on Portal5 (2026-06-13)
Confirmation(rev8), Login+WakeUp+InvalidPermissions(rev9), Requests+Transfer+PersonalLoan(rev10) — ALL
render clean (no errors, dark theme, no stubs/leaks) via the corrected layout-first order. Zero PARTIAL,
zero WALL. Data-bound screens work (Requests: 3 counters + ITableRecords with 10 live Transaction rows;
Transfer/PersonalLoan: bound inputs + multi-screen nav). Verdict: the ENTIRE Portal clones this way.
Applying W-A..W-D up front gave Transfer+PersonalLoan ZERO validation errors first-pass (no rediscovery).

### New widget-authoring walls (apply proactively; all self-corrected)
- **W-A:** `IButton.SetLabel` does NOT exist — set button/link text via an `IExpression` inside `btn.Content`.
- **W-B:** `IBuiltinEvent.SetDestination` does NOT exist — navigation is `btn.OnClick.Destination = screen`.
- **W-C:** NRWidgets `IInput` REQUIRES a bound Variable — `screen.CreateLocalVariable(...)` + `input.SetVariable(name)` or "Variable must be set" error.
- **W-D:** every Button REQUIRES an OnClick handler — wire `OnClick.Destination` (self-nav is valid) or "On Click must be set".
- **W-E (cosmetic fidelity gap):** the spec's custom blocks (Wizard, HBIcon, Menu, ConfirmationPDF, LayoutTopMenu/LeftSide/Blank) don't exist in Portal5 — only LayoutTopMenuRightSide. Screens use it + primitives; the gap is visual (icons/block chrome), not structural.
- **Positive recipe:** data-bound list screens clone first-try via CreateScreenAggregate → References.Named("HomeBankingCore") source → ITableRecords with cells bound to Get*.List.Current.Entity.Attr (no custom-PK crash).
