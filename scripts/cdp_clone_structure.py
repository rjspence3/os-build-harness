"""Clone (rev 48+) main-content subtree structure, cache-busted. Compare to the
original to see whether the two OSInline flex items size correctly and which
rule is missing.
"""
import json, sys, time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

JS = r"""() => {
  const info = (el) => { if(!el) return null; const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
    return {tag:el.tagName, cls:(el.className||'').toString().slice(0,70),
      w:Math.round(r.width), left:Math.round(r.left), display:cs.display, flexGrow:cs.flexGrow,
      flexBasis:cs.flexBasis, minH:cs.minHeight, children:el.children.length}; };
  const mc = document.querySelector('.main-content');
  const out = {mainContent: info(mc)};
  if (mc) out.directChildren = [...mc.children].map(info);
  out.lls = info(document.querySelector('.layout-left-side'));
  out.lrs = info(document.querySelector('.layout-right-side'));
  const lls = document.querySelector('.layout-left-side');
  out.llsParent = lls ? info(lls.parentElement) : null;
  return out;
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    page=None
    try:
        page=context.new_page(); page.set_viewport_size({"width":1280,"height":900})
        page.goto(DASH + "?_cb=" + str(int(time.time())), wait_until="networkidle", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(2000)
        print("URL:", page.url)
        print("CLONE_STRUCT:", json.dumps(page.evaluate(JS), indent=1))
        page.close()
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
