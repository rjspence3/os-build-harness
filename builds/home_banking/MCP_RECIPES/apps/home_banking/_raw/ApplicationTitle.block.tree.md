```
=== Block: ApplicationTitle ===
Public: False
Flow: Common
Inputs: (none)
Events: (none)
StyleSheet: (none)

--- WIDGETS ---
[1] Container 'ApplicationTitleWrapper' Style="application-name display-flex align-items-center full-height" Width="(fill parent)"
  [1.1] WebBlockInstance (unnamed)
  [1.2] Expression (unnamed) Style="font-semi-bold margin-left-base"
  [1.3] BlockInstance (HBIcon)
    PLACEHOLDER 'IconName'
      [1.3.1] Text Style="heading4" Value="homebankinglogo"
```

<!--
Provenance: probed via mcp__outsystems__mentor_start (app=fa7ab595-f8cd-4140-8826-2acc484727b6).
Capture run: 2026-06-09. Method: applyModelApiCode walking IMobileBlock descendants.
Total widgets: 6.

Note: Flat-walk to hierarchy reconstructed from depth indentation in stdout.
The two `WebBlockInstance (unnamed)` likely resolve to HBIcon (the logo wrapper) per
portal-confirmation.tree.md naming pattern (homebankinglogo Text inside HBIcon placeholder).
Expression at [1.2] likely renders the app name from a Site Property.
-->
