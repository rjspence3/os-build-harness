```
=== Block: HeaderActions ===
Public: False
Flow: Common
Inputs: (none)
Events: (none)
StyleSheet: (none)

--- WIDGETS ---
[1] Container (unnamed) Style="full-height display-inline-flex align-items-center" Width="(fill parent)"
  [1.1] Container (unnamed) Style="margin-right-base"
    [1.1.1] Container (unnamed) Style="margin-right-base"
    [1.1.2] Container (unnamed) Style="circle-bg-icon margin-right-base" Width="(fill parent)"
    [1.1.3] Container (unnamed) Style="circle-bg-icon margin-right-base" Width="(fill parent)"
    [1.1.4] Container (unnamed) Style="circle-bg-icon" Width="(fill parent)"
      [1.1.4.1] WebBlockInstance (unnamed)
      [1.1.4.2] WebBlockInstance (unnamed)
      [1.1.4.3] If 'IsDarkMode' Condition="Client.IsDarkMode"
        [TRUE BRANCH]
        [1.1.4.3.T.1] WebBlockInstance (unnamed)
          PLACEHOLDER 'IconName'
            [1.1.4.3.T.1.1] Text Value="lightmode"
        [FALSE BRANCH]
        [1.1.4.3.F.1] Text Value="search"
        [1.1.4.3.F.2] WebBlockInstance (unnamed)
        [1.1.4.3.F.3] WebBlockInstance (unnamed)
          PLACEHOLDER 'IconName'
            [1.1.4.3.F.3.1] Text Value="darkmode"
```

<!--
Provenance: probed via mcp__outsystems__mentor_start (app=fa7ab595-f8cd-4140-8826-2acc484727b6).
Capture run: 2026-06-09. Method: applyModelApiCode flat-walk + depth reconstruction.
Total widgets: 26.

Flat walk → hierarchy reconstruction is BEST-EFFORT here — Mentor returned a depth-
indented flat list but the structure suggests three circle-bg-icon Containers each holding
an icon-toggle button. The If 'IsDarkMode' is the dark/light mode toggle. Icon names seen:
"search", "darkmode", "lightmode" — three header action buttons.

The two leading WebBlockInstance (unnamed) at [1.1.4.1]/[1.1.4.2] likely:
  - NotificationsBalloon (notifications bell)
  - HBIcon (search icon wrapper)
This is inference; verify before bootstrap.
-->
