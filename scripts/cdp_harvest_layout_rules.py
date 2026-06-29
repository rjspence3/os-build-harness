"""Harvest the ORIGINAL Home Banking Portal's layout-shell width rules that make
the right-side two-column split work: rules whose selector mentions right-side /
layout-left-side / layout-right-side / content-middle. Read-only against the
original runtime. Output = the rule bodies to inject into the clone theme.
"""
import json, sys
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

ORIG = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard"

JS = r"""() => {
  const want = ['right-side','layout-left-side','layout-right-side','content-middle','content-top'];
  const hits = [];
  for (const sheet of document.styleSheets) {
    let rules; try{rules=sheet.cssRules;}catch(e){continue;}
    if(!rules) continue;
    for (const r of rules) {
      const sel = r.selectorText; if(!sel) continue;
      if (want.some(w => sel.indexOf(w) !== -1)) {
        const body = (r.style && r.style.cssText) ? r.style.cssText : '';
        // skip transition/animation noise
        if (/transition|animation|translate|opacity/i.test(body) && !/flex|width|grid|display/i.test(body)) continue;
        hits.push(sel + ' { ' + body + ' }');
      }
    }
  }
  return {count:hits.length, rules:hits};
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    page=None
    try:
        # prefer an open original tab
        for pg in context.pages:
            if "HomeBankingPortal/Dashboard" in pg.url:
                page = pg; break
        if page is None:
            page = context.new_page()
            page.goto(ORIG, wait_until="networkidle", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(1500)
        print("URL:", page.url)
        res = page.evaluate(JS)
        print("HARVEST_COUNT:", res["count"])
        for r in res["rules"]:
            print(r)
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
