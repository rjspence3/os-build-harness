"""Decisive authenticated-session test for V6 rev 32.

V6's Dashboard is now ROLE-PROTECTED (HomeBankingPortal role, AnonymousAccess=off);
Login stays anonymous. The faithful Login.OnReady auto-logs-in as Andrea then
navigates to the protected Dashboard.

Test: clear cookies for the domain, then visit the PROTECTED Dashboard UNauthenticated.
EXPECTED if the session works: ODC bounces to V6 Login -> auto-login -> returns to
the protected Dashboard rendering Welcome, Andrea / Total Balance / account cards.

Captures:
  compare/v6_populated.png            (V6 protected dashboard, post auto-login)
  compare/orig_andrea_same_session.png (original dashboard, same Andrea creds)
Creds: demo+andrea@outsystems.com / OutSystemsDemo123 (Andrea is Core-seeded).
Cleanup: close pages/contexts, then p.stop() only.
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
ANDREA_USER = "demo+andrea@outsystems.com"
ANDREA_PASS = "OutSystemsDemo123"
VIEW = {"width": 1280, "height": 900}

_METRICS = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  const m = bt.match(/Welcome,?\s*([A-Za-z]+)/i);
  const balances = (bt.match(/\$?\s*\d[\d,]*\.\d{2}/g) || []);
  return {
    url: location.href,
    on_login: /\/Login/i.test(location.href),
    welcome_name: m ? m[1] : null,
    has_balance_digits: /\$?\s*\d[\d,]*\.\d{2}/.test(bt),
    total_balance_zero: /Total Balance[^0-9]*0\.00/i.test(bt),
    balance_samples: balances.slice(0, 6),
    account_cards: document.querySelectorAll('[class*=dashboard-card], [class*=AccountCard], [class*=account-card]').length,
    chart_svg: document.querySelectorAll('svg.highcharts-root, .highcharts-container, canvas').length,
    hb_icons: document.querySelectorAll('.hb-icon').length,
    doc_h: document.documentElement.scrollHeight,
  };
}"""

_STRIP_EXT = r"""() => {
  const sel = '[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],div[data-lastpass],#lpcustom,[id^=__lpform]';
  document.querySelectorAll(sel).forEach(e => e.remove());
}"""


def fill_login(page, user, pw):
    usr = page.query_selector("#Input_Username") or page.query_selector("input[type=text]")
    pwd = page.query_selector("#Input_Password") or page.query_selector("input[type=password]")
    if not (usr and pwd):
        return False
    usr.fill(user)
    pwd.fill(pw)
    btn = page.query_selector("button:has-text('Login')") or page.query_selector("button.OSFillParent")
    if btn:
        btn.click()
    else:
        pwd.press("Enter")
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(4000)
    return True


def capture(page, out):
    try:
        page.evaluate(_STRIP_EXT)
        page.wait_for_timeout(300)
    except Exception:  # noqa: BLE001
        pass
    page.screenshot(path=out, full_page=True)
    return page.evaluate(_METRICS)


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    fresh = None
    try:
        # --- V6: fresh context (no cookies) -> hit PROTECTED Dashboard directly ---
        try:
            fresh = browser.new_context(viewport=VIEW)
        except Exception:  # noqa: BLE001
            fresh = None
        if fresh is not None:
            try:
                fresh.clear_cookies()
            except Exception:  # noqa: BLE001
                pass
            page = fresh.new_page()
        else:
            try:
                context.clear_cookies()
            except Exception:  # noqa: BLE001
                pass
            page = context.new_page()
            page.set_viewport_size(VIEW)

        print("== STEP 1: visit PROTECTED V6 Dashboard UNauthenticated ==")
        page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        print("  landed at:", page.url, "(expect bounce to /Login)")

        # If ODC bounced to Login, the OnReady auto-login should fire. Give it time.
        page.wait_for_timeout(7000)
        print("  after auto-login window:", page.url)

        # If the OnReady auto-login didn't carry us back, drive Login form manually,
        # then re-request the protected Dashboard (now that a session may exist).
        if "/Login" in page.url:
            print("  still on Login; attempting explicit form login as Andrea")
            fill_login(page, ANDREA_USER, ANDREA_PASS)
            print("  post-form-login url:", page.url)
        if "/Dashboard" not in page.url:
            page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)
            print("  re-requested protected Dashboard ->", page.url)

        v6 = capture(page, "compare/v6_populated.png")
        print("\n== V6 (protected, post-login) ==")
        print("screenshot: compare/v6_populated.png")
        print("metrics:", json.dumps(v6))
        v6_populated = (
            (not v6["on_login"]) and v6["has_balance_digits"]
            and (v6["account_cards"] > 0) and (not v6["total_balance_zero"])
        )
        print("V6_POPULATED:", v6_populated)

        # --- ORIGINAL: same Andrea creds, fresh context, for parity baseline ---
        og = None
        try:
            ofresh = browser.new_context(viewport=VIEW)
            try:
                ofresh.clear_cookies()
            except Exception:  # noqa: BLE001
                pass
            opage = ofresh.new_page()
            print("\n== STEP 2: original app, same Andrea creds ==")
            opage.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
            opage.wait_for_timeout(2500)
            if "/Login" in opage.url:
                fill_login(opage, ANDREA_USER, ANDREA_PASS)
            if "/Dashboard" not in opage.url:
                opage.goto(ORIG_DASH, wait_until="networkidle", timeout=60000)
                opage.wait_for_timeout(4500)
            og = capture(opage, "compare/orig_andrea_same_session.png")
            print("screenshot: compare/orig_andrea_same_session.png")
            print("metrics:", json.dumps(og))
            try:
                opage.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                ofresh.close()
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            print("original capture skipped:", repr(e))

        print("\n== PARITY ==")
        print("v6  :", json.dumps({k: v6.get(k) for k in ("welcome_name", "has_balance_digits", "account_cards", "total_balance_zero", "balance_samples")}))
        if og:
            print("orig:", json.dumps({k: og.get(k) for k in ("welcome_name", "has_balance_digits", "account_cards", "total_balance_zero", "balance_samples")}))

        try:
            page.close()
        except Exception:  # noqa: BLE001
            pass
        return 0 if v6_populated else 5
    finally:
        try:
            if fresh is not None:
                fresh.close()
        except Exception:  # noqa: BLE001
            pass
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
