# Real-time on OutSystems (the relay pattern)

OutSystems' reactive web model has **no native WebSocket / SSE server push** — a page
updates when *it* calls a server action, not when the server wants to push. So anything
genuinely live (a feed that updates without refresh, presence, chat, typing indicators,
WebRTC signaling) needs an external push layer. This is the pattern the harness uses to
get real-time **without leaving the OutSystems programming model**.

Two pieces:

1. **A tiny external relay** — [`harness/realtime/ws-relay/`](../harness/realtime/ws-relay/)
   (~55 lines of Node). A pure channel fan-out: clients connect to a channel and every
   message is broadcast to all *other* sockets on it. No media, no persistence.
2. **A client binding inside ODC** — the Forge **WebSocket Connector** ReactiveLibrary,
   which lets an ODC screen open a socket and react to messages **model-natively** (no
   custom JavaScript required).

**OS REST + entities stay the system of record.** The relay only carries change
*notifications*; the durable data still lives in ODC and is fetched via the normal
aggregates/actions. The relay is a "something changed, go refresh" bus, not a database.

---

## 1. Deploy the relay

```bash
cd harness/realtime/ws-relay
npm i
node server.js                 # listens on PORT (default 8080); GET / → "ws-relay ok"
```

For a public `wss://` URL, deploy it to any host that terminates TLS and exposes the port
(Railway / Render / Fly / your own box). It's stateless — scale/replace freely. The client
connect URL is:

```
wss://<your-relay-host>/?channel=<name>&peer=<id>
```

On connect the relay sends `{type:"peers",peers:[…]}`; on join/leave it emits
`{type:"join"|"leave",peer}`; every other message is rebroadcast verbatim to the channel.
**Channel convention:** scope by use case — e.g. `feed:global` (a shared feed) or
`room:<id>` (per-conversation / per-meeting).

---

## 2. Wire the ODC app (Forge WebSocket Connector)

1. Install the **WebSocket Connector** ReactiveLibrary from OutSystems Forge into your app
   (it's a third-party component — confirm its license/availability for your use).
2. It exposes a **`WebSocket` block** with events **`MessageReceived(Message: Text)`**
   (mandatory), `Connected`, `Disconnected`, `ErrorReceived`, and client actions
   `WebSocket_Connect`, `WebSocket_Disconnect`, `WebSocket_SendMessageJSON`,
   `WebSocket_SendMessageTXT`.
3. Drop the block on a screen and set its **`EndPointUrl`** to your relay channel, e.g.
   `"wss://<your-relay-host>/?channel=feed:global&peer=" + CurrentUserId`.
4. Handle **`MessageReceived`** → refresh the relevant aggregate (fetch the fresh data from
   ODC) so the screen updates live. Publish an event by calling `WebSocket_SendMessageJSON`
   after you commit a change through the normal server action.

### Authoring it via the MCP

The block is added like any block instance:

```
CreateWidget<OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget>("WsBlock")
  .SourceBlock = <the WebSocket block signature>
  .Id          = "appfeedws"
  .EndPointUrl = "wss://<your-relay-host>/?channel=feed:global&peer=" + <uid>
```

`MessageReceived` is a **mandatory** event handler — the model won't validate until it's
wired.

---

## Status + honesty

- **Proven live:** the receive path is model-native and works end to end — one client
  commits a change and pings the channel; other clients' screens update **with no page
  refresh**.
- **This is non-native / external infra.** You run (and pay for) a relay host, and you
  depend on a Forge component. It is *not* "pure OutSystems." What it buys you is that the
  one true platform ceiling for cloning a modern app — real-time — becomes reachable, with
  ODC still owning the data.
- **Not a message broker.** No delivery guarantees, ordering, or persistence — treat every
  message as a disposable "go refresh" hint and re-fetch the authoritative state from ODC.
