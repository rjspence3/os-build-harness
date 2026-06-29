"""Raw-CDP capture (no Playwright): ORIGINAL (demo+andrea picker) + V6 (own /Login auto-login).
Bypasses the Chrome 147+ Playwright connect_over_cdp wall by speaking CDP over a stdlib
websocket directly to a fresh page target. 1280x900 device metrics, full-page screenshot.

Usage: .venv/bin/python scripts/cdp_raw_capture.py
No app/model mutation. Closes the created target at the end.
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

ANDREA = "demo+andrea@outsystems.com"
BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"


# ---- raw websocket CDP client ----
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


def navigate(ws, url, settle_ms=5000):
    ws.call("Page.navigate", {"url": url}, timeout=60)
    time.sleep(settle_ms / 1000.0)


def full_screenshot(ws, path):
    m = ws.call("Page.getLayoutMetrics")
    css = m.get("cssContentSize") or m.get("contentSize")
    w = int(css["width"]); h = int(css["height"])
    ws.call("Emulation.setDeviceMetricsOverride",
            {"width": 1280, "height": h, "deviceScaleFactor": 1, "mobile": False})
    r = ws.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True,
                                           "clip": {"x": 0, "y": 0, "width": 1280, "height": h, "scale": 1}}, timeout=90)
    pathlib.Path(path).write_bytes(base64.b64decode(r["data"]))
    ws.call("Emulation.setDeviceMetricsOverride",
            {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    return w, h


STRIP = r"""(()=>{const k=e=>{try{e.remove()}catch(x){}};
document.querySelectorAll('[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],div[data-lastpass],#lpcustom,[id^=__lpform],[data-lastpass-root]').forEach(k);
[...document.querySelectorAll('div,iframe,section')].forEach(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect();
if((c.position==='fixed'||c.position==='absolute')&&r.top<80&&r.width>250&&r.width<560&&/lastpass|add password/i.test(e.innerText||''))k(e)});return 1})()"""

METRICS = r"""(()=>{const bt=(document.body.innerText||'').replace(/\s+/g,' ');
const m=bt.match(/Welcome,?\s*([A-Za-z]+)/i);const bal=bt.match(/Total Balance[^\d-]*([\d,]+\.\d{2})/i);
const cb=[...document.querySelectorAll('.account-card .font-size-40,.account-card .card-detail-font')].map(e=>(e.textContent||'').trim()).filter(Boolean).slice(0,8);
return {url:location.href,on_login:/\/Login/i.test(location.href),welcome:m?m[1]:null,total_balance:bal?bal[1]:null,
has_currency_balance:/\$[\d,]+\.\d{2}/.test(bt),has_raw_unsep:/(?<![\d.,$])\d{5,}(?![\d.,])/.test(bt),
card_balances:cb,account_cards:document.querySelectorAll('.account-card').length,
chart:document.querySelectorAll('svg.highcharts-root,.highcharts-container,canvas').length,doc_h:document.documentElement.scrollHeight}})()"""

SCALE = r"""(()=>{const o={};const H=document.documentElement,B=document.body;
o.html_fs=getComputedStyle(H).fontSize;o.body_fs=getComputedStyle(B).fontSize;
o.html_zoom=getComputedStyle(H).zoom;o.body_zoom=getComputedStyle(B).zoom;o.body_tf=getComputedStyle(B).transform;
const w=document.querySelector('.layout .content,.content');if(w){const c=getComputedStyle(w),r=w.getBoundingClientRect();
o.content_class=(w.className||'').slice(0,90);o.content_w=Math.round(r.width);o.content_maxw=c.maxWidth;o.content_pad=c.padding;}
const hero=document.querySelector('.account-card .font-size-40,.font-size-40');if(hero){const c=getComputedStyle(hero),r=hero.getBoundingClientRect();
o.hero_class=(hero.className||'').slice(0,60);o.hero_fs=c.fontSize;o.hero_text=(hero.textContent||'').trim().slice(0,20);o.hero_w=Math.round(r.width);}
const lay=document.querySelector('.layout,[class*=layout]');if(lay){o.layout_w=Math.round(lay.getBoundingClientRect().width);o.layout_class=(lay.className||'').slice(0,80);}
o.win=window.innerWidth+'x'+window.innerHeight;o.dpr=window.devicePixelRatio;return o})()"""


def capture(ws, url, out, label):
    navigate(ws, url, 5500)
    ev(ws, STRIP); time.sleep(0.3)
    full_screenshot(ws, out)
    mx = ev(ws, METRICS); sc = ev(ws, SCALE)
    print(f"\n== {label} ==\n{out}\nMETRICS {json.dumps(mx)}\nSCALE {json.dumps(sc)}")
    return mx, sc


def new_target():
    import urllib.error
    for method in ("PUT", "GET"):
        try:
            req = urllib.request.Request("http://localhost:9222/json/new?about:blank", method=method)
            t = json.loads(urllib.request.urlopen(req, timeout=10).read())
            return t, True
        except urllib.error.HTTPError:
            continue
    raise RuntimeError("cannot create target")


def main():
    pathlib.Path("compare").mkdir(exist_ok=True)
    t, created = new_target()
    tid = t["id"]
    ws = WS(t["webSocketDebuggerUrl"])
    try:
        ws.call("Page.enable"); ws.call("Runtime.enable")
        ws.call("Emulation.setDeviceMetricsOverride",
                {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False})
        # 1) ORIGINAL login via direct credentials (andrea seeded sample user)
        navigate(ws, ORIG_LOGIN, 3500)
        on_login = ev(ws, "/\\/Login/i.test(location.href)")
        if on_login:
            filled = ev(ws, r"""(()=>{const u=document.querySelector('#Input_Username');const p=document.querySelector('#Input_Password');
if(!u||!p)return 'no-fields';
const set=(el,v)=>{const d=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;d.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));el.dispatchEvent(new Event('blur',{bubbles:true}));};
set(u,'""" + ANDREA + r"""');set(p,'OutSystemsDemo123');return 'filled'})()""")
            print("fill:", filled)
            time.sleep(0.6)
            ev(ws, r"""(()=>{const b=[...document.querySelectorAll('button')].find(e=>/^\s*Login\s*$/i.test(e.textContent||''))||document.querySelector('button.OSFillParent');if(b){b.click();return 'login-click'}return 'no-login'})()""")
            time.sleep(5.0)
        url_now = ev(ws, "location.href")
        print("orig post-login url:", url_now)
        if "/Login" in (url_now or ""):
            full_screenshot(ws, "compare/orig_final_loginfail.png")
            print("ORIG STILL ON LOGIN"); return 4
        og, ogs = capture(ws, ORIG_DASH, "compare/orig_final.png", "ORIGINAL (andrea)")
        # 2) V6 auto-login
        navigate(ws, V6_LOGIN, 7000)
        print("v6 post-login url:", ev(ws, "location.href"))
        v6, v6s = capture(ws, V6_DASH, "compare/v6_final.png", "V6 (andrea own login)")
        print("\n== PARITY ==")
        print(f"orig welcome={og.get('welcome')} totalBal={og.get('total_balance')} cards={og.get('account_cards')} chart={og.get('chart')}")
        print(f"v6   welcome={v6.get('welcome')} totalBal={v6.get('total_balance')} cards={v6.get('account_cards')} chart={v6.get('chart')}")
        print(f"v6 card_balances={v6.get('card_balances')}")
        print(f"v6 has_currency={v6.get('has_currency_balance')} has_raw_unsep={v6.get('has_raw_unsep')}")
    finally:
        try:
            ws.call("Emulation.clearDeviceMetricsOverride")
        except Exception:  # noqa: BLE001
            pass
        ws.close()
        if created:
            try:
                urllib.request.urlopen(f"http://localhost:9222/json/close/{tid}", timeout=10).read()
            except Exception:  # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
