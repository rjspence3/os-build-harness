"""V6 rev-56 PersonalLoan verify: auto-login Andrea -> /PersonalLoan.
Confirms "Personal Loan" title renders ONCE in the header Title zone.
Captures compare/v6_personalloan2.png. close then p.stop()."""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_SCREEN = f"{BASE}/HomeBankingPortal6/PersonalLoan"
VIEW = {"width": 1280, "height": 900}
COMPARE = pathlib.Path(__file__).resolve().parent.parent / "builds" / "home_banking" / "compare"

# Count "Personal Loan" text nodes inside the header zone (Title placeholder
# lives in .header-top / .header-content). Count exact-match heading expressions.
_M = r"""() => {
  const all = Array.from(document.querySelectorAll('*'));
  const exact = all.filter(e => {
    const direct = Array.from(e.childNodes)
      .filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    return direct === 'Personal Loan';
  });
  // restrict to header zone for the title-triplication check
  const header = document.querySelector('.header-top, .header-content, [class*=header]');
  const inHeader = exact.filter(e => header && header.contains(e));
  return {
    url: location.href,
    on_login: /\/Login/i.test(location.href),
    is_error: /error processing your request/i.test((document.body.innerText||'')),
    exact_personal_loan_nodes_total: exact.length,
    exact_personal_loan_nodes_in_header: inHeader.length,
  };
}"""

_STRIP = r"""() => {
  const sel = '[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],#lpcustom,[id^=__lpform]';
  document.querySelectorAll(sel).forEach(e => e.remove());
}"""


def main() -> int:
    if not is_chrome_available():
        print("CDP not reachable")
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
            print("login note:", repr(e)[:100])
        page.wait_for_timeout(9000)
        try:
            page.goto(V6_SCREEN, wait_until="networkidle", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print("goto note:", repr(e)[:100])
        page.wait_for_timeout(5000)
        try:
            page.evaluate(_STRIP)
        except Exception:  # noqa: BLE001
            pass
        m = page.evaluate(_M)
        print("PERSONALLOAN:", json.dumps(m, indent=2))
        page.screenshot(path=str(COMPARE / "v6_personalloan2.png"), full_page=True)
        ok = (not m["on_login"]) and (not m["is_error"]) \
            and m["exact_personal_loan_nodes_in_header"] == 1
        print("TITLE_ONCE_IN_HEADER:", ok)
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
