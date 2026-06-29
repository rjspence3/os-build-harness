"""V6 rev-55 verification: clear cookies -> /Login (auto-login Andrea) -> Dashboard.

Confirms Fix 1 (exact balances) + Fix 2 (transaction labels) after re-seed.
Captures compare/v6_verify_dashboard.png. Cleanup: close then p.stop().
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
COMPARE = pathlib.Path(__file__).resolve().parent.parent / "builds" / "home_banking" / "compare"

_M = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  const m = bt.match(/Welcome,?\s*([A-Za-z]+)/i);
  const balances = (bt.match(/\$?\s*\d[\d,]*\.\d{2}/g) || []);
  const labels = ['Direct deposit','Grocery shopping','Cash withdrawal','Payroll credit'];
  const found = {};
  labels.forEach(l => { found[l] = bt.indexOf(l) >= 0; });
  return {
    url: location.href,
    on_login: /\/Login/i.test(location.href),
    is_error: /error processing your request/i.test(bt),
    welcome_name: m ? m[1] : null,
    has_total_6020: /6,?020\.00/.test(bt),
    has_5095: /5,?095\.00/.test(bt),
    has_925: /\b925\.00/.test(bt),
    has_1300: /1,?300\.00/.test(bt),
    has_8172: /8,?172\.00/.test(bt),
    welcome_name: m ? m[1] : null,
    balance_samples: balances.slice(0, 10),
    transaction_labels: found,
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
    COMPARE.mkdir(exist_ok=True)
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

        page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(6000)
        try:
            page.evaluate(_STRIP)
            page.wait_for_timeout(300)
        except Exception:  # noqa: BLE001
            pass
        m = page.evaluate(_M)
        print("DASH:", json.dumps(m, indent=2))
        page.screenshot(path=str(COMPARE / "v6_verify_dashboard.png"), full_page=True)
        page.screenshot(path=str(COMPARE / "v6_polished_dashboard.png"), full_page=True)
        ok = (not m["on_login"]) and (not m["is_error"]) and m["has_total_6020"] \
            and (not m["has_8172"]) and m["has_5095"] and m["has_925"] and m["has_1300"] \
            and (m["welcome_name"] == "Andrea") \
            and all(m["transaction_labels"].values())
        print("VERIFIED:", ok)
        try:
            page.close()
        except Exception:  # noqa: BLE001
            pass
        return 0 if ok else 5
    finally:
        try:
            if fresh is not None:
                fresh.close()
        except Exception:  # noqa: BLE001
            pass
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
