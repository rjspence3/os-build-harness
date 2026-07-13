"""Tests for harness-mitre — the ATT&CK/ATLAS adversary-review dimension (offline, deterministic)."""
from __future__ import annotations

import copy
import json

import pytest

from harness import mitre
from harness.mitre import (
    SEVERITIES,
    TECHNIQUES,
    Finding,
    assess_posture,
    navigator_layers,
    render_report,
    residual_prompt,
    review,
)


def _base_spec() -> dict:
    """A minimal valid-shaped spec with a login boundary and one gated screen."""
    return {
        "specVersion": "0.2",
        "app": {"name": "demo", "roles": ["Member", "Admin"]},
        "auth": {"provider": "platform-idp"},
        "dataModel": {"entities": [
            {"name": "Widget", "attributes": [{"name": "Id", "dataType": "Identifier", "isIdentifier": True}]},
        ]},
        "screens": [
            {"id": "list", "name": "List", "roles": ["Member"],
             "components": [{"id": "t", "type": "Table", "boundTo": "Widget"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "t"}]}},
        ],
    }


# ── rule: anonymous exposure ────────────────────────────────────────────────
def test_anonymous_app_with_pii_is_critical():
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}
    spec["dataModel"]["entities"].append(
        {"name": "Customer", "attributes": [{"name": "Email", "dataType": "Email"}]})
    findings = review(spec)
    hit = [f for f in findings if f.technique_id == "T1190"]
    assert hit and hit[0].severity == "critical"
    assert "Customer" in hit[0].evidence


def test_anonymous_absent_auth_defaults_to_anonymous():
    spec = _base_spec()
    del spec["auth"]
    ids = {f.technique_id for f in review(spec)}
    assert "T1190" in ids  # no auth block ⇒ treated as anonymous exposure


def test_authenticated_app_has_no_anonymous_finding():
    assert not [f for f in review(_base_spec()) if f.technique_id == "T1190"]


# ── rule: client session trust (app-local) ──────────────────────────────────
def test_app_local_flags_session_theft_and_escalation():
    spec = _base_spec()
    spec["auth"] = {"provider": "app-local", "userEntity": "Widget",
                    "adminAttribute": "IsAdmin", "sessionKeys": {"userId": "uid"}}
    ids = {f.technique_id for f in review(spec)}
    assert "T1539" in ids  # session in browser storage
    assert "T1548" in ids  # admin attribute reachable from client


def test_app_local_without_admin_attr_has_no_escalation_finding():
    spec = _base_spec()
    spec["auth"] = {"provider": "app-local", "sessionKeys": {"userId": "uid"}}
    findings = review(spec)
    assert any(f.technique_id == "T1539" for f in findings)
    assert not any(f.technique_id == "T1548" and "adminAttribute" in f.evidence for f in findings)


# ── rule: ungated write screens ─────────────────────────────────────────────
def test_ungated_write_screen_in_role_app_flags_bac():
    spec = _base_spec()
    spec["screens"].append({
        "id": "editor", "name": "Editor",
        "components": [{"id": "f", "type": "Form"}],
        "actions": [{"name": "save", "trigger": {"onComponent": "f", "event": "onSubmit"},
                     "does": ["UpdateEntity"]}],
        "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "f"}]},
    })
    hit = [f for f in review(spec) if f.technique_id == "T1548" and "editor" in f.evidence]
    assert hit and hit[0].severity == "high"


def test_gated_write_screen_is_not_flagged():
    spec = _base_spec()
    spec["screens"].append({
        "id": "editor", "name": "Editor", "access": {"adminOnly": True},
        "components": [{"id": "f", "type": "Form"}],
        "actions": [{"name": "save", "trigger": {"onComponent": "f", "event": "onSubmit"},
                     "does": ["UpdateEntity"]}],
        "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "f"}]},
    })
    assert not [f for f in review(spec) if "editor" in f.evidence]


def test_single_role_app_does_not_flag_ungated_writes():
    """No role model ⇒ no broken-access-control surface to flag."""
    spec = _base_spec()
    spec["app"]["roles"] = ["User"]
    spec["screens"].append({
        "id": "editor", "name": "Editor",
        "components": [{"id": "f", "type": "Form"}],
        "actions": [{"name": "save", "trigger": {"onComponent": "f", "event": "onSubmit"},
                     "does": ["CreateEntity"]}],
        "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "f"}]},
    })
    assert not [f for f in review(spec) if f.technique_id == "T1548"]


# ── rule: public data model ─────────────────────────────────────────────────
def test_public_data_model_flags_collection():
    spec = _base_spec()
    spec["dataModel"]["public"] = True
    hit = [f for f in review(spec) if f.technique_id == "T1213"]
    assert hit and hit[0].severity == "medium"


# ── rule: sensitive data on ungated screen (authenticated) ──────────────────
def test_authenticated_ungated_sensitive_screen_flags_exfil():
    spec = _base_spec()
    spec["dataModel"]["entities"].append(
        {"name": "Customer", "attributes": [{"name": "Email", "dataType": "Email"}]})
    spec["screens"].append({
        "id": "all", "name": "All",  # no roles/access ⇒ ungated
        "components": [{"id": "c", "type": "Table", "boundTo": "Customer"}],
        "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "c"}]},
    })
    assert any(f.technique_id == "T1530" for f in review(spec))


# ── rule: external integration ──────────────────────────────────────────────
def test_rest_integration_flags_exfil():
    spec = _base_spec()
    spec["integrations"] = [{"name": "PartnerAPI", "kind": "RestApi", "baseUrl": "https://x.example"}]
    hit = [f for f in review(spec) if f.technique_id == "T1567"]
    assert hit and "PartnerAPI" in hit[0].evidence


# ── rule: sql action ────────────────────────────────────────────────────────
def test_sql_action_flags_injection():
    spec = _base_spec()
    spec["logic"] = [{"kind": "sqlAction", "name": "RawSearch"}]
    assert any(f.technique_id == "T1190" and "RawSearch" in f.evidence for f in review(spec))


# ── rule: binary upload ─────────────────────────────────────────────────────
def test_binary_attribute_flags_upload():
    spec = _base_spec()
    spec["dataModel"]["entities"][0]["attributes"].append({"name": "Doc", "dataType": "BinaryData"})
    assert any(f.technique_id == "T1105" for f in review(spec))


# ── rule: AI agent (ATLAS) ──────────────────────────────────────────────────
def test_agent_with_tools_flags_injection_and_plugin():
    spec = _base_spec()
    spec["agents"] = [{"name": "Helper", "systemPrompt": "help",
                       "tools": ["LookupOrder"], "grounding": ["Widget"]}]
    ids = {f.technique_id for f in review(spec)}
    assert "AML.T0051" in ids  # prompt injection
    assert "AML.T0053" in ids  # plugin/tool compromise
    assert "AML.T0057" in ids  # grounding data leakage


def test_agent_without_tools_is_lower_severity():
    spec = _base_spec()
    spec["agents"] = [{"name": "Chat", "systemPrompt": "chat"}]
    inj = [f for f in review(spec) if f.technique_id == "AML.T0051"]
    assert inj and inj[0].severity == "medium"  # no tools ⇒ smaller blast radius


# ── ordering + KB integrity ─────────────────────────────────────────────────
def test_findings_sorted_worst_first():
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}
    spec["integrations"] = [{"name": "API", "kind": "RestApi", "baseUrl": "https://x"}]
    findings = review(spec)
    ranks = [SEVERITIES.index(f.severity) for f in findings]
    assert ranks == sorted(ranks)


def test_every_rule_cites_a_known_technique():
    """No rule may emit a technique id absent from the KB (the emitter looks it up)."""
    spec = _base_spec()
    spec["auth"] = {"provider": "app-local", "adminAttribute": "IsAdmin"}
    spec["dataModel"]["public"] = True
    spec["dataModel"]["entities"][0]["attributes"].append({"name": "Doc", "dataType": "BinaryData"})
    spec["integrations"] = [{"name": "API", "kind": "RestApi", "baseUrl": "https://x"}]
    spec["logic"] = [{"kind": "sqlAction", "name": "Raw"}]
    spec["agents"] = [{"name": "A", "systemPrompt": "p", "tools": ["T"], "grounding": ["Widget"]}]
    for f in review(spec):
        assert f.technique_id in TECHNIQUES


# ── posture contract (user owns the policy; we assert the shape) ─────────────
def test_posture_contract_and_monotonicity():
    clean = assess_posture([])
    assert set(clean) >= {"grade", "blocking", "counts", "rationale"}
    assert clean["blocking"] is False

    crit = assess_posture([Finding("T1190", "critical", "s", "e", "r")])
    assert crit["counts"]["critical"] == 1
    # A critical finding must never be graded better than a clean app.
    grades = "FDCBA"
    assert grades.index(crit["grade"]) <= grades.index(clean["grade"])


# ── emitters ────────────────────────────────────────────────────────────────
def test_navigator_layers_split_by_domain_and_are_valid():
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}  # ATT&CK finding
    spec["agents"] = [{"name": "A", "systemPrompt": "p", "tools": ["T"]}]  # ATLAS findings
    layers = navigator_layers(spec, review(spec))
    assert set(layers) == {mitre.ATTACK, mitre.ATLAS}
    for dom, layer in layers.items():
        assert layer["domain"] == dom
        assert layer["techniques"]
        for t in layer["techniques"]:
            assert t["techniqueID"] in TECHNIQUES
            assert 0 <= t["score"] <= 100
        # round-trips as JSON (Navigator import contract)
        json.dumps(layer)


def test_report_renders_markdown_with_tactics():
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}
    findings = review(spec)
    report = render_report(spec, findings, assess_posture(findings))
    assert "# MITRE" in report
    assert "Initial Access" in report  # T1190's tactic header


def test_report_handles_clean_spec():
    findings = review(_base_spec())
    report = render_report(_base_spec(), findings, assess_posture(findings))
    assert "No adversary techniques" in report or findings  # either clean message or real findings


def test_residual_prompt_lists_covered_and_facts():
    spec = _base_spec()
    spec["agents"] = [{"name": "A", "systemPrompt": "p", "tools": ["T"]}]
    prompt = residual_prompt(spec, review(spec))
    assert "AML.T0051" in prompt
    assert "app model facts" in prompt.lower()


# ── CLI ─────────────────────────────────────────────────────────────────────
def test_cli_json_output(tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}
    spec_path.write_text(json.dumps(spec))
    rc = mitre.main([str(spec_path), "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "posture" in out and "findings" in out


def test_cli_navigator_out(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}
    spec_path.write_text(json.dumps(spec))
    out_dir = tmp_path / "nav"
    assert mitre.main([str(spec_path), "--navigator-out", str(out_dir)]) == 0
    assert (out_dir / f"navigator-{mitre.ATTACK}.json").exists()


def test_cli_fail_on_threshold(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec = _base_spec()
    spec["auth"] = {"provider": "anonymous"}
    spec["dataModel"]["entities"].append(
        {"name": "Customer", "attributes": [{"name": "Email", "dataType": "Email"}]})
    spec_path.write_text(json.dumps(spec))
    assert mitre.main([str(spec_path), "--fail-on", "critical"]) == 1  # anonymous+PII ⇒ a critical
    # A clean, gated app produces no critical ⇒ threshold not tripped.
    clean_path = tmp_path / "clean.json"
    clean_path.write_text(json.dumps(_base_spec()))
    assert mitre.main([str(clean_path), "--fail-on", "critical"]) == 0


def test_cli_bad_spec_returns_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert mitre.main([str(bad)]) == 2


def test_cli_llm_prompt(tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_base_spec()))
    assert mitre.main([str(spec_path), "--llm-prompt"]) == 0
    assert "MITRE" in capsys.readouterr().out
