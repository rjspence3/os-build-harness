```
=== Block: LayoutTopMenuLeftSide ===
Public: False
Flow: Layouts
Inputs: HasFixedHeader:Boolean, EnableAccessibilityFeatures:Boolean, ExtendedClass:Text
--- WIDGETS (hierarchical) ---
[1] Container 'LayoutWrapper' Style="layout layout-top" + If(HasFixedHeader, " fixed-header", "") + If(not EnableAccessibilityFeatures, "", " has-accessible-features") + If(ExtendedClass = "", "", " " + ExtendedClass) Width="(fill parent)"
  [1.1] Placeholder 'content'
    [1.1.1] Container (unnamed) Style="main" Width="(fill parent)"
      [1.1.1.1] Placeholder 'content'
        [1.1.1.1.1] AdvancedHtml 'Header2' Width="(fill parent)"
          [1.1.1.1.1.1] Placeholder 'content'
            [1.1.1.1.1.1.1] Link (unnamed) Style="skip-nav"
              [1.1.1.1.1.1.1.1] Placeholder 'content'
                [1.1.1.1.1.1.1.1.1] Text (unnamed) Value="Skip to Content (Press Enter)"
            [1.1.1.1.1.1.2] Container (unnamed) Style="header-top ThemeGrid_Container" Width="(fill parent)"
              [1.1.1.1.1.1.2.1] Placeholder 'content'
                [1.1.1.1.1.1.2.1.1] Container (unnamed) Style="header-content display-flex " Width="(fill parent)"
                  [1.1.1.1.1.1.2.1.1.1] Placeholder 'content'
                    [1.1.1.1.1.1.2.1.1.1.1] BlockInstance (unnamed) SourceBlock="MenuIcon"
                    [1.1.1.1.1.1.2.1.1.1.2] BlockInstance (unnamed) SourceBlock="ApplicationTitle"
                    [1.1.1.1.1.1.2.1.1.1.3] Placeholder 'Header' Style="header-navigation"
                      [1.1.1.1.1.1.2.1.1.1.3.1] BlockInstance (unnamed) SourceBlock="Menu"
        [1.1.1.1.2] Container 'Content' Style="content" Width="(fill parent)"
          [1.1.1.1.2.1] Placeholder 'content'
            [1.1.1.1.2.1.1] Container 'MainContentWrapper' Style="main-content ThemeGrid_Container " + If(IsPhone(),"left-side-phone","left-side") Width="(fill parent)"
              [1.1.1.1.2.1.1.1] Placeholder 'content'
                [1.1.1.1.2.1.1.1.1] Container (unnamed) Style="display-flex" Width="(fill parent)"
                  [1.1.1.1.2.1.1.1.1.1] Placeholder 'content'
                    [1.1.1.1.2.1.1.1.1.1.1] Container (unnamed) Style="layout-left-side" Visible="If(IsPhone() or (IsTablet() and IsPortrait),False, True) " Width="40%"
                      [1.1.1.1.2.1.1.1.1.1.1.1] Placeholder 'content'
                        [1.1.1.1.2.1.1.1.1.1.1.1.1] Placeholder 'MainContent' Style="content-middle" Width="(fill parent)"
                    [1.1.1.1.2.1.1.1.1.1.2] Container (unnamed) Style="layout-right-side" Width="(fill parent)"
                      [1.1.1.1.2.1.1.1.1.1.2.1] Placeholder 'content'
                        [1.1.1.1.2.1.1.1.1.1.2.1.1] Placeholder 'SideContent' Style="content-middle" Width="(fill parent)"
            [1.1.1.1.2.1.2] AdvancedHtml (unnamed) Width="(fill parent)"
              [1.1.1.1.2.1.2.1] Placeholder 'content'
                [1.1.1.1.2.1.2.1.1] Placeholder 'Footer' Style="footer ThemeGrid_Container placeholder-empty" Width="(fill parent)"
WIDGET_LINES_TOTAL: 32
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6 (Home Banking Portal).
Capture run: 2026-06-11. Run note: Dialect-A re-capture incl. Placeholder widgets.
Method: applyModelApiCode hierarchical walk (parent-pointer attribution, numeric paths,
T/F branch segments via TrueBranch/FalseBranch reflection). Widget count emitted: 32.

ALL Placeholder widgets emitted as real [path] lines with Style values — the NAMED
placeholders Header, MainContent, SideContent, Footer plus the anonymous structural
'content' Placeholder each container exposes in the ODC model. NOTE: this block has NO
'Title' placeholder (unlike LayoutTopMenu / LayoutTopMenuRightSide) — confirmed absent
in the model walk, not a capture gap.

SourceBlock attribution resolved on all 3 BlockInstances: MenuIcon, ApplicationTitle,
Menu (supersedes the 2026-06-09 guesses of UserInfo/HeaderActions). Style values verbatim
incl. compound If(...) expressions (raw expression source follows Style=; the leading
string literal's quotes double as the attribute quotes). Visible="If(IsPhone() or
(IsTablet() and IsPortrait),False, True)" + Width="40%" on the layout-left-side container
confirm the left-side split.
-->
