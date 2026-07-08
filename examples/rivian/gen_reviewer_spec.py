"""Generate the Rivian **Reviewer Workspace** app_spec (the walking-skeleton hero app).

Single self-contained app (local entities, no cross-app refs yet) so the RICH UI is proven on
the real Rivian design before the multi-app/workflow/agent layers are added. The design.theme is
mined from `design/Supplier Onboarding.dc.html` (exact tokens) + the UI_CLASS_CONTRACT the harness
recipes emit (see harness/prompt_recipes.py). Re-run to regenerate the JSON.

    python examples/rivian/gen_reviewer_spec.py
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "apps" / "ReviewerWorkspace.app_spec.json"

# ── Design tokens mined from Supplier Onboarding.dc.html (:root) ──────────────
PALETTE = {
    "bg": "#0c0e0c", "panel": "#131612", "line": "#2a2f27", "line-soft": "#20241d",
    "ink": "#edefe8", "muted": "#a3a99c", "faint": "#6d7266",
    "yellow": "#ffd329", "green": "#7fce8f", "amber": "#f0b657", "red": "#ef7d6b", "blue": "#79b0e6",
}

# Component CSS painting the harness UI_CLASS_CONTRACT hooks into the Rivian dark look.
# Palette keys are injected as :root --<key> by the theme recipe; we reference var(--key).
THEME_CSS = """
body,.screen-container{background:var(--bg);color:var(--ink);font-family:'IBM Plex Sans',system-ui,sans-serif;}
h1,h2,h3,h4,h5,.kpi-value{font-family:'Space Grotesk',sans-serif;}
/* the fixed sidebar sits in this left gutter on every screen */
body{padding-left:248px;}

/* ── app-shell sidebar (fixed left rail) ── */
.app-sidebar{position:fixed;left:0;top:0;bottom:0;width:248px;overflow-y:auto;z-index:20;background:#0d0f0c;border-right:1px solid var(--line);padding:18px 14px;box-sizing:border-box;}
.sidebar-brand{color:var(--yellow);font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:20px;letter-spacing:.04em;}
.sidebar-brand small,.sidebar-sub{display:block;color:var(--faint);font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;margin-top:4px;}
.nav-section{color:var(--faint);font-family:'JetBrains Mono',monospace;font-weight:600;font-size:10px;letter-spacing:.14em;text-transform:uppercase;margin:18px 6px 6px;}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:5px;color:#c9cdc2;text-decoration:none;font-size:14px;border-left:3px solid transparent;}
.nav-item:hover{background:#161810;}
.nav-item.is-active{background:#1a1d13;border-left:3px solid var(--yellow);color:var(--ink);font-weight:600;}
.nav-tag{font-family:'JetBrains Mono',monospace;font-weight:600;font-size:10px;letter-spacing:.08em;background:#20241d;color:var(--muted);padding:3px 5px;border-radius:3px;}
.nav-badge{margin-left:auto;background:#20241d;color:var(--muted);border-radius:10px;padding:1px 8px;font-size:11px;}
.sidebar-user{display:flex;align-items:center;gap:10px;margin-top:20px;padding-top:14px;border-top:1px solid var(--line);}
.sidebar-user .avatar{width:32px;height:32px;}
.online-dot{width:8px;height:8px;border-radius:50%;background:var(--green);margin-left:auto;}

/* ── top bar ── */
.app-topbar{display:flex;align-items:center;gap:16px;padding:14px 20px;border-bottom:1px solid var(--line);}
.breadcrumb{color:var(--faint);font-size:13px;}
.breadcrumb b{color:var(--ink);}
.env-chip{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--green);border:1px solid var(--line);border-radius:3px;padding:3px 8px;}

/* ── status cells ── */
.chip,.tag,.badge{display:inline-block;padding:3px 8px;border-radius:3px;font-family:'JetBrains Mono',monospace;font-weight:600;font-size:11px;letter-spacing:.04em;text-transform:uppercase;}
.chip{background:#20241d;color:var(--ink);}
.chip-approved,.chip-clear,.chip-qualified,.badge-approved,.badge-clear{background:rgba(127,206,143,.15);color:var(--green);}
.chip-in-review,.chip-pending,.badge-in-review,.badge-pending{background:rgba(240,182,87,.15);color:var(--amber);}
.chip-overdue,.chip-rejected,.chip-blocked,.badge-overdue,.badge-breached{background:rgba(239,125,107,.15);color:var(--red);}
.chip-screening,.badge-screening{background:rgba(121,176,230,.15);color:var(--blue);}
.tag-t1,.tag-critical{background:rgba(255,211,41,.15);color:var(--yellow);}
.tag-t2,.tag-standard{background:#20241d;color:var(--muted);}
.cell-id{font-family:'JetBrains Mono',monospace;font-weight:500;font-size:12px;color:var(--muted);}
.avatar{width:28px;height:28px;border-radius:50%;background:#2a2f27;color:var(--ink);display:inline-flex;align-items:center;justify-content:center;font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:11px;}

/* ── KPI dashboard ── */
.kpi-row{display:flex;gap:16px;}
.kpi-card{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:16px;}
.kpi-icon{color:var(--yellow);font-size:16px;margin-bottom:8px;}
.kpi-value{font-weight:600;font-size:28px;color:var(--ink);}
.kpi-label{color:var(--faint);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-top:2px;}
.kpi-trend{color:var(--green);font-size:12px;margin-top:6px;}

/* ── case-detail: stepper + reviews + timeline ── */
.stepper{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 18px;}
.step{padding:8px 12px;border-radius:5px;border:1px solid var(--line);background:var(--panel);color:var(--faint);font-size:13px;}
.step.is-done{border-color:var(--green);color:var(--green);}
.step.is-active{border-color:var(--yellow);color:var(--ink);box-shadow:0 0 0 1px var(--yellow) inset;}
.step.is-pending{opacity:.55;}
.review-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:8px 0 18px;}
.review-card{background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:12px;}
.review-card h5{margin:0 0 8px;font-size:13px;color:var(--muted);}
.timeline{border-left:2px solid var(--line);padding-left:14px;margin-top:8px;}
.timeline-item{margin-bottom:12px;color:var(--muted);font-size:13px;}

/* ── tables + content ── */
.content{padding:20px;}
table{border-collapse:collapse;width:100%;}
th{text-align:left;color:var(--faint);font-family:'JetBrains Mono',monospace;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.06em;padding:10px;border-bottom:1px solid var(--line);}
td{padding:12px 10px;border-bottom:1px solid var(--line-soft);color:#c9cdc2;font-size:14px;}
tr:hover td{background:#10120f;}
.btn-primary,.is-primary{background:var(--yellow);color:#161810;border-radius:5px;font-weight:600;}
""".strip()

# NOTE: web fonts intentionally omitted — @import is stripped at ODC publish (known wall), and
# JS-injecting a <link> is a later-polish step. The CSS font-family fallbacks (system-ui / monospace)
# carry v1; the Rivian LOOK is the dark palette + layout + mono tags, which survive the fallback.


def entity(name, attrs, natural=None, sample=None):
    out = {"name": name, "attributes": [
        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}
    for a in attrs:
        col = {"name": a[0], "dataType": a[1]}
        if len(a) > 2 and a[2] == "ref":
            col = {"name": a[0], "dataType": "Identifier", "references": a[1]}
        elif a[0] == natural:
            col["naturalKey"] = True
        out["attributes"].append(col)
    if sample:
        out["sampleData"] = sample
    return out


ENTITIES = [
    entity("Supplier", [("Code", "Text"), ("Name", "Text"), ("Tier", "Text"),
                        ("Status", "Text"), ("Country", "Text")], natural="Code",
           sample=[
               {"Code": "ACM", "Name": "Acme Drivetrains", "Tier": "T1 · CRITICAL", "Status": "QUALIFIED", "Country": "USA"},
               {"Code": "NVL", "Name": "Novalite Cells", "Tier": "T1 · CRITICAL", "Status": "IN REVIEW", "Country": "USA"},
               {"Code": "BRG", "Name": "Bright Composites", "Tier": "T2 · STANDARD", "Status": "SCREENING", "Country": "MEX"},
               {"Code": "TORQ", "Name": "TorqWorks", "Tier": "T2 · STANDARD", "Status": "QUALIFIED", "Country": "CAN"}]),
    entity("Part", [("Sku", "Text"), ("Name", "Text"), ("SupplierId", "Supplier", "ref"),
                    ("Category", "Text"), ("Status", "Text")], natural="Sku",
           sample=[
               {"Sku": "BRK-014", "Name": "Regen Brake Module", "SupplierId": "ACM", "Category": "Braking", "Status": "PENDING"},
               {"Sku": "CEL-221", "Name": "4695 Cell Pack", "SupplierId": "NVL", "Category": "Battery", "Status": "IN REVIEW"},
               {"Sku": "PNL-071", "Name": "Frunk Panel", "SupplierId": "BRG", "Category": "Body", "Status": "BLOCKED"}]),
    entity("QualificationCase",
           [("CaseNo", "Text"), ("SupplierId", "Supplier", "ref"), ("PartId", "Part", "ref"),
            ("Tier", "Text"), ("Status", "Text"), ("Stage", "Text"), ("Score", "Text"),
            ("SlaState", "Text"), ("Owner", "Text")], natural="CaseNo",
           sample=[
               {"CaseNo": "Q-1041", "SupplierId": "ACM", "PartId": "BRK-014", "Tier": "T1 · CRITICAL",
                "Status": "IN REVIEW", "Stage": "Functional Review", "Score": "92", "SlaState": "OVERDUE", "Owner": "Devin Lang"},
               {"CaseNo": "Q-1042", "SupplierId": "NVL", "PartId": "CEL-221", "Tier": "T1 · CRITICAL",
                "Status": "SCREENING", "Stage": "Screening", "Score": "—", "SlaState": "IN REVIEW", "Owner": "Mara Vance"},
               {"CaseNo": "Q-1043", "SupplierId": "BRG", "PartId": "PNL-071", "Tier": "T2 · STANDARD",
                "Status": "APPROVED", "Stage": "Activation", "Score": "88", "SlaState": "CLEAR", "Owner": "Sanjay Rao"},
               {"CaseNo": "Q-1044", "SupplierId": "TORQ", "PartId": "BRK-014", "Tier": "T2 · STANDARD",
                "Status": "IN REVIEW", "Stage": "Qualification", "Score": "76", "SlaState": "IN REVIEW", "Owner": "Devin Lang"}]),
    entity("ReviewTask",
           [("CaseId", "QualificationCase", "ref"), ("Team", "Text"), ("State", "Text"), ("DueDate", "Text")],
           sample=[
               {"CaseId": "Q-1041", "Team": "Procurement", "State": "APPROVED", "DueDate": "2026-07-02"},
               {"CaseId": "Q-1041", "Team": "Quality", "State": "IN REVIEW", "DueDate": "2026-07-09"},
               {"CaseId": "Q-1041", "Team": "Engineering", "State": "IN REVIEW", "DueDate": "2026-07-09"},
               {"CaseId": "Q-1041", "Team": "Compliance", "State": "PENDING", "DueDate": "2026-07-11"}]),
    entity("AuditEvent",
           [("CaseId", "QualificationCase", "ref"), ("Description", "Text"), ("Actor", "Text"), ("At", "Text")],
           sample=[
               {"CaseId": "Q-1041", "Description": "Case created from supplier intake", "Actor": "System", "At": "Jul 1"},
               {"CaseId": "Q-1041", "Description": "Denied-party screening cleared", "Actor": "ScreeningAgent", "At": "Jul 1"},
               {"CaseId": "Q-1041", "Description": "Qualification score 92 recorded", "Actor": "Devin Lang", "At": "Jul 3"},
               {"CaseId": "Q-1041", "Description": "Procurement review approved", "Actor": "Mara Vance", "At": "Jul 3"}]),
]

NAV = {
    "block": "SidebarNav", "brand": "RIVIAN", "subtitle": "Supplier & Parts Onboarding",
    "userLabel": "Devin Lang", "userRole": "Tech Lead · AIDLC",
    "items": [
        {"label": "Dashboard", "toScreen": "dashboard", "tag": "DSH", "section": "OPERATIONS"},
        {"label": "Case Queue", "toScreen": "queue", "tag": "QUE", "badge": "47", "section": "OPERATIONS"},
        {"label": "Case Detail", "toScreen": "caseDetail", "tag": "CSE", "section": "OPERATIONS"},
        {"label": "Compliance Screening", "toScreen": "screening", "tag": "SCR", "badge": "3", "section": "OPERATIONS"},
        {"label": "Part Release", "toScreen": "release", "tag": "PRT", "badge": "4", "section": "OPERATIONS"},
        {"label": "Supplier Intake", "toScreen": "intake", "tag": "INT", "section": "SUPPLIER"},
    ],
}

SCREENS = [
    {"id": "dashboard", "name": "Dashboard", "isDefault": True,
     "dashboard": {"columns": 4, "cards": [
         {"label": "Open Cases", "icon": "folder", "entity": "QualificationCase"},
         {"label": "Overdue", "icon": "clock", "entity": "QualificationCase", "filter": "SlaState = \"OVERDUE\"", "trend": "SLA at risk"},
         {"label": "Suppliers", "icon": "truck", "entity": "Supplier"},
         {"label": "Parts", "icon": "cube", "entity": "Part"}]},
     "components": [{"id": "dashHead", "type": "Container", "label": "Onboarding Overview"}]},
    {"id": "queue", "name": "Case Queue",
     "components": [{"id": "caseTable", "type": "Table", "boundTo": "QualificationCase", "columns": [
         {"field": "CaseNo", "kind": "identifier"},
         {"field": "Owner", "kind": "avatar"},
         {"field": "Tier", "kind": "tag"},
         {"field": "Stage", "kind": "text"},
         {"field": "Status", "kind": "chip"},
         {"field": "SlaState", "kind": "badge"}]}],
     "navigation": [{"fromComponent": "caseTable", "event": "onClick", "toScreen": "caseDetail"}],
     "actions": [{"name": "UpdateCase", "trigger": {"onComponent": "caseTable", "event": "onClick"},
                  "does": ["UpdateEntity"]}]},
    {"id": "caseDetail", "name": "Case Detail",
     "inputParameters": [{"name": "CaseId", "dataType": "Identifier", "references": "QualificationCase"}],
     "detail": {
         "stages": [
             {"label": "Intake", "state": "done"}, {"label": "Screening", "state": "done"},
             {"label": "Qualification", "state": "done"}, {"label": "Functional Review", "state": "active"},
             {"label": "Approval", "state": "pending"}, {"label": "Activation", "state": "pending"}],
         "reviewTeams": ["Procurement", "Quality", "Engineering", "Compliance"],
         "reviewEntity": "ReviewTask", "reviewStateField": "State",
         "timelineEntity": "AuditEvent", "timelineFields": ["Description", "Actor", "At"]},
     "components": [{"id": "caseBody", "type": "Container"}]},
    {"id": "screening", "name": "Compliance Screening",
     "components": [{"id": "scrTable", "type": "Table", "boundTo": "Supplier", "columns": [
         {"field": "Code", "kind": "identifier"}, {"field": "Name", "kind": "text"},
         {"field": "Status", "kind": "chip"}, {"field": "Country", "kind": "text"}]}]},
    {"id": "release", "name": "Part Release",
     "components": [{"id": "relTable", "type": "Table", "boundTo": "Part", "columns": [
         {"field": "Sku", "kind": "identifier"}, {"field": "Name", "kind": "text"},
         {"field": "Category", "kind": "text"}, {"field": "Status", "kind": "chip"}]}],
     "actions": [{"name": "UpdatePart", "trigger": {"onComponent": "relTable", "event": "onClick"},
                  "does": ["UpdateEntity"]}]},
    {"id": "intake", "name": "Supplier Intake",
     "components": [
         {"id": "addSupplierBtn", "type": "Button", "label": "+ New Supplier"},
         {"id": "intakeTable", "type": "Table", "boundTo": "Supplier", "columns": [
             {"field": "Code", "kind": "identifier"}, {"field": "Name", "kind": "text"},
             {"field": "Tier", "kind": "tag"}, {"field": "Status", "kind": "chip"}]}],
     "actions": [{"name": "CreateSupplier", "trigger": {"onComponent": "addSupplierBtn", "event": "onClick"},
                  "does": ["CreateEntity"], "validate": True}]},
]

# Every screen needs a machine-checkable acceptance contract (harness-verify gates on it).
# Assert the screen's primary component is present at runtime.
for _s in SCREENS:
    _cid = (_s.get("components") or [{}])[0].get("id") or _s["id"]
    _s["acceptance"] = {"assertions": [{"kind": "componentPresent", "componentId": _cid}]}

SPEC = {
    "specVersion": "0.2",
    "app": {"name": "RivianReviewerWorkspace", "roles": ["Reviewer"]},
    "design": {"source": "screenshots", "referenceName": "Rivian Supplier Onboarding",
               "theme": {"palette": PALETTE,
                         "typography": {"body": "'IBM Plex Sans'", "heading": "'Space Grotesk'", "mono": "'JetBrains Mono'"},
                         "css": THEME_CSS}},
    "dataModel": {"entities": ENTITIES},
    "navigation": NAV,
    "screens": SCREENS,
}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(SPEC, indent=2))
    print(f"wrote {OUT}  ({len(json.dumps(SPEC))} bytes, {len(ENTITIES)} entities, {len(SCREENS)} screens)")
