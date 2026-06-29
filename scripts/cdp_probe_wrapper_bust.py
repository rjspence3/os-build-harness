"""Cache-busted re-read of the MainContentWrapper classes. Appends a cache-buster
query param and hard-reloads, then dumps the wrapper class + the raw outerHTML
opening tag of the .main-content element to see what HTML the server actually sent.
"""
import json, sys, time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

DASH = "https://your-tenant-dev.outsystems.app/HomeBankingPortal4/Dashboard"

JS = r"""() => {
  const mc = document.querySelector('.main-content');
  const wrappers = [...document.querySelectorAll('[class*=main-content]')].map(e=>({
    cls:(e.className||'').toString(), display:getComputedStyle(e).display}));
  return {mcCls: mc?(mc.className||'').toString():null,
    mcDisplay: mc?getComputedStyle(mc).display:null,
    allMainContent: wrappers};
}"""

def main():
    if not is_chrome_available(): print("CDP down"); return 1
    p, browser, context = connect_with_retry()
    page=None
    try:
        page = context.new_page()
        url = DASH + "?_cb=" + str(int(time.time()))
        page.goto(url, wait_until="networkidle", timeout=60000)
        # if redirected to login, the gate script handles auth; here just report
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        print("URL:", page.url)
        print("BUST:", json.dumps(page.evaluate(JS), indent=1))
        page.close()
    finally:
        p.stop()
    return 0

if __name__ == "__main__": raise SystemExit(main())
