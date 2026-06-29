```
=== Block: LayoutTopMenuLeftSideWithBanner ===
- 'LayoutWrapper': Container Style="layout layout-top" + If(HasFixedHeader, " fixed-header", "") + If(not EnableAccessibilityFeatures, ... Width=(fill parent)
  - (unnamed): Container Style="main" Width=(fill parent)
    - 'Header2': AdvancedHtml Width=(fill parent)
    - (unnamed): Container Style="banner-wrapper" Width=(fill parent)
    - 'Content': Container Style="content" Width=(fill parent)
      - (unnamed): Link Style="skip-nav"
      - (unnamed): Container Style="header-top ThemeGrid_Container" Width=(fill parent)
      - (unnamed): Container Style="ThemeGrid_Container" Width=(fill parent)
      - 'MainContentWrapper': Container Style="main-content ThemeGrid_Container " + If(IsPhone(),"left-side-phone","left-side") Width=(fill parent)
      - (unnamed): AdvancedHtml Width=(fill parent)
        - (unnamed): Text
        - (unnamed): Container Style="header-content display-flex " Width=(fill parent)
        - 'BannerContent': Placeholder Width=(fill parent)
        - (unnamed): Container Style="display-flex" Width=(fill parent)
        - 'Footer': Placeholder Style="footer ThemeGrid_Container placeholder-empty" Width=(fill parent)
          - (unnamed): WebBlockInstance
          - (unnamed): WebBlockInstance
          - 'Header': Placeholder Style="header-navigation"
          - (unnamed): Container Style="layout-left-side" Width=40%
          - (unnamed): Container Style="layout-right-side" Width=(fill parent)
            - (unnamed): WebBlockInstance
            - 'MainContent': Placeholder Style="content-middle" Width=(fill parent)
            - 'SideContent': Placeholder Style="content-middle" Width=(fill parent)
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 23.
LeftSide variant with a banner-wrapper inserted between Header2 and Content.
Named BannerContent Placeholder for the hero banner content slot.
Layout: 40% left-side + fill-parent right-side.
-->
