"""Read-only CDP probe: do the clone's app-custom classes resolve in the theme,
and how do the key Dashboard containers actually lay out at runtime?

STEP-0 follow-up for the Portal4 parity pass. The widget model already carries the
right Style classes (card-carousel-container, colored-card, dashboard-card-list,
full-height, etc.) — so the question is whether those classes EXIST in the clone's
served stylesheets and whether the containers compute a real width/height/columns.

Usage: .venv/bin/python scripts/cdp_probe_classes.py
Cleanup: p.stop() only — never browser.close().
"""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH_URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

PROBE_JS = r"""() => {
  // Which selectors resolve to at least one CSS rule across all same-origin sheets?
  const wanted = [
    'card-carousel-container','dashboard-card-list','colored-card','colored-card.orange',
    'colored-card.yellow','lightDark','slide-mini','cards-carousel','wallet-img-card',
    'wallet-img','pig-img','umbrella-img','align-right-content','chart-option',
    'total-in-chart','consolidated-position','tablePotraitPaddingLeft','balance-cntr',
    'full-height','right-side','left-side','display-flex','display-grid','gap-base',
    'ColumnsMediumLeft','columns','aside'
  ];
  const found = {};
  wanted.forEach(w => found[w] = 0);
  let sheetCount = 0, ruleCount = 0, blocked = 0;
  for (const sheet of document.styleSheets) {
    sheetCount++;
    let rules;
    try { rules = sheet.cssRules; } catch (e) { blocked++; continue; }
    if (!rules) continue;
    for (const rule of rules) {
      ruleCount++;
      const sel = rule.selectorText || '';
      if (!sel) continue;
      wanted.forEach(w => {
        const needle = '.' + w;
        if (sel.indexOf(needle) !== -1) found[w]++;
      });
    }
  }
  // Geometry of the key containers (by id/class fragment we know from the model).
  const geo = (label, sel) => {
    const el = document.querySelector(sel);
    if (!el) return {label, sel, present:false};
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {label, sel, present:true,
      w:Math.round(r.width), h:Math.round(r.height),
      left:Math.round(r.left), top:Math.round(r.top),
      display:cs.display, gridCols:cs.gridTemplateColumns,
      flexDir:cs.flexDirection, vis:cs.visibility,
      children:el.children.length};
  };
  const containers = [
    geo('Carouselcntr', '.card-carousel-container'),
    geo('cardList', '.dashboard-card-list'),
    geo('coloredCard', '.colored-card'),
    geo('rightSide', '.right-side'),
    geo('fullHeight', '.full-height'),
    geo('aside', 'aside'),
    geo('columns', '[class*=columns]'),
  ];
  // What does the main layout shell look like?
  const layout = geo('layoutMain', '.layout, [class*=layout]');
  const contentEl = document.querySelector('.main-content, [class*=main-content]');
  const sidebarCandidates = [...document.querySelectorAll('*')]
    .filter(e => { const r = e.getBoundingClientRect();
      return r.left > window.innerWidth*0.6 && r.width>180 && r.height>300; })
    .slice(0,3).map(e => ({tag:e.tagName, cls:(e.className||'').toString().slice(0,80),
      left:Math.round(e.getBoundingClientRect().left)}));
  return {sheetCount, ruleCount, blockedSheets:blocked, classRuleHits:found,
    containers, layout, sidebarCandidates, innerWidth:window.innerWidth};
}"""


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    p, browser, context = connect_with_retry()
    page = None
    try:
        for pg in context.pages:
            if "HomeBankingPortal4" in pg.url and "Dashboard" in pg.url:
                page = pg
                break
        if page is None:
            page = context.new_page()
            page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(1500)
        print("URL:", page.url)
        result = page.evaluate(PROBE_JS)
        print("PROBE:", json.dumps(result, indent=1))
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
