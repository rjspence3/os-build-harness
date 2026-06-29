```
=== Block: LayoutTopMenu ===
- 'LayoutWrapper': Container Style="layout layout-top" + If(HasFixedHeader, " fixed-header", "") + If(not EnableAccessibilityFeatures, ... Width=(fill parent)
  - (unnamed): Container Style="main" Width=(fill parent)
    - 'Header2': AdvancedHtml Width=(fill parent)
    - 'Content': Container Style="content" Width=(fill parent)
      - (unnamed): Link Style="skip-nav"
      - (unnamed): Container Style="header-top ThemeGrid_Container" Width=(fill parent)
      - 'MainContentWrapper': Container Style="main-content ThemeGrid_Container" Width=(fill parent)
      - (unnamed): AdvancedHtml Width=(fill parent)
        - (unnamed): Text
        - (unnamed): Container Style="header-content display-flex " Width=(fill parent)
        - 'Breadcrumbs': Placeholder Style="content-breadcrumbs placeholder-empty" Width=(fill parent)
        - (unnamed): Container Style="content-top display-flex align-items-center" Width=(fill parent)
        - 'MainContent': Placeholder Style="content-middle" Width=(fill parent)
        - 'Footer': Placeholder Style="footer ThemeGrid_Container placeholder-empty" Width=(fill parent)
          - (unnamed): WebBlockInstance
          - (unnamed): WebBlockInstance
          - 'Header': Placeholder Style="header-navigation"
          - 'Title': Placeholder Style="content-top-title heading1 placeholder-empty" Width=(fill parent)
          - 'Actions': Placeholder Style="content-top-actions placeholder-empty" Width=(fill parent)
            - (unnamed): WebBlockInstance
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 20.
PARENT of LayoutTopMenuLeftSide / LayoutTopMenuRightSide variants.
Standard OutSystemsUI top-menu layout: skip-nav link, header-top, main-content,
header-content, breadcrumbs, content-middle, footer, header-navigation.
Named placeholders: Breadcrumbs, MainContent, Footer, Header, Title, Actions.
-->
