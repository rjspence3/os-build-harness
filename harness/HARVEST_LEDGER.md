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
