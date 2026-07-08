"""Tests for harness/architecture.py — the NO-MONOLITH system-topology gate.

Two golden cases anchor the suite: the live 8-app banking system (system_banking.json) must be
MODULAR (every invariant PASS/OMIT, none FAIL), and a UI/data monolith (system_monolith.json) must
be a MONOLITH (verdict false). The rest pin each of the six invariants with a minimal topology so a
regression names the exact rule it broke.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import architecture as arch

FIX = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _rows_by_gate(rows: list[dict]) -> dict:
    return {r["gate"]: r for r in rows}


# ── golden cases ─────────────────────────────────────────────────────────────
def test_banking_is_modular():
    rows = arch.check_system(_load("system_banking.json"))
    assert arch.verdict(rows) is True, [r for r in rows if r["status"] == "FAIL"]
    # no invariant may FAIL; FKs are declared so INV3 actually runs (not OMIT).
    assert not [r for r in rows if r["status"] == "FAIL"]
    assert _rows_by_gate(rows)["no-cross-app-fk"]["status"] == "PASS"
    # all six invariants are present in the report
    assert len(rows) == 6


def test_retail_multicontext_is_modular():
    """A 3-bounded-context system (Catalog/Ordering/Payments) with same-rank Core->Core edges —
    the multi-context path banking's single Core never exercised."""
    rows = arch.check_system(_load("system_retail.json"))
    assert arch.verdict(rows) is True, [r for r in rows if r["status"] == "FAIL"]
    assert _rows_by_gate(rows)["context-cohesion"]["status"] == "PASS"
    assert _rows_by_gate(rows)["acyclic-downward"]["status"] == "PASS"


def test_monolith_is_not_modular():
    rows = arch.check_system(_load("system_monolith.json"))
    assert arch.verdict(rows) is False
    failed = {r["gate"] for r in rows if r["status"] == "FAIL"}
    # the monolith trips these five distinct invariants
    assert {"layer-purity", "single-owner", "no-cross-app-fk",
            "acyclic-downward", "orchestration-externalized"} <= failed


# ── INV1 layer purity ────────────────────────────────────────────────────────
def test_layer_purity_enduser_owning_data_fails():
    apps = [{"name": "UI", "layer": "enduser", "owns": ["Customer"]}]
    assert arch.check_layer_purity(apps)["status"] == "FAIL"


def test_layer_purity_foundation_with_events_fails():
    apps = [{"name": "Lib", "layer": "foundation", "kind": "Library", "exposes": {"events": ["X"]}}]
    assert arch.check_layer_purity(apps)["status"] == "FAIL"


def test_layer_purity_kind_layer_mismatch_fails():
    apps = [{"name": "A", "layer": "core", "kind": "AIAgent", "owns": ["E"], "context": "c"}]
    assert arch.check_layer_purity(apps)["status"] == "FAIL"


def test_layer_purity_clean_core_passes():
    apps = [{"name": "Core", "layer": "core", "kind": "WebApplication", "owns": ["E"], "context": "c"}]
    assert arch.check_layer_purity(apps)["status"] == "PASS"


# ── INV2 single owner ────────────────────────────────────────────────────────
def test_single_owner_duplicate_fails():
    apps = [{"name": "A", "layer": "core", "owns": ["E"]},
            {"name": "B", "layer": "core", "owns": ["E"]}]
    r = arch.check_single_owner(apps)
    assert r["status"] == "FAIL" and any("multiple apps" in d for d in r["results"])


def test_single_owner_dangling_consume_fails():
    apps = [{"name": "UI", "layer": "enduser", "consumes": [{"app": "Ghost", "entities": ["Nope"]}]}]
    r = arch.check_single_owner(apps)
    assert r["status"] == "FAIL" and any("no app owns it" in d for d in r["results"])


def test_single_owner_clean_passes():
    apps = [{"name": "Core", "layer": "core", "owns": ["E"]},
            {"name": "UI", "layer": "enduser", "consumes": [{"app": "Core", "entities": ["E"]}]}]
    assert arch.check_single_owner(apps)["status"] == "PASS"


# ── INV3 no cross-app FK (OS-DPL-50205) ──────────────────────────────────────
def test_fk_to_non_owned_fails():
    apps = [{"name": "A", "layer": "core", "owns": ["Invoice"],
             "foreignKeys": [{"from": "Invoice", "target": "Order"}]}]
    assert arch.check_no_cross_app_fk(apps)["status"] == "FAIL"


def test_fk_to_owned_passes():
    apps = [{"name": "A", "layer": "core", "owns": ["Invoice", "Order"],
             "foreignKeys": [{"from": "Invoice", "target": "Order"}]}]
    assert arch.check_no_cross_app_fk(apps)["status"] == "PASS"


def test_fk_none_declared_omits():
    apps = [{"name": "A", "layer": "core", "owns": ["E"]}]
    assert arch.check_no_cross_app_fk(apps)["status"] == "OMIT"


# ── INV4 acyclic + downward ──────────────────────────────────────────────────
def test_upward_dependency_fails():
    apps = [{"name": "Core", "layer": "core", "consumes": [{"app": "UI"}]},
            {"name": "UI", "layer": "enduser"}]
    r = arch.check_acyclic_downward(apps)
    assert r["status"] == "FAIL" and any("upward" in d for d in r["results"])


def test_cycle_fails():
    apps = [{"name": "A", "layer": "core", "consumes": [{"app": "B"}]},
            {"name": "B", "layer": "core", "consumes": [{"app": "A"}]}]
    r = arch.check_acyclic_downward(apps)
    assert r["status"] == "FAIL" and any("cycle" in d for d in r["results"])


def test_unknown_producer_fails():
    apps = [{"name": "UI", "layer": "enduser", "consumes": [{"app": "Ghost"}]}]
    assert arch.check_acyclic_downward(apps)["status"] == "FAIL"


def test_downward_chain_passes():
    apps = [{"name": "Lib", "layer": "foundation"},
            {"name": "Core", "layer": "core", "consumes": [{"app": "Lib"}]},
            {"name": "UI", "layer": "enduser", "consumes": [{"app": "Core"}, {"app": "Lib"}]}]
    assert arch.check_acyclic_downward(apps)["status"] == "PASS"


# ── INV5 bounded-context cohesion ────────────────────────────────────────────
def test_context_missing_fails():
    apps = [{"name": "Core", "layer": "core", "owns": ["E"]}]
    assert arch.check_context_cohesion(apps)["status"] == "FAIL"


def test_context_split_across_apps_fails():
    apps = [{"name": "A", "layer": "core", "owns": ["E1"], "context": "sales"},
            {"name": "B", "layer": "core", "owns": ["E2"], "context": "sales"}]
    r = arch.check_context_cohesion(apps)
    assert r["status"] == "FAIL" and any("split across" in d for d in r["results"])


def test_context_multi_on_one_app_fails():
    apps = [{"name": "A", "layer": "core", "owns": ["E"], "context": ["sales", "billing"]}]
    assert arch.check_context_cohesion(apps)["status"] == "FAIL"


def test_context_clean_passes():
    apps = [{"name": "A", "layer": "core", "owns": ["E1"], "context": "sales"},
            {"name": "B", "layer": "core", "owns": ["E2"], "context": "billing"}]
    assert arch.check_context_cohesion(apps)["status"] == "PASS"


# ── INV6 orchestration externalized ──────────────────────────────────────────
def test_enduser_exposing_events_fails():
    apps = [{"name": "UI", "layer": "enduser", "exposes": {"events": ["X"]}}]
    assert arch.check_orchestration_externalized(apps)["status"] == "FAIL"


def test_process_in_non_orchestration_fails():
    apps = [{"name": "Core", "layer": "core", "kind": "WebApplication", "process": {"trigger": "X"}}]
    assert arch.check_orchestration_externalized(apps)["status"] == "FAIL"


def test_process_in_bpt_passes():
    apps = [{"name": "WF", "layer": "orchestration", "kind": "BusinessProcess",
             "process": {"trigger": "X"}}]
    assert arch.check_orchestration_externalized(apps)["status"] == "PASS"


# ── CLI / exit codes ─────────────────────────────────────────────────────────
def test_cli_banking_exit_zero(capsys):
    assert arch.main([str(FIX / "system_banking.json")]) == 0
    assert "MODULAR" in capsys.readouterr().out


def test_cli_monolith_exit_one(capsys):
    assert arch.main([str(FIX / "system_monolith.json")]) == 1
    assert "MONOLITH" in capsys.readouterr().out


def test_cli_json_shape(capsys):
    assert arch.main([str(FIX / "system_banking.json"), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["modular"] is True and payload["verdict"] == "MODULAR"
    assert len(payload["invariants"]) == 6


def test_empty_topology_fails():
    rows = arch.check_system({"system": {"name": "x", "apps": []}})
    assert arch.verdict(rows) is False
