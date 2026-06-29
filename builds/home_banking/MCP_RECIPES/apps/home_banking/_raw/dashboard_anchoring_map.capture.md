# Dashboard Anchoring Map — the original Home Banking Portal (full-parity spec)

**Source app**: Home Banking Portal, key `fa7ab595-f8cd-4140-8826-2acc484727b6` (rev 6).
**Runtime**: https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard
**Method**: authored Style-expression text from `portal-dashboard.tree.md` (Mentor compact-walker, rule-6 `.DisplayName` accessor, verified Jun 11) + live CDP cross-check of resolved runtime classes (2026-06-12, sandbox-off Python via `cdp_helpers.py`).
**Read-only.** No Mentor mutation, no publish against the original — it is the reference/spec.

> The widget tree itself (every container + its verbatim Style expression) lives in
> `portal-dashboard.tree.md`. This file is the **distilled anchoring map**: the structural
> containers that carry a Style/CustomStyle, the dark-mode activation mechanism, and the
> class-existence cross-ref for the clone.

---

## 1. Anchoring map — structural containers (Style verbatim)

The Style column is the **OutSystems expression source text** exactly as authored (the form
`SetStyle(...)` must reproduce in the clone — conditionals included; Recipe 27). Tree path
references `portal-dashboard.tree.md`.

### Header / Total-Balance band (Title placeholder)
| path | Name | type | Style expression (verbatim) | CustomStyle |
|---|---|---|---|---|
| 1.2.2 | (unnamed) | Container | `If(IsDesktop(), "display-flex justify-content-space-between", "display-grid gap-s")` | — |
| 1.2.2.1.1.T.1 | (unnamed) TrueBranch | Container | `"balance-cntr"` | — |
| 1.2.2.1.1.F.1 | (unnamed) FalseBranch | Container | `"balance-cntr"` | — |
| 1.2.2.2 | (unnamed) | Container | `If(IsDesktop(), "vertical-align gap-s", "display-grid gap-s")` | — |
| 1.2.2.2.1 | (unnamed) | Container | — | `text-align: center;` |
| 1.2.2.1.1.F.1.1.1.1 | (Expr) | Expression | `"font-size-h5  margin-top-xs"` | — |
| 1.2.2.1.1.F.1.1.2.1 | (Expr) | Expression | `"font-size-h1 white-space-nowrap"` | — |

Balance buttons (anchor to OS UI btn classes): `"btn btn-no-border padding-x-none margin-top-xs"` (toggle), `"btn margin-top-xs"` (Account Insights), `"btn  btn-primary margin-top-xs"` (Consolidated Position).

### MainContent — card carousel grid (1.3.1)
| path | Name | type | Style expression (verbatim) | CustomStyle |
|---|---|---|---|---|
| 1.3.1 | **Carouselcntr** | Container | `"margin-top-l card-carousel-container"` | — |
| 1.3.1.1.T.1.1 | (List) | List | `"list list-group dashboard-card-list"` | — |
| 1.3.1.1.T.1.1.1 | **ListItemClickable** | Container | — (Width="fill") | — |
| — | (StackedCarousel BlockInstance) | block | Gap=`If(IsPhone(),0.8,0.05)` SlidesPerPage=`If(IsPhone(),2,3)` | — |

### MainContent — action-button row (Transfer / Pay / Add) (1.3.2)
| path | Name | type | Style expression (verbatim) |
|---|---|---|---|
| 1.3.2 | (unnamed) | Container | `"margin-top-xl"` |
| 1.3.2.1 | (unnamed) | Container | `If(IsDesktop(), "display-flex", "display-grid") + " gap-base"` |
| 1.3.2.1.1.1 | Transfer btn | Button | `"btn btn-primary " + If(IsPhone() or IsTablet(), "", "width-fit-content")` |
| 1.3.2.1.2.1 | Pay btn | Button | `"btn btn-primary " + If(IsPhone() or IsTablet(), "", "width-fit-content")` |
| 1.3.2.1.3.1 | Add btn | Button | `"btn " + If(IsPhone()  or IsTablet(), "", "width-fit-content")` |

### MainContent — Last-Transactions + Chart two-column (1.3.3, via ColumnsMediumLeft)
| path | Name | type | Style expression (verbatim) | CustomStyle |
|---|---|---|---|---|
| 1.3.3 | (unnamed) | Container | `"margin-top-xxl"` | — |
| 1.3.3.1 | (block) | ColumnsMediumLeft | PhoneBehavior=`Entities.BreakColumns.All` | — |
| 1.3.3.1.1.1.1.1 | Col1 header | Container | `"font-size-base font-semi-bold"` | — |
| 1.3.3.1.1.1.1.2 | Col2 (View All) | Container | — | `padding: 2px 0px 0px 0px; text-align: right;` |
| 1.3.3.1.1.2 | (unnamed) | Container | `"margin-top-xs"` | — |
| 1.3.3.1.1.2.1 | **IsTableLoadingOrEmpty** | Container | — | — |
| 1.3.3.1.1.2.1.1.T.1 | empty TrueBranch | Container | `"table-empty margin-top-l"` | — |
| 1.3.3.1.1.2.1.1.F.1.T.1 | loading | Container | `"list-updating"` | — |
| 1.3.3.1.1.2.1.1.F.1.F.1 | txn list | List | `"list list-group"` | — |
| 1.3.3.1.1.2.1.1.F.1.F.1.1 | txn row | Container | `"item-card horizontal listItem"` | — |
| 1.3.3.1.2 | **Column2** (chart side) | Container | `"full-height"` | — |
| 1.3.3.1.2.1 | (unnamed) | Container | `If(IsPhone(), "", "margin-left-s") + " display-flex flex-direction-column full-height"` | — |
| 1.3.3.1.2.1.1.1.2.1 | period ddl wrap | Container | `"chart-option"` (Width=125px) | `text-align: right;` |
| 1.3.3.1.2.1.1.1.2.1.1 | **PeroidFilterDdl** | Dropdown | `"dropdown "` | — |
| 1.3.3.1.2.1.2 | **ChartCntr** | Container | `"margin-top-base flex-grow-1"` | — |
| 1.3.3.1.2.1.2.1 | chart box | Container | — | `height: 256px;` |
| 1.3.3.1.2.1.3 | gallery wrap | Container | `"margin-top-m"` | — |

Chart axis dark-mode hooks (ColumnChart add-ons): `Label: { LabelColor: If(Client.IsDarkMode,"#ffffff","#000000") }`; YAxis GridLines `LinesColor: If(Client.IsDarkMode,"#565D88","#B9BBC7")`. **These read `Client.IsDarkMode` — the same flag the dark-mode class is driven from.**

### SideContent — right sidebar (1.5)
| path | Name | type | Style expression (verbatim) | CustomStyle |
|---|---|---|---|---|
| 1.5.1 | (unnamed) | Container | `"margin-top-s"` | — |
| 1.5.1.1 | "For you" hdr | Container | `"font-semi-bold font-size-base"` | — |
| 1.5.1.2 | **PersonalLoan** | Container | — | — |
| 1.5.1.2.1 | card body | Container | `"colored-card lightDark position-relative display-flex"` | — |
| 1.5.1.2.1.1 | wallet img wrap | Container | `"wallet-img-card"` | — |
| 1.5.1.2.1.1.1 | (Image) | Image | `"wallet-img"` | — |
| 1.5.1.2.1.2 | text col | Container | `"align-right-content"` | — |
| 1.5.1.3 | **DefineNewGoal** | Container | `"tablePotraitPaddingLeft"` | — |
| 1.5.1.3.1 | card body | Container | `"colored-card position-relative"` | — |
| 1.5.1.3.1.2.1 | (Image Pig) | Image | `"pig-img"` | — |
| 1.5.1.4 | **RetirementPlan** | Container | — | — |
| 1.5.1.4.1 | card body | Container | `"colored-card position-relative"` | — |
| 1.5.1.4.1.2.1 | (Image Umbrella) | Image | `"umbrella-img"` | — |
| 1.5.2.1 | **YourGoals** | Container | — | — |
| 1.5.2.1.1 | goals carousel wrap | Container | `"margin-top-xxl cards-carousel"` (Visible Count>0) | — |
| 1.5.2.1.1.2.1.1 | goal card | Container | `"colored-card orange"` | `margin-top: var(--space-base);` |
| 1.5.2.2.1 | **YourLoans** wrap | Container | `"margin-top-xxl margin-bottom-s cards-carousel"` (Visible Count>0) | — |
| 1.5.2.2.1.2.1.1 | loan card | Container | `"colored-card yellow slide-mini"` | `margin-top: var(--space-base);` |

### SideContent — Consolidated Position sidebar (1.5.3, Sidebar block)
ExtendedClass=`"consolidated-position"`, HasOverlay=True. Notable inner Style classes:
`"margin-top-base"` (Header), `"heading5"` (title), `"margin-top-12"` (repeated spacing rows),
`"button-group"` / `"button-group-item"` (ButtonGroup2 assets/debt toggle),
`"total-in-chart"` (pie-chart centre overlay), `"margin-top-l position-relative"` (pie wraps),
`"list list-group"` (accordion lists).

---

## 2. Dark-mode activation mechanism

**What renders**: `<html class="dark-mode iconLibrary-fontawesome">` (OutSystemsUI native dark
mode — a CLASS on `<html>`, NOT a `data-theme` attribute). `body` background `rgb(4, 13, 63)`
(navy). Live-confirmed via CDP 2026-06-12.

**When / how it activates** (CDP-verified):
- On **/Login** the class is **absent** (`html class="iconLibrary-fontawesome"`, light body
  `rgb(248,249,250)`). → dark-mode is **not** a global/static theme default.
- On **/Dashboard** the class appears ~**1 second after hydration** (it is NOT in the initial
  SSR HTML; it is added by client JS during the reactive bootstrap). → activation is the
  **authenticated layout's OnReady / InitClientVars client logic**, run per-screen after the
  SPA loads. This matches the `Client.IsDarkMode` flag the chart axes also read.
- **No persisted preference**: `localStorage` has NO `dark`/`theme`/`mode` key (checked all 47
  keys). So it is **default-ON for the logged-in app**, driven by the `Client.IsDarkMode` client
  variable being true (or a fixed `AddClass(html,"dark-mode")` in OnReady) — not a stored user
  toggle. The header `HeaderActions` block DOES expose a manual toggle button
  (`If 'IsDarkMode'` → icons `darkmode`/`lightmode`, `HeaderActions.block.tree.md` line 18),
  i.e. the user CAN flip it, but the steady state on entry is dark.

**Clone implication**: the clone must (a) ensure the `Client.IsDarkMode` client var is true / add
`dark-mode` to `<html>` via the layout OnReady JS, AND (b) carry the dark color tokens + the ~900
dark-related theme rules (original ≈591KB CSS vs clone 41KB). The class activation alone renders
light unless the dark token/theme rules exist. (Cross-ref `dashboard_spec_baseline.capture.md`:
`dark_mode` gate target = 1.)

**Outstanding (not blocking the spec)**: the exact action body (`InitClientVars` vs the layout
block's OnReady, and whether it's `If(Client.IsDarkMode) AddClass` or unconditional) was not
dumped as a LOGIC capture this turn — the runtime behaviour (default-on, no persistence, class on
`<html>`) is fully sufficient to spec the clone. If a verbatim body is needed, capture
`InitClientVars` + the authenticated Layout block's OnReady action via the CAPTURE_PLAYBOOK
"For actions" recipe in a follow-up Mentor turn.

---

## 3. Structure outline (layout shells to reproduce)

```
LayoutTopMenuRightSide  (1)                      ← top nav (logo · Home/Products/Locations · Welcome/avatar); nav_links=8 live
├─ Header  → Menu block                          (1.1)
├─ Title placeholder                             (1.2)
│   └─ Total-Balance band
│       ├─ balance display  [If HideBalance → "balance-cntr" dots / currency+amount]
│       └─ action col  [If(IsDesktop) "vertical-align gap-s"] : Show/Hide, Account Insights, Consolidated Position
├─ MainContent placeholder                       (1.3)
│   ├─ Carouselcntr  "margin-top-l card-carousel-container"   ← ACCOUNT-CARD GRID (StackedCarousel → AccountCard list)
│   ├─ action row    If(IsDesktop)"display-flex" else "display-grid" + " gap-base"   ← Transfer / Pay / Add
│   ├─ ColumnsMediumLeft  "margin-top-xxl"                                          ← two-column
│   │   ├─ Column1: Last Transactions  (header + IsTableLoadingOrEmpty → txn list)
│   │   └─ Column2: "full-height" → "...display-flex flex-direction-column full-height"  ← BAR CHART
│   │       ├─ Balance hdr + PeroidFilterDdl ("chart-option" / "dropdown ")
│   │       ├─ ChartCntr "margin-top-base flex-grow-1" → ColumnChart (height 256px; axes read Client.IsDarkMode)
│   │       └─ Gallery "margin-top-m" → 3× ItemCard (Balance/Income/Expenses)
│   └─ Chat block
└─ SideContent placeholder                        (1.5)   ← RIGHT SIDEBAR
    ├─ "For you" → PersonalLoan ("colored-card lightDark ...") / DefineNewGoal / RetirementPlan  (all "colored-card ...")
    ├─ YourGoals  "margin-top-xxl cards-carousel" → Carousel of "colored-card orange"
    ├─ YourLoans  "margin-top-xxl margin-bottom-s cards-carousel" → Carousel of "colored-card yellow slide-mini"
    └─ ConsolidatedPositionSidebare (Sidebar, ExtendedClass "consolidated-position", overlay)
        → My Assets / My Debt toggle (button-group) + PieChart ("total-in-chart") + Accordion lists
```

The two-column split (cards/chart left, sidebar right) comes from the layout shell's
`.left-side`/`.right-side` grid plus the `ColumnsMediumLeft`/`ColumnsMediumRight` blocks — NOT
from a Style expression on a single container. Live CDP confirmed `.right-side` resolves
(`display:flex`); `.left-side` was not matched as a literal selector (the left column is the
ColumnsMediumLeft Column1, not a `.left-side` element on this screen).

---

## 4. Classes referenced by Style expressions — clone-theme cross-ref

**Live-confirmed PRESENT in the original runtime theme** (CDP 2026-06-12): `display-flex`,
`balance-cntr`, `colored-card` (×3), `card-carousel-container`, `full-height`, `right-side`,
`total-in-chart`, `wallet-img-card`. (`display-grid` not matched as a literal selector this load —
no element currently carries it bare, but the rule exists per `layout_utility_css.capture.md`.)

| class | where used | already in clone theme? (per layout_utility_css.capture.md) |
|---|---|---|
| `display-flex` / `display-grid` | header band, action row, chart col | YES — injected (layout system v2) |
| `gap-s` / `gap-base` | header band, action row | YES — injected |
| `justify-content-space-between` / `vertical-align` | header band | YES (justify-* in v2 set); verify `vertical-align` present |
| `flex-direction-column` / `flex-grow-1` | chart column | YES (flex-* utilities in v2) |
| `full-height` | chart Column2 | YES (`.full-height*` in v2) |
| `card-carousel-container` | account-card grid | **app-custom — NOT a layout utility. Must exist in theme; CONFIRM/INJECT.** |
| `dashboard-card-list` | account list | **app-custom — CONFIRM/INJECT.** |
| `balance-cntr` | hidden-balance dots | **app-custom — CONFIRM/INJECT.** |
| `colored-card` (+ `orange`/`yellow`/`lightDark`/`slide-mini`) | sidebar cards, goals, loans | **app-custom — CONFIRM/INJECT (the sidebar's whole look).** |
| `wallet-img-card` / `wallet-img` / `pig-img` / `umbrella-img` | sidebar card art | **app-custom image sizing — CONFIRM/INJECT.** |
| `align-right-content` | personal-loan text col | **app-custom — CONFIRM/INJECT.** |
| `cards-carousel` | YourGoals / YourLoans wraps | **app-custom — CONFIRM/INJECT.** |
| `total-in-chart` | pie-chart centre overlay | **app-custom — CONFIRM/INJECT.** |
| `chart-option` | period dropdown wrap | **app-custom — CONFIRM/INJECT.** |
| `item-card horizontal listItem` | txn rows | partly OS UI (`list-group`) + app-custom `item-card`/`listItem` — CONFIRM |
| `table-empty` / `list-updating` | txn empty/loading | OS UI list states — likely present |
| `tablePotraitPaddingLeft` | DefineNewGoal | **app-custom responsive — CONFIRM/INJECT.** |
| `consolidated-position` | sidebar ExtendedClass | **app-custom — CONFIRM/INJECT.** |
| `btn` / `btn-primary` / `btn-no-border` / `btn-transparent-with-border` / `width-fit-content` | all buttons | OS UI + `width-fit-content` (layout v2) |
| `font-size-h1/h5/base/xs`, `font-semi-bold`, `margin-top-*`, `text-green/red/neutral-*`, `white-space-nowrap`, `heading5`, `button-group*` | typography/spacing throughout | OS UI design-system classes — present |

**The app-custom block (the visual identity)** — `colored-card*`, `card-carousel-container`,
`dashboard-card-list`, `balance-cntr`, `total-in-chart`, `wallet-img-card`/`wallet-img`/`pig-img`/
`umbrella-img`, `align-right-content`, `cards-carousel`, `chart-option`, `consolidated-position`,
`tablePotraitPaddingLeft`, `slide-mini`, `lightDark`, `item-card`/`listItem` — these are NOT in
the captured layout-utility CSS. They are the original app's own theme rules and must be harvested
from the original's served stylesheets (same CDP-capture method as `layout_utility_css`) and
injected into the clone theme, or the sidebar/cards/chart will render unstyled even with the
layout grid + dark-mode in place.

---

## STEP-0 parity diagnosis — Portal4 clone @ rev 47/48 (2026-06-12, this turn)

Walked the CLONE's Dashboard widget tree (Mentor applyModelApiCode, widget_count=559) + live
CDP geometry/CSS reads. The mandate assumed the 3 zones were MISSING or unanchored on the
Dashboard SCREEN. **They are not.** Per-zone verdict:

| zone | model state (clone Dashboard screen) | runtime verdict | root cause |
|---|---|---|---|
| card grid | `Carouselcntr` ["margin-top-l card-carousel-container"], `c2049` ["list list-group dashboard-card-list"], StackedCarousel — all PRESENT + already anchored | `card_columns=1` — list is EMPTY (h=21, 1 child) | **DATA gap**: no account rows → no cards to grid. Containers lay out correctly; grid needs ≥2 cards. |
| right sidebar | PersonalLoan / DefineNewGoal / RetirementPlan / YourGoals / YourLoans containers + colored-card styles — all PRESENT + anchored; the 5 colored-cards DO render | `right_sidebar=0` — cards render in the LEFT column (left=40, top≥1476); `layout-right-side` is EMPTY (w=40, descendants=[]) | **(a) layout-shell two-column split was inert** (fixed this turn, see below) + **(b) the Dashboard's SideContent-bound widgets render in the left/main column, not in the layout's `layout-right-side`** — i.e. content distribution into the SideContent placeholder is not happening in the clone the way it does in the original (orig `layout-right-side` w=288 with cards). |
| chart | `ChartCntr` container PRESENT; `c2106` ["full-height"] PRESENT | `chart=2` (only `.chart-option` matches; no canvas/svg) | **MISSING content (WALL candidate)**: ZERO Chart-typed widget nodes in the OML graph and ZERO `GetChartSampleData` data-action nodes. The chart container is an empty shell — the ColumnChart widget + its sample-data action were never authored into the clone. |

### The smoking-gun layout finding (renderer conditional-drop bug, in the LAYOUT BLOCK)
The original `LayoutTopMenuRightSide` > `MainContentWrapper` Style is:
`"main-content ThemeGrid_Container " + If(IsPhone(), "right-side-phone","right-side") + If(IsPhone() or IsTablet(), ""," display-flex")`
The clone's `MainContentWrapper` Style was the bare literal `"main-content ThemeGrid_Container"` — the
two responsive split classes (`right-side` + `display-flex`) were DROPPED. Confirmed two ways:
(1) Mentor read-back of the model; (2) live CDP — the runtime `.main-content` carried neither class
and computed `display:block`, so `layout-left-side` + `layout-right-side` stacked instead of sitting
as flex columns. This is the Recipe-27 conditional-Style-drop, landed one level up from the Dashboard
screen (in the shared layout block) — not on the Dashboard containers the mandate pointed at.

**Fix applied this turn (rev 48, published, committed clean):** set `MainContentWrapper.Style` to the
static desktop-equivalent `"main-content ThemeGrid_Container right-side display-flex"` (the desktop
branches of the original's conditional; the gate runs at width 1280). Verified live (cache-busted):
`.main-content` now carries `right-side display-flex` and computes `display:flex`, with two flex-item
children. This is NECESSARY but NOT SUFFICIENT — the right column still renders empty because the
SideContent widgets aren't bound into `layout-right-side` (see table row above).

### THE HEADLINE WALL — MCP cannot wire the Dashboard's SideContent placeholder (IDE can)
Confirmed via Mentor model walk + its own diagnosis (session eef9ef97, runs f5d62257 / 72d56772 /
b7e4fbc8), corroborated by the OML graph: **all 7 Dashboard content containers (PersonalLoan,
DefineNewGoal, RetirementPlan, YourGoals, YourLoans, Carouselcntr, ChartCntr) sit under NEITHER the
MainContent NOR the SideContent placeholder** — they are in the layout instance's undifferentiated
content stream, which renders into the LEFT column. The `LayoutTopMenuRightSide` block DEFINITION
declares 4 placeholders (MainContent, Header, IconName, SideContent), and `c20 > c21` carries Style
`"layout-right-side"` (the right column) wrapping the SideContent placeholder. But on the Dashboard's
block INSTANCE (`inst_1`) only MainContent + Header have content wired; **the SideContent slot has no
instance-level content container, and the Model API does not allow creating a placeholder content slot
on an existing block instance after the fact.** That binding is created by the IDE at screen-authoring
time (dropping widgets into the SideContent placeholder) and was never wired by the MCP-generated clone.
Therefore the static "For you" sidebar (Personal Loan / Define Goal / Retirement / Your Goals / Your
Loans) **cannot be moved into the right rail via MCP** — `right_sidebar` stays 0 even though the cards
themselves render (in the left column). The only MCP-offered workaround (move the cards into the block
DEFINITION's `c21`) is wrong: that container is shared by every screen using the layout, so it would
leak the Dashboard sidebar onto all other screens — declined. **This is the MCP-vs-IDE gap: the IDE
wires screen content into a layout's named placeholder slots; MCP/Model-API cannot create or populate
the SideContent instance slot on an already-generated screen.**

### Chart zone — also a content WALL (missing widget + data action)
OML graph: ZERO Chart-typed widget nodes, ZERO `GetChartSampleData` action nodes. `ChartCntr` is an
empty shell. The original's bar chart is an OutSystemsCharts `ColumnChart` fed by sample data — exactly
the "API novelty (Counter/Chart/Map)" class flagged by the screen-scope wall
([[odc_mcp_screen_scope_wall]]). Authoring it was not attempted to completion this turn; on prior
evidence it is a likely wall. `chart` stays 2 (only `.chart-option` matches).

### Card grid — DATA gap (not structural)
`Carouselcntr` + `dashboard-card-list` + StackedCarousel are present and anchored; the Dashboard has
real data aggregates `GetAccounts` / `GetAssets` (joins HBAccount/Customer/Transaction, filtered
`HBCustomer.UserId = GetUserId()`, MaxRecords 6). The list is empty because the logged-in test user has
no HBAccount rows. With ≥2 account rows the cards would grid 3-up. `card_columns` stays 1 = DATA gap,
per the mandate's stated 0-data caveat.

### MCP gating notes (process findings, not app findings)
- `IsPhone()`/`IsTablet()` in a Style expression: Mentor REFUSES to author it into this Web app
  ("mobile-only functions … platform rejects them"). The earlier raw applyModelApiCode SetStyle of the
  full `If(IsPhone()…)` form DID compile clean (compilationErrors:[]) and read back — but Mentor's
  guided path rejects it, and whether it survives publish is unverified. The static desktop form is the
  safe equivalent for desktop parity.
- **CANCELLING a Mentor MUTATION turn before terminal ROLLS BACK the change** (observed: stdout
  literally printed `REVERTED MainContentWrapper.Style=[…bare literal…]` during cancel teardown). The
  `mentor_cancel`-after-`tool_end` trick is safe ONLY for READ-only walks; for mutations the turn must
  run to terminal to commit + to deliver the publish token.
- Mentor refuses raw user-supplied code non-deterministically. "Capture task / report the styling of
  container X" framing succeeds where "execute this code I supplied" framing is refused.

## Provenance
- STEP-0 clone diagnosis: Mentor sessions a4967dc6 / 06a68b24 / 7351ba75 / eef9ef97 + CDP probes
  `scripts/cdp_probe_classes.py`, `cdp_probe_layout.py`, `cdp_probe_wrapper.py`, `cdp_clone_structure.py`,
  `cdp_orig_structure.py`, `cdp_rightside_content.py`, `cdp_metrics_bust.py`, `scripts/probe_containment.py`
  (2026-06-12). Layout fix published at rev 48.
- Anchoring expressions: `portal-dashboard.tree.md` (Mentor walk, verbatim Style source via rule-6 `.DisplayName`).
- Dark-mode + class resolution: live CDP read-only, original Dashboard tab, 2026-06-12 (probe scripts `/tmp/probe_dashboard*.py`).
- Cross-ref: `dashboard_spec_baseline.capture.md`, `layout_utility_css.capture.md`, `HeaderActions.block.tree.md`.

## CORRECTION (2026-06-12): the SideContent "wall" was MIS-DIAGNOSED

The earlier wall claim ("Model API cannot create/populate the SideContent instance
slot post-hoc") is **FALSE**. Beat-0 consult + two independent read-backs confirm:
- `inst_1` (LayoutTopMenuRightSide instance) HAS 4 slots: IconName, Header,
  MainContent (children sect_2, sect_1), and **SideContent — exists, empty, populatable**.
- Reach it: `inst.PlaceholdersContent.FirstOrDefault(p => p.Placeholder?.Name=="SideContent")`
  → `IPlaceholderContentWidget.CreateWidget<T>(...)`. Works any time, no author-time restriction.
- The 5 sidebar cards currently live under **MainContent / sect_1** (left column) — that's
  why they render left. The renderer authored screen content into the wrong slot.
- The REAL (narrower) constraint: there is NO reparent primitive (only same-parent
  Move*); so SideContent must be **rebuilt** (CreateWidget the cards in SideContent +
  delete the originals), not moved. A deliberate build turn — NOT a wall.
- Card grid: `c2049` is a plain IContainer (`list list-group dashboard-card-list`),
  not an IList. Fix is CSS (`.dashboard-card-list { display:grid; grid-template-columns:
  repeat(3,1fr); gap:var(--space-base); }`). NB card_columns>=3 also needs account
  DATA to render the 3 account cards (test user has none).
- RENDERER FIX: author screen content into MainContent/SideContent slots correctly
  at bake time, so future clones don't need the rebuild.
