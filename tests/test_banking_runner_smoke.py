"""Smoke tests for the banking app runner.

Coverage:
  - Manifest loads + counts match the source-of-truth
  - Recipe renderer produces non-empty C# blocks for all 4 renderer kinds
  - Recipe 01 attribute count matches manifest attribute count (HBCustomer 21/21)
  - StateDB CRUD + transitions
  - Orchestrator dispatches mocked recipe calls and records state correctly
  - MentorMCP spawns mcp-remote subprocess (skipped if npx unavailable)

Run: pytest tests/test_banking_runner_smoke.py -v
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make pipeline importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.banking_runner.manifest import load_home_banking
from harness.banking_runner.mcp_client import MentorRunResult, _build_run_result, _flatten_content
from harness.banking_runner.recipe import (
    collect_fk_targets,
    render_action_stub,
    render_fk_resolution_block,
    render_role,
    render_server_entity,
    render_static_entity,
)
from harness.banking_runner.state import StateDB


# ─── Manifest ──────────────────────────────────────────────────────────────────

def test_manifest_loads():
    m = load_home_banking()
    assert m.entities.total_count == 35, f"expected 35 entities, got {m.entities.total_count}"
    assert len(m.entities.static_entities) == 18
    assert len(m.entities.server_entities) == 17
    assert len(m.roles.roles) == 3
    # Actions: core 100 (62 SA + 38 ServiceA), Portal 26, Backoffice 26
    core = next(s for s in m.actions.apps if s.app == "core")
    assert len(core.server_actions) == 62
    assert len(core.service_actions) == 38


def test_manifest_hbcustomer_has_21_attrs():
    m = load_home_banking()
    hb = next(e for e in m.entities.server_entities if e.name == "HBCustomer")
    assert len(hb.attributes) == 21


# ─── Recipe renderer ───────────────────────────────────────────────────────────

def test_render_static_entity_chartdataoption():
    m = load_home_banking()
    e = next(x for x in m.entities.static_entities if x.name == "ChartDataOption")
    out = render_static_entity(e)
    assert "ChartDataOption" in out
    assert 'e.CreateRecord("Quarterly");' in out
    assert 'e.CreateRecord("Weekly");' in out
    assert 'e.CreateRecord("Monthly");' in out


def test_render_server_entity_hbcustomer_attrs_match_manifest():
    """The rendered C# must invoke AddX once per manifest attribute (no drops, no dupes)."""
    m = load_home_banking()
    hb = next(e for e in m.entities.server_entities if e.name == "HBCustomer")
    static_names = {e.name for e in m.entities.static_entities}
    server_names = {e.name for e in m.entities.server_entities}

    out = render_server_entity(hb, server_names, static_names)

    # Find every AddX(e, "Name", ...) call
    rendered = re.findall(r'    (Add\w+)\(e, "(\w+)"', out)
    rendered_names = sorted(x[1] for x in rendered)
    manifest_names = sorted(a.name for a in hb.attributes)
    assert rendered_names == manifest_names, (
        f"\n  manifest:    {manifest_names}\n  rendered:    {rendered_names}"
        f"\n  missing:     {set(manifest_names) - set(rendered_names)}"
        f"\n  unexpected:  {set(rendered_names) - set(manifest_names)}"
    )


def test_render_server_entity_fk_resolution():
    """FK targets must get a 'var <name> = ...' declaration before the attribute line."""
    m = load_home_banking()
    hb_account = next(e for e in m.entities.server_entities if e.name == "HBAccount")
    static_names = {e.name for e in m.entities.static_entities}
    server_names = {e.name for e in m.entities.server_entities}

    out = render_server_entity(hb_account, server_names, static_names)

    # HBAccount has FKs to: HBAccountName (static), ProductType (static),
    # HBCustomer (server), Employee (referenced AppsCommonCore), HBBranch (server), User (System)
    assert "userIdentType" in out, "User FK resolution missing"
    assert "hBCustomerEntity" in out, "HBCustomer FK resolution missing"
    assert "employeeEntity" in out, "Employee (cross-module) FK resolution missing"
    assert "productTypeStatic" in out, "ProductType (static) FK resolution missing"


def test_render_role():
    m = load_home_banking()
    role = next(r for r in m.roles.roles if r.name == "HomeBankingPortal")
    out = render_role(role)
    assert "HomeBankingPortal" in out
    assert "r.Public = true" in out


def test_render_action_stub():
    m = load_home_banking()
    static_names = {e.name for e in m.entities.static_entities}
    server_names = {e.name for e in m.entities.server_entities}
    core = next(s for s in m.actions.apps if s.app == "core")
    action = next(a for a in core.server_actions if a.name == "AgentsResponseCreate")
    out = render_action_stub(action, server_names, static_names)
    assert "AgentsResponseCreate" in out
    # The action has a Source param of type HAgentsResponse (an entity record),
    # and an Id output of HAgentsResponse Identifier. FK should resolve.
    assert "hAgentsResponseEntity" in out or "HAgentsResponse" in out


# ─── FK helpers ────────────────────────────────────────────────────────────────

def test_collect_fk_targets():
    m = load_home_banking()
    hb_account = next(e for e in m.entities.server_entities if e.name == "HBAccount")
    targets = collect_fk_targets(hb_account.attributes)
    # User Identifier is in there but appears later (CreatedBy is near end)
    assert "User" in targets
    assert "HBCustomer" in targets
    assert "HBBranch" in targets


def test_fk_resolution_block_for_known_targets():
    static_names = {"LoanRequestStatus", "HBDocumentType"}
    server_names = {"HBCustomer", "HBAccount"}
    cs, lookup, var_lookup = render_fk_resolution_block(
        ["User", "HBCustomer", "LoanRequestStatus", "Employee"], server_names, static_names
    )
    # lookup is keyed by entity name; values are null-safe IdentifierType
    # expressions: `.First()` was replaced by FirstOrDefault + a TextType
    # coalesce so a missing/hallucinated FK target degrades to Text instead of
    # throwing at runtime and aborting the whole batch.
    assert lookup["User"] == "(userEntity?.IdentifierType ?? eSpace.TextType)"
    assert lookup["HBCustomer"] == "(hBCustomerEntity?.IdentifierType ?? eSpace.TextType)"
    assert lookup["LoanRequestStatus"] == "(loanRequestStatusStatic?.IdentifierType ?? eSpace.TextType)"
    assert lookup["Employee"] == "(employeeEntity?.IdentifierType ?? eSpace.TextType)"
    # var_lookup maps the target to the bare entity variable (callers append
    # `?.IdentifierType` at the call site). User now declares an entity var too.
    assert var_lookup["User"] == "userEntity"
    assert var_lookup["HBCustomer"] == "hBCustomerEntity"
    # And the C# block declares the variables
    assert "userEntity" in cs
    assert "hBCustomerEntity" in cs
    assert "loanRequestStatusStatic" in cs


# ─── StateDB ───────────────────────────────────────────────────────────────────

@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


def test_state_db_lifecycle(db_path):
    db = StateDB(db_path)
    row_id = db.upsert_pending("core", "01_server", "HBCustomer", "/tmp/x.txt")

    # Idempotent
    same_id = db.upsert_pending("core", "01_server", "HBCustomer", "/tmp/x.txt")
    assert row_id == same_id

    # Pending → running → succeeded
    pending = db.list_pending("core")
    assert len(pending) == 1
    db.mark_running(row_id, "run-1")
    db.mark_succeeded(row_id, "Recipe 01: HBCustomer | Status: OK", session_id="s1", session_token="t1")

    succeeded = db.list_by_status("core", "succeeded")
    assert len(succeeded) == 1
    assert succeeded[0].session_id == "s1"
    assert succeeded[0].stdout.startswith("Recipe 01")

    counts = db.counts("core")
    assert counts == {"succeeded": 1}

    db.close()


def test_state_db_failure_increments_retries(db_path):
    db = StateDB(db_path)
    row_id = db.upsert_pending("core", "03_role", "TestRole", "/tmp/x.txt")
    db.mark_failed(row_id, "compile error xyz")
    db.mark_failed(row_id, "compile error xyz again")

    rows = db.list_by_status("core", "failed")
    assert len(rows) == 1
    assert rows[0].retries == 2
    assert "compile error xyz again" in rows[0].error
    db.close()


def test_state_db_gates(db_path):
    db = StateDB(db_path)
    gate_id = db.add_gate("core", "portal_create", "Portal-create HomeBankingCore")
    assert len(db.list_pending_gates("core")) == 1
    # Idempotent
    same_id = db.add_gate("core", "portal_create", "Portal-create HomeBankingCore")
    assert same_id == gate_id
    db.satisfy_gate(gate_id)
    assert db.list_pending_gates("core") == []
    db.close()


# ─── MCP client helpers (no live network) ──────────────────────────────────────

def test_build_run_result_extracts_stdout():
    events = [
        {
            "type": "tool_end",
            "name": "applyModelApiCode",
            "result": '{"compilationErrors":[],"stdoutOutput":"Recipe 03: HomeBankingPortal | Created: role | Status: OK","exceptionMessage":""}',
        },
    ]
    payload = {
        "status": "succeeded",
        "result": {
            "mentor_session_id": "s-123",
            "mentor_session_token": "jwt-abc",
            "summary": "Recipe 03 OK",
        },
    }
    result = _build_run_result("run-xyz", "succeeded", payload, events)
    assert result.status == "succeeded"
    assert "Recipe 03: HomeBankingPortal" in result.stdout
    assert result.session_id == "s-123"
    assert result.compile_errors == []


def test_build_run_result_captures_compile_errors():
    events = [
        {
            "type": "tool_end",
            "name": "applyModelApiCode",
            "result": '{"compilationErrors":["(13,81): error CS0234: missing type"],"stdoutOutput":"","exceptionMessage":""}',
        },
    ]
    payload = {"status": "succeeded", "result": {}, "summary": ""}
    result = _build_run_result("run-1", "succeeded", payload, events)
    assert result.compile_errors == ["(13,81): error CS0234: missing type"]


def test_flatten_content_handles_empty():
    assert _flatten_content([]) == ""
    assert _flatten_content(None) == ""


# ─── mcp-remote subprocess availability ────────────────────────────────────────

@pytest.mark.skipif(not shutil.which("npx"), reason="npx not installed")
def test_mcp_remote_executable_available():
    """Verifies mcp-remote can be located. Doesn't actually connect to OutSystems."""
    # mcp-remote installs on first use; check that the help cmd at least returns
    import subprocess
    result = subprocess.run(
        ["npx", "-y", "--prefer-offline", "mcp-remote", "--help"],
        capture_output=True, text=True, timeout=30
    )
    # mcp-remote --help prints to stderr; just verify it ran
    combined = result.stdout + result.stderr
    assert "mcp-remote" in combined.lower() or "usage" in combined.lower() or result.returncode == 0, (
        f"mcp-remote help failed: rc={result.returncode}, output: {combined[:500]}"
    )


# ─── Orchestrator with mocked MCP ──────────────────────────────────────────────

import asyncio


def test_orchestrator_dispatches_recipe_calls(db_path):
    """Mock the MCP client and verify orchestrator transitions state correctly."""
    from harness.banking_runner.orchestrator import AppConfig, Orchestrator

    db = StateDB(db_path)
    # Pre-load 3 fake recipe calls
    with tempfile.NamedTemporaryFile(mode="w", suffix=".prompt.txt", delete=False) as f:
        f.write("fake prompt for testing")
        prompt_path = f.name

    db.upsert_pending("core", "03_role", "RoleA", prompt_path)
    db.upsert_pending("core", "03_role", "RoleB", prompt_path)
    db.upsert_pending("core", "03_role", "RoleC", prompt_path)

    # Mock MentorMCP — every call returns a success result
    mock_mcp = MagicMock()
    mock_mcp.mentor_start = AsyncMock(return_value="run-fake-123")
    mock_mcp.mentor_poll = AsyncMock(return_value=MentorRunResult(
        run_id="run-fake-123",
        status="succeeded",
        stdout="Recipe 03: TestRole | Status: OK",
        compile_errors=[],
        summary="OK",
        session_id="sess-mock",
        session_token="jwt-mock",
        raw_events=[],
    ))
    # publish_start + publish_wait — orchestrator now publishes per recipe
    mock_mcp.publish_start = AsyncMock(return_value="pub-fake-456")
    mock_mcp.publish_wait = AsyncMock(return_value={"status": "Finished"})

    orch = Orchestrator(db, mock_mcp, Path("/tmp"))
    config = AppConfig(
        name="core",
        display_name="HomeBankingCore",
        app_key="fake-key-123",
        consumer_modules=[],
        require_studio_warmup=False,
    )

    async def run():
        # Skip Phase 0 gates by setting app_key + require_studio_warmup=False
        result = await orch._run_phase(config, "03_role")
        return result

    result = asyncio.run(run())
    assert result.succeeded == 3
    assert result.failed == 0
    assert result.halted_at is None

    # Verify state DB transitions
    succeeded = db.list_by_status("core", "succeeded", phase="03_role")
    assert len(succeeded) == 3
    assert all(s.stdout.startswith("Recipe 03:") for s in succeeded)

    db.close()
    Path(prompt_path).unlink(missing_ok=True)


def test_orchestrator_halts_on_failure(db_path):
    """On first compile error, orchestrator must halt and not dispatch dependent calls."""
    from harness.banking_runner.orchestrator import AppConfig, Orchestrator

    db = StateDB(db_path)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".prompt.txt", delete=False) as f:
        f.write("fake prompt")
        prompt_path = f.name

    db.upsert_pending("core", "01_server", "EntityA", prompt_path)
    db.upsert_pending("core", "01_server", "EntityB", prompt_path)

    # Mock returns compile error
    mock_mcp = MagicMock()
    mock_mcp.mentor_start = AsyncMock(return_value="run-x")
    mock_mcp.mentor_poll = AsyncMock(return_value=MentorRunResult(
        run_id="run-x",
        status="succeeded",
        stdout="",
        compile_errors=["(10,20): error CS0246: missing type"],
        summary="",
        session_id=None,
        session_token=None,
        raw_events=[],
    ))

    orch = Orchestrator(db, mock_mcp, Path("/tmp"), max_concurrent=1)
    config = AppConfig(name="core", display_name="C", app_key="k", consumer_modules=[])

    async def run():
        return await orch._run_phase(config, "01_server")

    result = asyncio.run(run())
    assert result.failed >= 1
    assert result.halted_at is not None
    db.close()
    Path(prompt_path).unlink(missing_ok=True)
