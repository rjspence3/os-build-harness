<!-- The full ODC recipe-gap list: constructs real-world specs demand that the harness cannot yet
     author first-try. Companion to CAPABILITY_MATRIX.md (the coverage grid) and GAP_CLOSURE_PLAN.md
     (the program). The discriminator here is DELIBERATE: a "gap" is only real if ODC itself CAN do the
     thing (natively, or via a Forge/external component) but the harness has no recipe. If ODC genuinely
     can't do it, it's a spec-gap/data-model rule, not a recipe backlog item. Every ODC-capability claim
     below was verified against official ODC docs (URLs inline) — NOT assumed from O11 behavior. -->

# RECIPE GAPS — recipe backlog surfaced by real specs, classified vs ODC-native capability

## Method (why the buckets matter)
A missing recipe only matters if **ODC can do the thing**. So every candidate gap is first checked
against the live ODC platform, then filed into one of three buckets:

- **B1 — ODC platform constraint (spec-gap):** ODC *cannot* represent it. No recipe fixes this; it
  becomes a data-model/normalization rule and spec-factory feedback.
- **B2 — ODC-native, no harness recipe:** ODC does it as a first-class feature; the harness just can't
  author it yet. Pure recipe backlog — closeable with recipe·spec·plan·verify, no external dependency.
- **B3 — ODC-via-Forge/external:** not native, but possible with a Forge component / external-logic
  library / external service. Carries an EXTRA dependency wall: the component must be installed to the
  tenant + referenced before any recipe can run (a `needs-human` step, per harness/CLAUDE.md fall-out).

**Do not re-file a B2/B3 item as "impossible."** The first-pass review of the source specs below
overcalled several native features (offline mobile, scheduled timers, the Email element, device
plugins, Excel parsing) as platform gaps — they are all ODC-native. Only arrays (B1) are a true limit.

**Source specs (2026-07-14 review):** Trust Banking System BRD (TBS), Credit Decisioning Screen Spec
(Credit), Lifecycle Management System BRD (LMS). These three cover three distinct failure axes:
back-office logic + batch (TBS), wizard/derived-field UX (Credit), mobile/offline/device (LMS).
**+ Agentic Pay-Code Mapping brief (PCM, 2026-07-15):** an AI-agent-in-a-loop pattern — agent proposes a
canonical match + **confidence score** + rationale per row; a deterministic guardrail (no LLM) thresholds
auto-approve vs route-to-review over a 400-row batch, fully logged. This is the FIRST source with an
agentic-loop shape, and it surfaces the agentic gaps the three BRDs missed (N1/N2 below).

---

## B0 — Binding-layer gaps (the "recipes generate blind" class) — schema-aware + rolling recipes
Surfaced end-to-end by the Wyandotte production build (2026-07-19). These are NOT missing recipes —
the recipes existed but emitted prompts that didn't match the entity SCHEMA or what PRIOR steps
actually built, because `plan_from_spec` rendered every step's params statically from the spec up
front, and the pure recipes never read the schema. Root cause + fix now landed in two layers:

- **Layer 1 — schema-aware planning (pure, in `plan_from_spec` + `prompt_recipes`):** compute correct
  params from the spec at plan time. LANDED:
  - `_mandatory_defaults()` → `create_form` defaults the entity's uncollected mandatory attributes in
    the CREATE branch (Status FK → static entity's initial record; Date → CurrDate(); Text → "") so a
    submit persists. Fixes **WALL-007** (create NO_PERSIST). Tests in test_prompt_step.py.
  - `create_form` edit-prefill now directs the record load into the aggregate's **OnAfterFetch** (not
    OnInitialize, which races the fetch and blanks mandatory fields on Update). Live-proven fix.
- **Layer 2 — rolling reconcile (`harness/reconcile.py` + `SpecDriver._reconcile_step` hook):** patch
  params against the LIVE model right before firing, so a step reflects what prior steps built. LANDED:
  - `conditional` self-heal: if the target widget (or the control its `visible_when` reads) is absent
    from the live screen, emit `ensure_widgets` bound to the form record → the recipe creates them
    instead of targeting a phantom. Fixes **WALL-003**.
  - `list-screen`: resolve a placeholder column set from live/spec entity attributes; set
    `detail_takes_id` from the detail screen's real input params. Fixes **WALL-003** nav.
  - `create-form`: refresh `mandatory_defaults` from live entity attributes.
  - `LiveModel` wraps context_entities/screens/actions defensively; unknown recipe / absent read /
    any error = safe no-op. Tests in test_reconcile.py + test_run_build.py.
  - `seed_graph`/`seed_entity` now emit TYPE-CORRECT values via `_typed_seed_value` + `_attr_types`
    (DateTime→CurrDateTime(), Date→CurrDate(), Boolean True/False unquoted, numbers unquoted, FK via
    captured Id) and flag any missing MANDATORY FK. Fixes **WALL-005** (seed).
  - `excel_import` now branches create-vs-update: the planner (`_excel_import_params`) checks whether
    the row structure can satisfy the target's mandatory create fields; if not, it emits
    `mode=bulk_update` (lookup by key → fetch-then-modify UpdateAction), and the action is Public=FALSE.
    Fixes **WALL-005** (excel).
  - `row_actions` edit now navigates to a SEPARATE edit/detail screen (passing the row Id) when one
    exists, instead of an inline same-screen assign against a record var on another screen. Fixes
    **WALL-004**. (`detail` binds display aggregates directly — read-only, no prefill race.)
- **RESIDUAL (not this class):** none of the B0 binding gaps remain open; the two-layer design
  (schema-aware planning + rolling reconcile) covers create-form, conditional, list-screen, seed,
  excel-import, row-actions. Extending reconcilers to more recipes is incremental.

## B1 — Genuine ODC platform constraints (spec-gap; no recipe can fix)

| # | Construct | Spec source | Verdict + evidence | Harness action |
|---|---|---|---|---|
| B1-1 | **Array / list-valued entity attributes** (`Seizure.EvidencePhotos Image[]`, `Person.RiskFactors Text[]`) | LMS | **NOT POSSIBLE.** ODC entity attributes are Basic types + Entity Identifier only; `List` is a variable/collection type, not an attribute type. [data_types_and_conversions](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/data_management/data_types_and_conversions/) | Add a **data-model lint** in `plan_from_spec`: fail closed on `Type[]`/`Image[]` attrs with a "promote to child entity + FK (or CSV column)" message — catches it BEFORE the first Mentor turn. Feed back to spec factory. Related: row-correlated child data (WALL-004). |

This is the **only** true platform gap in the three specs.

---

## B2 — ODC-native, but the harness has NO recipe (the real recipe backlog)

Each is a first-class ODC feature; the harness just can't author it. Closeable with no external dependency.
Priority ≈ how many of the three specs demand it.

| # | Construct | Specs | ODC-native mechanism (verified) | Matrix row today |
|---|---|---|---|---|
| B2-1 | **REST consume** | TBS, Credit, LMS (all 3) | Native — Consume REST in ODC Studio (Logic › Integrations › REST), OpenAPI import, per-stage base URL/auth. [use_rest_apis](https://success.outsystems.com/documentation/outsystems_developer_cloud/integration_with_external_systems/use_rest_apis_in_your_app/) | ✗ recipe |
| B2-2 | **Scheduled / recurrent timer** | TBS, LMS | Native — ODC Timer supports a recurrent daily/weekly schedule (not just WhenPublished), overridable per-stage. [create_and_run_timers](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/use_timers/create_and_run_timers/) | ~ (WhenPublished only) |
| B2-3 | **Excel parse → bulk insert** | TBS, Credit, LMS | Native `Excel to Record List` action → ForEach insert. (CSV is B3.) [excel_to_record_list](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/application_logic/excel_to_record_list/) | none (recipe 14 = storage only) |
| B2-4 | **If / conditional render** | Credit (conditional fields), LMS | Native If widget. | ○ doctrine only |
| B2-5 | **Expression / derived display field** | Credit (DTI, net worth, payment, risk score), TBS (fees) | Native Expression widget + SetValue. | ○ doctrine only |
| B2-6 | **Native Email** | TBS, LMS | Native Email element (delivery needs external SMTP configured in Portal — that config is the only external part). [emails](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/emails/) | none |
| B2-7 | **Offline mobile app + data sync** | LMS field app | Native — ODC builds native mobile apps with on-device SQLite, a sync framework, `OnSync`, and 5 conflict patterns. [offline_data_synchronization](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/data_management/offline_data_synchronization_in_mobile_apps/) | none. NOTE: also a VERIFY gap — `harness-capture` is a headless web browser and can't exercise a native mobile/offline app. |
| B2-8 | **Device plugins: camera / barcode-scan / GPS** | LMS mobile | Native OS-supported plugins (Camera, Barcode, Location); must be referenced into the app. [camera](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/mobile_apps/use_mobile_plugins/outsystems_supported_mobile_plugins/camera_plugin_version_2/) · [barcode](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/mobile_apps/use_mobile_plugins/outsystems_supported_mobile_plugins/barcode_plugin/) · [location](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/mobile_apps/use_mobile_plugins/outsystems_supported_mobile_plugins/location_plugin/) | none |
| B2-9 | **Web Blocks (reusable)** | LMS portals | Native Block (`CreateBlock` proven inline; no recipe). | ✗ recipe |
| B2-10 | **Settings construct** | LMS admin config | Native Settings, per-stage values in Portal. [configure_app_settings](https://success.outsystems.com/documentation/outsystems_developer_cloud/managing_outsystems_platform_and_apps/configure_app_settings/) | ✗ |
| B2-11 | **Audit-log pattern** (app data changes) | TBS, LMS | Hand-built write-on-mutate to an append-only entity. (ODC's native "Audit Trail" is platform-only — Portal/Studio/API actions — and explicitly does NOT track in-app data.) [audit_trail](https://success.outsystems.com/documentation/outsystems_developer_cloud/monitoring_and_troubleshooting_apps/audit_trail/) | none |
| B2-12 | **Per-role numeric limit / threshold gate** | TBS (authority limits), Credit (approval thresholds) | Plain logic on top of role-gate. `role-gate` today = presence-of-role only. | ~ (role-gate insufficient) |
| B2-13 | **Draft / resume + suspend/reactivate** | Credit | Plain server-side draft entity + resume load. Wizard recipe 12 is client-side StepNo only. | ~ (recipe 12 partial) |
| B2-14 | **SSN / sensitive-field masking** | Credit | Expression formatting on display. No recipe; security-relevant. | none |
| B2-15 | **Row-level org scoping** (multi-tenant data isolation) | LMS ("cannot view other orgs' data") | Query filter scoped to the caller's org. No general RLS recipe (only agent-multitenancy). | ~ |
| B2-16 | **Maker-checker breadth** | TBS (many txn types + reversal), LMS (Workflow A gates) | Covered ~ by `workflow` + workflow-engine role enforcement; not turnkey across many entities with reject/reverse. | ~ |
| B2-17 | **Agent structured / typed output** (Structure with a Decimal confidence field + rationale) | PCM (confidence-score routing) | Native — the Call Agent element has a **Structured output** tab backed by a Structure; Decimal fields supported (OpenAI structured-output spec; if an LLM ignores numeric min/max, fall back to Text/JSON + parse). The harness `agent` recipe emits a **Text-only** `Response` — no structured output. [structured_output](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/build_ai_powered_apps/agentic_apps_in_odc/structured_output/) | ~ (agent recipe = Text only) |
| B2-18 | **Batch agentic orchestration** (chunked, idempotent Timer loop calling an agent per row) | PCM (400-row batch) | Native documented pattern, but timeout-bound: client server-request max **60s**, BPT automatic activity **300s** hard cap, Timer **≤30min** + auto-retry (must be idempotent) — so loop async in a chunked Timer, NOT synchronously. No recipe. NB: the `agent` recipe hardcodes `ServerRequestTimeout=120`, which exceeds the 60s client max — review. [dealing_with_timeouts](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/build_ai_powered_apps/agentic_apps_in_odc/dealing_with_timeouts_on_ai_agent_calls/) · [long_server_requests](https://success.outsystems.com/documentation/outsystems_developer_cloud/monitoring_and_troubleshooting_apps/manage_technical_debt_in_odc/performance_findings/long_server_requests_timeout/) | ○ (matrix: ServerRequestTimeout doctrine-only) |
| B2-19 | **Deterministic guardrail / decision logic** (threshold routing, no LLM) | PCM (auto-approve vs review) | Native — authored as a Server Action with If/Switch/Assign. ODC has **no** native decision-table/DMN construct; the workflow Decision node branches a process only; RulesEspresso is Forge. Buildable today via `service-action`+If (~); no dedicated recipe. **Minor / low priority.** [workflows_in_odc](https://success.outsystems.com/documentation/outsystems_developer_cloud/building_apps/about_business_processes/workflows_in_odc/) | ~ (covered by service-action+If) |

**Highest leverage (native, no Forge dep, demanded by 2–3 specs):** B2-1 REST-consume, B2-2 scheduled-timer,
B2-3 Excel-parse, B2-4/B2-5 If + Expression. **Agentic-demo-critical (PCM):** B2-17 structured agent output +
B2-18 batch agentic loop — the harness can author *an* agent but not one that returns a confidence score or
runs safely over a batch.

---

## B3 — ODC-via-Forge / external component (recipe gap + tenant-install dependency)

Not native. Each needs a component installed to the tenant + referenced BEFORE a recipe can run — log
that as a `needs-human` wall (per harness/CLAUDE.md fall-out pattern), not pure recipe work.

| # | Construct | Specs | Path |
|---|---|---|---|
| B3-1 | **Editable Data Grid** (inline add/edit rows) | Credit (Assets & Liabilities table) | Forge "OutSystems Data Grid (ODC)" (Mescius/Wijmo). Native OS-UI Table/List are read-only. |
| B3-2 | **Maps / heatmap** | LMS (Command Dashboard) | Forge "OutSystems Maps (ODC)" — Google/Leaflet, bring-your-own API key. (Heatmap layer: high-confidence, confirm in-product.) |
| B3-3 | **PDF / letter generation** | TBS (statements), Credit (offer/decline letters) | Forge "Ultimate PDF (ODC)" (Chromium render of a token-protected screen). |
| B3-4 | **QR / barcode image GENERATION** | LMS (`Asset.SystemBarcode`) | Forge external-logic lib (QRCoder). Distinct from B2-8 barcode SCAN (native plugin). |
| B3-5 | **CSV parse** | bulk uploads where source is CSV not Excel | Forge CsvToolkit. (Excel path is native — B2-3.) |
| B3-6 | **SMS** | LMS (alerts) | External provider (Twilio etc.) via REST — never native on any OutSystems product. |

---

## Dropped — not an app-recipe concern

- **Session / idle timeout** (Credit/TBS/LMS "15-min timeout") — ODC platform per-stage Portal setting,
  shared SSO context; not app-authored. [configure_user_session](https://success.outsystems.com/documentation/outsystems_developer_cloud/user_management/configure_user_session/)

## Unconfirmed caveats (don't treat as settled; confirm in-product if load-bearing)
- Timer **interval floor / cron granularity** limits (recurrent daily/weekly is confirmed; finer cron is not).
- Whether **Settings** can be WRITTEN at runtime via logic (likely read-only).
- **Maps heatmap** layer and the verbatim array-attribute denial (high-confidence, not single-sentence quotable).

---

## Appendix — prior catalog-vs-capability gap pass (pre-M1, retained for reference)

_This earlier analysis graded the recipe CATALOG (NEW/FIX/HARDEN) rather than spec-demanded
constructs. Some items (e.g. the chart FIX) are since resolved; kept for the P1 backlog it captures._


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
