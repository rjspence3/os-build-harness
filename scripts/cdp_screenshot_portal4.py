"""Screenshot the Portal4 Dashboard via Rob's authenticated CDP Chrome.

Reuses the live logged-in session on port 9222 (Path A — no creds needed).
Finds an existing HomeBankingPortal4 tab if open; otherwise opens a new page to
the Dashboard URL (the profile's session cookie carries the auth). Saves a full
screenshot + dumps the visible balance-band text so we can confirm revs 34/35
compute real totals instead of "000".

Usage: .venv/bin/python scripts/cdp_screenshot_portal4.py [out.png]
Cleanup uses p.stop() — never browser.close() (that kills Rob's Chrome).
"""
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH_URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"
OUT = sys.argv[1] if len(sys.argv) > 1 else "compare/portal4_rev35_dashboard.png"


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    p, browser, context = connect_with_retry()
    page = None
    try:
        # Prefer an already-open Portal4 tab (keeps Rob's exact session/state).
        for pg in context.pages:
            if "HomeBankingPortal4" in pg.url:
                page = pg
                break
        if page is None:
            page = context.new_page()
            page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
        else:
            # Make sure we're on the Dashboard, not Login/another screen.
            if "Dashboard" not in page.url:
                page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
            page.wait_for_load_state("networkidle", timeout=45000)

        print("URL:", page.url)
        if "Login" in page.url:
            print("LANDED ON LOGIN — session not authenticated for Portal4. "
                  "Log into the app in the CDP Chrome first (Path A).")
        page.screenshot(path=OUT, full_page=True)
        print("screenshot:", OUT)

        # Dump candidate balance text so we can read the numbers without eyes.
        for sel in ["text=Total Balance", "text=My Assets", "[class*=counter]", "[class*=balance]"]:
            try:
                for el in page.query_selector_all(sel)[:6]:
                    t = (el.inner_text() or "").strip().replace("\n", " ")
                    if t:
                        print(f"  [{sel}] {t[:120]}")
            except Exception:
                pass
    finally:
        if page is not None and page not in (context.pages[:0]):
            # Only close pages WE opened; leave Rob's pre-existing tab alone.
            pass
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
