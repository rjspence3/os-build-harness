"""Probe the HomeBankingPortal5 Dashboard Spending Chart render via CDP.

Confirms the native OutSystemsCharts ColumnChart (Highcharts) actually rendered
SVG bars, captures the chart element + full-page screenshots. Cleanup p.stop() only.
"""
import json
import sys

import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.cdp_helpers import connect_with_retry  # noqa: E402

APP = "HomeBankingPortal5"
DASH = f"https://your-tenant-dev.outsystems.app/{APP}/Dashboard"


def main() -> int:
    p, browser, context = connect_with_retry()
    try:
        page = next((pg for pg in context.pages if APP in pg.url), None) or context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(DASH, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(6000)  # let Highcharts client-render
        info = page.evaluate(
            r"""() => {
              const svgs = [...document.querySelectorAll('svg')];
              const hc = [...document.querySelectorAll('.highcharts-container, [class*=highcharts]')];
              const rects = [...document.querySelectorAll('rect.highcharts-point, .highcharts-series rect, svg rect')];
              let bbox = null;
              const hcc = document.querySelector('.highcharts-container');
              if (hcc) { const r = hcc.getBoundingClientRect(); bbox = {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}; }
              return {
                svg_count: svgs.length,
                highcharts_containers: hc.length,
                svg_rect_count: rects.length,
                legend_text: [...document.querySelectorAll('.highcharts-legend text, text.highcharts-text')].map(t=>t.textContent).slice(0,12),
                axis_labels: [...document.querySelectorAll('.highcharts-xaxis-labels text')].map(t=>t.textContent),
                hc_bbox: bbox,
              };
            }"""
        )
        print("CHART_PROBE:", json.dumps(info))
        el = page.query_selector(".highcharts-container")
        if el:
            el.screenshot(path="compare/portal5_chart_only.png")
            print("chart element screenshot: compare/portal5_chart_only.png")
        else:
            print("no .highcharts-container element found")
        page.screenshot(path="compare/portal5_chart_after_full.png", full_page=True)
        print("full screenshot: compare/portal5_chart_after_full.png")
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
