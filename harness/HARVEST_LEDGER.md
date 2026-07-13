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
- **Pinned by:** test_dashboard_structure_phase_authors_kpi_card_container, test_plan_splits_dashboard_count_into_structure_aggregate_then_bind
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
