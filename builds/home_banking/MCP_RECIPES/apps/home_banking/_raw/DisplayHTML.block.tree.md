```
=== Block: DisplayHTML ===
- (unnamed): If
  - (unnamed): IfBranch
  - (unnamed): IfBranch
  - 'DummyText': Text
  - (unnamed): WebBlockInstance
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 5.
Tiny utility block. Renders raw HTML at runtime via a WebBlockInstance (likely an
AdvancedHTML or CustomHTML sub-block). Has a DummyText named Text that's used during
preview/empty states. If branch likely guards on input != "".
-->
