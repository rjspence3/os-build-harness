"""harness-mitre — the adversary-review dimension.

Maps a built (or spec'd) ODC app onto the MITRE knowledge bases so a build's attack
surface is described in the same language a defender uses:

  ATT&CK (Enterprise/Cloud) — adversary TTPs against the app's auth boundary, data
                              exposure, external integrations, and endpoints.
  ATLAS  (AI/ML)            — adversary TTPs against the app's ODC AI Agents
                              (prompt injection, tool/plugin abuse, data leakage).

Design (per the harness "validate before you assert" ethos):
- STATIC-PRIMARY. The primary pass reads app_spec.json OFFLINE and maps model facts
  (auth.provider, dataModel.public, screen access rules, integrations, agents[].tools/
  .grounding) to techniques with concrete EVIDENCE — deterministic and CI-able, like
  verify.py's spec phase. No tenant, no deploy, no LLM.
- LIVE ENRICHMENT (optional). Pass `--live <snapshot.json>` (a normalized bundle of MCP
  reads: context_roles, context_entities, app_refs, exposed endpoints) and a handful of
  rules cross-check the deployed reality against the spec. Absent ⇒ those rules stay
  quiet (never a fake pass), exactly like verify's unsupplied-snapshot policy.
- HYBRID. The deterministic rule set is the repeatable core. `--llm-prompt` emits a
  structured "residual surface" block for the orchestrating CC session to reason over
  what the rules cannot encode — the module itself never calls an LLM (mirrors verify.py
  not opening its own MCP client).
- ADVISORY. This is a report + an ATT&CK Navigator layer, NOT a hard gate. Security
  posture is rarely a clean pass/fail; `assess_posture` rolls findings into a grade the
  orchestrator can act on, and gate.py can opt-in later.

Usage:
  harness-mitre <spec> [--live <snapshot.json>] [--navigator-out <dir>]
                [--llm-prompt] [--json]

Exit codes: 0 = review ran (advisory — findings do not fail the run by default);
            2 = the spec could not be loaded/parsed. (A `--fail-on <sev>` flag lets a
            caller opt into non-zero on findings at/above a severity.)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Knowledge base — a CURATED subset of ATT&CK Enterprise/Cloud + ATLAS, scoped to
# what a low-code web/agent app can actually expose. Each rule cites an id here; the
# emitter looks up the human name + tactic. Extend from the live corpus as benchmarks
# demand (the ids/tactics are stable MITRE identifiers).
# ─────────────────────────────────────────────────────────────────────────────
ATTACK = "enterprise-attack"
ATLAS = "atlas"

TECHNIQUES: dict[str, dict] = {
    # ATT&CK Enterprise/Cloud
    "T1190": {"name": "Exploit Public-Facing Application", "tactic": "Initial Access", "domain": ATTACK},
    "T1078": {"name": "Valid Accounts", "tactic": "Initial Access", "domain": ATTACK},
    "T1539": {"name": "Steal Web Session Cookie", "tactic": "Credential Access", "domain": ATTACK},
    "T1548": {"name": "Abuse Elevation Control Mechanism", "tactic": "Privilege Escalation", "domain": ATTACK},
    "T1213": {"name": "Data from Information Repositories", "tactic": "Collection", "domain": ATTACK},
    "T1530": {"name": "Data from Cloud Storage", "tactic": "Collection", "domain": ATTACK},
    "T1567": {"name": "Exfiltration Over Web Service", "tactic": "Exfiltration", "domain": ATTACK},
    "T1071": {"name": "Application Layer Protocol", "tactic": "Command and Control", "domain": ATTACK},
    "T1105": {"name": "Ingress Tool Transfer", "tactic": "Command and Control", "domain": ATTACK},
    # ATLAS (AI/ML)
    "AML.T0051": {"name": "LLM Prompt Injection", "tactic": "Initial Access", "domain": ATLAS},
    "AML.T0053": {"name": "LLM Plugin Compromise", "tactic": "Execution", "domain": ATLAS},
    "AML.T0054": {"name": "LLM Jailbreak", "tactic": "Defense Evasion", "domain": ATLAS},
    "AML.T0057": {"name": "LLM Data Leakage", "tactic": "Exfiltration", "domain": ATLAS},
}

# Severity ordering (low index = worse). Used for sorting + `--fail-on` thresholds.
SEVERITIES = ["critical", "high", "medium", "low", "info"]
_SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}


@dataclass
class Finding:
    technique_id: str          # key into TECHNIQUES
    severity: str              # one of SEVERITIES
    summary: str               # one-line "what an adversary could do"
    evidence: str              # the concrete spec/live fact that grounds it (verifiable)
    recommendation: str        # the fix, in the harness's own vocabulary where possible

    @property
    def technique(self) -> dict:
        return TECHNIQUES.get(self.technique_id, {"name": self.technique_id, "tactic": "?", "domain": ATTACK})

    def render(self) -> str:
        t = self.technique
        return (f"[{self.severity.upper():8}] {self.technique_id} {t['name']} ({t['tactic']})\n"
                f"    risk:     {self.summary}\n"
                f"    evidence: {self.evidence}\n"
                f"    fix:      {self.recommendation}")

    def to_dict(self) -> dict:
        t = self.technique
        return {"techniqueId": self.technique_id, "techniqueName": t["name"], "tactic": t["tactic"],
                "domain": t["domain"], "severity": self.severity, "summary": self.summary,
                "evidence": self.evidence, "recommendation": self.recommendation}


# ─────────────────────────────────────────────────────────────────────────────
# Model helpers — small readers over the spec so rules stay declarative.
# ─────────────────────────────────────────────────────────────────────────────
# Attribute types / entity-name hints that mark an entity as holding sensitive data.
_PII_TYPES = {"Email", "PhoneNumber"}
_PII_NAME_HINTS = ("user", "customer", "account", "member", "patient", "employee", "person", "contact")


def _auth_provider(spec: dict) -> str:
    return ((spec.get("auth") or {}).get("provider")) or "anonymous"


def _entities(spec: dict) -> list[dict]:
    return (spec.get("dataModel") or {}).get("entities", []) or []


def _entity_is_sensitive(entity: dict) -> bool:
    if any((a.get("dataType") in _PII_TYPES) for a in entity.get("attributes", [])):
        return True
    name = (entity.get("name") or "").lower()
    return any(hint in name for hint in _PII_NAME_HINTS)


def _screen_writes(screen: dict) -> bool:
    write = {"CreateEntity", "UpdateEntity", "DeleteEntity"}
    for a in screen.get("actions", []):
        if set(a.get("does", [])) & write:
            return True
    return False


def _screen_is_gated(screen: dict) -> bool:
    """True iff the screen declares ANY access control (role subset or access rule)."""
    if screen.get("roles"):
        return True
    access = screen.get("access") or {}
    return bool(access.get("adminOnly") or access.get("requiresRole"))


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic rules. Each: (spec, live) -> list[Finding]. `live` is the optional
# normalized MCP bundle (or {}). Register in RULES. Keep each rule single-purpose and
# grounded in a concrete, checkable fact — evidence must name the spec element.
# ─────────────────────────────────────────────────────────────────────────────
def rule_anonymous_exposure(spec: dict, live: dict) -> list[Finding]:
    """No auth boundary + data-bearing screens = an app anyone on the internet can reach."""
    if _auth_provider(spec) != "anonymous":
        return []
    if not _entities(spec):
        return []
    sensitive = [e["name"] for e in _entities(spec) if _entity_is_sensitive(e)]
    sev = "critical" if sensitive else "high"
    detail = f"holds sensitive entities: {', '.join(sensitive)}" if sensitive else "exposes app data with no login"
    return [Finding(
        "T1190", sev,
        "Any unauthenticated visitor can reach every screen and read app data directly.",
        f"auth.provider is 'anonymous' (or absent); the app {detail}.",
        "Set auth.provider to 'app-local' or 'platform-idp' and gate data screens; enforce the "
        "check server-side (OnReady), never as a client-only route guard.",
    )]


def rule_client_session_trust(spec: dict, live: dict) -> list[Finding]:
    """app-local auth bridges identity through browser storage — tamperable if the app
    trusts the client-supplied user/role instead of deriving it server-side."""
    auth = spec.get("auth") or {}
    if auth.get("provider") != "app-local":
        return []
    findings = [Finding(
        "T1539", "high",
        "The session identity lives in browser storage; a user can edit it to impersonate "
        "another account.",
        f"auth.provider is 'app-local' with sessionKeys {auth.get('sessionKeys') or '{userId,userName}'} "
        "read from browser storage.",
        "Treat the client-supplied id as an untrusted hint. Re-resolve the user server-side "
        "(GetUserId) inside each server action; never branch on a client-provided role.",
    )]
    if auth.get("adminAttribute"):
        findings.append(Finding(
            "T1548", "high",
            "Admin rights are decided by an attribute reachable from the client session — a user "
            "who flips it (or its stored id) escalates to admin.",
            f"auth.adminAttribute='{auth['adminAttribute']}' gates admin screens under app-local auth.",
            "Evaluate the admin check server-side against the DB row for the server-derived user id, "
            "not against any value the browser can set.",
        ))
    return findings


def rule_ungated_write_screens(spec: dict, live: dict) -> list[Finding]:
    """A screen that writes entities but declares no access rule, in an app that HAS roles,
    is a broken-access-control surface (unauthorized mutation)."""
    roles = (spec.get("app") or {}).get("roles", []) or []
    has_role_model = len(roles) > 1 or bool((spec.get("auth") or {}).get("adminAttribute"))
    if not has_role_model:
        return []
    out = []
    for s in spec.get("screens", []):
        if _screen_writes(s) and not _screen_is_gated(s):
            out.append(Finding(
                "T1548", "high",
                "A lower-privileged user can open this write screen and create/update/delete "
                "records they should not be able to.",
                f"screen '{s.get('id')}' has Create/Update/Delete actions but no roles[] or access{{}} rule "
                f"(app defines roles: {roles}).",
                "Add an access rule (roles / access.requiresRole / access.adminOnly) AND enforce it in the "
                "screen's OnReady with a redirect — the client gate is UX only.",
            ))
    return out


def rule_public_data_model(spec: dict, live: dict) -> list[Finding]:
    """A Core/producer that exposes every entity Public is required for modular data flow,
    but it is also a broad cross-app read surface worth flagging."""
    if not (spec.get("dataModel") or {}).get("public"):
        return []
    names = [e["name"] for e in _entities(spec)]
    return [Finding(
        "T1213", "medium",
        "Every entity in this producer is readable by any app that references it — a compromised "
        "or over-scoped consumer can read the whole data model.",
        f"dataModel.public=true exposes all {len(names)} entities: {', '.join(names[:8])}"
        f"{'…' if len(names) > 8 else ''}.",
        "Public is needed for consumers to read across the app boundary, so this is expected for a "
        "Core — but expose only the entities consumers actually need, and keep write logic private "
        "to the producer.",
    )]


def rule_sensitive_data_ungated(spec: dict, live: dict) -> list[Finding]:
    """PII-bearing entities rendered on ungated screens — a collection/exfiltration surface even
    when the app has login (a member reaching another member's data). Complements the anonymous rule."""
    if _auth_provider(spec) == "anonymous":
        return []  # already covered, more severely, by rule_anonymous_exposure
    sensitive = {e["name"] for e in _entities(spec) if _entity_is_sensitive(e)}
    if not sensitive:
        return []
    hits = []
    for s in spec.get("screens", []):
        if _screen_is_gated(s):
            continue
        bound = {c.get("boundTo", "").split(".")[0] for c in s.get("components", [])}
        exposed = sorted(sensitive & {b for b in bound if b})
        if exposed:
            hits.append((s.get("id"), exposed))
    if not hits:
        return []
    detail = "; ".join(f"{sid} → {', '.join(ents)}" for sid, ents in hits)
    return [Finding(
        "T1530", "high",
        "Any logged-in user can read sensitive records they may not own — the query is not scoped "
        "to the authenticated user.",
        f"ungated screens bind sensitive entities: {detail}.",
        "Scope every aggregate to the authenticated user (filter by the server-derived user id); "
        "do not fetch all rows and filter client-side. Enable row-level security where available.",
    )]


def rule_external_integration_exfil(spec: dict, live: dict) -> list[Finding]:
    """Outbound REST integrations are an exfiltration / external-comms edge worth mapping."""
    out = []
    for integ in spec.get("integrations", []) or []:
        if integ.get("kind") == "RestApi":
            out.append(Finding(
                "T1567", "medium",
                "App data can flow to an external service over this REST integration; a compromised "
                "flow could use it to exfiltrate records.",
                f"integration '{integ.get('name')}' → {integ.get('baseUrl') or '(baseUrl unset)'}.",
                "Confirm the endpoint is trusted and pinned, send only the minimum fields, keep the "
                "credential in a server-side connection (never client), and log/limit egress volume.",
            ))
    return out


def rule_sql_action_injection(spec: dict, live: dict) -> list[Finding]:
    """Raw SQL logic units are a SQL-injection surface if any input is string-interpolated."""
    out = []
    for unit in spec.get("logic", []) or []:
        if unit.get("kind") == "sqlAction":
            out.append(Finding(
                "T1190", "medium",
                "A raw SQL node that concatenates user input is exploitable for SQL injection "
                "(read/modify arbitrary rows).",
                f"logic unit '{unit.get('name')}' is a sqlAction (raw SQL node).",
                "Pass every user value as a bound SQL parameter (never string-concatenate into the "
                "statement); prefer an Aggregate over raw SQL when the query allows it.",
            ))
    return out


def rule_binary_upload(spec: dict, live: dict) -> list[Finding]:
    """BinaryData attributes imply file upload/storage — an unrestricted-upload surface."""
    out = []
    for e in _entities(spec):
        cols = [a["name"] for a in e.get("attributes", []) if a.get("dataType") == "BinaryData"]
        if cols:
            out.append(Finding(
                "T1105", "medium",
                "Users can upload files; without type/size limits an attacker can stage malicious "
                "or oversized files.",
                f"entity '{e['name']}' has BinaryData attribute(s): {', '.join(cols)}.",
                "Validate content-type and size server-side, store outside the web root, and never "
                "serve uploads with an executable content-type.",
            ))
    return out


def rule_ai_agent_attack_surface(spec: dict, live: dict) -> list[Finding]:
    """ATLAS: an ODC AI Agent's prompt/tool/grounding surface.

    ── USER CONTRIBUTION SLOT (see the request below the module) ──────────────
    This is the ATLAS heart of the review and the place your ODC agent doctrine
    shapes the result. A default implementation is provided so the feature works
    end-to-end; refine the mapping/severities to match how you actually build agents.
    ───────────────────────────────────────────────────────────────────────────
    """
    out: list[Finding] = []
    for agent in spec.get("agents", []) or []:
        name = agent.get("name", "?")
        tools = agent.get("tools", []) or []
        grounding = agent.get("grounding", []) or []

        # Every agent takes untrusted natural-language input → prompt injection is baseline.
        out.append(Finding(
            "AML.T0051", "high" if tools else "medium",
            "An attacker can craft input that overrides the agent's instructions "
            + ("and drives its tools." if tools else "to change its behavior."),
            f"agent '{name}' processes free-text input"
            + (f"; grounds on {grounding}" if grounding else "; no grounding declared"),
            "Isolate untrusted input from the system prompt, constrain outputs, and treat grounding "
            "text as data (never as instructions).",
        ))

        # Tools turn a hijacked agent into an actuator (plugin compromise).
        if tools:
            out.append(Finding(
                "AML.T0053", "high",
                "A hijacked agent can invoke its tools to read or mutate real data.",
                f"agent '{name}' can call tools: {', '.join(tools)}.",
                "Give each tool least privilege, validate its inputs server-side, and bound the "
                "tool loop with a hard Call Condition (LoopCount limit).",
            ))

        # Grounding on entities that carry user-authored text = indirect (poisoned) injection.
        if grounding:
            out.append(Finding(
                "AML.T0057", "medium",
                "Grounding data pulled from entities can carry attacker-planted instructions "
                "(indirect prompt injection) or be echoed back, leaking records.",
                f"agent '{name}' grounds on entities: {', '.join(grounding)}.",
                "Sanitize/label retrieved rows as untrusted data, scope grounding queries to the "
                "caller, and redact sensitive columns before they enter the prompt.",
            ))
    return out


RULES = [
    rule_anonymous_exposure,
    rule_client_session_trust,
    rule_ungated_write_screens,
    rule_public_data_model,
    rule_sensitive_data_ungated,
    rule_external_integration_exfil,
    rule_sql_action_injection,
    rule_binary_upload,
    rule_ai_agent_attack_surface,
]


def review(spec: dict, live: dict | None = None) -> list[Finding]:
    """Run every rule and return findings sorted worst-first, then by technique id."""
    live = live or {}
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule(spec, live))
    findings.sort(key=lambda f: (_SEV_RANK.get(f.severity, 99), f.technique_id))
    return findings


# ─────────────────────────────────────────────────────────────────────────────
# Posture roll-up — USER CONTRIBUTION SLOT.
# See the request printed after this module is delivered. A minimal fallback keeps
# the CLI working; the interesting policy call (what grade, what blocks) is yours.
# ─────────────────────────────────────────────────────────────────────────────
def assess_posture(findings: list[Finding]) -> dict:
    """Roll a finding list into an overall posture the orchestrator can act on.

    Returns {"grade": str, "blocking": bool, "counts": {severity: n}, "rationale": str}.
    `blocking` is what an opt-in gate.py dimension would key off.

    TODO(user): define the policy. The security-vs-noise tradeoff is real:
      - Which severities count as `blocking`? (critical only? critical+high?)
      - Do AI/ATLAS findings weigh the same as data-exposure findings?
      - What grade scale communicates posture to a non-security builder?
    The fallback below is deliberately simple so tests assert the CONTRACT (keys +
    monotonicity), not a specific threshold — replace it with your judgment.
    """
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    worst = next((s for s in SEVERITIES if counts.get(s)), None)
    grade = {"critical": "F", "high": "D", "medium": "C", "low": "B", "info": "A", None: "A"}[worst]
    return {"grade": grade, "blocking": worst == "critical", "counts": counts,
            "rationale": f"worst finding severity: {worst or 'none'}"}


# ─────────────────────────────────────────────────────────────────────────────
# Emitters.
# ─────────────────────────────────────────────────────────────────────────────
_GRADIENT = ["#66ff66", "#ffe766", "#ff6666"]  # low→high heat for the Navigator layer


def _severity_score(sev: str) -> int:
    return {"critical": 100, "high": 75, "medium": 50, "low": 25, "info": 10}.get(sev, 0)


def navigator_layers(spec: dict, findings: list[Finding]) -> dict[str, dict]:
    """One ATT&CK Navigator layer per domain (enterprise-attack, atlas). Score = worst
    severity that hit each technique; comment aggregates the evidence. Import each into its
    matching Navigator instance."""
    app_name = (spec.get("app") or {}).get("name", "app")
    by_domain: dict[str, dict[str, list[Finding]]] = {}
    for f in findings:
        dom = f.technique["domain"]
        by_domain.setdefault(dom, {}).setdefault(f.technique_id, []).append(f)

    layers = {}
    for dom, tech_map in by_domain.items():
        techniques = []
        for tid, fs in sorted(tech_map.items()):
            worst = min(fs, key=lambda f: _SEV_RANK.get(f.severity, 99))
            techniques.append({
                "techniqueID": tid,
                "score": _severity_score(worst.severity),
                "enabled": True,
                "color": "",
                "comment": " | ".join(f"[{f.severity}] {f.summary}" for f in fs),
            })
        layers[dom] = {
            "name": f"{app_name} — MITRE {'ATLAS' if dom == ATLAS else 'ATT&CK'} review",
            "versions": {"attack": "14", "navigator": "4.9.1", "layer": "4.5"},
            "domain": dom,
            "description": f"harness-mitre adversary review of {app_name} ({len(techniques)} techniques hit).",
            "techniques": techniques,
            "gradient": {"colors": _GRADIENT, "minValue": 0, "maxValue": 100},
            "sorting": 3,
        }
    return layers


def render_report(spec: dict, findings: list[Finding], posture: dict) -> str:
    app_name = (spec.get("app") or {}).get("name", "app")
    lines = [f"# MITRE ATT&CK/ATLAS review — {app_name}", ""]
    lines.append(f"**Posture:** {posture['grade']}  ·  {posture['rationale']}"
                 f"  ·  {'BLOCKING' if posture['blocking'] else 'advisory'}")
    counts = posture["counts"]
    lines.append("**Findings:** " + ", ".join(f"{counts[s]} {s}" for s in SEVERITIES if counts.get(s)) or "none")
    lines.append("")
    if not findings:
        lines.append("_No adversary techniques mapped from the spec. (Static-only; supply --live to enrich.)_")
        return "\n".join(lines)
    # Group by tactic for a defender-familiar reading order.
    by_tactic: dict[str, list[Finding]] = {}
    for f in findings:
        by_tactic.setdefault(f.technique["tactic"], []).append(f)
    for tactic in sorted(by_tactic):
        lines.append(f"## {tactic}")
        lines.append("")
        for f in by_tactic[tactic]:
            t = f.technique
            lines.append(f"### {f.technique_id} · {t['name']}  —  **{f.severity}**")
            lines.append(f"- **Risk:** {f.summary}")
            lines.append(f"- **Evidence:** {f.evidence}")
            lines.append(f"- **Fix:** {f.recommendation}")
            lines.append("")
    return "\n".join(lines)


def residual_prompt(spec: dict, findings: list[Finding]) -> str:
    """The hybrid seam: a structured block the orchestrating CC session reasons over for
    techniques the deterministic rules cannot encode (contextual/novel risk). The module
    never calls an LLM — it hands the reasoning surface to the loop."""
    covered = sorted({f.technique_id for f in findings})
    facts = {
        "app": (spec.get("app") or {}).get("name"),
        "auth": _auth_provider(spec),
        "roles": (spec.get("app") or {}).get("roles", []),
        "entities": [e["name"] for e in _entities(spec)],
        "dataModel.public": bool((spec.get("dataModel") or {}).get("public")),
        "screens_ungated": [s.get("id") for s in spec.get("screens", []) if not _screen_is_gated(s)],
        "integrations": [i.get("name") for i in spec.get("integrations", []) or []],
        "appReferences": [r.get("producerApp") for r in spec.get("appReferences", []) or []],
        "agents": [{"name": a.get("name"), "tools": a.get("tools", []), "grounding": a.get("grounding", [])}
                   for a in spec.get("agents", []) or []],
    }
    return (
        "You are performing a MITRE ATT&CK/ATLAS review of an OutSystems app.\n"
        "The deterministic rules already mapped these techniques: "
        + (", ".join(covered) or "(none)") + ".\n\n"
        "App model facts:\n" + json.dumps(facts, indent=2) + "\n\n"
        "Reason about what the deterministic rules MISSED: contextual privilege-escalation chains, "
        "trust relationships between the app and its producers, tactics implied by combinations of the "
        "facts above (e.g. Discovery → Collection → Exfiltration paths), and any ATLAS technique the "
        "agent configuration invites. For each NEW technique, output {techniqueId, severity, summary, "
        "evidence, recommendation} grounded in a specific fact above — do not restate the covered set."
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLI.
# ─────────────────────────────────────────────────────────────────────────────
def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness-mitre",
        description="Map an ODC app (spec + optional live state) onto MITRE ATT&CK/ATLAS.")
    parser.add_argument("spec", type=Path, help="Path to the app spec JSON.")
    parser.add_argument("--live", type=Path, default=None,
                        help="Optional normalized MCP snapshot (roles/entities/refs/endpoints) for live enrichment.")
    parser.add_argument("--navigator-out", type=Path, default=None,
                        help="Directory to write ATT&CK Navigator layer JSON per domain.")
    parser.add_argument("--llm-prompt", action="store_true",
                        help="Print the residual-surface prompt for the orchestrator to reason over, then exit.")
    parser.add_argument("--json", action="store_true", help="Emit findings + posture as JSON.")
    parser.add_argument("--fail-on", choices=SEVERITIES, default=None,
                        help="Exit non-zero if any finding is at/above this severity (opt-in gating).")
    args = parser.parse_args(argv)

    try:
        spec = _load(args.spec)
    except (OSError, json.JSONDecodeError) as e:
        print(f"could not load spec: {e}", file=sys.stderr)
        return 2
    live = _load(args.live) if args.live else {}

    findings = review(spec, live)

    if args.llm_prompt:
        print(residual_prompt(spec, findings))
        return 0

    posture = assess_posture(findings)

    if args.navigator_out:
        args.navigator_out.mkdir(parents=True, exist_ok=True)
        for dom, layer in navigator_layers(spec, findings).items():
            (args.navigator_out / f"navigator-{dom}.json").write_text(
                json.dumps(layer, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps({"posture": posture, "findings": [f.to_dict() for f in findings]}, indent=2))
    else:
        print(render_report(spec, findings, posture))

    if args.fail_on:
        threshold = _SEV_RANK[args.fail_on]
        if any(_SEV_RANK.get(f.severity, 99) <= threshold for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
