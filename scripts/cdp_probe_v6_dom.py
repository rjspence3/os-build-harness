"""Read-only: dump the outerHTML of V6's leaking regions (nav/logo, header icons,
action buttons) so we can pinpoint WHY 'Button'/'homebankinglogo'/'search' leak as
text. Assumes an authenticated session already exists in the CDP browser."""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

V6 = "https://your-tenant-dev.outsystems.app/HomeBankingPortal6/Dashboard"

PROBE = r"""() => {
  const clip = s => (s||'').replace(/\s+/g,' ').slice(0,400);
  const find = re => [...document.querySelectorAll('button,a,div,span')]
    .filter(e => re.test((e.innerText||'').trim()) && e.children.length <= 6)
    .sort((a,b)=>a.innerText.length-b.innerText.length)[0];
  const btn = find(/^ButtonTransfer$/) || find(/Transfer/);
  const logo = find(/homebankinglogo/);
  const hdr = find(/search|notification|darkmode/);
  const dump = e => e ? {tag:e.tagName, cls:(e.className||'').slice(0,80), html: clip(e.outerHTML)} : null;
  // also: is .hb-icon used anywhere in nav/header?
  const navIcons = [...document.querySelectorAll('header *, nav *, [class*=menu] *')].filter(e=>e.classList.contains('hb-icon')).length;
  return {
    transfer_button: dump(btn),
    logo_region: dump(logo),
    header_icons: dump(hdr),
    nav_hb_icon_count: navIcons,
    total_hb_icons: document.querySelectorAll('.hb-icon').length,
  };
}"""


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    try:
        page = next((pg for pg in context.pages if "HomeBankingPortal6" in pg.url), None) or context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(V6, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        print(json.dumps(page.evaluate(PROBE), indent=2))
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
