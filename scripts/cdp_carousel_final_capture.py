"""Final clean comparable capture after the V6 carousel re-init fix (rev 44).

Both at 1280x900, populated as Andrea, carousel laid out:
  1. V6  : fresh ctx, clear cookies -> /HomeBankingPortal6/Login (auto-login Andrea)
           -> Dashboard -> wait for seed+carousel -> probe slide layout -> v6_final.png
  2. ORIG : manual login demo+andrea@outsystems.com / OutSystemsDemo123
           -> /HomeBankingPortal/Dashboard -> strip LastPass -> orig_final.png

The carousel probe reports each .slide's computed transform-scale, inline left, and
z-index. Stacked-peek (not overlapping) == distinct scales ~1.0/0.9/0.8, monotonically
increasing left offsets, descending z-index 3/2/1.

Closes all CDP pages before p.stop().
"""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
VIEW = {"width": 1280, "height": 900}

ANDREA_EMAIL = "demo+andrea@outsystems.com"
ANDREA_PASS = "OutSystemsDemo123"

_STRIP = r"""() => {
  const kill = el => { try { el.remove(); } catch(e){} };
  document.querySelectorAll('[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],div[data-lastpass],#lpcustom,[id^=__lpform],[data-lastpass-root]').forEach(kill);
  [...document.querySelectorAll('div,iframe,section')].forEach(e => {
    const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
    if ((cs.position==='fixed'||cs.position==='absolute') && r.top < 80 && r.width>250 && r.width<560 &&
        /lastpass|add password|add to lastpass/i.test(e.innerText||'')) kill(e);
  });
}"""

_METRICS = r"""() => {
  const bt = (document.body.innerText||'').replace(/\s+/g,' ');
  const m = bt.match(/Welcome,?\s*([A-Za-z]+)/i);
  const bal = bt.match(/Total Balance[^\d-]*([\d,]+\.\d{2})/i);
  return {url: location.href, on_login:/\/Login/i.test(location.href),
    is_error:/error processing your request/i.test(bt),
    welcome_name:m?m[1]:null, total_balance: bal?bal[1]:null,
    chart_svg:document.querySelectorAll('svg.highcharts-root,.highcharts-container,canvas').length,
    account_cards:document.querySelectorAll('[class*=dashboard-card],[class*=account-card]').length};
}"""

# Probe the stacked carousel slide layout. Reports per-slide scale/left/zIndex and an
# overlapping heuristic: if >=2 visible slides share (left<5 AND scale==1) the stack
# collapsed at top-left (the bug). Laid-out == distinct scales + increasing lefts.
_CAROUSEL = r"""() => {
  const ph = document.querySelector('.slider.slider-content') || document.querySelector('.slider-content');
  if(!ph) return {found:false};
  const list = ph.querySelector('.list') || ph;
  const slides = [...list.children].filter(c => !c.classList.contains('hidden-slide'));
  const rows = slides.map((s,i) => {
    const cs = getComputedStyle(s);
    const tr = cs.transform;  // matrix(a,..) -> a is scaleX
    let scale = 1;
    const mm = tr && tr.startsWith('matrix(') ? tr.slice(7,-1).split(',') : null;
    if(mm) scale = parseFloat(mm[0]);
    const r = s.getBoundingClientRect();
    return {i, scale: +scale.toFixed(3), left_inline: s.style.left||'', zIndex: cs.zIndex,
            box_left: Math.round(r.left), box_w: Math.round(r.width),
            display: cs.display, active: s.classList.contains('slide-active')};
  });
  const visible = rows.filter(r => r.display !== 'none');
  const scales = visible.map(r=>r.scale);
  const distinctScales = new Set(scales.map(s=>s.toFixed(2))).size;
  const boxLefts = visible.map(r=>r.box_left);
  const increasingLefts = boxLefts.every((v,idx)=> idx===0 || v >= boxLefts[idx-1]-2);
  // overlap bug: 2+ visible slides both at scale~1 and near-identical box_left
  let pileUp = 0;
  for(let a=0;a<visible.length;a++) for(let b=a+1;b<visible.length;b++){
    if(Math.abs(visible[a].box_left-visible[b].box_left)<8 && Math.abs(visible[a].scale-visible[b].scale)<0.02) pileUp++;
  }
  return {found:true, slide_count: rows.length, visible_count: visible.length,
          slides: rows, distinct_scales: distinctScales, increasing_lefts: increasingLefts,
          pile_up_pairs: pileUp,
          laid_out: visible.length>=2 && distinctScales>=2 && increasingLefts && pileUp===0};
}"""


def capture_v6(browser, context):
    # Per cdp_helpers contract: use the shared default context only; never new_context().
    context.clear_cookies()
    page = context.new_page()
    page.set_viewport_size(VIEW)
    try:
        page.goto(V6_LOGIN, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:  # noqa: BLE001
        print("v6 login goto note:", repr(e)[:120])
    page.wait_for_timeout(9000)
    page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
    # give seed + GetAccounts + IList render + ReinitCarousel time to lay out
    page.wait_for_timeout(7000)
    car = page.evaluate(_CAROUSEL)
    mx = page.evaluate(_METRICS)
    try:
        page.evaluate(_STRIP); page.wait_for_timeout(300)
    except Exception:  # noqa: BLE001
        pass
    page.screenshot(path="compare/v6_final.png", full_page=True)
    print("\n== V6 ==")
    print(json.dumps(mx))
    print("CAROUSEL:", json.dumps(car))
    try:
        page.close()
    except Exception:  # noqa: BLE001
        pass
    return car, mx


def capture_orig(context):
    page = context.new_page()
    page.set_viewport_size(VIEW)
    page.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2500)
    if "Login" in page.url:
        # manual credential login for Andrea
        try:
            email = page.query_selector("input[type=email]") or page.query_selector("input[name*=email i]") or page.query_selector("input[type=text]")
            pwd = page.query_selector("input[type=password]")
            if email and pwd:
                email.fill(ANDREA_EMAIL)
                pwd.fill(ANDREA_PASS)
                btn = page.query_selector("button:has-text('Login')") or page.query_selector("button[type=submit]") or page.query_selector("button.OSFillParent")
                if btn:
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=60000)
                    page.wait_for_timeout(3500)
        except Exception as e:  # noqa: BLE001
            print("orig login note:", repr(e)[:160])
    print("orig post-login url:", page.url)
    page.goto(ORIG_DASH, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)
    mx = page.evaluate(_METRICS)
    try:
        page.evaluate(_STRIP); page.wait_for_timeout(400)
    except Exception:  # noqa: BLE001
        pass
    page.screenshot(path="compare/orig_final.png", full_page=True)
    print("\n== ORIGINAL ==")
    print(json.dumps(mx))
    try:
        page.close()
    except Exception:  # noqa: BLE001
        pass
    return mx


def main():
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    try:
        car, v6mx = capture_v6(browser, context)
        ogmx = capture_orig(context)
        print("\n== SUMMARY ==")
        print(f"V6   welcome={v6mx.get('welcome_name')} balance={v6mx.get('total_balance')} cards={v6mx.get('account_cards')} chart={v6mx.get('chart_svg')}")
        print(f"ORIG welcome={ogmx.get('welcome_name')} balance={ogmx.get('total_balance')} cards={ogmx.get('account_cards')} chart={ogmx.get('chart_svg')}")
        print(f"CAROUSEL laid_out={car.get('laid_out')} visible={car.get('visible_count')} distinct_scales={car.get('distinct_scales')} pile_up_pairs={car.get('pile_up_pairs')}")
        return 0 if car.get("laid_out") else 5
    finally:
        # close any leftover pages, then stop driver (no lingering tabs)
        try:
            for pg in list(context.pages):
                try:
                    pg.close()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
