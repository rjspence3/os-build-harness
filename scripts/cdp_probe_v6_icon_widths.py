"""Read-only: measure rendered width + computed font-family of V6 chrome icon spans
to determine which actually render as a glyph (narrow, font=hb-icons) vs raw text.
Assumes an authenticated session already exists in the CDP browser."""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

V6 = "https://your-tenant-dev.outsystems.app/HomeBankingPortal6/Dashboard"

PROBE = r"""() => {
  const ids = ['LogoIcon','Icon_search','Icon_notifications','Icon_darkmode'];
  const out = {};
  for (const frag of ids) {
    const e = [...document.querySelectorAll('[id*="'+frag+'"]')][0];
    if (!e) { out[frag] = null; continue; }
    const cs = getComputedStyle(e);
    out[frag] = {
      text: (e.textContent||'').trim(),
      cls: e.className,
      w: Math.round(e.getBoundingClientRect().width),
      font: cs.fontFamily.slice(0,40),
      ffs: cs.fontFeatureSettings,
    };
  }
  // is the hb-icons font actually loaded?
  out._font_loaded = document.fonts ? [...document.fonts].some(f=>/hb-icons/i.test(f.family) && f.status==='loaded') : 'n/a';
  out._all_fonts = document.fonts ? [...document.fonts].map(f=>f.family+':'+f.status).slice(0,12) : [];
  return out;
}"""


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    try:
        page = next((pg for pg in context.pages if "HomeBankingPortal6" in pg.url), None) or context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(V6, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        print(json.dumps(page.evaluate(PROBE), indent=2))
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
