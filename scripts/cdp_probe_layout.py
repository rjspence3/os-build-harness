"""Read-only CDP probe #2: why is <aside> width 0, and what are the .right-side /
.left-side / aside rule bodies + the aside's ancestor chain display values?

The sidebar content renders stacked in the main column (colored-card at left=40,
full-width) and <aside> computes width 0. Either the two-column grid shell isn't
applied, or the sidebar content isn't parented under the aside. This dumps the
rule bodies and the aside ancestor chain so we can see which.
"""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH_URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

PROBE_JS = r"""() => {
  const bodies = {};
  const want = ['.right-side','.left-side','aside','.layout-side','.content','.main'];
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch(e){ continue; }
    if (!rules) continue;
    for (const rule of rules) {
      const sel = rule.selectorText; if (!sel) continue;
      want.forEach(w => {
        // match exact-ish selectors that END in the token (avoid huge compound rules)
        if (sel.split(',').some(s => s.trim() === w || s.trim().endsWith(' '+w) || s.trim().endsWith(w) && s.trim().length < 40)) {
          (bodies[w] = bodies[w] || []).push(sel + ' { ' + (rule.style.cssText||'').slice(0,200) + ' }');
        }
      });
    }
  }
  // aside ancestor chain
  const aside = document.querySelector('aside');
  const chain = [];
  let el = aside;
  while (el && el !== document.documentElement) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    chain.push({tag:el.tagName, cls:(el.className||'').toString().slice(0,90),
      w:Math.round(r.width), display:cs.display, gridCols:cs.gridTemplateColumns.slice(0,60),
      flexDir:cs.flexDirection});
    el = el.parentElement;
  }
  // Where does the first colored-card actually live (its ancestor chain to find if under aside)
  const card = document.querySelector('.colored-card');
  const cardUnderAside = card ? !!card.closest('aside') : null;
  // the content-wrapper that should be the 2-col grid
  const twocol = document.querySelector('[class*=ThemeGrid_Container], .main-content, [class*=content]');
  const tcInfo = twocol ? {cls:(twocol.className||'').toString().slice(0,90),
    display:getComputedStyle(twocol).display,
    gridCols:getComputedStyle(twocol).gridTemplateColumns.slice(0,80),
    w:Math.round(twocol.getBoundingClientRect().width)} : null;
  return {ruleBodies:bodies, asideChain:chain.slice(0,8), cardUnderAside, twocol:tcInfo};
}"""


def main() -> int:
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    page = None
    try:
        for pg in context.pages:
            if "HomeBankingPortal4" in pg.url and "Dashboard" in pg.url:
                page = pg; break
        if page is None:
            page = context.new_page()
            page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(1200)
        print("URL:", page.url)
        print("PROBE2:", json.dumps(page.evaluate(PROBE_JS), indent=1))
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
