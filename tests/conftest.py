"""Test bootstrap. Ensure repo root is on sys.path so `harness.*` imports cleanly.

Trimmed from the original kyleAccounts conftest during the repo split: the
`pytest_plugins = ["tests.conftest_browser"]` line was dropped (buildHarness has
no browser tests; loading that plugin would abort collection). REPO_ROOT is
computed relative to __file__ — never hardcoded — so tests always exercise THIS
repo's source, not the kyleAccounts archive.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
