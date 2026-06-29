"""Final FAITHFUL-CLONE capture: ORIGINAL (manual demo+andrea picker) + V6 (own /Login auto-login),
same Chrome session, 1280x900, full_page. Strips LastPass. Probes currency/transactions + scale on both.

Chrome 147+ wedges Playwright connect_over_cdp at the browser level (Browser.setDownloadBehavior
"Browser context management is not supported"). Workaround: create a fresh page TARGET via
/json/new and connect Playwright to THAT page's per-target ws endpoint (no browser-context mgmt).

Usage: .venv/bin/python scripts/cdp_final_capture.py
No app/model mutation. Cleanup: close created target via /json/close + p.stop() only.
"""
import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "https://your-tenant-dev.outsystems.app"
ORIG_LOGIN = f"{BASE}/HomeBankingPortal/Login"
ORIG_DASH = f"{BASE}/HomeBankingPortal/Dashboard"
V6_LOGIN = f"{BASE}/HomeBankingPortal6/Login"
V6_DASH = f"{BASE}/HomeBankingPortal6/Dashboard"
VIEW = {"width": 1280, "height": 900}
ANDREA = "demo+andrea@outsystems.com"

_STRIP = r"""() => {
  const kill = el => { try { el.remove(); } catch(e){} };
  document.querySelectorAll('[id*=lastpass i],[class*=lastpass i],iframe[src*=lastpass i],div[data-lastpass],#lpcustom,[id^=__lpform],[data-lastpass-root]').forEach(kill);
  [...document.querySelectorAll('div,iframe,section')].forEach(e => {
    const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
    if ((cs.position==='fixed'||cs.position==='absolute') && r.top < 80 && r.width>250 && r.width<560 &&
        /lastpass|add password|add to lastpass/i.test(e.innerText||'')) kill(e);
  });
}"""

_METRICS = r"""() => {
  const bt = (document.body.innerText||'').replace(/\s+/g,' ');
  const m = bt.match(/Welcome,?\s*([A-Za-z]+)/i);
  const bal = bt.match(/Total Balance[^\d-]*([\d,]+\.\d{2})/i);
  const cardBalances = [...document.querySelectorAll('.account-card .font-size-40, .account-card .card-detail-font')]
      .map(e => (e.textContent||'').trim()).filter(Boolean).slice(0,8);
  return {url: location.href, on_login:/\/Login/i.test(location.href),
    welcome_name:m?m[1]:null, total_balance: bal?bal[1]:null,
    has_currency_symbol_balance: /\$[\d,]+\.\d{2}/.test(bt),
    has_raw_unsep_digits: /(?<![\d.,$])\d{5,}(?![\d.,])/.test(bt),
    card_balance_samples: cardBalances,
    account_cards:document.querySelectorAll('.account-card').length,
    chart_svg:document.querySelectorAll('svg.highcharts-root,.highcharts-container,canvas').length,
    doc_h: document.documentElement.scrollHeight};
}"""

_SCALE = r"""() => {
  const out = {};
  const html = document.documentElement, body = document.body;
  out.html_fontSize = getComputedStyle(html).fontSize;
  out.body_fontSize = getComputedStyle(body).fontSize;
  out.html_zoom = getComputedStyle(html).zoom;
  out.body_zoom = getComputedStyle(body).zoom;
  out.body_transform = getComputedStyle(body).transform;
  const wrap = document.querySelector('.layout .content, .content');
  if (wrap) { const cs = getComputedStyle(wrap); const r = wrap.getBoundingClientRect();
    out.content_class = (wrap.className||'').slice(0,90); out.content_width = Math.round(r.width);
    out.content_maxWidth = cs.maxWidth; out.content_padding = cs.padding; }
  const hero = document.querySelector('.account-card .font-size-40, .font-size-40');
  if (hero) { const cs = getComputedStyle(hero); const r = hero.getBoundingClientRect();
    out.hero_class = (hero.className||'').slice(0,60); out.hero_fontSize = cs.fontSize;
    out.hero_text = (hero.textContent||'').trim().slice(0,20); out.hero_width = Math.round(r.width); }
  const lay = document.querySelector('.layout, [class*=layout]');
  if (lay) { out.layout_width = Math.round(lay.getBoundingClientRect().width); out.layout_class = (lay.className||'').slice(0,80); }
  // dashboard main content region width (first big column)
  const main = document.querySelector('[class*=content], main');
  out.win_inner = window.innerWidth + 'x' + window.innerHeight;
  out.dpr = window.devicePixelRatio;
  return out;
}"""


def _new_target(url="about:blank"):
    # Chrome 147+ rejects POST to /json/new (405) and PUT may be blocked too.
    # Try GET (legacy), then PUT; fall back to reusing an existing page target.
    import urllib.error
    for method in ("GET", "PUT"):
        try:
            req = urllib.request.Request(f"http://localhost:9222/json/new?{url}", method=method)
            return json.loads(urllib.request.urlopen(req, timeout=10).read()), True
        except urllib.error.HTTPError:
            continue
    # fallback: reuse an existing page-type target
    lst = json.loads(urllib.request.urlopen("http://localhost:9222/json/list", timeout=10).read())
    pages = [t for t in lst if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        raise RuntimeError("no reusable page targets in Chrome")
    return pages[0], False


def _close_target(tid):
    try:
        urllib.request.urlopen(f"http://localhost:9222/json/close/{tid}", timeout=10).read()
    except Exception:  # noqa: BLE001
        pass


def grab(page, url, out, label):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)
    try:
        page.evaluate(_STRIP); page.wait_for_timeout(300)
    except Exception:  # noqa: BLE001
        pass
    page.screenshot(path=out, full_page=True)
    mx = page.evaluate(_METRICS)
    sc = page.evaluate(_SCALE)
    print(f"\n== {label} ==\n{out}\nMETRICS {json.dumps(mx)}\nSCALE {json.dumps(sc)}")
    return mx, sc


def main():
    pathlib.Path("compare").mkdir(exist_ok=True)
    target, created = _new_target()
    tid = target["id"]
    ws = target["webSocketDebuggerUrl"]
    print(f"target id={tid} created_new={created}")
    p = sync_playwright().start()
    page = None
    try:
        browser = p.chromium.connect_over_cdp(ws)
        ctx = browser.contexts[0]
        # Chrome 147+: per-target connect surfaces the existing page; poll for it.
        page = None
        for _ in range(20):
            if ctx.pages:
                page = ctx.pages[0]
                break
            p.selectors  # noop touch
            import time as _t; _t.sleep(0.25)
        if page is None:
            # last resort: any page across all contexts
            for c in browser.contexts:
                if c.pages:
                    page = c.pages[0]; break
        if page is None:
            raise RuntimeError("no page surfaced on per-target CDP connection")
        page.set_viewport_size(VIEW)
        # 1) ORIGINAL — manual demo picker -> andrea
        page.goto(ORIG_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        if "Login" in page.url:
            try:
                page.click("text=Access your demo", timeout=8000); page.wait_for_timeout(2000)
            except Exception:  # noqa: BLE001
                print("no 'Access your demo' button (maybe already authed)")
            chip = page.query_selector(f"text={ANDREA}")
            if chip:
                chip.click(); page.wait_for_timeout(800)
                try:
                    page.click("button:has-text('Confirm')", timeout=8000)
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(2500)
                if "Login" in page.url:
                    b = page.query_selector("button:has-text('Login')") or page.query_selector("button.OSFillParent")
                    if b:
                        b.click(); page.wait_for_load_state("networkidle", timeout=60000); page.wait_for_timeout(3500)
            else:
                print(f"andrea chip not found; url={page.url}")
        print("orig post-login url:", page.url)
        if "Login" in page.url:
            page.screenshot(path="compare/orig_final_loginfail.png")
            print("ORIG STILL ON LOGIN"); return 4
        og, ogs = grab(page, ORIG_DASH, "compare/orig_final.png", "ORIGINAL (andrea)")
        # 2) V6 — its own /Login auto-login
        page.goto(V6_LOGIN, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(6500)
        print("v6 post-login url:", page.url)
        v6, v6s = grab(page, V6_DASH, "compare/v6_final.png", "V6 (andrea own login)")
        print("\n== PARITY ==")
        print(f"orig welcome={og.get('welcome_name')} totalBal={og.get('total_balance')} cards={og.get('account_cards')} chart={og.get('chart_svg')}")
        print(f"v6   welcome={v6.get('welcome_name')} totalBal={v6.get('total_balance')} cards={v6.get('account_cards')} chart={v6.get('chart_svg')}")
        print(f"v6 card_balances={v6.get('card_balance_samples')}")
        print(f"v6 has_currency_symbol={v6.get('has_currency_symbol_balance')} has_raw_unsep={v6.get('has_raw_unsep_digits')}")
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            p.stop()
        except Exception:  # noqa: BLE001
            pass
        if created:
            _close_target(tid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
