"""Read-only macro-layout bbox probe: login on original, then dump bounding boxes
of key dashboard containers/elements on BOTH HomeBankingPortal (orig) and
HomeBankingPortal6 (V6) in the same session. Used to quantify macro-layout
offsets driving the pixel diff. No model/data mutation."""
import json
import os
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
VIEW = {"width": 1280, "height": 900}


def _load_env(path=".env"):
    env = {}
    p = pathlib.Path(path)
    if p.exists():
        for ln in p.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                env[k.strip()] = v
    return env


PROBE_JS = r"""() => {
  const R = (el) => { if(!el) return null; const r=el.getBoundingClientRect();
    return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}; };
  const byText = (txt) => [...document.querySelectorAll('*')].find(e =>
    (e.children.length===0) && (e.textContent||'').trim().toLowerCase()===txt.toLowerCase());
  const firstSel = (...sels) => { for(const s of sels){ const e=document.querySelector(s); if(e) return e; } return null; };
  const header = firstSel('header', '.app-header', '[class*=Header]', '.top-bar', 'nav');
  const main = firstSel('main', '.main-content', '[class*=MainContent]', '[class*=content]');
  const aside = document.querySelector('aside');
  const chartC = firstSel('.highcharts-container', 'svg.highcharts-root', '[class*=chart] svg', 'canvas');
  const chartWrap = chartC ? chartC.closest('[class*=card],[class*=Card],[class*=block],section,div') : null;
  // Find the "Total Balance" label + its $ value
  const tbLabel = byText('Total Balance');
  const balCard = tbLabel ? tbLabel.closest('[class*=card],[class*=Card],section,div') : null;
  // count chart x-axis category labels (Wk..)
  const axisLabels = [...document.querySelectorAll('.highcharts-xaxis-labels text, .highcharts-axis-labels text')].map(t=>t.textContent.trim());
  // bar count
  const bars = document.querySelectorAll('.highcharts-series rect, .highcharts-point').length;
  // Last Transactions area: spinner vs blankslate
  const hasSpinner = !!document.querySelector('.spinner, [class*=Spinner], [class*=loading], .OSBlock_osblock_Loading');
  const blankText = (document.body.innerText||'').includes("aren't any trans");
  return {
    viewport:{w:window.innerWidth,h:window.innerHeight},
    body_pad: getComputedStyle(document.body).padding,
    header:{rect:R(header), cls:(header&&header.className||'').toString().slice(0,80)},
    main:{rect:R(main), cls:(main&&main.className||'').toString().slice(0,80)},
    aside:{rect:R(aside), cls:(aside&&aside.className||'').toString().slice(0,80)},
    balanceCard:{rect:R(balCard), tbLabelRect:R(tbLabel)},
    chartWrap:{rect:R(chartWrap)},
    chartContainer:{rect:R(chartC)},
    axisLabels, barCount:bars,
    lastTx:{hasSpinner, blankText},
  };
}"""


def probe(page, url, label):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4500)
    data = page.evaluate(PROBE_JS)
    print(f"\n===== {label} =====")
    print(json.dumps(data, indent=1))
    return data


def main() -> int:
    env = _load_env()
    user = os.environ.get("HB_PORTAL_USER") or env.get("HB_PORTAL_USER")
    pw = os.environ.get("HB_PORTAL_PASS") or env.get("HB_PORTAL_PASS")
    if not (user and pw):
        print("HB_PORTAL_USER/HB_PORTAL_PASS missing"); return 2
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222"); return 1
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size(VIEW)
        page.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        if "Login" in page.url:
            usr = page.query_selector("#Input_Username") or page.query_selector("input[type=text]")
            pwd = page.query_selector("#Input_Password") or page.query_selector("input[type=password]")
            usr.fill(user); pwd.fill(pw)
            btn = page.query_selector("button:has-text('Login')") or page.query_selector("button.OSFillParent")
            (btn.click() if btn else pwd.press("Enter"))
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(4000)
        if "Login" in page.url:
            print("STILL ON LOGIN — auth failed"); return 4
        probe(page, ORIG_DASH, "ORIGINAL")
        probe(page, V6_DASH, "V6")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
