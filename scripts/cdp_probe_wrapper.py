"""Does the clone's MainContentWrapper carry 'right-side display-flex' at runtime,
and is there a layout-right-side element with width? Disambiguates: missing class
on the wrapper (renderer dropped the conditional suffix) vs missing theme rule.
"""
import json, sys
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH_URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

JS = r"""() => {
  const out = {};
  const mc = document.querySelector('.main-content.ThemeGrid_Container, .main-content');
  if (mc) {
    out.mainContent = {cls:(mc.className||'').toString(),
      display:getComputedStyle(mc).display,
      hasRightSide:mc.classList.contains('right-side'),
      hasDisplayFlex:mc.classList.contains('display-flex'),
      w:Math.round(mc.getBoundingClientRect().width)};
  }
  const lls = document.querySelector('.layout-left-side');
  const lrs = document.querySelector('.layout-right-side');
  out.leftSide = lls ? {w:Math.round(lls.getBoundingClientRect().width),
    left:Math.round(lls.getBoundingClientRect().left),
    display:getComputedStyle(lls).display} : null;
  out.rightSide = lrs ? {w:Math.round(lrs.getBoundingClientRect().width),
    left:Math.round(lrs.getBoundingClientRect().left),
    display:getComputedStyle(lrs).display,
    children:lrs.children.length,
    innerH:Math.round(lrs.getBoundingClientRect().height)} : 'NO .layout-right-side ELEMENT';
  // does .right-side resolve to a flex rule anywhere?
  let rightSideFlexRule = null;
  for (const sheet of document.styleSheets) {
    let rules; try{rules=sheet.cssRules;}catch(e){continue;}
    if(!rules) continue;
    for (const r of rules) {
      const s=r.selectorText; if(!s) continue;
      if (s.split(',').some(x=>x.trim()==='.main-content.right-side' || x.trim()==='.right-side')) {
        rightSideFlexRule = s + ' { ' + (r.style.cssText||'').slice(0,160) + ' }';
      }
    }
  }
  out.rightSideRule = rightSideFlexRule;
  return out;
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    page=None
    try:
        for pg in context.pages:
            if "HomeBankingPortal4" in pg.url and "Dashboard" in pg.url: page=pg; break
        if page is None:
            page=context.new_page(); page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(1200)
        print("URL:", page.url)
        print("WRAP:", json.dumps(page.evaluate(JS), indent=1))
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
