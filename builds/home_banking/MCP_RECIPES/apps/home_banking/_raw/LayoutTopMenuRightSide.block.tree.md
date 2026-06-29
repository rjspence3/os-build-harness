```
=== Block: LayoutTopMenuRightSide ===
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
                    [1.1.1.1.1.1.2.1.1.1.2] If (unnamed) Condition="not IsPhone()"
                      [1.1.1.1.1.1.2.1.1.1.2.T.1] BlockInstance (unnamed) SourceBlock="ApplicationTitle"
                      [1.1.1.1.1.1.2.1.1.1.2.F.1] Container (unnamed) Style="display-flex align-items-center" CustomStyle="text-align: left;" Width="(fill parent)"
                        [1.1.1.1.1.1.2.1.1.1.2.F.1.1] Placeholder 'content'
                          [1.1.1.1.1.1.2.1.1.1.2.F.1.1.1] BlockInstance (unnamed) SourceBlock="HBIcon"
                            [1.1.1.1.1.1.2.1.1.1.2.F.1.1.1.1] Placeholder 'IconName'
                              [1.1.1.1.1.1.2.1.1.1.2.F.1.1.1.1.1] Text (unnamed) Value="homebankinglogo" Style="heading4"
                    [1.1.1.1.1.1.2.1.1.1.3] If (unnamed) Condition="not(IsPhone() or IsTablet())"
                      [1.1.1.1.1.1.2.1.1.1.3.F.1] Container (unnamed) Style="flex-grow-1 text-align-right" Width="(fill parent)"
                        [1.1.1.1.1.1.2.1.1.1.3.F.1.1] Placeholder 'content'
                          [1.1.1.1.1.1.2.1.1.1.3.F.1.1.1] BlockInstance (unnamed) SourceBlock="HeaderActions"
                    [1.1.1.1.1.1.2.1.1.1.4] Placeholder 'Header' Style="header-navigation"
                      [1.1.1.1.1.1.2.1.1.1.4.1] BlockInstance (unnamed) SourceBlock="Menu"
        [1.1.1.1.2] Container 'Content' Style="content" Width="(fill parent)"
          [1.1.1.1.2.1] Placeholder 'content'
            [1.1.1.1.2.1.1] Container 'MainContentWrapper' Style="main-content ThemeGrid_Container " + If(IsPhone(), "right-side-phone","right-side")+ If(IsPhone() or IsTablet(), ""," display-flex") Width="(fill parent)"
              [1.1.1.1.2.1.1.1] Placeholder 'content'
                [1.1.1.1.2.1.1.1.1] Container (unnamed)
                  [1.1.1.1.2.1.1.1.1.1] Placeholder 'content'
                    [1.1.1.1.2.1.1.1.1.1.1] Container (unnamed) Style="layout-left-side" Width="(fill parent)"
                      [1.1.1.1.2.1.1.1.1.1.1.1] Placeholder 'content'
                        [1.1.1.1.2.1.1.1.1.1.1.1.1] Container (unnamed) Style="content-top align-items-center margin-bottom-xl" Width="(fill parent)"
                          [1.1.1.1.2.1.1.1.1.1.1.1.1.1] Placeholder 'content'
                            [1.1.1.1.2.1.1.1.1.1.1.1.1.1.1] Placeholder 'Title' Style="font-size-base font-semi-bold placeholder-empty" Width="(fill parent)"
                        [1.1.1.1.2.1.1.1.1.1.1.1.2] Placeholder 'MainContent' Style="content-middle" Width="(fill parent)"
                [1.1.1.1.2.1.1.1.2] Container (unnamed)
                  [1.1.1.1.2.1.1.1.2.1] Placeholder 'content'
                    [1.1.1.1.2.1.1.1.2.1.1] Container (unnamed) Style="layout-right-side " + If(IsPhone(), "right-side-padding-phone","right-side-padding") Width="(fill parent)"
                      [1.1.1.1.2.1.1.1.2.1.1.1] Placeholder 'content'
                        [1.1.1.1.2.1.1.1.2.1.1.1.1] Placeholder 'SideContent' Style="content-middle" Width="(fill parent)"
            [1.1.1.1.2.1.2] AdvancedHtml (unnamed) Width="(fill parent)"
              [1.1.1.1.2.1.2.1] Placeholder 'content'
                [1.1.1.1.2.1.2.1.1] Placeholder 'Footer' Style="footer ThemeGrid_Container placeholder-empty" Width="(fill parent)"
WIDGET_LINES_TOTAL: 47
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6 (Home Banking Portal).
Capture run: 2026-06-11. Run note: Dialect-A re-capture incl. Placeholder widgets.
Method: applyModelApiCode hierarchical walk (parent-pointer attribution, numeric paths,
T/F branch segments via TrueBranch/FalseBranch reflection). Widget count emitted: 47.

ALL Placeholder widgets emitted as real [path] lines with Style values — including the
5 NAMED placeholders (Footer, Header, MainContent, SideContent, Title) and the anonymous
structural 'content' Placeholder each container/block exposes in the ODC model, plus the
'IconName' placeholder of the HBIcon instance.

SourceBlock attribution resolved on all 5 BlockInstances: MenuIcon, ApplicationTitle,
HBIcon, HeaderActions, Menu. Style values verbatim incl. compound If(...) expressions
(raw expression source follows Style=; the leading string
literal's quotes double as the attribute quotes).

Mirror of LayoutTopMenuLeftSide — main content lands on the RIGHT side, sidebar on the
LEFT. "right-side" / "right-side-padding" CSS markers tell the layout to flip.
-->
