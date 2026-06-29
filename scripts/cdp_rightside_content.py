"""What is actually inside the clone's layout-right-side? Dump each descendant's
tag/class/width/height/text so we can tell if the static sidebar cards (Personal
Loan / Define Goal / Retirement) are present-but-collapsed or simply absent.
Cache-busted, 1280 viewport.
"""
import json, sys, time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

JS = r"""() => {
  const lrs = document.querySelector('.layout-right-side');
  if(!lrs) return {present:false};
  const r = lrs.getBoundingClientRect();
  const kids = [...lrs.querySelectorAll('*')].slice(0,40).map(e=>{
    const rr=e.getBoundingClientRect();
    return {tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
      w:Math.round(rr.width), h:Math.round(rr.height),
      txt:(e.textContent||'').trim().slice(0,30)};
  }).filter(k=>k.txt || k.w>5);
  // also: any .colored-card anywhere and its position
  const cards = [...document.querySelectorAll('.colored-card')].map(e=>{
    const rr=e.getBoundingClientRect();
    return {cls:(e.className||'').toString().slice(0,50), w:Math.round(rr.width),
      h:Math.round(rr.height), left:Math.round(rr.left), top:Math.round(rr.top)};
  });
  return {present:true, lrs:{w:Math.round(r.width),h:Math.round(r.height),left:Math.round(r.left)},
    descendants:kids, coloredCards:cards};
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    try:
        page=context.new_page(); page.set_viewport_size({"width":1280,"height":900})
        page.goto(DASH+"?_cb="+str(int(time.time())), wait_until="networkidle", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(2000)
        print("URL:", page.url)
        print("RIGHTSIDE:", json.dumps(page.evaluate(JS), indent=1))
        page.close()
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
