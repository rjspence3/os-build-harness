"""PASS D batch 3a verification: auth via V6's own Login (auto-login as Andrea),
then navigate to the two new screens (Confirmation, Requests) and screenshot each
at 1280x900. Confirm each RENDERS on the dark theme (URL stays on the screen, not
_error.html). Output: compare/v6_confirmation.png, compare/v6_requests.png.

Cleanup: page.close() each page, then p.stop() only — never browser.close().
"""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
SCREENS = {
    "v6_confirmation": f"{BASE}/HomeBankingPortal6/Confirmation",
    "v6_requests": f"{BASE}/HomeBankingPortal6/Requests",
}
VIEW = {"width": 1280, "height": 900}

_PROBE = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  return {
    url: location.href,
    is_error: /_error/i.test(location.href) || /Sorry, an unexpected error/i.test(bt) || /Something went wrong/i.test(bt),
    title: document.title,
    text_sample: bt.slice(0, 400),
    has_menu: document.querySelectorAll('[class*=menu i], nav').length,
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
    out_dir = pathlib.Path(__file__).resolve().parent.parent / "builds" / "home_banking" / "compare"
    out_dir.mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    fresh = None
    page = None
    try:
        try:
            fresh = browser.new_context(viewport=VIEW)
            page = fresh.new_page()
        except Exception:  # noqa: BLE001
            page = context.new_page()
            page.set_viewport_size(VIEW)

        # Auth: V6 Login auto-logs-in as Andrea then redirects to Dashboard.
        page.goto(V6_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(7000)
        print("after V6 login url:", page.url)

        results = {}
        all_ok = True
        for name, url in SCREENS.items():
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(4000)
            try:
                page.evaluate(_STRIP_EXT)
                page.wait_for_timeout(200)
            except Exception:  # noqa: BLE001
                pass
            shot = out_dir / f"{name}.png"
            page.screenshot(path=str(shot), full_page=True)
            probe = page.evaluate(_PROBE)
            renders = (not probe["is_error"]) and (name.split("_")[1].lower() in probe["url"].lower())
            results[name] = {"renders": renders, "probe": probe, "screenshot": str(shot)}
            all_ok = all_ok and renders
            print(f"\n== {name} ==")
            print("screenshot:", shot)
            print("probe:", json.dumps(probe))
            print("RENDERS (not _error):", renders)

        print("\nALL_RENDER:", all_ok)
        return 0 if all_ok else 5
    finally:
        try:
            if page is not None:
                page.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if fresh is not None:
                fresh.close()
        except Exception:  # noqa: BLE001
            pass
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
