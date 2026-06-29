# Recipe 28 — Build a Screen the CORRECT way (layout-first, fill placeholders)

**This supersedes the dechrome → chrome-wrap model (Recipe 23), which was the
wrong order.** Proven on HomeBankingPortal5 (8/8 screens cloned clean, 2026-06-13):
build the screen ON its layout and author content INTO the layout's named
placeholders. Content lands in the right slot BY CONSTRUCTION — no post-hoc
reparenting (the Model API has no reparent primitive anyway), no empty SideContent.

## Canonical ODC order (web-confirmed)
data → **THEME (active)** → **LAYOUT block (placeholders)** → **SCREENS on the
layout, content filled into placeholders** → logic. The theme owns the layouts +
grid + stylesheet; a screen gets its layout from the active theme.

## Preconditions (do once per app, before screens)
1. **References**: `eSpace.AddDependency(...)` the data/core app + any block/action
   libs. Referenced elements live under `eSpace.References.Named("X").Entities` /
   `.ServerActions` — NOT `eSpace.Entities` (V25).
2. **Theme ACTIVE** (V26): setting `theme.StyleSheet` does nothing until the theme
   is assigned active — `eSpace.DefaultMobileTheme` / `MainFlow.Theme` /
   `Layouts.Theme`. Put the full theme CSS (base + layout utilities + app-custom
   card classes + `hb-icons` @font-face + `.hb-icon`) on it.
3. **Layout block** with MainContent + SideContent placeholders (e.g.
   LayoutTopMenuRightSide). NEVER `block.Public=true` on a layout/UI block (V23 →
   OS-BLD-40409 deprecated-feature publish crash).
4. **Dark mode** (if the theme is dark): wire the layout's OnReady → a JavaScript
   node `document.documentElement.classList.add('dark-mode')` (it's a JS-set class,
   not a data-theme attr).

## Per screen
```
1. var screen = mainFlow.CreateScreen("X");                 // gets the active theme's layout
   // anonymous screens (Login/InvalidPermissions): screen.AnonymousAccess=true; clear Roles (V27)
2. // find the layout instance on the screen, then its placeholders:
   var inst = <the layout block instance on the screen>;
   var main = inst.PlaceholdersContent.FirstOrDefault(p => p.Placeholder?.Name == "MainContent");
   var side = inst.PlaceholdersContent.FirstOrDefault(p => p.Placeholder?.Name == "SideContent");
3. // AUTHOR CONTENT INTO THE PLACEHOLDERS — this is the whole point:
   var c = main.CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>("Band");
   c.SetStyle("\"balance-cntr\"");                          // anchor to theme class (Recipe 27)
   // ... build main content under `main`; build the right-rail under `side`
4. // anchor responsive layout: SetStyle with the original's expression, BUT
   //   IsDesktop()/IsTablet()/IsPhone() are REJECTED in Web Style exprs (V24) —
   //   use the static desktop-equivalent classes, e.g. "display-flex justify-content-space-between".
```

## Widget-authoring walls (apply PROACTIVELY — zero-error first-pass)
- **W-A** Button/Link TEXT: `IButton.SetLabel` does NOT exist. Create an
  `IExpression` inside `btn.Content` and set its value.
- **W-B** Navigation: `IBuiltinEvent.SetDestination` does NOT exist. Set the
  property: `btn.OnClick.Destination = targetScreen`.
- **W-C** `IInput` REQUIRES a bound Variable: `screen.CreateLocalVariable(name)` +
  `input.SetVariable(name)` or "Variable must be set" error.
- **W-D** Every Button REQUIRES an OnClick handler (set `OnClick.Destination`,
  self-nav valid) or "On Click must be set" error.

## Data-bound list screens (clones first-try)
`screen.CreateScreenAggregate(false,"GetX")` → source =
`eSpace.References.Named("HomeBankingCore").Entities...` → `ITableRecords` (or list)
with header + row cells bound to `GetX.List.Current.<Entity>.<Attr>`. Only
reference Core entities — do NOT author new custom-PK entities (publish crash).

## Verify (beat 7)
Publish (let the turn reach terminal — do NOT cancel a mutation), snapshot, then
CDP gate: screen renders clean (not `_error.html`), dark theme, `leaked_icons=0,
text_stubs=0, inline_colored=0`, and for the dashboard `card_columns>=3,
right_sidebar=1`. Content visibly IN the right placeholders (sidebar on the right).

## Known wall
ColumnChart / OutSystemsCharts (API-novelty screen-scope wall) — substitute a
styled placeholder. Custom block chrome (HBIcon/Menu/colored-cards) is cosmetic:
clone the blocks for full fidelity, or substitute primitives + theme classes.

## CHART WALL RETIRED (2026-06-13) — native OutSystemsCharts ColumnChart WORKS via MCP
The "ColumnChart / OutSystemsCharts API-novelty wall" was DISPROVEN (like SideContent). It authored cleanly:
- `addReferenceToElements` for OutSystemsCharts `ColumnChart` → resolves as ReferenceWebBlock in `MobileFlows["Charts"]`.
- `chartContainer.CreateWidget<IMobileBlockInstanceWidget>("SpendingChart")` + `SourceBlock = Charts\ColumnChart`. Clean.
- DATA wiring is the only real friction, and it's GRAMMAR not capability: inline record/list literals are rejected (`Unknown function 'DataPoint'` / `'ListAppend'` — ListAppend is a (System) ClientAction NODE, not an expression fn). Pattern that works: a screen local `ChartDataPoints` (DataPoint List) + a `SeedChartData` screen action (per-row: Assign typed Row → ExecuteClientAction ListAppend(list,Row)) wired to OnInitialize, then bind `SpendingChart.DataPointList = ChartDataPoints`.
- Runtime: chart metric 1→66 (Highcharts), legend [Income,Expenses], real grouped bars. Rev 14.
**Implication: no confirmed "Studio-can / MCP-can't" build gap remains** — every wall this effort hit (SideContent, the chart) dissolved on a real constructive attempt. The pattern: assume nothing is a wall until an actual error proves it.
