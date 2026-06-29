"""Cache-busted structural-metrics read of the Portal4 Dashboard (same metric JS as
the gate, but forces a fresh page load with a cache-buster query param so we don't
read a stale cached DOM). Assumes the CDP Chrome already has an authenticated session.
"""
import json, sys, time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

METRICS_JS = r"""() => {
  const leaves = Array.from(document.querySelectorAll('*')).filter(e => e.children.length === 0);
  const txt = e => (e.textContent || '').trim();
  const ICON = /^(transfer|scan|insights|columnchart|plussquare|eyeshow|eyehide|banknote)$/;
  return {
    leaked_icons: leaves.filter(e => ICON.test(txt(e)) && !e.closest('.hb-icon')).length,
    text_stubs: leaves.filter(e => txt(e) === 'text').length,
    hb_icons: document.querySelectorAll('.hb-icon').length,
    button_logout_raw: leaves.filter(e => txt(e) === 'ButtonLogout' || txt(e) === 'LogoutLogout').length,
    nav_menu: document.querySelectorAll('nav, [class*=menu], [class*=Menu]').length,
    dark_mode: document.documentElement.classList.contains('dark-mode') ? 1 : 0,
    main_width: Math.round((document.querySelector('.main-content,[class*=main-content],[class*=ThemeGrid_Container]') || {getBoundingClientRect:()=>({width:0})}).getBoundingClientRect().width),
    card_columns: (() => {
      const cards = [...document.querySelectorAll('[class*=card],[class*=cntr],[class*=colored]')]
        .map(e => e.getBoundingClientRect()).filter(r => r.width > 120 && r.height > 60);
      const rows = {};
      cards.forEach(r => { const k = Math.round(r.top / 40); (rows[k] = rows[k] || []).push(Math.round(r.left)); });
      return Math.max(0, ...Object.values(rows).map(xs => new Set(xs).size));
    })(),
    right_sidebar: [...document.querySelectorAll('*')].some(e => { const r = e.getBoundingClientRect(); return r.left > window.innerWidth * 0.6 && r.width > 180 && r.height > 300; }) ? 1 : 0,
    chart: document.querySelectorAll('canvas,svg,[class*=chart],[class*=Chart]').length,
    inline_colored: [...document.querySelectorAll('[style]')].filter(e => /(^|;)\s*(color|background(-color)?)\s*:/i.test(e.getAttribute('style') || '')).length,
  };
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    page=None
    try:
        page = context.new_page()
        page.set_viewport_size({"width":1280,"height":900})
        url = DASH + "?_cb=" + str(int(time.time()))
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        print("URL:", page.url)
        print("RUNTIME_METRICS:", json.dumps(page.evaluate(METRICS_JS)))
        page.screenshot(path="compare/portal4_rev48_bust.png", full_page=True)
        print("screenshot: compare/portal4_rev48_bust.png")
        page.close()
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
