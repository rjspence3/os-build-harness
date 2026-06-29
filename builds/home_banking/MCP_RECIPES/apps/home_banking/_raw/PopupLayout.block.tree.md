```
=== Block: PopupLayout ===
- (unnamed): Container Width=(fill parent)
- 'FormRequestInfo': Form Style="form" Width=(fill parent)
- (unnamed): Container Style="margin-top-m vertical-align justify-content-space-between" Width=(fill parent)
  - (unnamed): Container Style="heading6" Width=11 col
  - (unnamed): Container Width=1 col
  - (unnamed): Container Style="margin-top-m" Width=(fill parent)
  - (unnamed): Link
  - (unnamed): Container Width=(fill parent)
    - (unnamed): Text
    - (unnamed): Link
    - (unnamed): Container Width=(fill parent)
    - (unnamed): Container Style="margin-top-s" Width=(fill parent)
    - (unnamed): Text
    - (unnamed): Butto... [TRUNCATED]
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Output truncated near tail of batched call (~29K stdout cap).
Modal/popup layout: top row with 11-col heading + 1-col close icon, content area with form,
margin-top-s + margin-top-m sections, terminal Button(s) — likely Submit/Cancel pair.
Form name: FormRequestInfo (suggests this layout backs the loan-request popup specifically,
not a generic popup chrome).
-->
