"""Deep-inspect V6 Dashboard after auto-login: total band, account cards,
transactions table rows. Read-only. close then p.stop()."""
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
  const out = {};
  const txt = e => (e ? (e.innerText||'').replace(/\s+/g,' ').trim() : null);
  // Total balance band: find element containing 'Total Balance'
  const all = Array.from(document.querySelectorAll('*'));
  const tb = all.find(e => /Total Balance/i.test(e.childNodes && Array.from(e.childNodes).filter(n=>n.nodeType===3).map(n=>n.textContent).join('')||'') );
  out.total_band_context = (function(){
    const hit = all.find(e => /Total Balance/i.test(e.innerText||'') && e.children.length<=4);
    return hit ? txt(hit) : null;
  })();
  // Tables
  out.tables = Array.from(document.querySelectorAll('table')).map(t => ({
    headers: Array.from(t.querySelectorAll('th')).map(th=>txt(th)),
    rows: Array.from(t.querySelectorAll('tbody tr')).slice(0,8).map(tr =>
      Array.from(tr.querySelectorAll('td')).map(td=>txt(td)))
  }));
  // Any list items that look like transactions
  out.list_rows = Array.from(document.querySelectorAll('[class*=list] li,[class*=transaction],[class*=Transaction]'))
    .slice(0,12).map(e=>txt(e)).filter(Boolean);
  out.welcome = (function(){
    const m=(document.body.innerText||'').match(/Welcome,?\s*([^\n<]{0,40})/i);
    return m?m[1].trim():null;
  })();
  return out;
}"""

_STRIP = r"""() => {
  const sel = '[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],#lpcustom,[id^=__lpform]';
  document.querySelectorAll(sel).forEach(e => e.remove());
}"""


def main() -> int:
    if not is_chrome_available():
        print("CDP not reachable")
        return 1
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
        page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(6000)
        try:
            page.evaluate(_STRIP)
        except Exception:  # noqa: BLE001
            pass
        print(json.dumps(page.evaluate(_M), indent=2))
        try:
            page.close()
        except Exception:  # noqa: BLE001
            pass
        return 0
    finally:
        try:
            if fresh is not None:
                fresh.close()
        except Exception:  # noqa: BLE001
            pass
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
