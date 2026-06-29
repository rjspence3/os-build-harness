"""Read-only: dump the ORIGINAL dashboard chart's rendered x-axis labels + bar
heights straight from the SVG DOM (Highcharts JS object not exposed there)."""
import json, os, pathlib, sys
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402
BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
VIEW = {"width": 1280, "height": 900}
def _env(path=".env"):
    e={}; p=pathlib.Path(path)
    if p.exists():
        for ln in p.read_text().splitlines():
            ln=ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k,v=ln.split("=",1); v=v.strip()
                if len(v)>=2 and v[0]==v[-1] and v[0] in "\"'": v=v[1:-1]
                e[k.strip()]=v
    return e
PROBE = r"""() => {
  const xl=[...document.querySelectorAll('.highcharts-xaxis-labels text, [class*=xaxis] text')].map(t=>t.textContent.trim());
  const yl=[...document.querySelectorAll('.highcharts-yaxis-labels text, [class*=yaxis] text')].map(t=>t.textContent.trim());
  const bars=[...document.querySelectorAll('.highcharts-series rect, .highcharts-point')].map(r=>({
    h:Math.round(+(r.getAttribute('height')||0)), fill:(r.getAttribute('fill')||r.style.fill||'')}));
  // any text containing Wk
  const wk=[...document.querySelectorAll('text')].map(t=>t.textContent.trim()).filter(s=>/Wk\d/.test(s));
  return {xLabels:xl, yLabels:yl, barCount:bars.length, bars:bars.slice(0,24), wkTexts:wk};
}"""
def main():
    e=_env(); u=os.environ.get("HB_PORTAL_USER") or e.get("HB_PORTAL_USER")
    pw=os.environ.get("HB_PORTAL_PASS") or e.get("HB_PORTAL_PASS")
    if not (u and pw): print("creds missing"); return 2
    if not is_chrome_available(): print("no CDP"); return 1
    p,b,ctx=connect_with_retry()
    try:
        pg=ctx.new_page(); pg.set_viewport_size(VIEW)
        pg.goto(ORIG_LOGIN,wait_until="networkidle",timeout=60000); pg.wait_for_timeout(2500)
        if "Login" in pg.url:
            usr=pg.query_selector("#Input_Username") or pg.query_selector("input[type=text]")
            pwd=pg.query_selector("#Input_Password") or pg.query_selector("input[type=password]")
            usr.fill(u); pwd.fill(pw)
            btn=pg.query_selector("button:has-text('Login')") or pg.query_selector("button.OSFillParent")
            (btn.click() if btn else pwd.press("Enter"))
            pg.wait_for_load_state("networkidle",timeout=60000); pg.wait_for_timeout(4000)
        if "Login" in pg.url: print("AUTH FAIL"); return 4
        pg.goto(ORIG_DASH,wait_until="networkidle",timeout=60000); pg.wait_for_timeout(5000)
        print(json.dumps(pg.evaluate(PROBE),indent=1))
    finally: p.stop()
    return 0
if __name__=="__main__": raise SystemExit(main())
