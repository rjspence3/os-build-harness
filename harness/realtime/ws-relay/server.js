// Tiny channel-based WebSocket relay — the harness's real-time layer.
//
// OutSystems' reactive web has no native server push, so real-time features (live
// feeds, presence, chat, WebRTC signaling) route through this small external relay
// while OS REST + entities stay the system of record. It is a pure fan-out: no
// media, no persistence. Clients connect  wss://<host>/?channel=<name>&peer=<id>
// and every message is broadcast to all OTHER sockets on the same channel.
//
// Example channels: a global feed ("feed:global"); a per-room signaling channel
// ("room:<id>"). Deploy anywhere that gives a public wss:// URL (Railway / Render /
// Fly / your own box). Run:  npm i && node server.js  (PORT from env, default 8080).
// See ../../../docs/REALTIME.md for how the ODC app connects (Forge WebSocket Connector).

const { WebSocketServer } = require('ws');
const http = require('http');

const PORT = process.env.PORT || 8080;
const channels = new Map(); // channel -> Set<ws>

const server = http.createServer((req, res) => {
  // health check for the hosting platform
  res.writeHead(200, { 'content-type': 'text/plain' });
  res.end('ws-relay ok');
});

const wss = new WebSocketServer({ server });

wss.on('connection', (ws, req) => {
  const url = new URL(req.url, 'http://x');
  const channel = url.searchParams.get('channel') || 'default';
  const peer = url.searchParams.get('peer') || '';
  ws.channel = channel;
  ws.peer = peer;
  if (!channels.has(channel)) channels.set(channel, new Set());
  channels.get(channel).add(ws);

  // tell the newcomer who's already here, and announce them
  const peers = [...channels.get(channel)].filter(c => c !== ws && c.peer).map(c => c.peer);
  ws.send(JSON.stringify({ type: 'peers', peers }));
  broadcast(channel, ws, JSON.stringify({ type: 'join', peer }));

  ws.on('message', (data) => {
    // relay verbatim to the rest of the channel (e.g. WebRTC SDP/ICE, or app events)
    broadcast(channel, ws, data.toString());
  });
  ws.on('close', () => {
    channels.get(channel)?.delete(ws);
    broadcast(channel, ws, JSON.stringify({ type: 'leave', peer }));
    if (channels.get(channel)?.size === 0) channels.delete(channel);
  });
});

function broadcast(channel, sender, msg) {
  for (const c of channels.get(channel) || []) {
    if (c !== sender && c.readyState === 1) c.send(msg);
  }
}

server.listen(PORT, () => console.log(`ws-relay listening on :${PORT}`));
