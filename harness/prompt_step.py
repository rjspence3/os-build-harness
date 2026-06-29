"""harness-prompt-step — bounded, templated build sub-steps.

NOT IMPLEMENTED. This is meant to run repetitive, well-specified build work as
deterministic templated steps against the ODC MCP (cheaper than free-form agent
reasoning). It needs the MCP actuator + a step-template library. Stubbed so
`harness-prompt-step` resolves on PATH after `pip install -e .`; never a false pass.
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    print(
        "harness-prompt-step is NOT IMPLEMENTED. It should execute bounded, templated build "
        "sub-steps against the ODC MCP. Define the step-template library + MCP wiring to implement.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
