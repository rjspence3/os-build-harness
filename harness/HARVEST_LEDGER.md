# Harvest ledger — harness self-improvement

Auto-rendered from `harvest_ledger.jsonl` (see `harness/learning.py`). Each entry is a
gap the AI took over to fill, harvested into a harness change + a pinning test.

## 1. theme-outsystemsui-reset  _(landed)_
- **Trigger:** Hand-applied the theme to RivianReviewerPortal, but nav-item links rendered default blue + underlined.
- **Evidence:** Live DOM (browser_evaluate): the .nav-item DIV carried its class, but its inner <a> had class='' color=rgb(0,0,238) text-decoration=underline, and NO '.nav-item a' rule existed in the loaded stylesheets.
- **Root cause:** The theme recipe applied the design CSS but never reset OutSystemsUI's default link styling, so styled .nav-item Containers still showed browser/OSUI-default links.
- **Harness change:** harness/prompt_recipes.py: THEME_RESET_CSS is now PREPENDED to every theme stylesheet ('.nav-item a{color:inherit;text-decoration:none}' etc.), so the UI class contract wins.
- **Pinned by:** test_theme_includes_outsystemsui_reset
- **Memory:** theme-recipe-must-reset-outsystemsui-link-defaults

## 2. dashboard-kpi-card-structure  _(landed)_
- **Trigger:** KPI values on RivianReviewerPortal rendered as bare numbers with no card chrome.
- **Evidence:** Live DOM: ZERO '.kpi-card' elements; '.kpi-value' existed with an empty parent class; the theme DID have a '.kpi-card' rule — so the container was never authored.
- **Root cause:** The phased dashboard path emitted aggregate + bind but no STRUCTURE step; the bind turn was told 'do not add widgets', so the .kpi-card Container was never created.
- **Harness change:** harness/prompt_recipes.py: added dashboard phase='structure' (authors the .kpi-card containers + placeholder value/label/icon); plan_from_spec now emits structure->aggregate->bind for COUNT cards.
- **Pinned by:** test_dashboard_structure_phase_authors_kpi_card_container, test_plan_dashboard_count_order_is_aggregate_structure_bind
- **Memory:** dashboard-phased-path-needs-structure-step

## 3. corruption-wedge-broaden  _(landed)_
- **Trigger:** QualifyWorkflow and the portal send-back button ground through in-place retries and cascaded (workflow exhausted 3 attempts; the portal resume then failed on step 1) instead of halting to rebuild fresh.
- **Evidence:** Live build 2026-07-12: QualifyWorkflow app-reference:rivianonboardingcore failed OS-BEW-50000 (exhausted 3 attempts, state DB); RivianReviewerPortal send-back:wire failed OS-APPS-40028 'Input binary does not contain a valid OML', after which the corruption cascade broke the resume at step 1.
- **Root cause:** _drive_step's halt-fast-on-wedge guard only matched 'OS-BEW-COMP', so OS-BEW-50000 and OS-APPS-40028 fell through to endless in-place retries that deepen OML corruption.
- **Harness change:** harness/run_build.py: _CORRUPTION_MARKERS + _is_corruption_wedge() now cover OS-BEW-COMP, OS-BEW-50000, OS-APPS-40028, 'invalid OML'; _drive_step halts-fast after 2 with rebuild-fresh guidance (message 'OML-WEDGED').
- **Pinned by:** test_os_bew_50000_crash_halts_fast_with_rebuild_fresh_guidance, test_invalid_oml_40028_halts_fast_with_rebuild_fresh_guidance, test_os_bew_comp_crash_halts_fast_with_rebuild_fresh_guidance
- **Memory:** corruption-wedge-rebuild-fresh

## 4. session-reuse-verified  _(landed)_
- **Trigger:** Was about to build session-reuse (per the 'harness leaks a session per step' memory + handoff) to kill the cap grind.
- **Evidence:** State DB of the live RivianReviewerPortal build: 12 succeeded steps ran on only 3 distinct session_ids — steps 2-10 (nine steps) shared ONE session via fresh_context. SpecDriver._attempt_step already resumes with fresh_context.
- **Root cause:** No harness gap — session-reuse was already implemented (SpecDriver, reuse_session default True) and already tested. The memory + handoff claiming one-session-per-step were STALE and would have led to redundant work.
- **Harness change:** No code change (verified already-implemented by evidence). Corrected the stale 'harness-leaks-mentor-session-per-step' memory. The behavior is guarded by the existing test.
- **Pinned by:** test_session_is_reused_across_steps_not_one_per_step
- **Memory:** harness-leaks-mentor-session-per-step

## 5. chart-native-widget  _(landed)_
- **Trigger:** The chart recipe supported only Column/Pie and told Mentor to addReferenceToElements an OutSystemsCharts block.
- **Evidence:** ODC docs research (charts_extensibility, Highcharts 12.5.0) + live-app probe: ODC charts are NATIVE toolbox widgets, NOT a referenced OutSystemsCharts block (that is O11 framing). ODC ships exactly 7: Area/Bar/Column/Line/Pie/Donut/Radar.
- **Root cause:** The recipe carried the O11/monorepo mental model (ReferenceWebBlock Charts\ColumnChart), which misfires in ODC, and only covered 2 of the 7 widget types.
- **Harness change:** harness/prompt_recipes.py: chart recipe rewritten — native-widget framing (no reference), validates chart_type against the 7 ODC types, per-type props (StackingType/Spline/InnerSize/SeriesType/inverted), ChartX/YAxis+Legend+SeriesStyling addons, and a SetHighcharts*Configs escape hatch for gauge/scatter/etc.
- **Pinned by:** test_chart_recipe_is_native_widget_not_a_reference_block, test_chart_recipe_supports_all_seven_odc_types, test_chart_recipe_advanced_escape_hatch
- **Memory:** odc-charts-are-native-widgets

## 6. structure-drop-harden-cells  _(landed)_
- **Trigger:** Rivian portal UI read as bare/unmodern; status chips and review cards rendered as loose text.
- **Evidence:** Live DOM (harvest #2) proved Mentor authors the value and DROPS the styled Container (.kpi-card had zero elements). The same failure mode applies to list-screen chip/avatar cells and detail review cards.
- **Root cause:** The cell/review-card prompts said 'inside a Container' but did not FORCE it, so Mentor dropped the container and the value rendered bare.
- **Harness change:** harness/prompt_recipes.py: _cell_instruction (chip/badge/tag) and detail review-grid now state the Container is REQUIRED (without it the value renders bare — live-proven) — the harvest-#2 hardening extended to list cells + review cards. Plus NEW top-bar + page-header recipes for the missing app-shell chrome.
- **Pinned by:** test_list_and_detail_cells_forbid_structure_drop, test_top_bar_authors_shell_header_as_shared_block, test_page_header_composes_title_tag_and_action_row
- **Memory:** dashboard-phased-path-needs-structure-step

## 7. ui-shell-auto-emission  _(landed)_
- **Trigger:** top-bar and page-header recipes existed but a spec author had to call them by name — builds didn't get the app-shell for free.
- **Evidence:** plan_from_spec emitted nav-block/place-nav from app.navigation but nothing emitted top-bar or page-header, so every spec-driven build shipped without the shell chrome (the Rivian 'bare' UI).
- **Root cause:** No pipeline emission for the new shell recipes; the emitter only knew nav/dashboard/detail/dynamicForm.
- **Harness change:** harness/prompt_recipes.py plan_from_spec: emit `top-bar` for free whenever a sidebar exists (navigation.topBar, disable with false) placed on all screens, and `page-header` per screen that declares screen.header. Schema: navigation.topBar + screen.header added to app_spec.v0.json.
- **Pinned by:** test_plan_auto_emits_top_bar_when_nav_exists, test_plan_top_bar_disabled_by_false, test_plan_emits_page_header_from_screen_header
- **Memory:** —

## 8. dashboard-aggregate-order-before-structure  _(landed)_
- **Trigger:** Harvest #2's structure-first order was hypothesized to cause the dashboard aggregate OS-BEW-COMP crash.
- **Evidence:** DISPROVEN by RivianReviewerPortal5: with the reorder to aggregate-FIRST (aggregate on a clean screen, step 5), the aggregate step STILL crashed OS-BEW-COMP-50008. So the crash is NOT caused by the structure-first ordering. The reorder is retained (aggregate-first matches the old working order and is the safe direction) but it does NOT fix the crash.
- **Root cause:** UNRESOLVED. The dashboard COUNT-aggregate step crashes the ODC compiler (OS-BEW-COMP-50008, opaque — no per-element detail) deterministically on the new portal builds (3/4/5) but the OLD portal (no top-bar recipe) compiled the same aggregates fine. Leading suspect: the new top-bar block placed on the dashboard, but UNCONFIRMED (nav-block is also a placed block and did not crash). Needs an isolation build (navigation.topBar:false) to confirm.
- **Harness change:** harness/prompt_recipes.py plan_from_spec: dashboard phased emission ordered aggregate -> structure -> bind (harmless/reasonable, aggregate-first). NOTE: this did NOT resolve the OS-BEW-COMP crash — that root cause is still open.
- **Pinned by:** test_plan_dashboard_count_order_is_aggregate_structure_bind
- **Memory:** dashboard-phased-path-needs-structure-step

## 9. data-model-idempotent-no-duplicate-entities  _(landed)_
- **Trigger:** Fresh portal builds crashed OS-BEW-COMP-50008 at the dashboard aggregate; I wrongly chased the aggregate/ordering (harvest 8) for 3 builds. Root cause was elsewhere.
- **Evidence:** context_entities on RivianOnboardingCore showed 7 DUPLICATE pairs (Supplier+Supplier2, QualificationCase+QualificationCase2, ...): originals private w/ CRUD + real data, '2' versions public read-only + orphaned. Mentor (asked to diagnose, read-only) confirmed: the consumer references the PRIVATE originals -> illegal cross-app dependency -> the build engine rejects it at compile time with OS-BEW-COMP-50008 (the aggregate was a red herring).
- **Root cause:** The data_model recipe says 'CREATE these entities + set Public=Yes' with NO idempotency guard. When build_system reused an existing Core and re-ran the data-model step (public=True), Mentor created NEW public copies ('<Name>2', ODC's name-collision auto-suffix) instead of flipping the existing private originals -> duplicate entities; consumers reference the private originals and crash.
- **Harness change:** harness/prompt_recipes.py data_model: added an IDEMPOTENT clause (look up each entity by name; UPDATE in place if it exists, never create a duplicate; never let ODC auto-suffix to '<Name>2') and made the public exposure flip the EXISTING/ORIGINAL entity (not create a public copy).
- **Pinned by:** test_data_model_is_idempotent_no_duplicate_entities
- **Memory:** data-model-recipe-must-be-idempotent
