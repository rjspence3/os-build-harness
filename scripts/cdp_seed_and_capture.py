"""Log into the original HB Portal (establishes the domain-wide ODC session for
HB_PORTAL_USER), POST to the V6 DemoSeed/Seed REST endpoint with credentials so
GetUserId() resolves to that session user, then navigate to the V6 Dashboard and
screenshot. Read-only on the original; the only mutation is the per-user seed via
the published endpoint.

Outputs:
  compare/v6_populated.png   (deliverable)
  prints the JSON Seed response + V6 metrics
Creds from .env HB_PORTAL_USER/HB_PORTAL_PASS (never hardcoded/echoed).
Cleanup: p.stop() only.
"""
import json
import os
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
SEED_URL = f"{BASE}/HomeBankingPortal6/rest/DemoSeed/Seed"
VIEW = {"width": 1280, "height": 900}


def _load_env(path=".env"):
    env = {}
    p = pathlib.Path(path)
    if p.exists():
        for ln in p.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                env[k.strip()] = v
    return env


_METRICS = r"""() => {
  const bt = (document.body.innerText || '').replace(/\s+/g,' ');
  return {
    url: location.href,
    welcome_name: (bt.match(/Welcome,?\s*([A-Za-z]+)/i)||[])[1] || null,
    has_balance_digits: /\$?\s*\d[\d,]*\.\d{2}/.test(bt),
    total_balance_zero: /Total Balance[^0-9]*0\.00/i.test(bt),
    account_cards: document.querySelectorAll('[class*=dashboard-card], [class*=AccountCard], [class*=account-card]').length,
    chart_svg: document.querySelectorAll('svg.highcharts-root, .highcharts-container, canvas').length,
    has_vacation: /Vacation Fund/i.test(bt),
    has_personal_loan: /Personal/i.test(bt) && /Loan/i.test(bt),
    your_goals_present: /Your Goals/i.test(bt),
    your_loans_present: /Your Loans/i.test(bt),
    body_snippet: bt.slice(0, 1200),
  };
}"""


def main() -> int:
    env = _load_env()
    user = os.environ.get("HB_PORTAL_USER") or env.get("HB_PORTAL_USER")
    pw = os.environ.get("HB_PORTAL_PASS") or env.get("HB_PORTAL_PASS")
    if not (user and pw):
        print("HB_PORTAL_USER/HB_PORTAL_PASS missing")
        return 2
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    pathlib.Path("compare").mkdir(exist_ok=True)
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size(VIEW)
        # 1) authenticate on the original
        page.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        if "Login" in page.url:
            usr = page.query_selector("#Input_Username") or page.query_selector("input[type=text]")
            pwd = page.query_selector("#Input_Password") or page.query_selector("input[type=password]")
            if not (pwd and usr):
                print("login fields not found; url=", page.url)
                return 3
            usr.fill(user)
            pwd.fill(pw)
            btn = page.query_selector("button:has-text('Login')") or page.query_selector("button.OSFillParent")
            if btn:
                btn.click()
            else:
                pwd.press("Enter")
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(4000)
        if "Login" in page.url:
            print("STILL ON LOGIN — creds rejected.")
            return 4
        print("post-login url:", page.url)

        # 2) POST to the seed endpoint from the authenticated session
        seed_js = """async (url) => {
          try {
            const r = await fetch(url, {method:'POST', credentials:'include',
              headers:{'Content-Type':'application/json'}, body:'{}'});
            const txt = await r.text();
            return {status: r.status, ok: r.ok, body: txt};
          } catch(e) { return {error: String(e)}; }
        }"""
        seed_resp = page.evaluate(seed_js, SEED_URL)
        print("SEED RESPONSE:", json.dumps(seed_resp))

        # 3) navigate to V6 dashboard and capture
        page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        try:
            page.evaluate("""() => {
              const sel = '[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],#lpcustom,[id^=__lpform]';
              document.querySelectorAll(sel).forEach(e => e.remove());
              [...document.querySelectorAll('div,iframe')].forEach(e => {
                const cs = getComputedStyle(e);
                if (cs.position === 'fixed' && /lastpass|add password/i.test(e.innerText||'')) e.remove();
              });
            }""")
            page.wait_for_timeout(300)
        except Exception:
            pass
        page.screenshot(path="compare/v6_populated.png", full_page=True)
        mx = page.evaluate(_METRICS)
        print("V6 METRICS:", json.dumps(mx))
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
