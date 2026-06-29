"""Authenticate once (original app), then capture ORIGINAL + V6 Dashboards in the
SAME session at the SAME viewport — the precondition for a valid pixel comparison.

Why: the original Dashboard is auth-gated (sample user "Andrea" with seeded
HomeBankingCore data); V6 references the same Core. ODC end-user sessions are
domain-wide, so logging into the original sets a cookie that V6 also honours →
V6's GetUserId() resolves to the same user → same data renders. No app/model
mutation, no HomeBankingCore data writes — login + read-only screenshots only.

Outputs (both at 1280x900, full_page):
  compare/orig_dash_live.png   + ORIG metrics
  compare/v6_dash_live.png     + V6 metrics
Creds from .env HB_PORTAL_USER/HB_PORTAL_PASS (never hardcoded/echoed).
Cleanup: p.stop() only.
"""
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


_METRICS = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  const m = bt.match(/Welcome,?\s*([A-Za-z]+)/i);
  return {
    url: location.href,
    on_login: /\/Login/i.test(location.href),
    body_bg: getComputedStyle(document.body).backgroundColor,
    dark_mode: document.documentElement.classList.contains('dark-mode'),
    welcome_name: m ? m[1] : null,
    has_balance_digits: /\$?\s*\d[\d,]*\.\d{2}/.test(bt),
    total_balance_zero: /Total Balance[^0-9]*0\.00/i.test(bt),
    hb_icons: document.querySelectorAll('.hb-icon').length,
    chart_svg: document.querySelectorAll('svg.highcharts-root, .highcharts-container, canvas').length,
    colored_cards: document.querySelectorAll('[class*=colored-card]').length,
    account_cards: document.querySelectorAll('[class*=dashboard-card], [class*=AccountCard], [class*=account-card]').length,
    doc_h: document.documentElement.scrollHeight,
  };
}"""


_STRIP_EXT = r"""() => {
  // Remove browser-extension injected overlays (LastPass etc.) that contaminate screenshots
  const sel = '[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],div[data-lastpass],#lpcustom,[id^=__lpform]';
  document.querySelectorAll(sel).forEach(e => e.remove());
  // also nuke fixed-position top-right overlays that aren't ours
  [...document.querySelectorAll('div,iframe')].forEach(e => {
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    if (cs.position === 'fixed' && r.top < 60 && r.right > window.innerWidth - 20 && r.width > 300 && r.width < 520 && /lastpass|password/i.test(e.innerText||'')) e.remove();
  });
}"""


def grab(page, url, out, label, settle=4500):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(settle)
    try:
        page.evaluate(_STRIP_EXT)
        page.wait_for_timeout(300)
    except Exception:  # noqa: BLE001
        pass
    page.screenshot(path=out, full_page=True)
    mx = page.evaluate(_METRICS)
    print(f"\n== {label} ==\nscreenshot: {out}\nmetrics: {json.dumps(mx)}")
    return mx


def main() -> int:
    env = _load_env()
    user = os.environ.get("HB_PORTAL_USER") or env.get("HB_PORTAL_USER")
    pw = os.environ.get("HB_PORTAL_PASS") or env.get("HB_PORTAL_PASS")
    if not (user and pw):
        print("HB_PORTAL_USER/HB_PORTAL_PASS missing")
        return 2
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size(VIEW)
        # 1) authenticate on the original
        page.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        if "Login" in page.url:
            usr = page.query_selector("#Input_Username") or page.query_selector("input[type=text]")
            pwd = page.query_selector("#Input_Password") or page.query_selector("input[type=password]")
            if not (pwd and usr):
                page.screenshot(path="compare/orig_login_debug.png")
                print("login fields not found; url=", page.url, "(see compare/orig_login_debug.png)")
                return 3
            usr.fill(user)
            pwd.fill(pw)
            btn = page.query_selector("button:has-text('Login')") or page.query_selector("button.OSFillParent")
            if btn:
                btn.click()
            else:
                pwd.press("Enter")
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(4000)
        print("post-login url:", page.url)
        if "Login" in page.url:
            page.screenshot(path="compare/orig_login_failed.png")
            print("STILL ON LOGIN — creds rejected or MFA/demo-picker required.")
            return 4
        # 2) capture both in the same session
        og = grab(page, ORIG_DASH, "compare/orig_dash_live.png", "ORIGINAL (authed)")
        v6 = grab(page, V6_DASH, "compare/v6_dash_live.png", "V6 (same session)")
        print("\n== DATA-PARITY CHECK ==")
        print(f"orig welcome={og.get('welcome_name')} has_balance={og.get('has_balance_digits')}")
        print(f"v6   welcome={v6.get('welcome_name')} has_balance={v6.get('has_balance_digits')} total0={v6.get('total_balance_zero')}")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
