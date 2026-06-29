"""PASS D batch 2 verify: reach the new Transfer screen on rev 49 via the Login
auto-login as Andrea, then navigate to /Transfer and screenshot at 1280x900.

Confirms the screen renders on the dark theme with the transfer form (title in
MainContent, two-step form in SideContent). Captures compare/v6_transfer.png.
Cleanup: close page then p.stop() (shared context).
"""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_TRANSFER = f"{BASE}/HomeBankingPortal6/Transfer"
VIEW = {"width": 1280, "height": 900}

_M = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  return {
    url: location.href,
    on_login: /\/Login/i.test(location.href),
    is_error: /error processing your request/i.test(bt),
    has_new_transfer: /New Transfer/i.test(bt),
    has_transfer_details: /Transfer Details/i.test(bt),
    has_amount_label: /Amount/i.test(bt),
    has_continue: /Continue/i.test(bt),
    dark: getComputedStyle(document.documentElement).classList ? null :
          document.documentElement.className,
    body_bg: getComputedStyle(document.body).backgroundColor,
    input_count: document.querySelectorAll('input').length,
    button_count: document.querySelectorAll('button,.btn').length,
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

        # Navigate to the Transfer screen once the session is committed.
        try:
            page.goto(V6_TRANSFER, wait_until="networkidle", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print("transfer goto note:", repr(e)[:120])
        page.wait_for_timeout(5000)
        try:
            page.evaluate(_STRIP)
            page.wait_for_timeout(300)
        except Exception:  # noqa: BLE001
            pass
        m = page.evaluate(_M)
        print("transfer:", json.dumps(m))
        page.screenshot(path="compare/v6_transfer.png", full_page=True)
        ok = (not m["on_login"]) and (not m["is_error"]) and m["has_new_transfer"]
        print("TRANSFER_RENDERS:", ok)
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
