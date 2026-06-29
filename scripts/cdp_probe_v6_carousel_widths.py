"""Probe V6 carousel element widths to diagnose the scale-correct-but-width-0 bug."""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

BASE = "https://your-tenant-dev.outsystems.app"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
VIEW = {"width": 1280, "height": 900}

_PROBE = r"""() => {
  const ph = document.querySelector('.slider.slider-content') || document.querySelector('.slider-content');
  if(!ph) return {found:false};
  function info(el){
    if(!el) return null;
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return {tag: el.tagName, cls: el.className, id: el.id||'',
      box_w: Math.round(r.width), box_h: Math.round(r.height),
      style_w: el.style.width||'', style_left: el.style.left||'',
      display: cs.display, position: cs.position, scale: cs.transform};
  }
  const list = ph.querySelector('.list');
  const slides = [...(list||ph).children].slice(0,4).map(info);
  return {found:true, placeholder: info(ph), parent: info(ph.parentElement),
    list: info(list), slides,
    slider_instances_note: 'check console',
    list_classes: list? list.className : null};
}"""


def main():
    if not is_chrome_available():
        print("CDP not reachable"); return 1
    p, browser, context = connect_with_retry()
    fresh = None
    try:
        fresh = browser.new_context(viewport=VIEW)
        fresh.clear_cookies()
        page = fresh.new_page()
        try:
            page.goto(V6_LOGIN, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print("login note:", repr(e)[:120])
        page.wait_for_timeout(9000)
        page.goto(V6_DASH, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(7000)
        print(json.dumps(page.evaluate(_PROBE), indent=2))
        page.close()
    finally:
        try:
            if fresh is not None:
                fresh.close()
        except Exception:  # noqa: BLE001
            pass
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
