```
=== Block: Chat ===
- 'ChatWrapper': Container Style="floating-ai-chat" Width=(fill parent)
  - (unnamed): If
  - (unnamed): Container Style="toggle-ai-chat-btn" Width=(fill parent)
    - (unnamed): IfBranch
    - (unnamed): IfBranch
    - 'Chat': Container Style="ai-chat" + If(IsOpen, " is--opened", " is--closed") Width=(fill parent)
    - (unnamed): Container Style="toggle-ai-chat-icon" Width=(fill parent)
      - 'ChatHeader': Container Style="ai-chat-header" Width=(fill parent)
      - 'ChatBody': Container Style="ai-chat-body scrollable-element" Width=(fill parent)
      - 'ChatFooter': Container Style="ai-chat-footer" Width=(fill parent)
      - 'IsClosed': If
        - (unnamed): IfBranch
        - (unnamed): IfBranch
        - (unnamed): Container Width=80%
        - (unnamed): Container Style="text-align-right" Width=20%
        - 'HasMessages': If
        - (unnamed): WebBlockInstance
        - (unnamed): Image Width=60px
          - (unnamed): IfBranch
          - (unnamed): IfBranch
          - (unnamed): WebBlockInstance
          - (unnamed): Link
          - 'MessageList': List Style="list list-group" Width=(fill parent)
          - 'IF_IsWaitingForResponse': If
            - (unnamed): IfBranch
            - (unnamed): IfBranch
            - (unnamed): Image Width=32px
            - (unnamed): If
            - (unnamed): WebBlockInstance
            - (unnamed): Container Width=(fill parent)
            - (unnamed): List Style="list list-group" Width=(fill parent)
              - (unnamed): IfBranch
              - (unnamed): IfBranch
              - (unnamed): Expression Style="ai-assistant-name margin-left-s"
              - (unnamed): Text Style="ai-assistant-name margin-left-s"
              - (unnamed): Text
              - 'Message': WebBlockInstance
              - (unnamed): Container Width=10 col
                - (unnamed): Container Style="vertical-align gap-xs" Width=(fill parent)
                - (unnamed): Container Style="padding-top-base" Width=(fill parent)
                  - (unnamed): WebBlockInstance
                  - (unnamed): Container Style="sidebar-chat__skeleton" Width=(fill parent)
                  - (unnamed): Container Style="sidebar-chat__skeleton margin-y-12" Width=10 col
                  - (unnamed): Container Style="sidebar-chat__skeleton" Width=8 col
                    - (unnamed): WebBlockInstance
                    - (unnamed): Expression Style="loading-ellipsis margin-left-s "
```

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6.
Capture run: 2026-06-09 (run 2). Widget count emitted: 46.

Floating AI-chat widget — the right-side assistant UI.
Top-level: floating-ai-chat ChatWrapper Container, two states (toggle button + expanded panel).
Expanded panel:
  - ChatHeader: ai-chat-header
  - ChatBody: ai-chat-body scrollable-element (the message list lives here)
  - ChatFooter: ai-chat-footer (input lives here, via ChatInput sub-block)
  - IsClosed/IsOpen If: toggles ai-chat is--opened / is--closed class
  - HasMessages If: empty-state vs message-list rendering
  - MessageList List with list-group of Message WebBlockInstance (ChatMessage block)
  - IF_IsWaitingForResponse If: shows sidebar-chat__skeleton placeholders + loading-ellipsis
    while assistant is generating a response.
-->
