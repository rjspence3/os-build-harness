```
=== Block: AccountAccordian ===
- (unnamed): Container Style="position-relative" Width=(fill parent)
  - (unnamed): Container Style="accordian-left-color"
  - (unnamed): WebBlockInstance
    - (unnamed): Container Width=6 col
    - (unnamed): Container Style="padding-right-base" Width=6 col
    - (unnamed): WebBlockInstance
    - (unnamed): List Style="list list-group" Width=(fill parent)
      - (unnamed): Expression Style="font-regular font-size-s"
      - (unnamed): Expression Style="font-size-s font-semi-bold"
      - (unnamed): Container Style="margin-bottom-l" Width=(fill parent)
        - (unnamed): Container Width=7 col
        - (unnamed): Container Width=5 col
          - (unnamed): WebBlockInstance
          - (unnamed): Expression Style="font-semi-bold"
            - (unnamed): If
            - (unnamed): Expression
              - (unnamed): IfBranch
              - (unnamed): IfBranch
              - (unnamed): Text Style="margin-top-xs"
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 19.
Domain accordion: position-relative wrapper + colored stripe + content panel with 6/6 column split
+ list-group of expand items (each margin-bottom-l, 7/5 column split for label/value).
-->
