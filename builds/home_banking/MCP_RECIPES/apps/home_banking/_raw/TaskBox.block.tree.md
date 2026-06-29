```
=== Block: TaskBox ===
- (unnamed): If
- (unnamed): If
  - (unnamed): IfBranch
  - (unnamed): IfBranch
  - (unnamed): IfBranch
  - (unnamed): IfBranch
  - (unnamed): WebBlockInstance
  - (unnamed): If
  - 'Firebase_configured': If
    - (unnamed): IfBranch
    - (unnamed): IfBranch
    - (unnamed): IfBranch
    - (unnamed): IfBranch
    - (unnamed): Text
    - 'TasksNotification': WebBlockInstance
    - (unnamed): Container Style="chatbot-balloon" Width=(fill parent)
    - 'NoTaskNotification': Container Width=(fill parent)
    - (unnamed): Container Style="chatbot-balloon" Width=(fill parent)
    - (unnamed): WebBlockInstance
      - (unnamed): WebBlockInstance
      - (unnamed): WebBlockInstance
      - (unnamed): WebBlockInstance
      - (unnamed): WebBlockInstance
        - (unnamed): WebBlockInstance
        - (unnamed): List Style="list list-group" Width=(fill parent)
        - (unnamed): Text
        - (unnamed): Container Style="item-task" Width=(fill parent)
          - (unnamed): Text
          - (unnamed): Container Style="item-task" Width=(fill parent)
          - (unnamed): WebBlockInstance
            - (unnamed): WebBlockInstance
            - (unnamed): Expression
              - (unnamed): Icon Style="text-primary" Width=(fill parent)
              - (unnamed): Expression
              - (unnamed): Expression Style="text-neutral-8"
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 35.
Floating chatbot-style task balloon — likely the lower-right ribbon UI for in-app tasks.
"Firebase_configured" If gates on push-notification provisioning.
TasksNotification + NoTaskNotification: two named display states.
"item-task" Container in list-group renders each task item with primary-colored Icon
+ Expression label + neutral-8 Expression timestamp/caption.
-->
