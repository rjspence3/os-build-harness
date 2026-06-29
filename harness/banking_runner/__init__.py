"""Banking app rebuild runner.

Drives the recipe library at data/MCP_RECIPES/ against fresh OutSystems apps
to reconstruct the Home Banking suite (Core + Portal + Backoffice + LoanRequest +
Mobile) from per-app YAML manifests.

Architecture:
  - manifest.py: load + validate YAML manifests
  - recipe.py: load recipe templates + render placeholders
  - mcp_client.py: HTTP client for OutSystems MCP (mentor_start, publish_start, etc.)
  - state.py: SQLite state DB tracking what's been built per app + per recipe
  - gate.py: prompt-and-wait UX for manual Portal/Studio steps
  - orchestrator.py: top-level phase coordinator

Entry point: scripts/build_banking.py.

Status: Phase A — manifest + recipe renderer + dry-run CLI. Phases B+C pending.
"""
