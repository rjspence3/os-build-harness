```
=== Block: ChatMessage ===
- (unnamed): Container Style="ai-chat-message-cntr" Width=(fill parent)
  - (unnamed): If
    - (unnamed): IfBranch
    - (unnamed): IfBranch
    - (unnamed): Container Style="display-flex justify-content-flex-end" Width=(fill parent)
    - (unnamed): Container Style="display-flex" Width=(fill parent)
    - (unnamed): If
      - (unnamed): IfBranch
      - (unnamed): IfBranch
      - (unnamed): Container Style="ai-chat-message-user-cntr" Width=(fill parent)
      - (unnamed): Container Style="ai-chat-message-icon" Width=(fill parent)
      - (unnamed): Container Style="ai-chat-message-icon" Width=(fill parent)
      - (unnamed): Container Width=(fill parent)
      - (unnamed): Container Style="margin-bottom-xl" Width=(fill parent)
        - 'BodyUser': Container Style="ai-chat-message ai-user" Width=(fill parent)
        - (unnamed): Container Style="margin-top-s" Width=(fill parent)
        - 'IsUserMessage2': If
        - (unnamed): Image
        - 'Body': Container Style="ai-chat-message ai-assistant" Width=(fill parent)
        - (unnamed): Container Style="margin-top-s" Width=(fill parent)
        - (unnamed): List Style="list list-group" Width=(fill parent)
          - (unnamed): IfBranch
          - (unnamed): IfBranch
          - (unnamed): WebBlockInstance
          - (unnamed): Expression Style="ai-chat-message-date"
          - (unnamed): If
          - (unnamed): WebBlockInstance
          - (unnamed): Expression Style="ai-chat-message-date"
          - (unnamed): Container Width=(fill parent)
            - (unnamed): IfBranch
            - (unnamed): IfBranch
            - (unnamed): Image Style="avatar avatar-small border-radius-rounded user-img" Width=20px
            - 'UserAvatar2': WebBlockInstance
            - (unnamed): Container Style="suggestions"
              - (unnamed): Expression
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 35.

Individual chat-message bubble.
Two variants gated by IsUserMessage2 If:
  - BodyUser: ai-chat-message ai-user (right-aligned, justify-content-flex-end)
  - Body: ai-chat-message ai-assistant (left-aligned)
Each variant includes:
  - ai-chat-message-icon Container (avatar slot)
  - ai-chat-message-cntr message wrapper
  - ai-chat-message-date Expression timestamp
  - margin-top-s / margin-bottom-xl spacing
User message: shows user avatar (avatar-small border-radius-rounded user-img Image, 20px).
Assistant message: shows assistant avatar via UserAvatar2 WebBlockInstance + optional
suggestions Container (list of clickable Expression follow-up prompts).
-->
