# Decomposing a spec into a modular ODC architecture (no monoliths)

A stranger's spec describes *what the system does*. This doctrine governs *how it is carved into apps*
so the harness never builds a monolith. It is the design counterpart to `BUILD_LOOP.md`: BUILD_LOOP
builds one app well; this decides **how many apps there are and what each owns**.

The intelligence lives in the harness as two durable pieces — a **rubric** (the rules below) and a
**gate** (`architecture.py`, machine-checkable). An LLM "architect pass" only *proposes*; the gate
*disposes*. LLM proposes, gate verifies — the same shape as the rest of the harness (recipes + verify).

---

## The hybrid loop: propose → dispose

```
flat domain spec ──▶ architect pass ──▶ system.apps topology ──▶ harness-arch-gate ──▶ per-app app_specs ──▶ build
   (entities,          (applies the       (system_spec.v0.json,      (6 no-monolith         (one app_spec        (BUILD_LOOP
    actors,             rubric; may be      human-editable)            invariants;            per app, in         per app, in
    capabilities)       an LLM step)                                   FAIL = monolith)       dep order)          topo order)
```

1. **Architect pass** reads the flat domain spec and proposes a `system.apps` decomposition
   (which apps exist, what each `owns` / `exposes` / `consumes`, which layer). Deterministic where
   the rubric is mechanical; an LLM step for the fuzzy clustering — but always constrained by the rubric.
2. The proposal is written as an editable `system_spec.v0.json`. A human can hand-tune it.
3. **`harness-arch-gate`** runs the six invariants. A monolith **fails the build** here — it is not
   merely advised against. This is the enforcement point.
4. Each app node expands into its own `app_spec.v0` document; a multi-app runner builds them in
   dependency order (producer before consumer). *(runner = next pass; this pass ships the rubric + gate.)*

---

## Target shape: the ODC 3-Layer Architecture Canvas

| Layer | rank | ODC construct | Owns | Rule |
|---|---|---|---|---|
| **foundation** | 0 | Libraries / stateless services | reusable code, themes, integration wrappers | **no entities, no state, no events** |
| **core** | 1 | Service apps — **one per bounded context** | the domain entities + business logic for **one** concept | exposes Service Actions + Events; owns its data |
| **orchestration** | 2 | Workflow (BPT) + AI Agent apps | nothing persistent | coordinate Core via **events + public Service Actions** |
| **enduser** | 3 | Web / Mobile apps — **one per actor** | UI/UX state only | **zero persistent domain entities**; consumes Core |

Dependencies flow **downward only**: a consumer's layer rank is `>=` its producer's, and the graph is
a DAG. Foundation is the floor everything may depend on; nothing may depend on an end-user app.

---

## The split rubric — when to make a separate app

1. **Distinct bounded context (DDD) → its own Core service app.** Cluster entities by cohesion:
   entities that change together and are referenced together belong to one Core. A seam (few
   references crossing a group boundary) marks a context boundary — split there. One context = one Core.
2. **Distinct actor / persona / lifecycle → its own End-User app.** Customer vs. back-office vs. admin
   are different apps even over the same data. Different release cadence or sponsor ⇒ different app.
3. **Multi-step coordination across services → a Workflow (BPT) app.** Never bury orchestration in a
   UI event handler. (Proven: `[[odc_mcp_human_activity_node_authoring]]`, `[[odc_mcp_business_process_authoring_works]]`.)
4. **An AI reasoning step → its own AIAgent app.** (Proven end-to-end: agent authored + deployed +
   invoked from a BPT automatic activity.)
5. **Stateless reusable code (theme, utils, integration wrapper) → a Library (Foundation).** Libraries
   have their own release/version lifecycle in ODC.

---

## The data-ownership law (the anti-monolith teeth — and it's *grounded*)

The platform itself forbids the monolith shortcut. **A local entity cannot FK a cross-app referenced
entity** — ODC rejects it at build with `OS-DPL-50205` (live-proven; see the recipe rule + memory).
Therefore:

- **Every entity has exactly one owner app.** Consumers reference it **read-only** and **write only
  through the owner's public Service Actions**. You physically cannot make one giant app "own
  everything and let others FK in" — the build engine rejects the cross-app FK.
- **Cross-app coupling is events (decoupled) or public Service Actions (a contract)** — never a shared
  table. Events are Core-produces / orchestration-consumes; an event-raising Service Action must be
  **non-public** (`OS-DPL-50205`'s sibling rule, `[[odc_mcp_raise_event_action_cannot_be_public]]`).
- **Cross-app screens** aren't referenceable in a plain session — a human-task UI lives in an end-user
  app, and the Workflow gates on the completion **event**, not a shared screen.

---

## The six no-monolith invariants (enforced by `architecture.py`)

Each returns `PASS` / `FAIL` / `OMIT` (same shape as `gate.py`). A single `FAIL` ⇒ `MONOLITH`, exit 1.

| # | Invariant | What it forbids |
|---|---|---|
| **INV1** | **layer purity** | an end-user/orchestration app owning entities; a Library holding state/events (the UI/data monolith) |
| **INV2** | **single owner** | an entity owned by two apps (shared-table coupling); a consumed entity no app owns (dangling contract) |
| **INV3** | **no cross-app FK** | a local FK whose target isn't owned by the same app (`OS-DPL-50205`). `OMIT` if no FKs are declared in the topology |
| **INV4** | **acyclic + downward** | a dependency pointing *up* a layer (Core→EndUser); a cycle (coupling knot) |
| **INV5** | **context cohesion** | a data-owning app with no bounded context or spanning several; a context split across two Core apps |
| **INV6** | **orchestration externalized** | an end-user app owning/raising events; a BPT `process` living outside an orchestration app |

`OMIT` never vacuously passes: it means "nothing of this kind was declared to check" (e.g. INV3 when
the topology carries no FK edges — still enforced downstream at the app_spec/recipe layer).

Run it:

```bash
harness-arch-gate <system_spec.json> [--json]
# exit 0 = MODULAR, 1 = MONOLITH, 2 = bad input
```

---

## Golden case: the banking system

`tests/fixtures/system_banking.json` is the live 8-app banking system as a topology, and it passes all
six invariants. It is the reference every proposed decomposition is measured against.

| App | layer | owns / role |
|---|---|---|
| `HomeBankingCore6` | core (ctx `banking`) | owns Customer/Account/LoanRequest/Document/Decision/DecisionLog/EmailLog; exposes Validate/Enrich/Underwrite/Communicate/LogDecision + LoanRequested/LoanApproved/LoanDenied |
| `HomeBankingTheme` | foundation | shared theme/UI library (no state) |
| `HomeBankingPortal6` | enduser (customer) | UI; consumes Core6 read-only + LogDecision |
| `Backoffice6` | enduser (loan-officer) | UI; consumes Core6 |
| `HomeBankingMobile` | enduser (customer-mobile) | UI; consumes Core6 |
| `IntakeAgent6` … `CommunicationAgent6` | orchestration (AIAgent) | reasoning; expose one Service Action each; consume Core6 |
| `LoanRequestWorkflow6` | orchestration (BusinessProcess) | BPT triggered by Core6.LoanRequested; calls the agents' public SAs |

`tests/fixtures/system_monolith.json` is the counter-example (a UI/data app plus an upward coupling
knot) and correctly fails INV1/INV2/INV3/INV4/INV6.

---

## Mechanism status + remaining seams

- **`harness/decompose.py` → `decompose(flat_spec) -> {system, invariants, modular}`** — DONE. The
  architect pass: a flat domain spec (entities+contexts+references, actors, capabilities, libraries)
  becomes a `system.apps` topology and self-checks against `architecture.check_system`. Deterministic
  v1 (explicit `context` tags, else connected-components over the reference graph). The FK-vs-consume
  split is automatic: intra-context references become FKs, cross-context references become read-only
  consumes (never a cross-app FK). `harness-decompose <domain.json> [--emit-system out.json]`. An LLM
  clusterer can replace the deterministic step later — its output still passes the same six invariants.
- **`harness/expand.py` → `expand_system(system, domain) -> {specs, libraries}`** — DONE. Each app node
  becomes an `app_spec.v0.2` document, wiring the topology onto the fields built for it: a Core gets its
  owned entities (intra-context FKs only) + `logic` (a serviceAction per exposed SA, a globalEvent per
  event); a consumer gets `appReferences` (never a cross-app FK); a Workflow gets a `processes` block; an
  Agent gets an `agents` block. Every emitted spec passes `verify.validate_spec` and `plan_from_spec`
  as-is. This forced app_spec.v0.2 to relax `dataModel.entities`/`screens` to `minItems 0` — the two
  non-monolith shapes (service app: entities, no screens; consumer app: references + screens, no owned
  entities) a self-contained spec never needed. `harness-expand <system.json> --domain <domain.json>
  --out-dir <dir>`. **Open seam:** data-BOUND consumer screens need `verify` to accept `appReference`
  entities as binding targets; v1 emits non-binding placeholder screens.
- **`harness/run_system.py` → `plan_system(system, domain)` / `plan_from_domain(domain)`** — DONE. The
  multi-app orchestration PLANNER at the top of the pipeline: composes decompose → arch-gate → expand →
  `plan_from_spec` into one master plan of topo-ordered per-app phases (a real topological sort over the
  consume DAG, so a Core that consumes another Core still builds after it — not just layer rank). Each
  phase carries the `app_create` kind, the per-app authoring steps, the create→author→publish lifecycle
  (including the BPT special case: `app_create` does NOT auto-publish, publish ONCE with the process
  present), and cross-app gates (`dependsOn` = producers, published first). It REFUSES to plan a monolith
  — the six invariants run first as a precondition. It is a planner; the session executes (Mentor OAuth
  is interactive). `harness-run-system <domain.json> --domain [--emit-plan plan.json]`.
- **`harness/system_gate.py` → `run_system_gate(system)` / `derive_system_flows(system)`** — DONE. The
  system-level DEFINITION OF DONE: the six static invariants PLUS the cross-app runtime flow contracts
  derived from the topology — one `read` per consumed entity, one `call` per consumed Service Action, one
  `orchestrate` per BPT process (trigger event → activities), one `agent` per AI Agent. It follows
  verify.py's honest-channel discipline: a flow with no wired live executor is `unconfigured` /
  `not-implemented`, NEVER a fake pass — so a system is DONE only when MODULAR *and* every flow is
  runtime-green, and can never be called done from static analysis alone. `harness-system-gate
  <system.json> [--live]`.
- **`verify` appReference binding** — DONE. `_check_binding` now accepts `appReference` (cross-app)
  entities as valid screen binding targets (attribute-level binding to one is advisory, not a gap), so
  `expand.py` emits data-BOUND consumer screens (a Table per consumed entity) instead of placeholders.

**Remaining (execution, not planning):** the live flow EXECUTORS behind `system_gate`'s channels
(`capture` / `behavioral` / `drive` / `agent-invoke`) — the session-driven runtime proof. Every planning
and gating layer is now complete and tested; what's left is wiring the deployed-system drivers, which is
the interactive session's job (Mentor/CDP), exactly as with `gate.py`.

Cross-refs: `BUILD_LOOP.md` (§Workflow), `CAPABILITY_MATRIX.md` (Batch C), `reference/BANKING_MINED.md`,
`SEAMS.md`.
