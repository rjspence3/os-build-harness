"""harness-capture — drive CDP to capture rendered screens for advisory visual diff.

NOT IMPLEMENTED. This needs the authenticated CDP path (harness/cdp_helpers.py +
Chrome on --remote-debugging-port=9222) wired to the built app's URLs, plus the
mockupRef assets from the spec for the advisory (non-gating) comparison. Stubbed
so `harness-capture` resolves on PATH after `pip install -e .`; it never reports
a false success.
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    print(
        "harness-capture is NOT IMPLEMENTED. Wire harness/cdp_helpers.py "
        "(connect_with_retry/is_chrome_available) to the built app's screen URLs and emit "
        "captures for ADVISORY visual diff against spec mockupRef. Visual diff is non-gating.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
