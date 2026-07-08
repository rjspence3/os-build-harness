"""Tests for harness/system_gate.py — the system-level definition of done.

Pins the derivation (the right cross-app flow contracts fall out of a topology) and the HONEST-CHANNEL
discipline it inherits from verify.py: a runtime flow is never reported PASS without a wired executor,
so a system is never DONE from static analysis alone — MODULAR-but-unverified is not done.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import decompose, system_gate

FIX = Path(__file__).resolve().parent / "fixtures"


def _retail_system() -> dict:
    return decompose.decompose(json.loads((FIX / "domain_retail.json").read_text()))["system"]


# ── derivation ───────────────────────────────────────────────────────────────
def test_flows_derived_by_kind():
    flows = system_gate.derive_system_flows(_retail_system())
    kinds = {}
    for f in flows:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    assert kinds["orchestrate"] == 1        # one BPT process
    assert kinds["agent"] == 1              # one AI agent
    assert kinds["read"] >= 5 and kinds["call"] >= 3


def test_orchestrate_flow_carries_trigger_and_activities():
    flows = system_gate.derive_system_flows(_retail_system())
    orch = next(f for f in flows if f["kind"] == "orchestrate")
    assert orch["app"] == "FulfillWorkflow"
    assert orch["trigger"] == "OrderPlaced"
    assert set(orch["activities"]) == {"ScoreOrderRisk", "CapturePayment", "AdjustInventory"}


def test_a_specific_read_flow_is_present():
    flows = system_gate.derive_system_flows(_retail_system())
    assert any(f["kind"] == "read" and f["consumer"] == "ShopperApp"
               and f["producer"] == "CatalogCore" and f["element"] == "Product" for f in flows)


# ── honest-channel discipline ────────────────────────────────────────────────
def test_no_flow_is_ever_a_fake_pass():
    for live in (False, True):
        report = system_gate.run_system_gate(_retail_system(), live_configured=live)
        assert all(r["status"] != "PASS" for r in report["flows"])
        assert report["done"] is False  # no executor wired -> never done


def test_unconfigured_without_live():
    report = system_gate.run_system_gate(_retail_system(), live_configured=False)
    assert report["modular"] is True
    assert all(r["status"] == "unconfigured" for r in report["flows"])
    assert report["flows_green"] is False


def test_not_implemented_with_live():
    report = system_gate.run_system_gate(_retail_system(), live_configured=True)
    assert all(r["status"] == "not-implemented" for r in report["flows"])


def test_static_invariants_included():
    report = system_gate.run_system_gate(_retail_system())
    assert {r["gate"] for r in report["static"]} == {
        "layer-purity", "single-owner", "no-cross-app-fk",
        "acyclic-downward", "context-cohesion", "orchestration-externalized"}


# ── monolith ─────────────────────────────────────────────────────────────────
def test_monolith_not_modular_not_done():
    report = system_gate.run_system_gate(json.loads((FIX / "system_monolith.json").read_text()))
    assert report["modular"] is False and report["done"] is False


# ── CLI ──────────────────────────────────────────────────────────────────────
def test_cli_exit_one_when_runtime_unverified(tmp_path, capsys):
    sys_path = tmp_path / "sys.json"
    decompose.main([str(FIX / "domain_retail.json"), "--emit-system", str(sys_path)])
    rc = system_gate.main([str(sys_path)])
    assert rc == 1  # modular but runtime unverified -> not done
    out = capsys.readouterr().out
    assert "MODULAR, runtime unverified" in out


def test_cli_json_shape(tmp_path, capsys):
    sys_path = tmp_path / "sys.json"
    decompose.main([str(FIX / "domain_retail.json"), "--emit-system", str(sys_path)])
    capsys.readouterr()  # drain decompose's output
    system_gate.main([str(sys_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["modular"] is True and payload["done"] is False
    assert len(payload["flows"]) == 19
