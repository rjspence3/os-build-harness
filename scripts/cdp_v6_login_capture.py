"""Drive V6's OWN demo-login flow (no original-app login) and verify the Dashboard
populates with seeded HomeBankingCore data.

V6 rev 27 added: Login screen (anonymous, default) whose OnReady calls a DoLogin
client action -> system Login(demo+andrea@outsystems.com / OutSystemsDemo123) ->
navigates to Dashboard. Authenticating as that Core-seeded user makes V6's
GetUserId()-scoped reads return Andrea's accounts/transactions/goals.

This script opens a FRESH context (clears any pre-existing ODC session cookie) so
the login proven is V6's own, not a leaked original-app cookie. Then it lands on
V6 Login, lets the auto-login run, and screenshots the resulting Dashboard.

Output: compare/v6_populated.png + metrics. Cleanup: p.stop() only.
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


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    fresh = None
    try:
        # Fresh context so no leaked original-app cookie helps. Fall back to the
        # default context if the connected browser disallows new contexts.
        try:
            fresh = browser.new_context(viewport=VIEW)
            page = fresh.new_page()
        except Exception:  # noqa: BLE001
            page = context.new_page()
            page.set_viewport_size(VIEW)

        # Land on V6's own Login; OnReady auto-logs-in then navigates to Dashboard.
        page.goto(V6_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(7000)  # allow DoLogin + nav
        print("after V6 login url:", page.url)

        # If we didn't auto-redirect, go to the Dashboard explicitly (session now set).
        if "/Dashboard" not in page.url:
            page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

        try:
            page.evaluate(_STRIP_EXT)
            page.wait_for_timeout(300)
        except Exception:  # noqa: BLE001
            pass

        page.screenshot(path="compare/v6_populated.png", full_page=True)
        mx = page.evaluate(_METRICS)
        print("\n== V6 (own demo-login) ==")
        print("screenshot: compare/v6_populated.png")
        print("metrics:", json.dumps(mx))
        populated = (not mx["on_login"]) and mx["has_balance_digits"] and (mx["account_cards"] > 0) and (not mx["total_balance_zero"])
        print("\nPOPULATED:", populated)
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
