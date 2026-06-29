```
=== Block: HBIcon ===
Public: True
Flow: Widgets
Inputs: Classes:Text
Events: (none)
StyleSheet: (none)

--- WIDGETS ---
[1] Placeholder 'IconName'
```

<!--
Provenance: probed via mcp__outsystems__context_search 2026-06-01.
  query="HBIcon", objects=["Blocks"], search_type="full-text"
Source app: AgentsCommonResources (assetKey=0d6e0ed8-79f8-42c2-a664-b4656db187eb,
  assetType=ReactiveLibrary).
Block key: dad9f4b3-33b0-4bda-81f9-d6b9edf2e4ee
UI flow:   Widgets (uiFlowKey=b28bdc3c-b6a3-413c-aa8d-4a4ac17f885a)

HBIcon is a single-placeholder wrapper: consumers drop their own Text/Image
widget into the IconName placeholder (see portal-dashboard widget tree —
`HBIconInstance → [IconName placeholder] → [1] ITextWidget Text="eyeshow"`).
The optional `Classes` input lets consumers append CSS classes to the wrapper.

The original Home Banking Portal (assetKey fa7ab595-...) only CONSUMES HBIcon
via cross-app reference. The block itself lives in AgentsCommonResources.
-->
