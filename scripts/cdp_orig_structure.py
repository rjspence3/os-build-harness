"""Read the ORIGINAL Dashboard's main-content subtree: the direct children of
.main-content and their widths/display, plus layout-left-side / layout-right-side
geometry. This shows EXACTLY what DOM structure + computed layout produces the
working two-column split, so we can replicate it in the clone.
"""
import json, sys
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

ORIG = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard"

JS = r"""() => {
  const info = (el) => { if(!el) return null; const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
    return {tag:el.tagName, cls:(el.className||'').toString().slice(0,70),
      w:Math.round(r.width), left:Math.round(r.left), display:cs.display, flexGrow:cs.flexGrow,
      flexBasis:cs.flexBasis, width:cs.width, children:el.children.length}; };
  const mc = document.querySelector('.main-content');
  const out = {mainContent: info(mc)};
  if (mc) {
    out.directChildren = [...mc.children].map(info);
    // depth-2
    out.grandChildren = [];
    [...mc.children].forEach(c => [...c.children].forEach(g => out.grandChildren.push(info(g))));
  }
  out.lls = info(document.querySelector('.layout-left-side'));
  out.lrs = info(document.querySelector('.layout-right-side'));
  // parents of layout-left/right-side (the actual flex items)
  const lls = document.querySelector('.layout-left-side');
  const lrs = document.querySelector('.layout-right-side');
  out.llsParent = lls ? info(lls.parentElement) : null;
  out.lrsParent = lrs ? info(lrs.parentElement) : null;
  out.llsGrandparent = lls ? info(lls.parentElement && lls.parentElement.parentElement) : null;
  return out;
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    page=None
    try:
        for pg in context.pages:
            if "HomeBankingPortal/Dashboard" in pg.url: page=pg; break
        if page is None:
            page=context.new_page(); page.goto(ORIG, wait_until="networkidle", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(1500)
        print("URL:", page.url)
        print("ORIG_STRUCT:", json.dumps(page.evaluate(JS), indent=1))
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
