```
=== Block: LayoutSideMenu ===
- 'LayoutWrapper': Container Style="layout layout-side" + If(HasFixedHeader, " fixed-header", "") + " " + MenuBehavior + If(not EnableA... Width=(fill parent)
  - (unnamed): Link Style="skip-nav"
  - (unnamed): AdvancedHtml Width=(fill parent)
  - (unnamed): Container Style="main" Width=(fill parent)
    - (unnamed): Text
    - 'Navigation': Placeholder Width=(fill parent)
    - 'Header3': AdvancedHtml Width=(fill parent)
    - 'Content': Container Style="content" Width=(fill parent)
      - (unnamed): WebBlockInstance
      - (unnamed): Container Style="header-top ThemeGrid_Container" Width=(fill parent)
      - 'MainContentWrapper': Container Style="main-content ThemeGrid_Container" Width=(fill parent)
      - (unnamed): AdvancedHtml Width=(fill parent)
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
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 22.
Side-nav layout variant. layout-side wrapper, MenuBehavior input controls collapsed/expanded.
Has dedicated Navigation Placeholder for the side menu.
Same Footer/Header/Title/Actions/Breadcrumbs/MainContent shape as LayoutTopMenu.
-->
