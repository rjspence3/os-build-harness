"""Read-only: recover the ORIGINAL chart's 10 Income + 10 Expenses values by
measuring rendered bar geometry (y/height of each series rect path) against the
0..1000 y-axis. Highcharts column rects carry x/y/width/height attrs even if the
'height' read 0 earlier was due to wrong selector — re-probe the actual point rects
inside .highcharts-series-N groups and map pixel-space to data-space via the axis."""
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
  const out={series:[]};
  const groups=[...document.querySelectorAll('g.highcharts-series')];
  // axis ticks: map yLabel text positions to data values
  const ticks=[...document.querySelectorAll('.highcharts-yaxis-labels text')].map(t=>{
    const m=t.getBoundingClientRect(); return {v:parseFloat(t.textContent.replace(/[^0-9.]/g,'')), cy:m.top+m.height/2};
  }).filter(t=>!isNaN(t.v));
  out.ticks=ticks;
  // linear fit value = a*cy + b from two extreme ticks
  let a=null,b=null;
  if(ticks.length>=2){
    const lo=ticks.reduce((p,c)=>c.v<p.v?c:p), hi=ticks.reduce((p,c)=>c.v>p.v?c:p);
    a=(hi.v-lo.v)/(hi.cy-lo.cy); b=lo.v-a*lo.cy;
  }
  out.fit={a,b};
  groups.forEach((g,gi)=>{
    const rects=[...g.querySelectorAll('rect.highcharts-point, rect')];
    const vals=rects.map(r=>{
      const bb=r.getBoundingClientRect(); const topY=bb.top; // bar top
      const val = (a!==null)? Math.round(a*topY+b) : null;
      return {top:Math.round(topY), h:Math.round(bb.height), val,
        fill:(r.getAttribute('fill')||'')};
    }).filter(v=>v.h>0);
    out.series.push({i:gi, n:vals.length, vals});
  });
  return out;
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
        pg.goto(ORIG_DASH,wait_until="networkidle",timeout=60000); pg.wait_for_timeout(5500)
        print(json.dumps(pg.evaluate(PROBE),indent=1))
    finally: p.stop()
    return 0
if __name__=="__main__": raise SystemExit(main())
