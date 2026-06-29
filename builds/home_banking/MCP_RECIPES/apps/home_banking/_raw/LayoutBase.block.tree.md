```
=== Block: LayoutBase ===
- 'LayoutWrapper': Container Style="layout layout-blank" + If(HasFixedHeader, " fixed-header", "") + If(not EnableAccessibilityFeatures... Width=(fill parent)
  - (unnamed): Container Style="main" Width=(fill parent)
    - 'Header2': AdvancedHtml Width=(fill parent)
    - 'Content': Container Style="content" Width=(fill parent)
      - (unnamed): Link Style="skip-nav"
      - (unnamed): Container Style="header-top ThemeGrid_Container" Width=(fill parent)
      - 'MainContentWrapper': Container Style="main-content" Width=(fill parent)
        - (unnamed): Text
        - (unnamed): Container Style="header-content display-flex " Width=(fill parent)
        - 'MainContent': Placeholder Style="content-middle" Width=(fill parent)
          - (unnamed): WebBlockInstance
          - (unnamed): WebBlockInstance
          - (unnamed): WebBlockInstance
          - 'Header': Placeholder Style="header-navigation"
            - (unnamed): WebBlockInstance
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 15.
Bare layout-blank variant (no nav bar). Used by login / wakeup / invalid-permission flows.
Same skip-nav + header-top + main-content scaffold as LayoutTopMenu, minus breadcrumbs/footer/title/actions.
Named placeholders: MainContent, Header.
-->
