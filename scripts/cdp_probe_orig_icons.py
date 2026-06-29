"""Read-only: dump the ORIGINAL app's header/logo/nav icon spans to learn the exact
hb-icons ligature TOKENS the font actually supports (the original renders 18 glyphs).
Assumes an authenticated session already exists in the CDP browser."""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

ORIG = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard"

PROBE = r"""() => {
  const els = [...document.querySelectorAll('.hb-icon')];
  const out = els.slice(0, 40).map(e => ({
    text: (e.textContent||'').trim().slice(0,40),
    cls: (e.className||'').slice(0,80),
    tag: e.tagName,
    id: (e.id||'').slice(0,60),
    rect_w: Math.round(e.getBoundingClientRect().width),
  }));
  // Also grab the logo + header action area regardless of class
  const logo = [...document.querySelectorAll('[id*=Logo], [id*=logo]')].slice(0,5)
    .map(e => ({id:e.id, text:(e.textContent||'').trim().slice(0,40), cls:(e.className||'').slice(0,60)}));
  const headerActions = [...document.querySelectorAll('.circle-bg-icon')].slice(0,8)
    .map(e => ({id:e.id, html:(e.outerHTML||'').replace(/\s+/g,' ').slice(0,200)}));
  return {hb_icon_samples: out, logo_nodes: logo, header_action_nodes: headerActions};
}"""


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    try:
        page = next((pg for pg in context.pages if "HomeBankingPortal/" in pg.url), None) or context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(ORIG, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        print(json.dumps(page.evaluate(PROBE), indent=2))
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
