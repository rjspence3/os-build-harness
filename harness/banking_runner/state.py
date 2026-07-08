"""Compatibility shim — the resumable build-state store is now a public harness module.

`StateDB` moved to `harness.build_state` so the public harness on git is self-sufficient.
This shim re-exports it for the banking_runner orchestrator + its tests. New code should
import from `harness.build_state` directly.
"""
from harness.build_state import RecipeCall, StateDB  # noqa: F401
