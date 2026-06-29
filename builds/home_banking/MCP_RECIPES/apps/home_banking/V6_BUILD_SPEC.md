# V6 BUILD SPEC — Pixel-Exact Home Banking Portal clone

**Goal:** rebuild the original Home Banking Portal (`fa7ab595-f8cd-4140-8826-2acc484727b6`,
rev 6) literally — same theme, layout, 8 screens, carousel, charts, sidebar, resources.
This is the consolidated master spec; the original is READ-ONLY (never mutated/published).

**Phase-1 status (this doc):** harvest COMPLETE. Every known-missing piece captured. The
GAP LIST at the bottom enumerates the only remaining uncertainties (all LOW-risk).

All capture sources live in `_raw/`. Pointers are given per section.

---

## 0. App shape

| Property | Value |
|---|---|
| App name | Home Banking Portal |
| Original assetKey | `fa7ab595-f8cd-4140-8826-2acc484727b6` (rev 6) |
| Kind | Reactive Web App |
| DefaultScreen | **Login** (UIFlow `Common`) |
| UIFlows | `Common` (Login, InvalidPermissions), `MainFlow` (the 6 authed screens) |
| Theme | **HomeBankingPortal** (+ EmailTheme, secondary, transactional email only) |
| Grid | Fluid, 12 cols, gutter 20, **maxWidth 1280** |
| Role | `HomeBankingPortal` (gates the 6 MainFlow screens; Login/InvalidPermissions anonymous) |

### References (producers to add to V6)
| Producer | assetKey | Used for |
|---|---|---|
| HomeBankingCore | `695efc5b-8f39-4a53-8d71-35c59097d245` | entities/actions (HBAccount, Transaction, LoanRequest, etc.) |
| OutSystemsUI | `8be17f2a-431c-4958-b894-c77b988a7271` | layouts + UI patterns (Sidebar, Wizard, Accordion, RangeSlider, Tooltip, masks…) |
| OutSystemsCharts | `38b70e23-50fc-4710-80cf-3682a9dc998a` | ColumnChart + PieChart |
| AgentsCommonResources | `0d6e0ed8-79f8-42c2-a664-b4656db187eb` | AI chat / markdown / hb-icons theme bits |
| AppsCommonCore | `4ba075ee-bb56-43a2-adc2-a81271fa5ee2` | common utilities |
| (System) | `478870b9-2d60-4f73-9eb3-7cd8b994a737` | platform |

Data model + actions: `entities.yaml`, `actions.yaml`, `actions-bodies.md`,
`dashboard_data_infra.capture.md` (aggregates/wiring), `roles.yaml`.

---

## 1. Theme (the full CSS)

**Primary source for V6 theme StyleSheet → `_raw/theme_hb_specific.capture.css` (50.8 KB).**
This is the HomeBankingPortal-specific CSS only (theme classes + tokens + @font-face + card
classes + sidebar/chart/balance classes), extracted from the live CSSOM. It is the V6 theme.

- **Full live stylesheet** (everything, incl. the entire OutSystemsUI framework): `_raw/theme_full.capture.css` (**630 KB**, 15 sheets). Reference only — the framework portion comes free with the OutSystemsUI ref; do NOT paste it into the V6 theme.
- **Design tokens** (288): `_raw/theme_tokens.capture.json` — all `--color-*`, `--font-size-*`, `--font-*` weights, spacing/radius/shadow. Key brand tokens:
  - `--color-secondary: #040d3f` (deep navy brand)
  - `--color-green: #23E2A3`, `--color-red: #FF6C6A`
  - Full palette families: red/orange/yellow/lime/green/teal/cyan/blue/indigo/violet (each lightest→darkest)
  - Font sizes: h1 32 / h2 28 / h3 26 / h4 22 / h5 20 / h6 18 / display 36 / base 16 / s 14 / xs 12 / label 11; weights 300/400/600/700.
- **@font-face**: `_raw/theme_fontfaces.capture.json` (7 rules). App fonts: **Sora** (Regular/SemiBold/Bold .ttf) + **hb-icons** (.ttf custom icon font). FontAwesome + FeedbackMessage ship with the platform.

**V6 theme wiring:** paste `theme_hb_specific.capture.css` into the V6 HomeBankingPortal theme
StyleSheet, then fix the `url(../…)` font/image paths to point at the re-uploaded V6 Resources
(see §7). The captured CSS already contains the @font-face + `.account-card.*` bg-image rules.

---

## 2. Layout + placeholders

The Dashboard (and most MainFlow screens) use layout block **`LayoutTopMenuRightSide`**
(captured: `LayoutTopMenuRightSide.block.tree.md`, 75 lines). Placeholders observed: `Header`
(→ `Menu` block), `Title`, `MainContent`/main, and a right-side region hosting the
ConsolidatedPosition `Sidebar`. Other layouts captured and available:
- `LayoutTopMenu` (base), `LayoutTopMenuLeftSide`, `LayoutTopMenuLeftSideWithBanner`
  (PersonalLoan uses this, with `ShowBanner` + a `Wizard`), `LayoutSideMenu`, `LayoutBase`,
  `LayoutBaseSection`, `LayoutBlank`, `PopupLayout`.
- Chrome blocks captured: `Menu`, `MenuIcon`, `ApplicationTitle`, `HeaderActions`, `UserInfo`,
  `NotificationsBalloon`.

`layout_utility_css.capture.md` + `dashboard_anchoring_map.capture.md` carry the exact
margin/padding/grid utility classes and the anchoring Style expressions per zone.

---

## 3. The 8 screens (all captured, complete)

All 8 Portal screen trees are present in `_raw/` with full widget hierarchy + Style/CustomStyle/
Text/Source/Expression values. Verified complete (style=true, expr=true on all).

| # | Screen | Capture file | Lines | Notes |
|---|---|---|---|---|
| 1 | Login | `portal-login.tree.md` | 91 | login form + marketing curve image (`CurveLoginPortal.svg`) + locale (EN) + theme |
| 2 | InvalidPermissions | `portal-invalidpermissions.tree.md` | 18 | small error screen |
| 3 | **Dashboard** | `portal-dashboard.tree.md` | 296 | the main canvas — see §4/§5/§6. Locals + 7 aggregates listed in tree header. |
| 4 | PersonalLoan | `portal-personalloan.tree.md` | 527 | richest screen: `Wizard`/`WizardItem` (OS UI), `AmountRangeSlide`/`MonthRangeSlide` (OS UI RangeSlider), document upload, popup. Inputs RequestId+StepNo. |
| 5 | Transfer | `portal-transfer.tree.md` (+ `.flat.txt`) | 170 | `AccountCard`, `FormInfoField`, masks, `InputWithIcon`, an embedded `StackedCarousel` instance. Input AccountId. |
| 6 | WakeUp | `portal-wakeup.tree.md` | 88 | session warmup / auth bootstrap |
| 7 | Requests | `portal-requests.tree.md` | 174 | request list |
| 8 | Confirmation | `portal-confirmation.tree.md` | 60 | `ConfirmationPDF`, `Wizard`, `CheckMark`/`CheckMark2` (OS UI). Inputs TransactionId (+opt RequestId). |

**Anchoring Style expressions** (the per-zone Style/CustomStyle that position content) are in
`dashboard_anchoring_map.capture.md` and inline in each tree. Notable Dashboard locals driving
layout: `SelectedAccountId`, `TotalBalance/TotalAssets/TotalDept`, `ChartHeight`, `HideChart`,
`ChartOptionList`, `ChatMessages`.

---

## 4. The carousel (block + JS) — THE centerpiece

Full detail: **`_raw/carousel_js.capture.md`** + verbatim source **`_raw/Slider.userscript.js`**.

- **Block:** `StackedCarousel` = `Container > Placeholder.slider.slider-content` (trivial; see
  `StackedCarousel.block.tree.md`). The stack EFFECT is **NOT** in the widget tree.
- **Driver:** a **custom `class Slider`** UserScript (15.7 KB, fully captured, not minified).
  NOT Splide/Swiper/Slick. (Splide *is* loaded but powers other `osui-carousel` tracks.)
- **Mechanism:** on init it writes inline `transform: scale(N); left: Npx; z-index: N` on each
  child slide. Runtime-confirmed scales **1.0 / 0.9 / 0.8** (active on top, each next 10% smaller
  + shifted right, peeking out). Uses Web Animations API for the fade transitions.
- **Effective desktop config** (block inputs → Slider options): `slidesPerPage: 3`, `gap: 0.05`
  (block input; JS default is 0.1), `scaleDown: 0.1`, `isVertical: false`, `moveOnClick: true`.
  Phone: slidesPerPage 2, gap 0.8.
- **Per-card vertical offset:** `AccountCard.PaddingTop = 54` (active) / `54 - Order*8` (inactive)
  — adds the descending stack offset on top of the JS scale.
- **V6 wiring:** add `Slider.userscript.js` as a UserScript, then in the StackedCarousel block's
  **OnReady** run a JS node: `new Slider($parameters.ContentId, { moveOnClick:true });`.

`AccountCard.block.tree.md` (98 lines, complete) has the card contents; bindings (Balance,
AccountNumber4Digit, AccountName, IsActive, AccountTypeId, PaddingTop) are in
`dashboard_contents_probe.capture.md`. Card art per type via `.account-card.{checking|saving|
creditcard|loancard|transfer}` bg-image (§7).

---

## 5. The chart

Full detail: **`_raw/chart_sidebar.capture.md`** + raw `_raw/chart_probe_out.json`.
Component: OutSystemsCharts (Highcharts). Two charts on the Dashboard:

- **ColumnChart** "Income vs Expenses" (`b21-ChartContainer`): grouped column, 2 series —
  `Income` (#234F4F) / `Expenses` (#B34852); x = Wk14…Wk23 (10 weeks); legend off (custom legend
  in markup); custom tooltip `point.custom.tooltipText`. **Period dropdown** `PeroidFilterDdl`
  (note original misspelling): 0=Weekly, 1=Monthly, 2=Quarterly.
- **PieChart** (`b47-ChartContainer`): Checking #C678D9 (5095) / Saving #56A6B2 (925) /
  Investment #F99551 (2152); legend off; custom tooltips.

V6: OutSystems ColumnChart + PieChart widgets; per-point colors + custom tooltip via
AdvancedFormat. Seed the listed sample values for pixel-match.

---

## 6. The sidebar (Consolidated Position)

Full detail: **`_raw/chart_sidebar.capture.md`** + dashboard tree `[1.5.3.x]`.

- **NOT an app block** — it's the OutSystemsUI **`Sidebar`** pattern instance named
  `ConsolidatedPositionSidebare`, `ExtendedClass="consolidated-position"`, `HasOverlay=True`,
  opened via `ConsolidatedPositionSidebarOpen` / closed via `…Close` client actions. A "close"
  `HBIcon` in the header. Its full content is captured inline in `portal-dashboard.tree.md`.
- **Content:** an OutSystemsUI **Accordion** (`osui-accordion`) — items per account (Checking
  $5,095.00, Saving $925.00, …), each item header = name + right-aligned balance, expanded
  content = masked card number (`****  ****  ****  4478`) + balance. Items start closed.

V6: OS UI Sidebar (ExtendedClass `consolidated-position`) + Accordion/AccordionItem, data-driven.

---

## 7. Resources / images / fonts

Full detail: **`_raw/resources.capture.md`**. All 18 binaries downloaded to **`_raw/resources/`**
(byte-verified). **Re-host plan:** every original URL is UUID-hashed and unstable across deploys —
re-upload each as a V6 app Image/Resource and reference via the OS picker (fonts via @font-face →
V6 Resource path). Do NOT hardcode the original hashed URLs.

- **Card art (bg-image):** CardChecking / CardSaving / CardCreditCard / LoanCard / CardTransfer (.svg)
- **Illustrations (`<img>`):** Wallet, Pig, Illustratiion (umbrella — orig misspelled), send, Agent2 (.svg)
- **Decorative curves (bg):** Curves (header), CurveLoginPortal (login) (.svg)
- **Floating chat toggles:** Assistant.png (open), Close.png (close)
- **Fonts (re-host):** hb-icons.ttf (custom icon font), Sora-Regular/SemiBold/Bold.ttf
- **Platform (no re-host):** FontAwesome, FeedbackMessage (inline data-URI)

---

## 8. AI chat (floating assistant)

Captured blocks: `Chat`, `ChatInput`, `ChatMessage`, `DisplayHTML`, `TaskBox`. Toggled by the
floating button (`.toggle-ai-chat-btn`, Assistant.png ↔ Close.png). Dashboard locals
`ChatMessages` / `IsWaitingForResponse` drive it. Agent pipeline: `agent_pipeline.capture.md`.
(In scope for visual parity; the AI backend wiring is in the capture but optional for a visual V6.)

---

# GAP LIST — what's still uncertain / risky for pixel-exact

Everything below is the residue after a complete harvest. **No HIGH-risk gaps.** Nothing blocks
arming the V6 build.

### Solid (no gap)
- ✅ Carousel JS — full source + effective config + runtime-confirmed scales. Captured verbatim.
- ✅ Full theme CSS — 630 KB full + 50.8 KB HB-specific + 288 tokens + 7 @font-face.
- ✅ All 18 resources downloaded + byte-verified; re-host plan defined.
- ✅ All 8 Portal screens captured complete (full tree + Style/CustomStyle/Expression).
- ✅ All 30 **app-owned** Portal blocks captured (the 29 from SCOPE + AccountCard re-capture).
- ✅ Chart configs (column + pie) + period dropdown + sidebar accordion — live config captured.
- ✅ Resolved: every "missing" block referenced by screens (`Sidebar`/`Wizard`/`WizardItem`/
  `CheckMark`/`CheckMark2`/`Slider`-widget/`MaskCurrency`/`MaskText`/`Tooltip`/`InputWithIcon`/
  `ButtonLoading`/`AmountRangeSlide`/`MonthRangeSlide`/`AlignCenter`) is an **OutSystemsUI
  framework pattern**, not app-owned — reused with ExtendedClass + inline content already in the
  screen trees. None need a separate capture.

### LOW-risk gaps (note, but not blocking)
1. **Carousel `eventListener` callback body** — the block's OnReady passes an `eventListener`
   into `Slider`; its exact body wasn't byte-captured (lives in compiled client logic). Live
   shows no visible side-effect beyond the animation → a no-op is a safe V6 default. *(carousel)*
2. **Carousel OnReady JS-node source** — the literal `new Slider(...)` call is inferred from the
   block inputs + runtime, not byte-extracted (not in any static bundle). Reconstruction in
   §4 is faithful. *(carousel)*
3. **OutSystemsCharts widget property panel** — we have the *rendered* Highcharts config (ground
   truth, sufficient), not the Studio AdvancedFormat JSON the SC originally typed. Reproduce from
   the rendered config. *(chart)*
4. **Non-Dashboard images** — resource scan was Dashboard-network + CSS. If Transfer/Loan/Requests/
   Confirmation reference an image not on the Dashboard or in HB CSS, it's not in `resources/`.
   Card art + curves + illustrations + chat toggles are confirmed; risk is a stray icon. *(resources)*
5. **SCOPE.md is stale** — it predates the post-2026-06-09 captures and still lists Dashboard/Login/
   blocks as "missing". They now exist in `_raw/`. Treat THIS spec as authoritative; SCOPE.md is
   historical. *(docs)*
6. **`portal-dashboard.summary.md`** is the old summary-only artifact; superseded by the full
   `portal-dashboard.tree.md`. *(docs)*

### Candidate-walls for Phase 2 (build risk, not capture risk)
- **Resource URL instability** (`odc_resource_url_uuid_unstable`) — must re-host all 18 assets as
  V6 Resources; do not depend on original URLs.
- **OutSystemsCharts novelty wall** (`odc_mcp_screen_scope_wall`) — Charts widgets are a known
  Mentor/MCP authoring-novelty area; may need Studio for the chart widgets.
- **Custom UserScript add via MCP** — adding the `Slider` UserScript + wiring a JS node in OnReady
  may need Studio (UserScript authoring isn't a confirmed MCP path).
- **OS UI Sidebar + Accordion patterns** via MCP — RangeSlider/Wizard/Sidebar pattern instances
  with inline placeholder content; standard but volume-heavy.

---

## VERDICT — Ready to arm the V6 build? YES.

Phase-1 harvest is complete. All centerpiece-missing pieces (carousel JS, full theme, resources,
charts, sidebar) are captured, and the only residual gaps are LOW-risk and have safe defaults.
The remaining risk is **build-time authoring** (charts / UserScript / OS-UI patterns via MCP vs
Studio), not capture. No blocking capture gap remains.
