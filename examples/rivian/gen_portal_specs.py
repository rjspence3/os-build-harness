"""Enrich the expand'd THIN portal app_specs (ReviewerApp, SupplierApp) into RICH, on-design specs —
REPEATABLY. `harness-expand` emits structurally-correct but thin portals (one plain table per capability);
this overlays the Rivian design (sidebar nav, KPI dashboard, styled `columns[].kind` queues, the
case-detail stepper/reviews/timeline, intake create form) + the design-system theme, and re-points the
producer reference — WITHOUT losing the expand'd appReferences (the cross-app wiring).

Run AFTER `harness-expand` (which regenerates thin portals), so enrichment survives regeneration:

    python -m harness.expand ... --out-dir examples/rivian/apps
    python examples/rivian/gen_portal_specs.py --core RivianCoreV2

Idempotent + deterministic. The rich screen shapes are the R8-proven, gate-green set.
"""
import argparse
import json
from pathlib import Path

APPS = Path(__file__).parent / "apps"
TOKENS_CSS = (Path(__file__).parent / "design" / "rivian-design-system" / "tokens" / "tokens.css").read_text()

DESIGN = {
    "source": "referenceApp", "referenceName": "Rivian Supplier Onboarding",
    "themeReference": "design/rivian-design-system/tokens/tokens.css", "mode": "dark",
    "theme": {"palette": {"bg": "#0c0e0c", "panel": "#131612", "line": "#2a2f27", "ink": "#edefe8",
                          "muted": "#a3a99c", "faint": "#6d7266", "yellow": "#ffd329", "green": "#7fce8f",
                          "amber": "#f0b657", "red": "#ef7d6b", "blue": "#79b0e6"},
              "typography": {"body": "'IBM Plex Sans'", "heading": "'Space Grotesk'", "mono": "'JetBrains Mono'"},
              "css": TOKENS_CSS}}


def _acc(screen):
    cid = (screen.get("components") or [{}])[0].get("id") or screen["id"]
    screen["acceptance"] = {"assertions": [{"kind": "componentPresent", "componentId": cid}]}
    return screen


# ── Reviewer workspace: dashboard, queue, case-detail (stepper+reviews+timeline), screening, release ──
def reviewer_screens():
    return [
        _acc({"id": "dashboard", "name": "Dashboard", "isDefault": True,
              "dashboard": {"columns": 4, "cards": [
                  {"label": "Open Cases", "icon": "folder", "entity": "QualificationCase"},
                  {"label": "Overdue", "icon": "clock", "entity": "QualificationCase", "filter": "SlaState = \"OVERDUE\"", "trend": "SLA at risk"},
                  {"label": "Suppliers", "icon": "truck", "entity": "Supplier"},
                  {"label": "Parts", "icon": "cube", "entity": "Part"}]},
              "components": [{"id": "dashHead", "type": "Container", "label": "Onboarding Overview"}]}),
        _acc({"id": "queue", "name": "Case Queue",
              "components": [{"id": "caseTable", "type": "Table", "boundTo": "QualificationCase", "columns": [
                  {"field": "CaseNo", "kind": "identifier"}, {"field": "Owner", "kind": "avatar"},
                  {"field": "Tier", "kind": "tag"}, {"field": "Stage", "kind": "text"},
                  {"field": "Status", "kind": "chip"}, {"field": "SlaState", "kind": "badge"}]}],
              "navigation": [{"fromComponent": "caseTable", "event": "onClick", "toScreen": "caseDetail", "params": ["CaseId"]}]}),
        _acc({"id": "caseDetail", "name": "Case Detail",
              "inputParameters": [{"name": "CaseId", "dataType": "Identifier", "references": "QualificationCase"}],
              "detail": {"stages": [{"label": "Intake", "state": "done"}, {"label": "Screening", "state": "done"},
                                    {"label": "Qualification", "state": "done"}, {"label": "Functional Review", "state": "active"},
                                    {"label": "Approval", "state": "pending"}, {"label": "Activation", "state": "pending"}],
                         "reviewTeams": ["Procurement", "Quality", "Engineering", "Compliance"],
                         "reviewEntity": "ReviewTask", "reviewStateField": "State",
                         "timelineEntity": "AuditEvent", "timelineFields": ["Description", "Actor", "At"],
                         "stateActions": [
                             {"label": "Approve Case", "style": "is-primary", "set": {"Status": "APPROVED", "Stage": "Approval"}},
                             {"label": "Send Back", "set": {"Status": "IN REVIEW", "Stage": "Functional Review"}},
                             {"label": "Activate Supplier", "set": {"Status": "ACTIVATED", "Stage": "Activation"}}]},
              "components": [{"id": "caseBody", "type": "Container"}]}),
        _acc({"id": "screening", "name": "Compliance Screening",
              "components": [{"id": "scrTable", "type": "Table", "boundTo": "Supplier", "columns": [
                  {"field": "Code", "kind": "identifier"}, {"field": "Name", "kind": "text"},
                  {"field": "Status", "kind": "chip"}, {"field": "Country", "kind": "text"}]}]}),
        _acc({"id": "release", "name": "Part Release",
              "components": [{"id": "relTable", "type": "Table", "boundTo": "Part", "columns": [
                  {"field": "Sku", "kind": "identifier"}, {"field": "Name", "kind": "text"},
                  {"field": "Category", "kind": "text"}, {"field": "Status", "kind": "chip"}]}]}),
    ]


REVIEWER_NAV = {"block": "SidebarNav", "brand": "RIVIAN", "subtitle": "Supplier & Parts Onboarding",
                "userLabel": "Devin Lang", "userRole": "Tech Lead · AIDLC", "items": [
                    {"label": "Dashboard", "toScreen": "dashboard", "tag": "DSH", "section": "OPERATIONS"},
                    {"label": "Case Queue", "toScreen": "queue", "tag": "QUE", "badge": "47", "section": "OPERATIONS"},
                    {"label": "Case Detail", "toScreen": "caseDetail", "tag": "CSE", "section": "OPERATIONS"},
                    {"label": "Compliance Screening", "toScreen": "screening", "tag": "SCR", "badge": "3", "section": "OPERATIONS"},
                    {"label": "Part Release", "toScreen": "release", "tag": "PRT", "badge": "4", "section": "OPERATIONS"}]}


# ── Supplier portal: intake create form, documents, status tracker ──
def supplier_screens():
    return [
        _acc({"id": "intake", "name": "Submit Intake", "isDefault": True,
              "components": [{"id": "supTable", "type": "Table", "boundTo": "Supplier", "columns": [
                  {"field": "Code", "kind": "identifier"}, {"field": "Name", "kind": "text"},
                  {"field": "Country", "kind": "text"}, {"field": "Status", "kind": "chip"}]}],
              "actions": [{"name": "CreateSupplier", "trigger": {"onComponent": "supTable", "event": "onClick"},
                           "does": ["CreateEntity"], "validate": True}]}),
        _acc({"id": "status", "name": "Status Tracker",
              "components": [{"id": "statusTable", "type": "Table", "boundTo": "QualificationCase", "columns": [
                  {"field": "CaseNo", "kind": "identifier"}, {"field": "Tier", "kind": "tag"},
                  {"field": "Stage", "kind": "text"}, {"field": "Status", "kind": "chip"}, {"field": "SlaState", "kind": "badge"}]}]}),
    ]


SUPPLIER_NAV = {"block": "SidebarNav", "brand": "RIVIAN", "subtitle": "Supplier Portal",
                "userLabel": "Acme Drivetrains", "userRole": "Supplier · ACM", "items": [
                    {"label": "Submit Intake", "toScreen": "intake", "tag": "INT", "section": "SUBMIT"},
                    {"label": "Status Tracker", "toScreen": "status", "tag": "STA", "section": "TRACK"}]}


def enrich(spec_name, nav, screens, core):
    p = APPS / f"{spec_name}.app_spec.json"
    s = json.loads(p.read_text())
    s["design"] = DESIGN
    s["navigation"] = nav
    s["screens"] = screens
    s["dataModel"] = {"entities": []}                       # references the Core; owns nothing
    # keep expand's appReferences but re-point the producer to the actual Core app name
    for ref in s.get("appReferences", []):
        ref["producerApp"] = core
    p.write_text(json.dumps(s, indent=2))
    print(f"enriched {spec_name}: {len(screens)} rich screens, producer={core}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", default="OnboardingCore", help="tenant app name of the producer Core")
    args = ap.parse_args()
    enrich("ReviewerApp", REVIEWER_NAV, reviewer_screens(), args.core)
    enrich("SupplierApp", SUPPLIER_NAV, supplier_screens(), args.core)
