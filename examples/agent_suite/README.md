# Agent Suite — 10 highest-ROI enterprise agent patterns, built spec-driven on ODC

Ten production-grade OutSystems agent apps, one per high-value use case, all produced by the SAME harness
pipeline (`domain_spec → decompose → system_gate → expand → build_system`). This is the harness thesis at
N=10: the machinery is fixed; each use case is just a spec.

## The shared architecture (every use case)

Each spec decomposes into the same modular topology — no bespoke wiring:

```
<Name>Core          (system of record + immutable AuditEvent)      — owns the entities
<Name>Agent         (AIAgent: grounding + native Action-calling)   — classifies / retrieves / PROPOSES
<Name>Workflow      (BusinessProcess / BPT)                        — the human-in-the-loop approval
Customer/Ops/Admin  (end-user portals)                             — queues, inboxes, dashboards
<Name>DesignSystem  (foundation library)
```

**The write step is the whole game.** The agent never mutates the system of record directly — it *proposes*
a bounded action (a small closed set per use case). Low-risk proposals auto-execute; anything above the risk
bar holds at a **native OutSystems approval activity (BPT)** until a human signs off. Every action writes an
`AuditEvent`. That is the filter that separates pilots that ship from pilots that die in security review:
**bounded action space + human at the write step + provable audit trail.**

The two agent tool shapes are both live-proven (see `examples/knowledge_agent/`): READ/retrieve (grounding +
Consumed REST to an external corpus) and WRITE (a server action, bounded, fires through the native tool loop
with Call Condition `LoopCount >= N`).

## The ten (roughly by proven ROI)

| # | Use case | Agent proposes (bounded action space) | Write step / HITL |
|---|----------|----------------------------------------|-------------------|
| 1 | **Support triage & resolution** | reply · auto-resolve · escalate | auto low-risk; approve tier-2+ |
| 2 | **Sales/CRM hygiene & prep** | update field · log next-step · draft brief | approve CRM writes on key accounts |
| 3 | **Document processing** | extract → validate → post/route | approve post-to-SoR above $ / low-confidence |
| 4 | **Internal knowledge assistant** | answer w/ citation · escalate | read-only; escalate = the only "write" |
| 5 | **Coding & test generation** | draft change · generate tests | PR review = the human gate |
| 6 | **Procurement & vendor ops** | match PO · flag exception · approve pay | approve payment release |
| 7 | **Compliance & audit prep** | gather evidence · flag gap · draft remediation | approve control attestations |
| 8 | **Data analysis / reporting** | NL→query · generate report · narrate anomaly | approve published/distributed reports |
| 9 | **Recruiting ops** | screen · schedule · structured notes | approve advance/reject decisions |
| 10 | **Field service & ops dispatch** | diagnose · parts lookup · create work order | approve dispatch / parts commit |

Folders `01_…` … `10_…`, each with `domain_spec.json` (+ generated `system_spec.json`). Every spec
decomposes MODULAR with all six architecture gates PASS. Build order and live-build status tracked below.

## Build order (proven patterns first, cap-paced)

1. **#1 support triage, #4 knowledge, #3 document processing** — exercise read-ground, external-tool, and
   the write/approval spine. (KnowledgeAgent already proves the #4 read pattern live.)
2. #2 CRM, #6 procurement, #9 recruiting — CRM/SoR writes through approval.
3. #5 coding, #7 compliance, #8 reporting, #10 field service.

Live builds run against the ODC tenant in cap-paced batches (each app ≈ 2–4 Mentor sessions; tenant cap is
100 concurrent / 24h). Spec authoring here is cap-free and complete first.
