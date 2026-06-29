"""Read-only: open the original Login, click 'Access your demo', and dump whatever
UI appears (sample-user chips / buttons / inputs) so we can drive a POPULATED-user
login (the empty HB_PORTAL_USER shows $0.00; the demo picker selects a seeded user
like Andrea). Screenshots each step. No app/model mutation."""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

LOGIN = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Login"

DUMP = r"""() => {
  const vis = e => !!(e.offsetWidth || e.offsetHeight);
  const clickable = [...document.querySelectorAll('button,a,[role=button],li,.btn,[onclick],div[class*=card],div[class*=chip],div[class*=item]')]
    .filter(vis).map(e => ({t:(e.innerText||'').replace(/\s+/g,' ').trim().slice(0,50), cls:(e.className||'').toString().slice(0,50)}))
    .filter(x => x.t);
  const emails = [...document.querySelectorAll('*')].filter(e=>e.children.length===0 && /@/.test(e.textContent||'')).map(e=>e.textContent.trim()).slice(0,20);
  return {url: location.href, body: (document.body.innerText||'').replace(/\s+/g,' ').slice(0,500), clickable: clickable.slice(0,40), emails};
}"""


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        print("STEP 0 (login page):")
        print(json.dumps(page.evaluate(DUMP), indent=2))
        # click "Access your demo"
        el = page.query_selector("text=Access your demo") or page.query_selector(":text('Access your demo')")
        if el:
            el.click()
            page.wait_for_timeout(2500)
            page.screenshot(path="compare/demo_picker.png")
            print("\nSTEP 1 (after 'Access your demo'):")
            print(json.dumps(page.evaluate(DUMP), indent=2))
        else:
            print("\n'Access your demo' element not found")
            page.screenshot(path="compare/demo_picker_notfound.png")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
