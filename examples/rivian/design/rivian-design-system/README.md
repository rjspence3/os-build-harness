# Rivian Supplier & Parts Onboarding — Design System

Design layer for the ODC production build, generated in-terminal by `/design-layer` and **mined from the
staged reference** `../Supplier Onboarding.dc.html` + `../screenshots/`. This is the pixel source-of-truth
and the ODC `theme.StyleSheet` payload.

## Design language
- **Dark enterprise theme**, near-black canvas (`--bg #0c0e0c`), panels `#131612`. Rivian **yellow `#ffd329`**
  accent for active nav, tier tags, and the primary CTA. Feedback: green `#7fce8f` / amber `#f0b657` /
  red `#ef7d6b` / blue `#79b0e6`.
- **Type**: IBM Plex Sans (body), Space Grotesk (headings/KPI values), JetBrains Mono (tags, ids, labels).
- **App-shell sidebar** on every screen: RIVIAN brand + subtitle, OPERATIONS/SUPPLIER sections, nav items
  with mono 3-letter tag chips (DSH/QUE/CSE/SCR/PRT/INT) + count badges, yellow active left-border, user footer.
- **Status system**: tier tags (`T1 · CRITICAL` yellow, `T2 · STANDARD` muted), state chips/badges keyed to
  the value (`chip chip-<value>`), SLA badges. **Case Detail** = the workflow made visual: horizontal stage
  stepper + parallel functional-review grid + audit timeline.

## Contents
```
tokens/tokens.css   # :root tokens + @font-face + the full component-class contract (the theme payload)
tokens/tokens.ts    # tokens as TS objects; statusColor/tierColor keyed to the spec's data
src/components/*.tsx # SidebarNav, KpiCard/KpiRow, StatusChip/TierTag, StageStepper/ReviewGrid, CaseRow
mockups/*.html      # case-queue, case-detail — standalone, double-clickable; the pixel target
```

## ODC consumption
- Apply `tokens/tokens.css` via `theme.StyleSheet` (full CSS surface).
- Load fonts via `@font-face` from the fontsource CDN — ODC **strips `@import`** on publish (already `@font-face`).
- Fight OutSystemsUI specificity with the theme CSS vars / inline styles where classes don't take.
- The recipes emit STRUCTURE + the stable class hooks (`.app-sidebar .nav-item .nav-tag .nav-badge .chip
  .chip-<v> .tag .badge .avatar .kpi-card .kpi-value .stepper .step.is-* .review-grid .timeline`); the theme
  paints them — keep the two in lockstep.

## Frontier caveats (not gating)
- Cmd-K palette, real-time/presence, animated route transitions are ODC-platform ceilings — match the static look.

Reference: `../Supplier Onboarding.dc.html`, `../screenshots/{case,queue,q3,q4,q5}.png`.
