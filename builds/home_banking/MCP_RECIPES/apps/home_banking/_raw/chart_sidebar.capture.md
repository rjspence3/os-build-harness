# Charts + Sidebar rich components — CAPTURE

**Provenance:** CDP read-only against live `…/HomeBankingPortal/Dashboard` (app `fa7ab595`),
2026-06-13. Read directly from the live `Highcharts.charts` config objects + the rendered DOM.
Raw dump: `_raw/chart_probe_out.json` (copied below).

The dashboard charts are the **OutSystemsCharts** component (Highcharts under the hood —
`OutSystemsCharts.UserScripts.Highcharts*` bundles loaded). In V6 use the OutSystems **Charts**
widgets (ColumnChart + PieChart) — they emit this same Highcharts config.

## 1) ColumnChart — "Income vs Expenses" (renderTo `b21-ChartContainer`)
- **type:** `column`, grouped (2 series side-by-side)
- **x-axis categories:** `Wk14, Wk15, Wk16, Wk17, Wk18, Wk19, Wk20, Wk21, Wk22, Wk23` (10 weeks)
  - x-axis title: none. y-axis title: none.
- **series:**
  - `Income`  — per-point color **`#234F4F`** (dark teal). Sample data: 400, 420, 440, 540, 560, 700, …
  - `Expenses` — per-point color **`#B34852`** (dark red). Sample data: 500, 520, 540, 600, 620, 500, …
  - chart-level `colors: ["#4263EB", "#F59F00"]` (theme default; overridden per-point above)
- **legend:** disabled (`legend.enabled = false`) — custom legend is in the markup, not Highcharts.
- **tooltip:** custom `point.custom.tooltipText` e.g. `"Income: $400.00"` / `"Expenses: $500.00"`.
- **Period dropdown** controlling the chart: native `<select id="PeroidFilterDdl"
  class="dropdown-display dropdown">` (note original misspelling `Peroid`):
  - `0 → Weekly`, `1 → Monthly`, `2 → Quarterly`
  - Changing it re-queries the aggregation (Weekly = Wk14–Wk23 view).

## 2) PieChart — account balance split (renderTo `b47-ChartContainer`)
- **type:** `pie`, single series, **legend disabled**.
- **slices (live):**
  - `Checking` — y **5095**, color **`#C678D9`** (violet), tooltip `"Checking: $5,095.00"`
  - `Saving`   — y **925**,  color **`#56A6B2`** (cyan-light), tooltip `"Saving: $925.00"`
  - `Investment` — y **2152**, color **`#F99551`** (orange-light), tooltip `"Investment: $2,152.00"`
- y-axis title `"Values"` (default, not visible on a pie).

## 3) Consolidated Position — OutSystemsUI **Accordion** (sidebar)
- Component: **`osui-accordion`** (the OS UI Accordion pattern), items start **closed**
  (`osui-accordion-item--is-closed`), title aligned right, caret icon
  (`osui-accordion-item__icon--caret`), item bg `background-neutral-2`.
- **Items (live):**
  - `Checking` — header right value **$5,095.00**; expanded content shows masked number
    `****  ****  ****  4478` + `$5,095.00`.
  - `Saving` — header right value **$925.00**.
  - (Investment/others follow the same item template, data-driven.)
- In V6: OutSystemsUI Accordion + AccordionItem, header = account name + right-aligned balance,
  content = masked card number + balance.

## Color cross-reference (these are HB theme tokens — see theme_tokens.capture.json)
- `#C678D9` violet, `#56A6B2` cyan-light, `#F99551` orange-light (pie slices)
- `#234F4F` income dark-teal, `#B34852` expenses dark-red (column series)
- Chart palette default `#4263EB` indigo / `#F59F00` yellow.

## Data bindings (from portal-dashboard.tree.md / dashboard_data_infra.capture.md)
The chart + pie + accordion are bound to aggregates over the `Accounts` / transactions data. See
`dashboard_data_infra.capture.md` for the entity + aggregate wiring. The *values* above are the
live seeded sample-data values (use as V6 seed for pixel-match).

## GAP
- Exact OutSystemsCharts widget property panel (e.g. AdvancedFormat JSON the SC set in Studio) was
  not separately captured — but the **rendered Highcharts config above is the ground truth** and is
  fully sufficient to reproduce. Reproduce via the OS Charts widget's series/colors/categories +
  AdvancedFormat for per-point colors + custom tooltip. **LOW-RISK GAP.**
