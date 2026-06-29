"""Dispose orphaned CDP browser contexts using a stdlib-only websocket client.

No third-party websocket dependency. Performs the RFC6455 handshake over a raw socket,
sends Target.getBrowserContexts + Target.disposeBrowserContext, then closes. This clears
the incognito context leaked by a prior browser.new_context() that wedges Playwright's
connect_over_cdp on Chrome 147+.
"""
import base64
import json
import os
import socket
import struct
import urllib.request
from urllib.parse import urlparse


def ws_url():
    v = json.load(urllib.request.urlopen("http://localhost:9222/json/version", timeout=5))
    return v["webSocketDebuggerUrl"]


def connect(url):
    u = urlparse(url)
    host, port = u.hostname, u.port or 80
    path = u.path
    s = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    s.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += s.recv(4096)
    if b"101" not in resp.split(b"\r\n")[0]:
        raise RuntimeError("ws handshake failed: " + resp[:80].decode(errors="replace"))
    return s


def send_text(s, text):
    data = text.encode()
    header = bytearray([0x81])  # FIN + text
    mask = os.urandom(4)
    n = len(data)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", n)
    header += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    s.sendall(bytes(header) + masked)


def recv_frame(s):
    def rd(n):
        buf = b""
        while len(buf) < n:
            chunk = s.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("socket closed")
            buf += chunk
        return buf

    b0, b1 = rd(2)
    length = b1 & 0x7F
    if length == 126:
        length = struct.unpack(">H", rd(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", rd(8))[0]
    payload = rd(length) if length else b""
    return payload.decode(errors="replace")


def call(s, _id, method, params=None):
    send_text(s, json.dumps({"id": _id, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(recv_frame(s))
        if msg.get("id") == _id:
            return msg


def main():
    s = connect(ws_url())
    try:
        res = call(s, 1, "Target.getBrowserContexts")
        ctxs = res.get("result", {}).get("browserContextIds", [])
        print("orphan browser contexts:", ctxs)
        for i, cid in enumerate(ctxs, start=2):
            r = call(s, i, "Target.disposeBrowserContext", {"browserContextId": cid})
            print("disposed", cid, "->", r.get("result", r.get("error")))
        print("recovery done")
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
