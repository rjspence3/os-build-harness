"""V6 real user path: /Login (auto-login as Andrea) -> Dashboard, on rev 34.

Session is proven to carry server-side (SessionProbe = AUTHENTICATED, uid
7f8d7120...). Question: does the protected Dashboard now render populated when
reached via the Login flow? Also reload the Dashboard a second time to rule out
a first-render race against the double-login.

Captures compare/v6_populated.png. Cleanup: close then p.stop().
"""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
VIEW = {"width": 1280, "height": 900}

_M = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  const m = bt.match(/Welcome,?\s*([A-Za-z]+)/i);
  const balances = (bt.match(/\$?\s*\d[\d,]*\.\d{2}/g) || []);
  return {
    url: location.href,
    on_login: /\/Login/i.test(location.href),
    is_error: /error processing your request/i.test(bt),
    welcome_name: m ? m[1] : null,
    has_balance_digits: /\$?\s*\d[\d,]*\.\d{2}/.test(bt),
    total_balance_zero: /Total Balance[^0-9]*0\.00/i.test(bt),
    balance_samples: balances.slice(0, 6),
    account_cards: document.querySelectorAll('[class*=dashboard-card],[class*=account-card]').length,
    chart_svg: document.querySelectorAll('svg.highcharts-root,.highcharts-container,canvas').length,
  };
}"""

_STRIP = r"""() => {
  const sel = '[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],#lpcustom,[id^=__lpform]';
  document.querySelectorAll(sel).forEach(e => e.remove());
}"""


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    fresh = None
    try:
        try:
            fresh = browser.new_context(viewport=VIEW)
            fresh.clear_cookies()
            page = fresh.new_page()
        except Exception:  # noqa: BLE001
            fresh = None
            context.clear_cookies()
            page = context.new_page()
            page.set_viewport_size(VIEW)

        try:
            page.goto(V6_LOGIN, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print("login goto note:", repr(e)[:120])
        page.wait_for_timeout(9000)
        print("after login:", page.url)
        print("dash (auto-nav):", json.dumps(page.evaluate(_M)))

        # Reload Dashboard once the session is fully committed.
        page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(6000)
        try:
            page.evaluate(_STRIP)
            page.wait_for_timeout(300)
        except Exception:  # noqa: BLE001
            pass
        m2 = page.evaluate(_M)
        print("dash (reloaded):", json.dumps(m2))
        page.screenshot(path="compare/v6_populated.png", full_page=True)
        populated = (not m2["on_login"]) and (not m2["is_error"]) and m2["has_balance_digits"] \
            and (m2["account_cards"] > 0) and (not m2["total_balance_zero"])
        print("POPULATED:", populated)
        try:
            page.close()
        except Exception:  # noqa: BLE001
            pass
        return 0 if populated else 5
    finally:
        try:
            if fresh is not None:
                fresh.close()
        except Exception:  # noqa: BLE001
            pass
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
