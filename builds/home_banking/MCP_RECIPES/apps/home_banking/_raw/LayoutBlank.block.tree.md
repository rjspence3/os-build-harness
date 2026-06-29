```
=== Block: LayoutBlank ===
- (unnamed): Container Style="layout blank" + If(not EnableAccessibilityFeatures, "", " has-accessible-features") + If(ExtendedCl... Width=(fill parent)
  - (unnamed): Container Style="content" Width=(fill parent)
    - 'Content': Placeholder Style="main-content" Width=(fill parent)
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 3.
Truly blank layout — just wrapper + content + Content Placeholder.
Used by full-bleed pages (login, error walls, splash) where no chrome is desired.
Toggle for accessibility-features class. ExtendedClass input for ad-hoc wrapper classes.
-->
