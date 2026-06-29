"""Read-only: extract Highcharts categories + series data from BOTH dashboards."""
import json, os, pathlib, sys
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402
BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
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
  const out={categories:null, series:null, found:false};
  try {
    if (window.Highcharts && Highcharts.charts) {
      const c = Highcharts.charts.find(x=>x);
      if (c) { out.found=true;
        out.categories = c.xAxis && c.xAxis[0] ? c.xAxis[0].categories : null;
        out.series = (c.series||[]).map(s=>({name:s.name, n:(s.data||[]).length,
          pts:(s.data||[]).slice(0,12).map(d=>d.y)}));
      }
    }
  } catch(e){ out.err=String(e); }
  // fallback: x-axis label texts
  out.xLabels=[...document.querySelectorAll('.highcharts-xaxis-labels text')].map(t=>t.textContent.trim());
  return out;
}"""
def probe(page,url,label):
    page.goto(url,wait_until="networkidle",timeout=60000); page.wait_for_timeout(4500)
    print(f"\n== {label} ==\n"+json.dumps(page.evaluate(PROBE),indent=1))
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
        probe(pg,ORIG_DASH,"ORIGINAL"); probe(pg,V6_DASH,"V6")
    finally: p.stop()
    return 0
if __name__=="__main__": raise SystemExit(main())
