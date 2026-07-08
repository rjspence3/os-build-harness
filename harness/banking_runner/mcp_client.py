"""Compatibility shim — the MCP client is now a first-class PUBLIC harness module.

The generic OutSystems-MCP client moved to `harness.mcp_client` so the public harness
on git is self-sufficient (a clone can drive Mentor without the home-banking runner).
This shim re-exports it so the banking_runner orchestrator + its tests keep working.
New code should import from `harness.mcp_client` directly.
"""
from harness.mcp_client import (  # noqa: F401
    DEFAULT_POLL_SECONDS,
    DEFAULT_TENANT,
    DEFAULT_TIMEOUT_SECONDS,
    MentorError,
    MentorMCP,
    MentorRunResult,
    _build_run_result,
    _flatten_content,
)
