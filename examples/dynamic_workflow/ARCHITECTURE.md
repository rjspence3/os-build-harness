# Dynamic Workflow Engine — architecture + harness build plan

**The app class:** a decomposable workflow coupled to the UI — an intake questionnaire resolves to a
**scenario** from a library, and a generic orchestrator instantiates that scenario as a running workflow
that decomposes into **tasks / units of work** routed to users. This is the Pega / Appian / dynamic-case-
management pattern (and the generalized form of the Rivian onboarding, which replaced Appian).

## The load-bearing principle: N is invariant

You cannot author N static workflows (N ≈ hundreds–thousands). So the workflow **structure lives in data**
and you build **one generic engine that interprets it at runtime.** The consequence — and the whole point:

> **N never changes what gets built.** The engine loads ONE scenario per instance (it never touches the
> other N−1). Scenario resolution is an INDEXED lookup, not a scan over N. The library is pure storage
> (Postgres does not care: 8 rows or 80,000). The dynamic form renders ONE task. "How many scenarios" is
> a **row count**, never a design input.

So the harness work is finite and N-invariant: **one engine, one dynamic-form renderer, one bulk loader.**
Build once, serve any N. The only place N surfaces is **ops, not architecture** — 50 rows is a seed, 50k
is an ETL job; same schema, same engine, different loader throughput.

(Data *modeling* — factoring N scenarios into a smaller reusable TaskTemplate set — is a real recommendation
for CLIENT maintainability, but NOT a harness-buildability concern. The harness builds the same engine
either way. Keep it as a footnote for the client's authoring UX.)

## ODC reference architecture (one hard constraint)

**Do NOT use native ODC BPT (BusinessProcess) for the scenarios.** ODC BPT is for *statically authored*
processes — it cannot define a process graph at runtime. A dynamic engine reimplements process semantics
in **data + a state machine**:

- **State machine in data:** `WorkflowInstance.state` + an `AdvanceInstance` server action that reads the
  instance's scenario graph and computes the next unit(s) of work. No per-scenario BPT.
- **The queue IS the data:** `TaskInstance` rows are the work queue; a reactive "My Work" screen aggregates
  them by assignee/role/SLA. No BPT activity inbox.
- **Timers** only for cross-cutting sweeps (SLA breach, escalation) — not per-instance flow.

## Data model (factored)

```
TaskTemplate    — a reusable unit of work: Type (form|approval|review|integration|decision),
                  FieldDefinition (JSON — the dynamic form spec), DefaultRole, SlaHours
Scenario        — a named process (EntryCriteria, Status)
ScenarioStep    — composes TaskTemplates into a Scenario (→Scenario, →TaskTemplate; Sequence,
                  ParallelGroup, DependsOnStep)
TransitionRule  — →Scenario; FromStep → ToStep, Condition (expression over task outcome/data)
DecisionRow     — intake answers → resolved Scenario (the scenario-selection decision table)
WorkflowInstance— →Scenario; State, Context (JSON — accumulated answers/data), StartedBy, StartedAt
TaskInstance    — →WorkflowInstance, →TaskTemplate; Assignee, Status, InputData, OutputData, DueAt
AuditEvent      — →WorkflowInstance; immutable, one per state transition
```

## Modular decomposition (build_system handles the topo)

- **WorkflowEngineCore** (producer) — owns all entities + the FIXED engine service actions
  (`ResolveScenario`, `InstantiateWorkflow`, `AdvanceInstance`, `CompleteTask`, `ClaimTask`,
  `EscalateOverdue`). Public entities + SAs so the portals consume them.
- **IntakePortal** (consumer, actor=requester) — the questionnaire → kicks off an instance.
- **WorkspacePortal** (consumer, actor=worker) — "My Work" queue + the **dynamic task screen** + instance
  tracker.
- **AdminAuthoring** (consumer, actor=admin) — CRUD TaskTemplates / Scenarios / rules, so the client
  maintains the library without code.

## What the harness builds TODAY (~60–65%)

The entire data model; the work-queue list screens; the instance tracker; the intake form; the admin CRUD
(create-form / row-actions); roles + dashboards; the immutable audit trail; integration stubs; and the
modular topo build via `build_system`. All existing recipes. The boring, large majority.

## The three N-invariant gaps (the real work — all fixed code, data-driven)

| Gap | Why hard | Why bounded |
|---|---|---|
| **G1 — the engine** (`AdvanceInstance`: load scenario graph → eval TransitionRules → parallel gateways → spawn next TaskInstance(s); `ResolveScenario` decision-table match; `InstantiateWorkflow`) | Real algorithm code; recipes template CRUD, not algorithms | It is **ONE canonical engine**, parameterized only by entity names. Author **once** as a new `workflow-engine` recipe. Same code for any N/any scenario. |
| **G2 — dynamic task forms** (render inputs from `TaskTemplate.FieldDefinition` at runtime) | Metadata-driven UI ≠ static entity-bound screens | **ONE renderer** — a reactive web block that switches on a FIXED field-type set (~10: text, textarea, number, date, select, multiselect, checkbox, file, lookup, readonly). New `dynamic-form` recipe. |
| **G3 — library load at any N** (rows of templates/scenarios/rules) | Blows the ~10-row lean-seed choke rule | **Bulk import** — generalize the deterministic-SQL / REST loader (B2c). Source is the client's existing defs (ETL from Appian/Pega/sheets), not hand-authoring. N-invariant throughput concern only. |

So the harness roadmap to build **this entire app class** = exactly three write-once capabilities. Nothing
per-scenario.

## The UX risk (the one to spike first)

"Coupled to the UI with good UX" is where these die — metadata forms are notoriously Pega-ugly. The fix is
the trick proven on Rivian: `FieldDefinition` carries **layout + type hints**, and the dynamic renderer emits
the **design-system's STYLED components** (chips, date pickers, section groups, column spans) — not raw
inputs — plus **per-task-type chrome** (an approval task, a review task, a data-entry task get different
framed layouts, not one generic form). That is the difference between "Pega-ugly" and bespoke. Authorable,
but **spike it first** — it is the value-prop risk (and, like everything else, N-invariant).

## Build sequence

Once the 3 recipes exist, it's the standard flow — no hand execution:
```
domain_spec.json → decompose → system_gate (MODULAR) → expand → gen_portal_specs (design + dynamic screens)
  → build_system --prefix <X> --specs-dir …   (WorkflowEngineCore → IntakePortal → WorkspacePortal → Admin)
  → bulk-load the scenario library (deterministic SQL/REST)  → gate each (incl. role + pixel)
```

## De-risk order (recommended)

1. **Hand-author a vertical slice in ODC** — one `AdvanceInstance`, one dynamic form, ~3 scenarios, the
   queue — to prove the architecture AND the UX. (Same "mine what worked, then recipe-ify it" flow that got
   Rivian to green.)
2. **Recipe-ify** the proven pattern: `workflow-engine` (G1), `dynamic-form` (G2), bulk-load (G3).
3. Then `build_system` reproduces it for any client's library.

## Open questions for the client (sharpen before the spike)

- **Scenario composability** — are the N scenarios combinations of a smaller TaskTemplate set (near-certain),
  or genuinely N unique graphs? Changes maintainability + load volume, NOT the engine.
- **Where the definitions come from** — client migration (ETL), an admin authoring UI, or both.
- **Field-type set** — a fixed ~10 types (makes G2 tractable) or arbitrary? Fixed is strongly preferred.

## Agentic intake — compose the workflow, don't select it (the headline)

The coolest version replaces the static resolver (questionnaire → `ResolveScenario` decision-table match
over N pre-authored scenarios) with an **AI agent that COMPOSES the workflow from governed building blocks.**
The agent interviews the requester, reasons about their situation, and **assembles the task graph on the
fly** — selecting, ordering, and routing `TaskTemplate`s into a valid instance-specific plan, then
instantiating it. "The agent executes the build" = it *builds the workflow*, per instance.

**This takes N-invariance to its conclusion: N → emergent.** You no longer pre-author scenarios at all.
You author the reusable **TaskTemplate building blocks + the governance rules**; the agent composes
unbounded scenarios from them at runtime. `Scenario`/`ScenarioStep`/`DecisionRow` collapse from a hand-
maintained library to **governed primitives + runtime output**. Stronger than the static library, and it
is the same recursion the harness is built on: **a spec composes an app; an intake composes a workflow.**

### Buildable with today's recipes + a bit
Rivian's ScreeningAgent already proved the harness builds ODC **AIAgent apps** (the `agent` recipe:
systemPrompt / model / tools grounded on public entities). So the composer is just another AIAgent app —
**additive**, not a rebuild. The engine (`AdvanceInstance`), the dynamic forms, and the queue are unchanged.

- **IntakeAgent** (AIAgent app), tools bound to WorkflowCore's PUBLIC service actions:
  - `GetTaskTemplates` — read the governed building blocks (+ their routing/dependency metadata)
  - `ComposeInstance` — create a `WorkflowInstance` + its dynamic `ScenarioStep` graph from selected templates
  - `AdvanceInstance` — the fixed engine (unchanged)
- System prompt: *interview → select + sequence TaskTemplates into a valid graph honoring roles/dependencies
  → hand the candidate graph to the validator → instantiate on approval.*

### The compose → validate → gate → run pipeline (the part that makes it shippable)
Agentic composition of business-critical, regulated workflows (the Pega/Appian/P&G/Silvomo territory) has
three governance problems a naive "LLM builds workflows" version cannot survive. The real design:

1. **Compose from GOVERNED blocks only.** The agent may select/sequence/route existing `TaskTemplate`s — it
   may NOT invent a task, skip a mandatory control, or route to a non-existent role. Composition is a
   constrained assembly, not free generation.
2. **Hard VALIDATOR between propose and run.** A deterministic `ValidateComposition` action gates every
   agent-proposed graph: every step resolves to a real TaskTemplate; every routing role exists; required
   controls (approvals, screenings) are present; no orphan step, no cycle; SLAs sane. Invalid → reject +
   ask the agent to revise. Nothing runs unvalidated.
3. **Risk-tiered human-in-the-loop.** Low-risk intake → agent composes + auto-runs. High-risk (large $,
   regulated, novel shape) → agent composes a *candidate*, a human confirms. The agent ACCELERATES;
   governance GATES.
4. **Fully audited + reproducible.** The agent's selection + reasoning is written to `AuditEvent` so a
   composed instance is explainable and repeatable — the non-negotiable for compliance. (Pin the model +
   record inputs so a composition can be re-derived.)

Get this boundary wrong and it is a demo no compliance team approves. Get it right and it is both novel and
shippable: **agent composes from governed primitives → validator enforces invariants → risk-tiered approval
→ the fixed engine runs it, audited.**

### Harness gap delta (small)
On top of G1–G3, agentic intake adds: (G4) the `IntakeAgent` AIAgent app (existing `agent` recipe, tools =
the engine SAs), (G5) `ComposeInstance` + `ValidateComposition` service actions on WorkflowCore (part of the
canonical engine recipe — fixed code, N-invariant), and the risk-tier/approval policy as data. Still bounded.

## Honest assessment

More than Rivian, but **bounded, not open-ended** — precisely because it is an engine. ≈ 1 UX spike + 3
write-once recipes (+ the additive agent) away from harness-buildable. The engine, the UI machinery, the
loader, and the intake agent are all N-invariant. Scenarios are data — or, with agentic intake, *emergent*.
