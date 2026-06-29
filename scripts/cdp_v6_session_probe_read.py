"""Read V6's server-side session identity via the SessionProbe screen (rev 34).

SessionProbe (anonymous) runs GetSessionInfoServer at load: returns
  SERVER GetUserId: <id text>
  SERVER Email: ANONYMOUS/NULL | AUTHENTICATED

Two probes, each in a fresh cookie-cleared context:
  A) Baseline: visit /SessionProbe with NO prior login -> expect ANONYMOUS/NULL.
  B) After V6 own-Login auto-login: visit /Login (auto-logs-in as Andrea),
     then visit /SessionProbe in the SAME context -> does GetUserId() resolve
     to Andrea's id (AUTHENTICATED) or stay ANONYMOUS/NULL?

This is the decisive server-side test of whether the session carries.
Cleanup: close pages/contexts then p.stop().
"""
import json
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_PROBE = f"{BASE}/HomeBankingPortal6/SessionProbe"
VIEW = {"width": 1280, "height": 900}

_PROBE_READ = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  const uid = bt.match(/SERVER GetUserId:\s*([^\n]*?)(?:\s*SERVER|$)/i);
  const email = bt.match(/SERVER Email:\s*([A-Za-z\/]+)/i);
  return {
    url: location.href,
    is_error: /error processing your request/i.test(bt),
    raw: bt.slice(0, 200),
    server_userid: uid ? uid[1].trim() : null,
    server_auth_flag: email ? email[1].trim() : null,
  };
}"""


def fresh_page(browser, context):
    try:
        fresh = browser.new_context(viewport=VIEW)
        fresh.clear_cookies()
        return fresh, fresh.new_page()
    except Exception:  # noqa: BLE001
        context.clear_cookies()
        pg = context.new_page()
        pg.set_viewport_size(VIEW)
        return None, pg


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    try:
        # A) baseline anonymous
        fa, pa = fresh_page(browser, context)
        print("== A) baseline: /SessionProbe, no login ==")
        pa.goto(V6_PROBE, wait_until="networkidle", timeout=60000)
        pa.wait_for_timeout(4000)
        a = pa.evaluate(_PROBE_READ)
        print(json.dumps(a))
        pa.screenshot(path="compare/v6_sessionprobe_anon.png")
        try:
            pa.close()
        except Exception:  # noqa: BLE001
            pass
        if fa:
            fa.close()

        # B) after V6 own auto-login
        fb, pb = fresh_page(browser, context)
        print("\n== B) after V6 /Login auto-login, then /SessionProbe (same context) ==")
        pb.goto(V6_LOGIN, wait_until="networkidle", timeout=60000)
        pb.wait_for_timeout(8000)  # allow DoLogin (login -> grant role -> login2) + nav
        print("  post-login url:", pb.url)
        pb.goto(V6_PROBE, wait_until="networkidle", timeout=60000)
        pb.wait_for_timeout(4000)
        b = pb.evaluate(_PROBE_READ)
        print(json.dumps(b))
        pb.screenshot(path="compare/v6_sessionprobe_after_login.png")
        try:
            pb.close()
        except Exception:  # noqa: BLE001
            pass
        if fb:
            fb.close()

        print("\n== DECISIVE ==")
        print(f"anonymous baseline : userid='{a.get('server_userid')}' flag={a.get('server_auth_flag')}")
        print(f"after V6 auto-login : userid='{b.get('server_userid')}' flag={b.get('server_auth_flag')}")
        carries = (b.get("server_auth_flag") == "AUTHENTICATED") and bool(b.get("server_userid"))
        print("SESSION CARRIES SERVER-SIDE:", carries)
        return 0
    finally:
        p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
