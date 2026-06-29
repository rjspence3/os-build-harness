"""Read-only inspect of the original Login page: enumerate inputs + buttons +
any demo email-picker chips, so we can drive auth correctly. No fills, no submit."""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

URL = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Login"

PROBE = r"""() => {
  const inputs = [...document.querySelectorAll('input,select,textarea')].map(e => ({
    tag: e.tagName, type: e.type||'', name: e.name||'', id: e.id||'',
    ph: e.placeholder||'', vis: !!(e.offsetWidth||e.offsetHeight)
  }));
  const buttons = [...document.querySelectorAll('button,[role=button],a.btn,input[type=submit]')].map(e => ({
    text: (e.innerText||e.value||'').trim().slice(0,40), cls: (e.className||'').slice(0,60),
    vis: !!(e.offsetWidth||e.offsetHeight)
  })).filter(b => b.text);
  const bt = (document.body.innerText||'').replace(/\s+/g,' ').slice(0,400);
  // demo chips: clickable elements that look like emails/names
  const chips = [...document.querySelectorAll('*')].filter(e => e.children.length===0 && /@|Andrea|Sample|Demo/i.test(e.textContent||'')).map(e=>(e.textContent||'').trim()).slice(0,15);
  return {url: location.href, inputs, buttons, body_sample: bt, chips};
}"""


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        print(json.dumps(page.evaluate(PROBE), indent=2))
        page.screenshot(path="compare/orig_login_inspect.png")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
