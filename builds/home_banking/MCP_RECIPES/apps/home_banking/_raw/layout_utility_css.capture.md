# Layout Utility CSS — Raw Capture (from the original app)

**Source**: `https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard` live stylesheets (CDP), 2026-06-12.
**Why**: GAP 2 (Portal4 V22 turn) — the clone's Dashboard renders raw left-stacked because the original's container Style *expressions* (`If(IsDesktop(),"display-flex justify-content-space-between","display-grid gap-s")`, `... + " gap-base"`, from `portal-dashboard.tree.md`) reference utility classes that exist in the ORIGINAL theme but are ABSENT from the clone's 41KB theme (`ThemeProbe: flex=False grid=False gapBase=False`). The fix is to inject these rule bodies into the clone's theme StyleSheet (the hb-icons-font precedent). The `--space-*` vars are OutSystemsUI design tokens already present in the clone theme.

```css
.display-grid { display: grid; }
.display-flex { display: flex; }
.gap-s { gap: var(--space-s); }
.gap-base { gap: var(--space-base); }
.ThemeGrid_Container { box-sizing: border-box; margin: var(--space-none) auto; width: 100%; max-width: 1280px; padding-left: 5%; padding-right: 5%; }
.layout .main-content.ThemeGrid_Container { padding: var(--space-xl); }
.header .ThemeGrid_Container { padding: var(--space-none) var(--space-xl); }
.full-width-section .ThemeGrid_Container { padding: var(--space-none) var(--space-xl); }
```

NOTE: also seen but lower-priority (responsive variants for `.tablet`/`.phone`/`.aside-expandable`/`.layout-native`/`.layout .footer`) — capture the full set if the desktop subset doesn't fully resolve the grid.

## v2 full layout system (Portal4, 2026-06-12)

The 8-rule desktop subset above was injected (rev 41) but the Dashboard still rendered
single-left-column at runtime (CDP screenshot). Root cause: the dashboard's container
Style expressions also depend on the `.layout`/`.main`/`.main-content`/`.content-top`/
`.right-side`/`.left-side` layout-shell rules and the responsive `.tablet`/`.desktop`/
`.aside-expandable` variants — none present in the clone theme. Captured the full
108-rule layout system from the original's served stylesheets via CDP
(`/tmp/inject_css_v2.txt`, ~13KB) and injected it into Portal4's theme StyleSheet
(marker `HBPortal4 layout system v2`). The block includes every `.display-*`,
`.justify-content-*`, `.align-items-*`, `.gap-*`, `.flex-grow-*`, `.full-height*`
utility plus `.layout .main`, `.main-content.ThemeGrid_Container`, `.content-top*`,
`.full-width-section`, and the `.right-side`/`.left-side` two-column grid rules.
