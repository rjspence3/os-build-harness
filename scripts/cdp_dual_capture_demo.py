"""Demo-picker login (populated sample user) + dual capture ORIGINAL & V6 same-session.

The manual HB_PORTAL_USER (you@example.com) is an empty demo account ($0.00).
The original Login's 'Access your demo' picker selects a SEEDED sample user. This
script picks a chosen email chip, confirms, logs in, then screenshots both apps at
1280x900 and reports balances so we can pick a populated user for the pixel gate.

Usage: .venv/bin/python scripts/cdp_dual_capture_demo.py [email]
  default email: kyle.russell@outsystems.com
No app/model mutation. Cleanup: p.stop() only.
"""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
VIEW = {"width": 1280, "height": 900}
EMAIL = sys.argv[1] if len(sys.argv) > 1 else "kyle.russell@outsystems.com"

_STRIP = r"""() => {
  const kill = el => { try { el.remove(); } catch(e){} };
  document.querySelectorAll('[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],div[data-lastpass],#lpcustom,[id^=__lpform],[data-lastpass-root]').forEach(kill);
  // any fixed/absolute top overlay mentioning lastpass/password manager
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
    body_bg:getComputedStyle(document.body).backgroundColor,
    welcome_name:m?m[1]:null, total_balance: bal?bal[1]:null,
    hb_icons:document.querySelectorAll('.hb-icon').length,
    chart_svg:document.querySelectorAll('svg.highcharts-root,.highcharts-container,canvas').length,
    account_cards:document.querySelectorAll('[class*=dashboard-card],[class*=account-card]').length,
    colored_cards:document.querySelectorAll('[class*=colored-card]').length};
}"""


def grab(page, url, out, label):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4500)
    try:
        page.evaluate(_STRIP); page.wait_for_timeout(300)
    except Exception:  # noqa: BLE001
        pass
    page.screenshot(path=out, full_page=True)
    mx = page.evaluate(_METRICS)
    print(f"\n== {label} ==\n{out}\n{json.dumps(mx)}")
    return mx


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size(VIEW)
        page.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        if "Login" in page.url:
            page.click("text=Access your demo")
            page.wait_for_timeout(2000)
            chip = page.query_selector(f"text={EMAIL}")
            if not chip:
                print(f"email chip {EMAIL} not found"); page.screenshot(path="compare/demo_pick_fail.png"); return 3
            chip.click()
            page.wait_for_timeout(800)
            page.click("button:has-text('Confirm')")
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(2500)
            # may need to click Login after confirm
            if "Login" in page.url:
                b = page.query_selector("button:has-text('Login')") or page.query_selector("button.OSFillParent")
                if b:
                    b.click(); page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(3500)
        print("post-login url:", page.url)
        if "Login" in page.url:
            page.screenshot(path="compare/demo_login_failed.png")
            print("STILL ON LOGIN after demo pick"); return 4
        og = grab(page, ORIG_DASH, "compare/orig_dash_demo.png", f"ORIGINAL ({EMAIL})")
        v6 = grab(page, V6_DASH, "compare/v6_dash_demo.png", f"V6 ({EMAIL})")
        print("\n== PARITY ==")
        print(f"orig balance={og.get('total_balance')} cards={og.get('account_cards')} chart={og.get('chart_svg')}")
        print(f"v6   balance={v6.get('total_balance')} cards={v6.get('account_cards')} chart={v6.get('chart_svg')}")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
