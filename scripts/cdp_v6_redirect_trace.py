"""Trace the redirect/error chain for V6's protected Dashboard.

Two probes in fresh (cookie-cleared) contexts:
  A) Visit V6 /Login directly -> does the auto-login carry to a populated Dashboard?
  B) Visit V6 /Dashboard (protected) unauthenticated -> capture the FULL navigation
     chain (every document response: url + status) to see where the _error.html
     comes from (redirect to Login then error, or direct error).

No mutation. Cleanup: close pages/contexts then p.stop().
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
  return {
    url: location.href,
    title_text: (bt.slice(0,140)),
    welcome_name: m ? m[1] : null,
    has_balance_digits: /\$?\s*\d[\d,]*\.\d{2}/.test(bt),
    account_cards: document.querySelectorAll('[class*=dashboard-card],[class*=account-card]').length,
    is_error: /error processing your request/i.test(bt),
  };
}"""


def trace_context(browser, context, label, url, settle=9000):
    fresh = None
    try:
        fresh = browser.new_context(viewport=VIEW)
        fresh.clear_cookies()
        page = fresh.new_page()
    except Exception:  # noqa: BLE001
        fresh = None
        context.clear_cookies()
        page = context.new_page()
        page.set_viewport_size(VIEW)

    docs = []
    page.on("response", lambda r: (
        docs.append({"url": r.url, "status": r.status})
        if (r.request.resource_type == "document") else None
    ))
    print(f"\n== {label}: {url} ==")
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
    except Exception as e:  # noqa: BLE001
        print("  goto exception:", repr(e))
    page.wait_for_timeout(settle)
    mx = page.evaluate(_METRICS)
    print("  final:", json.dumps(mx))
    print("  document responses (redirect chain):")
    for d in docs:
        print("    ", d["status"], d["url"])
    try:
        page.close()
    except Exception:  # noqa: BLE001
        pass
    if fresh is not None:
        try:
            fresh.close()
        except Exception:  # noqa: BLE001
            pass
    return mx, docs


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    try:
        trace_context(browser, context, "A) direct V6 Login", V6_LOGIN)
        trace_context(browser, context, "B) protected V6 Dashboard unauth", V6_DASH)
        return 0
    finally:
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
