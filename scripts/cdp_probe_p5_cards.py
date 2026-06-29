"""Focused runtime probe of Portal5 Dashboard account cards via CDP.

Reads the live rendered DOM (after hydration) and reports, for each account
card: its class list (to confirm colored-card variant) and its text content
(name / number / balance). Also reports the Total Balance band value.

Usage: .venv/bin/python scripts/cdp_probe_p5_cards.py [out.png]
Cleanup: p.stop() only.
"""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry, is_chrome_available  # noqa: E402

APP = "HomeBankingPortal5"
DASH_URL = f"https://your-tenant-dev.outsystems.app/{APP}/Dashboard"
OUT = next((a for a in sys.argv[1:] if not a.startswith("--")), "compare/portal5_cards_probe.png")

PROBE_JS = r"""() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  // account cards: containers carrying the account-card class
  const cards = [...document.querySelectorAll('[class*="account-card"]')].map(e => {
    const r = e.getBoundingClientRect();
    return {
      cls: e.className,
      text: norm(e.textContent).slice(0, 120),
      hasColored: /colored-card/.test(e.className),
      variant: (e.className.match(/\b(orange|yellow|lightDark)\b/) || [null,null])[1],
      w: Math.round(r.width), h: Math.round(r.height),
      left: Math.round(r.left), top: Math.round(r.top),
    };
  });
  // Total Balance band: find the element whose label sibling says "Total Balance"
  let totalBalance = null;
  const all = [...document.querySelectorAll('*')];
  for (const e of all) {
    if (norm(e.textContent) === 'Total Balance') {
      // next sibling or parent's next expression
      const parent = e.parentElement;
      if (parent) {
        const amt = [...parent.children].map(c => norm(c.textContent)).filter(t => t && t !== 'Total Balance');
        if (amt.length) { totalBalance = amt[0]; break; }
      }
    }
  }
  // fallback: any $-prefixed currency text near top
  if (!totalBalance) {
    const dollar = all.filter(e => e.children.length === 0 && /^\$[\d,]+\.\d{2}$/.test(norm(e.textContent)));
    if (dollar.length) totalBalance = norm(dollar[0].textContent) + ' (fallback)';
  }
  // distinct color variants observed across cards
  const variants = [...new Set(cards.map(c => c.variant).filter(Boolean))];
  // distinct balance $ values rendered in cards
  const balances = cards.map(c => (c.text.match(/\$[\d,]+\.\d{2}/g) || [])).flat();
  return { cardCount: cards.length, cards, totalBalance, distinctVariants: variants, cardBalances: balances };
}"""


def main() -> int:
    if not is_chrome_available():
        print("CDP Chrome not reachable on 9222")
        return 1
    p, browser, context = connect_with_retry()
    try:
        page = next((pg for pg in context.pages if APP in pg.url), None)
        if page is None:
            page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(DASH_URL, wait_until="networkidle", timeout=45000)
        # wait for cards to actually render (poll up to 15s)
        for _ in range(30):
            n = page.evaluate("() => document.querySelectorAll('[class*=\"account-card\"]').length")
            if n and n > 0:
                break
            page.wait_for_timeout(500)
        page.wait_for_timeout(2000)
        result = page.evaluate(PROBE_JS)
        print("PROBE:", json.dumps(result, indent=2))
        page.screenshot(path=OUT, full_page=False)
        print("screenshot:", OUT)
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
