"""Log into Portal4 and screenshot the Dashboard via the CDP Chrome.

Reads creds from .env (HB_PORTAL_USER / HB_PORTAL_PASS) — never hardcoded.
Drives the CDP Chrome's existing Login tab (port 9222): fills the username +
password fields, submits, waits for the Dashboard, screenshots it, and dumps
the visible balance-band text so we can read the numbers headlessly.

Usage:
  .venv/bin/python scripts/cdp_login_screenshot.py [out.png] [--assert "k=v,k<=v"]
Prints RUNTIME_METRICS json every run. With --assert, exits 5 if any clause
fails — the loop's hard runtime gate (beat 7): a turn is NOT done until CDP
confirms the expected delta actually rendered. Ops: = <= >= < >.
Cleanup: p.stop() only — never browser.close() (kills Rob's Chrome).
"""
import json
import os
import pathlib
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

LOGIN_URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Login"
DASH_URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
_flags = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else True) for a in sys.argv[1:] if a.startswith("--")}
OUT = _args[0] if _args else "compare/portal4_dashboard.png"
assert_spec = _flags.get("--assert")


def _load_env(path=".env"):
    """Tiny .env reader (strips matching surrounding quotes)."""
    env = {}
    p = pathlib.Path(path)
    if not p.exists():
        return env
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        env[k.strip()] = v
    return env


def main() -> int:
    env = _load_env()
    user = os.environ.get("HB_PORTAL_USER") or env.get("HB_PORTAL_USER")
    pw = os.environ.get("HB_PORTAL_PASS") or env.get("HB_PORTAL_PASS")
    if not user or not pw:
        print("HB_PORTAL_USER / HB_PORTAL_PASS not found in env or .env")
        return 2
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1

    p, browser, context = connect_with_retry()
    try:
        page = next((pg for pg in context.pages if "HomeBankingPortal4" in pg.url), None)
        if page is None:
            page = context.new_page()
        if "Dashboard" not in page.url:
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=45000)

        if "Login" in page.url:
            # OutSystems renders a username text/email input + a password input.
            pwd = page.query_selector("input[type=password]")
            usr = page.query_selector("input[type=email]") or page.query_selector("input[type=text]")
            if not (pwd and usr):
                print("Could not locate login fields; current URL:", page.url)
                page.screenshot(path="compare/portal4_login_debug.png")
                return 3
            usr.fill(user)
            pwd.fill(pw)
            # Submit via Enter: the visible "Save"-labelled button is an unwired
            # stub on this clone; the OutSystems form submits on Enter.
            pwd.press("Enter")
            page.wait_for_load_state("networkidle", timeout=45000)

        print("post-login URL:", page.url)
        if "Login" in page.url:
            print("STILL ON LOGIN — creds rejected for this app, or extra step (MFA) needed.")
            page.screenshot(path="compare/portal4_login_failed.png")
            return 4

        # Ensure we're on the Dashboard.
        if "Dashboard" not in page.url:
            page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)  # let aggregates + OnAfterFetch settle
        page.screenshot(path=OUT, full_page=True)
        print("screenshot:", OUT)

        metrics = page.evaluate(_METRICS_JS)
        print("RUNTIME_METRICS:", json.dumps(metrics))
        if assert_spec:
            failures = _check_assertions(metrics, assert_spec)
            for f in failures:
                print("ASSERT FAIL:", f)
            if failures:
                return 5  # hard-fail the turn: published but did not render as expected
            print("ASSERT OK:", assert_spec)
    finally:
        p.stop()
    return 0


# Leaf-element runtime metrics for the Dashboard — the un-fakeable "did it
# actually render" numbers a visual turn asserts against (beat 7).
_METRICS_JS = r"""() => {
  const leaves = Array.from(document.querySelectorAll('*')).filter(e => e.children.length === 0);
  const txt = e => (e.textContent || '').trim();
  const ICON = /^(transfer|scan|insights|columnchart|plussquare|eyeshow|eyehide|banknote)$/;
  return {
    // a LEAK is icon-name text NOT rendered by the hb-icon font (i.e. raw text).
    // Elements inside/at a .hb-icon ancestor render as a glyph — not a leak.
    leaked_icons: leaves.filter(e => ICON.test(txt(e)) && !e.closest('.hb-icon')).length,
    text_stubs: leaves.filter(e => txt(e) === 'text').length,
    hb_icons: document.querySelectorAll('.hb-icon').length,
    button_logout_raw: leaves.filter(e => txt(e) === 'ButtonLogout' || txt(e) === 'LogoutLogout').length,
    nav_menu: document.querySelectorAll('nav, [class*=menu], [class*=Menu]').length,
    // full-parity-vs-original structural targets (spec baseline from the live
    // original: dark_mode=1, main_width>=1000, nav_menu~9). hb_icons is partly
    // data-driven (account-card icons need rows) so it's informational, not asserted.
    dark_mode: document.documentElement.classList.contains('dark-mode') ? 1 : 0,
    main_width: Math.round((document.querySelector('.main-content,[class*=main-content],[class*=ThemeGrid_Container]') || {getBoundingClientRect:()=>({width:0})}).getBoundingClientRect().width),
    // STRUCTURAL sameness-vs-original (data-independent). Targets from the live
    // original: card_columns=3, right_sidebar=1, chart>=1 (orig 107). A green
    // gate must MATCH these — main_width alone was a false-pass proxy.
    card_columns: (() => {
      const vw = window.innerWidth;
      const cards = [...document.querySelectorAll('[class*=card],[class*=cntr],[class*=colored]')]
        .map(e => e.getBoundingClientRect()).filter(r => r.width > 120 && r.height > 60);
      const rows = {};
      cards.forEach(r => { const k = Math.round(r.top / 40); (rows[k] = rows[k] || []).push(Math.round(r.left)); });
      return Math.max(0, ...Object.values(rows).map(xs => new Set(xs).size));
    })(),
    right_sidebar: [...document.querySelectorAll('*')].some(e => { const r = e.getBoundingClientRect(); return r.left > window.innerWidth * 0.6 && r.width > 180 && r.height > 300; }) ? 1 : 0,
    chart: document.querySelectorAll('canvas,svg,[class*=chart],[class*=Chart]').length,
    // THEME-ANCHORING: elements with inline color/background won't flip with the
    // theme (dark mode) — they're hardcoded, not anchored to theme tokens/classes.
    // High count = parity will break on dark-mode activation. Target: low / 0.
    inline_colored: [...document.querySelectorAll('[style]')].filter(e => /(^|;)\s*(color|background(-color)?)\s*:/i.test(e.getAttribute('style') || '')).length,
  };
}"""


def _check_assertions(metrics: dict, spec: str) -> list[str]:
    """spec: comma-separated `key<op>value`, ops: = <= >= < >. Returns failures."""
    import re
    failures = []
    for clause in spec.split(","):
        clause = clause.strip()
        if not clause:
            continue
        m = re.match(r"^(\w+)\s*(<=|>=|=|<|>)\s*(-?\d+)$", clause)
        if not m:
            failures.append(f"{clause} (unparseable)")
            continue
        key, op, val = m.group(1), m.group(2), int(m.group(3))
        if key not in metrics:
            failures.append(f"{clause} (no such metric; have {list(metrics)})")
            continue
        actual = metrics[key]
        ok = {"=": actual == val, "<=": actual <= val, ">=": actual >= val,
              "<": actual < val, ">": actual > val}[op]
        if not ok:
            failures.append(f"{clause} (actual {key}={actual})")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
