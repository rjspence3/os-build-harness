# Recipe gap analysis — ODC capabilities vs. the recipe catalog

Sourced from the official ODC docs (`outsystems/docs-odc`, success.outsystems.com) + live-app
ground truth in this repo (2026-07). Current catalog = 35 recipes. Gaps below are grouped and
prioritized; each names the ODC capability, why it's a gap, and what a recipe must author.

Legend: **NEW** = no recipe · **FIX** = existing recipe is wrong/incomplete · **HARDEN** = works
but drops structure at runtime (the harvest-#2 class).

## P0 — bugs + the highest-visibility UI gaps

### 1. `chart` — FIX + EXPAND
- **Bug:** the recipe tells Mentor to `addReferenceToElements` an `OutSystemsCharts` block. In ODC
  charts are **native toolbox widgets** — there is no reference block. This is O11/monorepo framing
  and misfires in ODC. Remove the reference step.
- **Incomplete:** supports only Column + Pie. ODC ships **7 widgets**: Area, Bar, Column, Line, Pie,
  Donut, Radar. Add the 5. All share the same wiring: `DataPointList` of DataPoint{`Label`,`Value`} +
  `SeriesName`; bind an **aggregate** (inline `DataPoint`/`ListAppend` throws over MCP).
- **Per-type props:** Area→`StackingType`; Line→`Spline`+`Marker`; Donut→`InnerSize`; Radar→per-series
  `SeriesType`; Bar→inverted axes. **Addons:** `ChartXAxis`/`ChartYAxis`/`ChartLegend`(Position/Layout,
  delete-to-remove)/`ChartSeriesStyling`(SeriesName/ShowDataPointValues/SeriesType/Marker).
- **Escape hatch:** `SetHighcharts{Chart,XAxis,YAxis,Series}Configs` for anything beyond the 7
  (gauge/scatter/bubble/waterfall/boxplot/…) — an "advanced chart" path.

### 2. `top-bar` — NEW (biggest Rivian "modern" gap)
- Every mockup screen has an app-shell top bar: breadcrumb (`App / Screen`) + env chip (`ODC · PROD`,
  `.env-chip`) + a primary CTA (`.btn-primary`). The harness builds the sidebar (`nav-block`) but
  nothing builds this band, so every screen reads as unfinished. Author as a shared Web Block placed
  above the content area (like `nav-block`), classes `.app-topbar`/`.breadcrumb`/`.env-chip`.

### 3. `page-header` — NEW
- A screen's lead block: title + subtitle + status/tier `tag` + a right-aligned **action-button row**.
  Composes `action-button`s into one header (mockup: "Acme Drivetrains — Regen Brake Module  T1·CRITICAL"
  + Approve/Send Back/Activate). Today only individual `action-button`s exist.

### 4. list-screen cells + detail review-grid — HARDEN (the "bare UI" cause)
- Same failure mode as harvest #2 (dashboard-kpi-card): the recipe asks for a styled Container
  (chip/avatar/tier-tag cell, review-card) but Mentor authors the value and **drops the container**,
  so it renders bare. Apply the harvest-#2 pattern: force the container as its own structural unit +
  verify it post-author (a screen-walk assertion that `.chip`/`.avatar`/`.review-card` elements exist).

## P1 — the integration gap the user named

### 5. `rest-consume` — NEW
- ODC: Logic→Integrations→Consume REST API. Two modes: **import OpenAPI** (URL/file, all-or-selected
  methods, auto-gen Request/Response Structures) OR **add single method** (verb + URL w/ `{path}` params,
  paste JSON to gen structures). **Auth via `OnBeforeRequest`** header injection (Bearer/API-key);
  **secrets = Settings with `Is Secret=Yes`**, values set per-stage in the ODC Portal (no `GetSecret()`
  builtin — read the Setting). **Errors:** ≥400 throws; `OnAfterResponse` to mutate/suppress. **Limit:
  60s method timeout, 28.6MB upload.** Per-stage base URL config lives in the Portal, not Studio.

### 6. `rest-expose` — NEW
- Expose REST API (name **includes version**, e.g. `v1`) → add methods (verb + descriptive name) →
  implement as an action flow; input/output params become the contract. **`Receive In` = URL vs Body**;
  path params mandatory + in the URL Path; non-path URL inputs → query string. URL:
  `https://<server>/<App>/rest/<Api>/<Method>`. **Auth None/Basic/Custom** (Custom = `OnAuthentication`
  callback validating the bearer); default `None` is flagged tech-debt → recipe defaults to Basic/Custom.
  Custom status via HTTP extension `Response_SetStatusCode`.

## P2 — form + input palette (create-form/dynamic-form only cover plain inputs)

### 7. `wizard` — NEW (first-class ODC pattern)
- Multi-step form. State-driven: a `CurrentStep` variable + Next/Previous visibility guards
  (`CurrentStep < N` / `> 1`). Emit the scaffolding, not just a widget.
### 8. `master-detail` — NEW (first-class Adaptive pattern)
- List + detail split; browse+edit without leaving the list.
### 9. `data-grid` (editable / inline-edit) — NEW
- ODC's inline-edit story (the plain Table is read-only). `AllowColumnEdit=True`; save loop =
  `GetChangedLines`→`JSONDeserialize`→server action updating each edited row.
### 10. rich inputs — NEW/EXTEND create-form
- `Dropdown Search` (typeahead), `Dropdown Tags` (multi-select chips), `Date Picker`/Range/Month,
  `Range Slider Interval`, `Animated Label` (float-label), `Upload` (file/binary; 28.6MB cap).
### 11. `input-validation` — EXTEND
- Add the ODC pattern: `Form.Valid` gate; **`setWidgetAsInvalid(widgetId,msg)`/`isWidgetValid`** JS API
  (the ONLY path for widgets inside loops/iterators — a common miss); `showFeedbackMessage(msg,type)`
  toast on save (type 0=Info/1=Success/2=Warning/3=Error, a magic number).

## P3 — modern UI components (raise the "clean/modern" ceiling)

### 12. `tabs` · 13. `accordion` · 14. `cards`/card-gallery · 15. `sidebar`/modal · 16. `notification`/feedback-toast · 17. `carousel` · 18. `progress-bar`
- All first-class ODC patterns with no recipe. `notification`/feedback (`NotificationOpen/Close`,
  `showFeedbackMessage`) is small + high-value (every save/error needs it). `cards`/card-gallery
  generalizes the KPI-card chrome. `tabs`/`accordion` densify detail screens.

## Known ODC gaps (NOT recipe-fixable — Forge/custom, flag as spec walls)
Rich-text editor, star rating, input masks/currency formatting, drag-drop upload zone, dedicated
time-only picker — **not first-class in ODC**; a spec asking for these = Forge dependency or custom.

## Doc sources
`github.com/outsystems/docs-odc` — `building-apps/ui/patterns/*`, `integration-with-systems/{consume,expose}_rest/*`,
`security/set-as-secret.md`, `reference/apis/javascript/{validation,feedbackmessage}.md`; charts:
`.../user_interface/charts_extensibility/*` (Highcharts 12.5.0); limits: `getting-started/system-requirements.md`.
