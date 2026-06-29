"""What does .OSInline resolve to in the ORIGINAL, and is the rule present in the
CLONE? Also dump the original's two flex-item divs' full class + the rule that
sizes them. This isolates why the original's columns size (741/288) but the
clone's collapse (340/40).
"""
import json, sys, time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

def rule_dump_js(token):
    return r"""() => {
      const tok = '%s';
      const hits = [];
      for (const sheet of document.styleSheets) {
        let rules; try{rules=sheet.cssRules;}catch(e){continue;}
        if(!rules) continue;
        for (const r of rules) { const s=r.selectorText; if(!s) continue;
          if (s.indexOf(tok) !== -1) hits.push(s + ' { ' + ((r.style&&r.style.cssText)||'').slice(0,180) + ' }'); } }
      return hits;
    }""" % token

ORIG = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard"
CLONE = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

def read(page, url, bust=False):
    u = url + ("?_cb="+str(int(time.time())) if bust else "")
    page.goto(u, wait_until="networkidle", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(1500)
    osinline = page.evaluate(rule_dump_js("OSInline"))
    return {"url":page.url, "OSInline_rules":osinline}

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    try:
        page=context.new_page(); page.set_viewport_size({"width":1280,"height":900})
        print("ORIGINAL:", json.dumps(read(page, ORIG), indent=1))
        print("CLONE:", json.dumps(read(page, CLONE, bust=True), indent=1))
        page.close()
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
