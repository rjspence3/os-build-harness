"""Head-to-head layout/scale probe: compare original vs V6 Dashboard computed geometry
to isolate the residual (fixed-header, content offset, card geometry). Requires being logged in:
original via direct andrea creds, V6 via own /Login.
"""
import json
import pathlib
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cdp_raw_capture import (WS, ev, navigate, new_target,  # noqa: E402
                             ORIG_LOGIN, ORIG_DASH, V6_LOGIN, V6_DASH, ANDREA)

GEOM = r"""(()=>{const o={};const g=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();const c=getComputedStyle(e);return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),cls:(e.className||'').toString().slice(0,70),pos:c.position}};
o.layout=g('.layout');o.header=g('.layout .header,header');o.content=g('.layout .content,.content');
o.firstcard=g('.account-card');o.maincard=g('.main-card');
// header height + whether fixed
const lay=document.querySelector('.layout');o.layout_classes=lay?(lay.className||'').toString():null;
o.has_fixed_header=lay?/fixed-header/.test(lay.className||''):null;
// first big content column (transactions/balance area)
o.balance_block=g('[class*=Balance],[class*=balance]');
o.body_scrollW=document.documentElement.scrollWidth;o.client_w=document.documentElement.clientWidth;
return o})()"""


def probe(ws, url, label):
    navigate(ws, url, 5500)
    g = ev(ws, GEOM)
    print(f"\n== {label} ==\n{json.dumps(g, indent=1)}")
    return g


def main():
    t, created = new_target()
    tid = t["id"]
    ws = WS(t["webSocketDebuggerUrl"])
    try:
        ws.call("Page.enable"); ws.call("Runtime.enable")
        ws.call("Emulation.setDeviceMetricsOverride", {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False})
        navigate(ws, ORIG_LOGIN, 3500)
        if ev(ws, "/\\/Login/i.test(location.href)"):
            ev(ws, r"""(()=>{const u=document.querySelector('#Input_Username'),p=document.querySelector('#Input_Password');const s=(el,v)=>{const d=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;d.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));};s(u,'""" + ANDREA + r"""');s(p,'OutSystemsDemo123');const b=[...document.querySelectorAll('button')].find(e=>/^\s*Login\s*$/i.test(e.textContent||''))||document.querySelector('button.OSFillParent');b&&b.click();return 1})()""")
            time.sleep(5.0)
        probe(ws, ORIG_DASH, "ORIGINAL")
        navigate(ws, V6_LOGIN, 7000)
        probe(ws, V6_DASH, "V6")
    finally:
        ws.close()
        if created:
            try:
                urllib.request.urlopen(f"http://localhost:9222/json/close/{tid}", timeout=10).read()
            except Exception:  # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
