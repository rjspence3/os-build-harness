"""Read-only CDP diagnostic: compare ORIGINAL vs V6 runtime theme/auth/data state.

Answers the gating questions before more build work:
  - Does each app load theme CSS? (stylesheet hrefs, count, dark-mode class, body bg)
  - What viewport does the original actually render its content at? (content width)
  - Is each rendered authenticated? (presence of a welcome/user name, account rows)

No mutations, no login attempts — just inspects whatever each tab currently shows.
Navigates the existing CDP Chrome (Rob's authenticated session) to each URL.
Cleanup: p.stop() only.
"""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

ORIG = "https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard"
V6 = "https://your-tenant-dev.outsystems.app/HomeBankingPortal6/Dashboard"

_PROBE = r"""() => {
  const sheets = [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href);
  const styleTags = document.querySelectorAll('style').length;
  const bodyBg = getComputedStyle(document.body).backgroundColor;
  const htmlClass = document.documentElement.className;
  const bodyText = (document.body.innerText || '');
  const fontFaces = (() => { let n=0; for (const ss of document.styleSheets) { try { for (const r of ss.cssRules) if (r.constructor.name==='CSSFontFaceRule') n++; } catch(e){} } return n; })();
  return {
    url: location.href,
    on_error_page: location.href.includes('_error') || /Sorry, an error/i.test(bodyText),
    stylesheet_count: sheets.length,
    stylesheets: sheets.slice(0, 12),
    style_tag_count: styleTags,
    font_face_rules: fontFaces,
    dark_mode_class: document.documentElement.classList.contains('dark-mode'),
    html_class: htmlClass,
    body_bg: bodyBg,
    hb_icons: document.querySelectorAll('.hb-icon').length,
    has_welcome: /welcome|Andrea/i.test(bodyText),
    sample_text: bodyText.replace(/\s+/g,' ').slice(0, 300),
    content_width: Math.round(document.body.getBoundingClientRect().width),
    doc_width: document.documentElement.scrollWidth,
  };
}"""


def probe(page, url, label):
    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3500)
        data = page.evaluate(_PROBE)
        print(f"\n===== {label} =====")
        print(json.dumps(data, indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"\n===== {label} ERROR: {e} =====")


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        probe(page, ORIG, "ORIGINAL HomeBankingPortal/Dashboard")
        probe(page, V6, "V6 HomeBankingPortal6/Dashboard")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
