```
=== Block: DocumentItem ===
- (unnamed): Container Style="document-item " + If(FileStructure.ValidationProgressId = Entities.ValidationProgress.Validating, "... Width=(fill parent)
  - 'Validated': If
    - (unnamed): IfBranch
    - (unnamed): IfBranch
    - (unnamed): Container Style="display-flex flex-1 justify-content-space-between align-items-center full-width gap-s" Width=(fill parent)
    - (unnamed): Container Style="vertical-align full-width" Width=(fill parent)
      - (unnamed): Container Style="min-width-0" Width=(fill parent)
      - (unnamed): Container Style="display-flex gap-xs" Width=(fill parent)
      - (unnamed): WebBlockInstance
      - (unnamed): Text Style="white-space-nowrap"
      - (unnamed): Expression Style="loading-ellipsis"
        - (unnamed): Container Style="text-ellipsis" Width=(fill parent)
        - (unnamed): If
        - (unnamed): Link
          - (unnamed): IfBranch
          - (unnamed): IfBranch
          - (unnamed): Link
          - (unnamed): WebBlockInstance
          - (unnamed): WebBlockInstance
            - (unnamed): Expression Style="text-underline text-ellipsis"
            - (unnamed): Text Style="font-size-h4 margin-left-s text-green"
            - (unnamed): Text Style="font-size-h4 text-red"
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 22.
Document-item row used in loan-request document checklist.
Status driven by FileStructure.ValidationProgressId comparison with ValidationProgress static records
(Validating / Validated / NotValidated).
"loading-ellipsis" Expression renders the three-dot animation while Validating.
Green check (text-green) vs red X (text-red) for terminal validation states.
-->
