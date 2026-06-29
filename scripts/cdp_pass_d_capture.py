"""Pass D capture: screenshot V6 Login / InvalidPermissions / WakeUp at 1280x900.

Raw-CDP (no Playwright) — speaks CDP over a stdlib websocket to a fresh page
target, sidestepping the Chrome 147+ Playwright connect_over_cdp wall. Creates
its own target and CLOSES it at the end (shared context: never close Rob's pages).

Usage: .venv/bin/python scripts/cdp_pass_d_capture.py
Writes PNGs into data/MCP_RECIPES/apps/home_banking/_raw/compare/.
No app/model mutation.
"""
import base64
import json
import os
import pathlib
import socket
import struct
import time
import urllib.request
from urllib.parse import urlparse

BASE = "https://your-tenant-dev.outsystems.app"
OUT_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw" / "compare"
)
SCREENS = [
    ("v6_invalidperms.png", f"{BASE}/HomeBankingPortal6/InvalidPermissions"),
    ("v6_wakeup.png", f"{BASE}/HomeBankingPortal6/WakeUp"),
    ("v6_login.png", f"{BASE}/HomeBankingPortal6/Login"),
]


class WS:
    def __init__(self, url):
        u = urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port or 80), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {u.path}{('?'+u.query) if u.query else ''} HTTP/1.1\r\n"
               f"Host: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.s.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.s.recv(4096)
        if b"101" not in resp.split(b"\r\n")[0]:
            raise RuntimeError("ws handshake failed")
        self._id = 0

    def _send(self, text):
        data = text.encode()
        h = bytearray([0x81])
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            h.append(0x80 | n)
        elif n < 65536:
            h.append(0x80 | 126); h += struct.pack(">H", n)
        else:
            h.append(0x80 | 127); h += struct.pack(">Q", n)
        h += mask
        self.s.sendall(bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recv(self):
        def rd(n):
            buf = b""
            while len(buf) < n:
                c = self.s.recv(n - len(buf))
                if not c:
                    raise RuntimeError("socket closed")
                buf += c
            return buf
        b0, b1 = rd(2)
        ln = b1 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", rd(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", rd(8))[0]
        return rd(ln).decode("utf-8", "replace") if ln else ""

    def call(self, method, params=None, timeout=60):
        self._id += 1
        mid = self._id
        self._send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            msg = json.loads(self._recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise RuntimeError(f"{method}: timeout")

    def close(self):
        try:
            self.s.close()
        except Exception:  # noqa: BLE001
            pass


def ev(ws, expr, timeout=60):
    r = ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                     "awaitPromise": True}, timeout=timeout)
    if r.get("exceptionDetails"):
        return {"__error__": str(r["exceptionDetails"].get("exception", {}).get("description", "eval error"))}
    return r.get("result", {}).get("value")


def navigate(ws, url, settle_ms=6000):
    ws.call("Page.navigate", {"url": url}, timeout=60)
    time.sleep(settle_ms / 1000.0)


def shot(ws, path):
    ws.call("Emulation.setDeviceMetricsOverride",
            {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    r = ws.call("Page.captureScreenshot", {"format": "png",
                                           "clip": {"x": 0, "y": 0, "width": 1280, "height": 900, "scale": 1}},
                timeout=90)
    pathlib.Path(path).write_bytes(base64.b64decode(r["data"]))


METRICS = r"""(()=>{const bt=(document.body.innerText||'').replace(/\s+/g,' ');
return {url:location.href,on_login:/\/Login/i.test(location.href),is_error:/\/_error/i.test(location.href),
dark_mode:document.documentElement.classList.contains('dark-mode'),
has_login:/Home Banking/i.test(bt),has_username_input:!!document.querySelector('input[type=text],input[type=email]'),
has_password_input:!!document.querySelector('input[type=password]'),has_switch:!!document.querySelector('[class*=switch i],input[type=checkbox]'),
has_permission_msg:/necessary permission/i.test(bt),has_wakeup:/Wake me up/i.test(bt),
service_rows:document.querySelectorAll('.serviceitem').length,
btn_login:/\bLogin\b/.test(bt),btn_wakeup:/Wake up/i.test(bt),
demo_link:/Access your demo/i.test(bt),admin_msg:/system administrator/i.test(bt),
body_snippet:bt.slice(0,180)}})()"""


def new_target():
    import urllib.error
    for method in ("PUT", "GET"):
        try:
            req = urllib.request.Request("http://localhost:9222/json/new?about:blank", method=method)
            t = json.loads(urllib.request.urlopen(req, timeout=10).read())
            return t
        except urllib.error.HTTPError:
            continue
    raise RuntimeError("cannot create target")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t = new_target()
    tid = t["id"]
    ws = WS(t["webSocketDebuggerUrl"])
    try:
        ws.call("Page.enable"); ws.call("Runtime.enable")
        ws.call("Emulation.setDeviceMetricsOverride",
                {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False})
        for fname, url in SCREENS:
            navigate(ws, url, 6500)
            mx = ev(ws, METRICS)
            out = OUT_DIR / fname
            shot(ws, str(out))
            print(f"\n== {fname} ==\n{out}\nMETRICS {json.dumps(mx)}")
    finally:
        try:
            ws.call("Emulation.clearDeviceMetricsOverride")
        except Exception:  # noqa: BLE001
            pass
        ws.close()
        try:
            urllib.request.urlopen(f"http://localhost:9222/json/close/{tid}", timeout=10).read()
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
