# Recipe 29 — Build the Dashboard (the centerpiece screen), staged

**This is Pass C of the V6 clone.** The Dashboard is the hardest screen in the
Home Banking Portal: 7 aggregates + 1 DataAction, 16 screen locals, ~11 screen
actions, and a deep widget tree across the layout's **Title / MainContent /
SideContent** placeholders. It cannot be authored in one Mentor turn — stage it.

Ground truth: `apps/home_banking/_raw/portal-dashboard.summary.md` (full tree),
`dashboard_data_infra.capture.md` (aggregate joins/filters/calc/group-by),
`chart_sidebar.capture.md` (chart + pie + accordion config & live values),
`dashboard_spec_baseline.capture.md` (pixel-gate targets). Build ON the active
theme's layout and author INTO placeholders (Recipe 28). NEVER cancel a mutation
turn (rolls back) — let each reach terminal `succeeded`, then publish + snapshot.

## Block / pattern dependency inventory (resolve refs BEFORE the screen)
- **LOCAL** (cloned in Pass A/B, in the `Layouts` flow): `Menu`, `StackedCarousel`
  (+Slider JS), `AccountCard`, `ItemCard`, `Chat`/`ChatInput`/`ChatMessage`,
  `AccountAccordian`, `LoanAccordian`, `HBIcon` (Core), `AlignCenter` if local.
- **REFERENCED OutSystemsUI** (via `addReferenceToElements` → ReferenceWebBlock):
  `ColumnsMediumLeft`, `ColumnsMediumRight`, `Columns2`, `BlankSlate`, `Gallery`,
  `Carousel`, `ProgressBar`, `Sidebar`, `Tag`, `ButtonGroup`/`ButtonGroupItem`,
  `Accordion`.
- **REFERENCED OutSystemsCharts**: `ColumnChart`, `PieChart`, `ChartXAxis`,
  `ChartYAxis`, `ChartSeriesStyling` (chart wall is RETIRED — Recipe 27/28; data
  wiring is the only friction, handled via the `GetChartSampleData` DataAction +
  `DataPointList` bind).
- **Core entities** (via `eSpace.References.Named("HomeBankingCore")`): `HBAccount`,
  `ProductType`(static), `HBCustomer`, `Transaction`, `TransactionType`,
  `HBAccountName`, `ChartDataOption`(static), `CustomerGoal`, `CustomerLoan`,
  `Color`(static), `Locale2`(static). Element-import each used type via
  `eSpace.AddDependency((sig as IModelObject).GlobalKey)` (GlobalKey, not signature).

## Staged turns (one publish per stage, snapshot after each)

> **CREATE the screen first** — the Dashboard does NOT pre-exist (rev 10 had only
> ThemeCheck/ProbeBlocks). `mainFlow.CreateScreen("Dashboard")` on the active theme.
> **HIDDEN-STUB PRECONDITION (mandatory before any aggregate/expression):** every
> referenced Core entity an aggregate/expression touches must be FULLY element-imported,
> not an Id-only `#HiddenReferenceEntity` stub — else publish dies with `OS-APPS-40028`
> "invalid OML" (zero in-session errors). Import via
> `Services.ModelServices.TryParseGlobalKey(s, out IGlobalKey k)` → `eSpace.AddDependency(k)`
> → `RefreshDependencies`. Applies to STATIC entities too (`ChartDataOption`, `Color`,
> `Locale2`). Memory: `odc_mcp_hidden_stub_import_os_apps_40028`.

### C1 — data layer  [DONE @ rev 12 — 15 locals, 4 structs, 7 aggregates, GetChartSampleData (empty), 12 action skeletons]
C1 + C1-tail + C2 are COMPLETE: all 7 aggregates incl. GetChartDataOptions; the 12
screen-action skeletons; GetChartSampleData exists but returns an EMPTY list.

**CHART DATA — use an AGGREGATE, not ListAppend.** Wiring `(System).ListAppend` onto
an `IExecuteClientActionNode` throws via MCP (memory:
`odc_mcp_listappend_node_wiring_throws`). For pixel-parity bars, add a
`GetChartData` aggregate over the existing `HomeBankingCore.ChartData` entity
(Income/Expenses/Week/Order columns) and bind `ColumnChart.DataPointList` to it in
C4 — NOT the empty GetChartSampleData DataAction. Import ChartData if it's a hidden
stub (isolate the import in its own committing turn).
- 16 locals: `SelectedAccountId, SelectedChartDataOptionId, Accounts, ChartHeight,
  TotalBalance, TotalAssets, TotalDept, IsDeptConsolidatedPositionOption, HideChart,
  DeptList, ChartCardsValue, IsPortrait, ChatMessages, IsWaitingForResponse,
  ChartOptionList` (+ `SelectedAccountId` dup-guard). Types per the tree (Identifier,
  Decimal, record-list locals as the matching structure/list types).
- 7 aggregates via `screen.CreateScreenAggregate(false,"GetX")`: `GetAccounts`,
  `GetAssets`, `GetChartDataOptions`, `GetCreditCardsDept`, `GetCustomerGoals`,
  `GetCustomerLoans`, `GetLastTransactions`. Joins/filters/calc/group-by/sort/max
  EXACTLY per `dashboard_data_infra.capture.md` (GetAccounts: 6 sources, 3 filters,
  `AmountWithSign` calc, 4 group-bys, `AccountBalance=Sum`, sort `ProductType.Order`,
  max 6). Aggregate API lives in `OutSystems.Model.Logic.Aggregates` (NOT the root —
  CS0234 otherwise): `CreateSource/CreateJoin/CreateFilter/CreateCalculatedAttribute/
  CreateGroupByAttribute/CreateAggregatedAttribute/CreateSort/SetMaxRecords`;
  `AggregationType.Sum`.
- 1 DataAction `GetChartSampleData` returning `ChartDataPoints` (DataPoint List) —
  per chart_sidebar values (Wk14–Wk23, Income/Expenses series). Seed the live
  sample values so the pixel-gate has the same bars.

### C2 — screen-action skeletons (so buttons/handlers validate — W-D)
Create empty-but-valid handlers, wire real bodies later: `ToggleHideBallanceOnClick`
(flip `Client.HideBalance`), `ConsolidatedPositionSidebarOpen/Close` (Sidebar
open/close), `PeroidFilterDdlOnChange` (refresh chart), `CarouselAccountOnSlideMoved`
(set `SelectedAccountId`), `ColumnChartInitialized`, `DonutChartInitialized`,
`ChatOnSendMessage`, `ChatOnFirstToggle`, `RedirectToLoan`, `NewLoanOnClick`, and a
shared `NotImplemented` no-op. Every Button needs an OnClick (W-D); self-nav OK.

### C3 — Title placeholder (Total Balance band)
"Total Balance" label; HideBalance If → 4 `circle` dots vs `AlignCenter`(Currency +
`FormatCurrency(TotalBalance)`); Show/Hide Balance button (HBIcon eyeshow/eyehide,
`ToggleHideBallanceOnClick`); Account Insights button (HBIcon insights); Consolidated
Position primary button (HBIcon columnchart → `ConsolidatedPositionSidebarOpen`).
Responsive Style: use static desktop classes (`display-flex justify-content-space-between`)
— `IsDesktop()` is rejected in Web Style exprs (V24).

### C4 — MainContent
1. `Carouselcntr` (`margin-top-l card-carousel-container`) → If `not Accounts.Empty and
   GetAccounts.IsDataFetched` → `StackedCarousel` Content → `IList Source="Accounts"`
   (`list list-group dashboard-card-list`) → `ListItemClickable` → `AccountCard` (bind
   Balance/AccountNumber4Digit/AccountName/IsActive/AccountTypeId). Carousel OnClick →
   `CarouselAccountOnSlideMoved(ItemIndex=ActiveSlide)`.
2. Transfer / Pay / Add button row (HBIcon transfer/scan/plussquare; Transfer →
   Transfer screen w/ AccountId).
3. `ColumnsMediumLeft`: **Column1** = Last Transactions (`ColumnsMediumRight` header +
   "View All" link; `GetLastTransactions` empty/loading/list states; row = HBIcon +
   label + signed amount + date). **Column2** = Balance header + `PeroidFilterDdl`
   dropdown (`Variable=SelectedChartDataOptionId List=ChartOptionList` →
   `PeroidFilterDdlOnChange`), `ChartCntr` → `ColumnChart` (`DataPointList=
   GetChartSampleData.ChartDataPoints`, AddOns ChartXAxis/ChartYAxis/ChartSeriesStyling),
   then `Gallery` (RowItemsDesktop=3) of 3 `ItemCard`s (primary/green/red — Balance/
   Income/Expenses; HBIcon banknote/deposit/withdrawal; percentage + range exprs).
4. `Chat` instance (UserName/IsWaitingForResponse/ChatMessages; OnSendMessage/OnFirstToggle).

### C5 — SideContent
1. "For you" header + 3 colored cards: `PersonalLoan` (`colored-card lightDark` +
   Wallet img → `NewLoanOnClick`), `DefineNewGoal` (`colored-card` + Pig img),
   `RetirementPlan` (`colored-card` + umbrella img). Card classes come from the theme
   (`colored-card`, color variants) — already staged in `theme_v6_staged.css`.
2. `YourGoals` (Visible `GetCustomerGoals.Count>0`) → `Carousel` of goal cards
   (`colored-card orange`, name + Add btn + `FormatCurrencyCustom` of/total + ProgressBar).
3. `YourLoans` (Visible `GetCustomerLoans.Count>0`) → `Carousel` of loan cards
   (`colored-card yellow slide-mini`, label + View btn + amounts + ProgressBar).
4. `ConsolidatedPositionSidebare` (`Sidebar ExtendedClass="consolidated-position"`):
   Header (title + close link → `ConsolidatedPositionSidebarClose`); Content = My
   Assets/My Debt ProgressBars + Tag(+23%) + `ButtonGroup`(Assets/Debt toggle) +
   `Assets2`/`Depts2` → `PieChart` (Height 245px; `DataPointList` mapped from
   `GetAssets.List`/`DeptList` to Value/Label/Color/Tooltip; `total-in-chart` overlay)
   + `Accordion` → `AccountAccordian`/`LoanAccordian` list.

## CHART FIDELITY FIX (post-C4 — V6 currently shows a single blue "Series 1" bar)
The original ColumnChart (chart_sidebar.capture.md) is **grouped, 2 series over 10
week categories**: x-axis `Wk14…Wk23`; series **Income** per-point `#234F4F` (dark
teal), **Expenses** per-point `#B34852` (dark red); chart-level colors
`["#4263EB","#F59F00"]`; legend DISABLED (custom legend in markup); custom tooltip
`point.custom.tooltipText`. V6's `GetChartData` mapped only Income→Value (one
series, default blue) — WRONG. Fix: produce TWO DataPoint series (Income +
Expenses) across the 10 weeks and wire `ChartSeriesStyling` for the per-series
colors + disable the legend. Data source = `HomeBankingCore.ChartData`
(Income/Expenses/Week/Order columns) — NOT ListAppend. The PieChart (sidebar) is
single-series from GetAssets (violet/cyan/orange slices) — see capture.

## Pixel gate (after C5 publishes clean)
Reset V6 to the SAME seeded user/data as the original (Andrea), same viewport
(width 1280, dark-mode active). `scripts/cdp_login_screenshot.py` → V6 dashboard PNG;
`scripts/pixel_diff.py compare/original_dashboard_spec.png <v6>.png --tol 16
--threshold 99.5`. Heatmap bbox drives the next iteration. Each remaining mismatch is
either a fixable build delta (iterate) or — with a verbatim MCP error on a real
constructive attempt — a precisely-defined WALL = the mandate's headline finding.

## Pre-applied walls (don't rediscover)
Aggregate ns = `OutSystems.Model.Logic.Aggregates` (CS0234 else). Chart data via
DataAction + `DataPointList` bind, NOT inline `DataPoint`/`ListAppend` literals
(grammar wall — Recipe 27). `AddDependency(GlobalKey)`. Referenced blocks →
`addReferenceToElements` → typed `bi.SourceBlock`; LOCAL blocks → reflection on
SourceWebBlock (Preamble anti-pattern #6). Placeholders use `SetStyleClasses(
ExpressionDefinition)`; containers/buttons use `SetStyle`. W-A..W-D on every
button/link/input. PLAIN Mentor phrasing; raw `"""..."""` literals for CSS/JS.
