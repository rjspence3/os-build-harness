# Harness Decisions

## ★ North Star (the mission) — 2026-06-18
**The harness exists to make OutSystems build a MODERN, PIXEL-PERFECT app that hits 100% against its spec —
proven repeatably across many well-known platforms (Linear first; then others) and use cases.** Success =
the built ODC app matches the spec **100%, INCLUDING real UI structure + design** (pixel parity to the spec's
design target), not merely data + generic functional screens. Consequences that override earlier doctrine:
1. **The spec is the COMPLETE contract** — data + *real* screen structure + design. Nothing about the target
   app is "advisory." The `/design-layer` mockup is the contract and must itself be faithful to the real product
   (so 100%-to-mockup = 100%-to-product).
2. **A pixel/structure plateau below 100% is a WALL / harness work-item** — a missing spec component type or a
   missing authoring recipe — NOT "done." (Supersedes the old "accept eyeball-faithful + plateaued" stance.)
3. **Everything must GENERALIZE** — patterns are cracked once on a benchmark and reused across platforms. The
   three pillars to reach 100%: (a) spec EXPRESSIVENESS (component model rich enough to specify the real UI —
   grouped lists, glyph cells, boards, shells); (b) BUILD capability (MCP/Mentor authors that structure +
   custom widgets/Forge — the custom-authoring frontier); (c) VERIFICATION (harness-verify gates structure +
   pixel to ~100%, not just entity/attribute presence — the screen-walk executor D12 + a real pixel gate).
Linear is benchmark #1; its structural-fidelity walls are the harness backlog.

## D1 — Build phase runs as a normal CC session (not `claude -p`) — 2026-06-16

**Decision.** The build phase launches Claude Code as a normal session in the build root —
the same operational pattern `banking_runner` ran under — with CC as the orchestrator. We are
**not** using `claude -p` (headless) yet.

**Why.** The supervision `-p` buys for unattended/CI use — turn budget, permission
pre-authorization, structured output capture — Kernel already provides (tiered autonomy, audit
logging) on top of the wall-cap hook. `-p` would be supervision layered on supervision.

**Future.** `claude -p` is the planned migration for fully unattended builds. It is a one-flag
switch, **not** a redesign:

```
RUN_MODE=headless harness/launch_build.sh <app>
```

The scaffolding, the spec seam, CLAUDE.md / `.mcp.json` inheritance, and the wall-cap PreToolUse
hook are all mode-independent — they fire identically whether CC is launched normally or via `-p`.
So moving to headless changes one variable and nothing else.

**Seam.** Spec phase (interactive interview + Figma, human-approved) → approved `app_spec` in the
build root → build phase (this session). The approved spec is the handoff; nothing autonomous runs
before sign-off. This is unaffected by run mode.

**Orchestrator.** CC is the orchestrator brain in both modes. We did **not** revert to a
deterministic `banking_runner`-style script — the runner survives only as the tool belt
(`harness-verify` / `harness-capture` / `harness-prompt-step`) that CC calls.

## D2 — ODC MCP server = the connected `your-tenant` tenant — 2026-06-16 (revised)

**Decision.** The harness uses the ODC MCP server already connected in Claude Code —
`https://your-tenant.outsystems.dev/mcp` (the `your-tenant` tenant) — for **both reads
and the build churn** (create / publish / delete).

**Revision note.** This **supersedes the original D2 stance** ("sandbox / throwaway tenant — never
`your-tenant`"). On review the user chose to use the already-connected tenant for builds too.
The original concern stands as an **accepted risk**: P1.5/P9 run repeated create/publish/delete cycles
against the live demo tenant.

**Mitigation (required because of the accepted risk).** Namespace every harness-created app with a clear
prefix (e.g. `harnessbuild_<app>`) and delete build apps after each run, so the churn never collides with
or pollutes real demo apps. P9's fresh builds in particular must be cleaned up.

**Why (revised).** The tenant is already authenticated/reachable in-session; standing up a separate
sandbox added friction the user judged unnecessary for now.

**Implication.** No separate sandbox needed. The harness uses the connected server; tenant
`OUTSYSTEMS_MCP_TENANT=your-tenant.outsystems.dev`. (The original sandbox `.mcp.json` framing in
P1 is relaxed accordingly.)

## D3 — `integrations` taxonomy is minimal v1, grounded in home_banking — 2026-06-16

**Decision.** The `app_spec` v1 `integrations` block models **only the connector kinds
home_banking actually uses** (likely REST), derived from the MCP doctrine notes' `context_connections` findings.
Widen in later schema versions.

**Why.** Avoid speculative schema surface. Ground the first cut in the one real reference app rather
than guessing a connector catalog.

**Correction (2026-06-17, from P2 grounding).** The original premise — "derived from `context_connections`"
— was based on a misread: `context_connections` lists **AI-model connections only**, and it returns
**empty** for home_banking. There is **no `context_*` surface that lists consumed-REST integrations**
(they surface as Actions/Structures). So: home_banking uses **zero** external integrations. v0.2 ships an
**optional, minimal `integration` block (kind enum: `RestApi` only)** so the contract is forward-capable,
but home_banking's reversed spec carries none. Consequently the `integrationExists` assertion routes to
**`unverifiable`** (no established read path), not `mcp`.

**Implication.** P2 added the minimal block + `integrationExists` (unverifiable). Widen the `kind` enum +
revisit the channel if/when a consumed-REST read path is found.

## D4 — Spec approval is a marker file the launcher enforces — 2026-06-16

**Decision.** Spec approval is a marker file `builds/<app>/spec/APPROVED`. `launch_build.sh` **refuses
the build phase** if it is absent.

**Why.** The seam (D1) requires explicit human sign-off before any build runs. A marker file is the
simplest gate the launcher can enforce mode-independently.

**Implication.** Implementation (write-on-approval + launcher refusal check) lands in **P4**, not in
this docs pass.

## D5 — Figma layer uses `mattholihan/outsystems-figma-cli` — 2026-06-16

**Decision.** The Figma UI layer uses **`mattholihan/outsystems-figma-cli`** (OutSystems-UI-aware,
design-token export, CDP-to-Figma-Desktop driving).

**Why.** It is OS UI Kit aware and exports tokens, which is exactly the spec phase's need.

**Caveat (accepted).** It requires Figma Desktop to be open. Fine — the spec phase is **interactive**,
so a human-attended Desktop session is the normal case.

**Implication.** P5 builds on this CLI; tokens → ODC theme/`portal.css`.

## D6 — `componentId → DOM` mapping is contingent on P1.5 — 2026-06-16

**Decision.** Whether a `componentId → rendered-DOM selector` mapping is needed is **contingent on
P1.5's channel map**. If `componentPresent` is OML-readable, no mapping is needed for *presence*
verification (the mcp executor handles it); the mapping is then only needed for the advisory visual diff.

**Why.** Don't build a mapping mechanism until P1.5 empirically shows it is required for gating.

**Implication.** D6 is provisional. P1.5's result finalizes whether P7 needs the mapping at all, or
only the visual-diff path (P6) does.

## D7 — harness-verify consumes an orchestrator-supplied live snapshot (not its own MCP client) — 2026-06-17

**Decision.** In session mode (D1), `harness-verify`'s mcp-channel executor evaluates assertions against a
`context_entities` snapshot that the **orchestrator (CC, which holds the authenticated MCP)** fetches and
passes via `--entities`. `harness-verify` does **not** open its own MCP client.

**Why.** CC already has the live MCP; `harness-verify` is a CLI subprocess without those tools. Injecting
the snapshot keeps the judge **pure, deterministic, and unit-testable** (against a saved snapshot) and
matches D1's "CC orchestrates → calls MCP → feeds the judge." A self-contained MCP client in verify would
duplicate auth + the client lib for no benefit in session mode.

**Implication.** The orchestrator loop is: fetch `context_entities` → save snapshot → `harness-verify
--phase live --entities <snapshot>`. The capture-channel kinds (P6/P7) follow the same injection pattern
(CDP-captured artifacts passed in). Headless mode (future) may add a standalone MCP client so verify can
self-fetch; the snapshot path stays the tested core. Proven 2026-06-17 against live home_banking
(HBCustomer/Email pass; mistyped Email fail).

## D8 — The build orchestrator is ALWAYS a Claude Code session in the build root — 2026-06-17

**Decision.** Every app build is driven by a **Claude Code session launched in the build root** (via
`launch_build.sh`, RUN_MODE=session). There is **no non-CC autonomous orchestrator** — CC is the executor.
"You, or a version of you, running in a different root, will always drive this process" (Rob). The
`banking_runner` Python `orchestrator.py`/`mcp_client.py` are **not** the driver and are dead weight for
this model; `build_banking` only *renders* the ordered prompts — **CC drives** them through the MCP.

**Why.** Driving requires judgment the playbooks assume of a thinking driver — diagnose-before-fix,
read-events-not-summary, phantom-authoring detection, wall handling, validate-before-advance. The clone
was *proven* exactly this way (the CC + Mentor + recipe + pixel-diff loop). Deterministic engines kept
hitting the very walls those playbooks encode.

**Implication (the load-bearing one).** The build root must be a **self-sufficient program** for a fresh
CC: the doctrine (@imported `harness/CLAUDE.md` + the build's `MCP_RECIPES` playbooks), the recipe library,
the tool belt on PATH, and the fidelity gate — all present so the driver does **not re-derive the process**
(which a driver had to on 2026-06-17 before this was wired into `harness/CLAUDE.md`).
`harness-verify`/`pixel_diff` are tools the driver calls, not the driver.

**Concurrency (clarified 2026-06-17, Rob).** Multiple builds = **multiple CC sessions a human opens in
different roots**, one per build. There is no meta-orchestrator, no fanning-out, no fleet — the human
manages parallelism by opening sessions. Each session **authenticates its own MCP interactively (`/mcp`)**;
that per-session auth is the expected default, NOT a gap. An automated token / `.mcp.json` (P1) is only for
the future *unattended/headless* RUN_MODE — it is NOT a prerequisite for the normal human-driven model, and
`launch_build.sh` scaffolds + opens a single build root, it does not spawn or coordinate sessions.

## D9 — Missing external dependency → human imports, harness generates explicit OutSystems steps — 2026-06-17

**Decision (Rob).** When a build needs an element (FK target entity, block, action) owned by a **producer
app this build doesn't reference**, the driver does NOT silently drop it or auto-guess a producer. The
resolution is a fixed protocol: **(1)** log a `needs-human` wall; **(2)** identify the exact element(s) +
the *specific* producer (decode the source FK's `globalKey`/`entityKey`, or `context_search` + disambiguate
the owner); **(3)** **generate explicit OutSystems import instructions** (`./IMPORT_INSTRUCTIONS.md`:
consumer + producer app names/keys, exact elements, step-by-step Manage-Dependencies actions); **(4)** ask
the user to perform the import, then resume and re-author the dropped element.

**Why.** The MCP *can* import refs (`addReferenceToElements` + `AddDependency`), but the same entity name is
public across many tenant apps — picking the RIGHT producer is a human/design call, and a wrong auto-import
is silent fidelity corruption. Human-in-the-loop with harness-generated, zero-guesswork steps is the safe
form. (This corrects WALL-001's first ruling, which wrongly called cross-app refs Studio-only via the
superseded `odc_mcp_reference_add_studio_only`.)

**Implication.** Encoded in `harness/CLAUDE.md` ("Fall-out pattern: missing external dependency"). It's a
distinct, named pattern under the `needs-human` wall category with a mandatory generate-instructions step.

## D10 — Spec creation produces the DESIGN layer up front, not just structure — 2026-06-17

**Decision (Rob).** A complete `app_spec` = **structure** (data model + screen components/bindings/nav/
acceptance) **AND design** (layout / theme / look). The spec-creation phase must produce BOTH at the start.
A structure-only spec is **incomplete** — a "design-spec hole." Surfaced by the Linear build: the data
model verified 11/11, but the screen phase had nothing to build toward or diff against because the spec
carried no design. Design is **front-loaded** because the build phase otherwise designs blind, and
retrofitting design mid-build is the churn the clone work already learned to avoid (DISPATCH_PLAYBOOK Phase 0).

**Design source by app type** (already the rule for the visual reference — now made a spec-creation duty):
- **Known app** → capture the real product's reference (screenshots) as the de-facto design spec; populate
  each `screen.mockupRef` + a theme/design reference.
- **Novel app (cohort, no public reference)** → generate the design (Figma → tokens → theme).

**Implication.** This **merges ROADMAP P5 (Figma UI layer) into the spec-creation phase** — design is a
spec OUTPUT, not a later build phase. `screen.mockupRef` is elevated from optional hook to a spec-creation
deliverable for screens; `harness-verify --phase spec` may later flag screens with no design reference.
The **current Linear spec is structure-complete but design-incomplete** (mockupRef empty, no theme ref) →
complete it by adding the design layer (Linear screenshots → mockupRef + theme) before the screen build.
Structural verify (`context_graph`) is orthogonal to this — two separate halves of the screen phase.

## D11 — Spec-creation methodology: research-first → interview; rubric = NO HOLES — 2026-06-17

**Decision (Rob).** The spec-creation phase (P4) produces a COMPLETE, fully-connected spec. Process order:
1. **Web research run FIRST.** Research the app comprehensively up front — for a *known* app: its
   objects/data model, screens/views, user capabilities/workflows, and design/UX (docs + screenshots);
   for a *novel* app: the domain. Research front-loads knowledge so the interview is targeted.
2. **Then interview the user.** Fill what research can't determine; get scope cuts, preferences, decisions.
3. **Validate against the NO-HOLES rubric** before writing `APPROVED`.

**The NO-HOLES rubric** (the spec's acceptance standard):
- **Connected — every piece references every other; no orphans, no dangling refs.** Every entity is
  surfaced by ≥1 screen AND mutated by ≥1 action; every screen is reachable via navigation AND used by
  ≥1 capability; every action is triggered by something; every role is exercised; every component is
  bound; every screen carries a design reference (D10).
- **Capabilities — the spec explicitly defines "the various ways and things a user can do."** A
  user-capability / flow layer: each capability → its role(s), the screens it uses, the actions it
  triggers, the entities it touches, the steps. Structure exists to SERVE capabilities; every capability
  has a complete data→screen→action→nav path.
- **Complete — no TODOs, no unspecified screens/actions; design layer present.**

**Implication (schema + verifier work).** `app_spec` must add a `capabilities`/`userFlows` section (+ the
design refs from D10); `harness-verify --phase spec` must add CONNECTIVITY / COVERAGE / REACHABILITY checks
(orphan + unreachable detection), not just cross-ref resolution. The current Linear spec was authored from
memory — no research run, no interview, no capability layer, design holes — so it is a **structure-only
DRAFT** and must be REDONE through this process (research → interview → no-holes spec → validate).

## D12 — Screen structure is mcp-verifiable via the applyModelApiCode walk (PROVEN) — 2026-06-18

**Decision / finding.** `componentPresent`, `navigates`, and `binding` are **mcp-verifiable** by a read-only
`applyModelApiCode` model-walk (the CAPTURE_PLAYBOOK / DISPATCH_PLAYBOOK Phase-6 pattern) — NOT via
`context_screens` (metadata-only) or `context_graph` (flaky on large apps). **Proven live** on
harnessbuild_linear rev 5: the walk read 17/17 screens, navigation resolved, and the **binding channel is
readable** (`IssuesTable.SourceRecordList = GetIssues.List over entity Issue`; filter dropdowns → WorkflowState
+ Label). This settles the P6/P7 "screens unverifiable" question and supersedes the disproven
`verify.py LIVE_CHANNELS` rationale ("binding → no read path → unverifiable").

**Next build (required to gate it).** The rev5 walk was **narrative** (`{screen_count, screens:[{name,inputs}]}`),
not machine-checkable. To promote the three kinds from capture/unverifiable → gated `mcp`, the harness needs:
(a) a **structured screen-walk snapshot contract** — per screen `{components:[{id,boundTo}], navigation:[{from,event,to}]}`;
(b) the walker (CAPTURE_PLAYBOOK) updated to emit it; (c) `verify.py` `load_screens_snapshot` +
`_eval_component_present/_eval_binding/_eval_navigates` (mirrors the entities-snapshot executor, D7). Until then
the read path is proven but the executor is unbuilt — channels stay routed as-is.

**Also confirmed:** `context_entities` can be index-down tenant-wide; `context_search` is the proven fallback
(same shape the verifier's snapshot loader accepts). Reserved ODC names (e.g. `Attachment` = built-in
SystemStructure) are silently refused → candidate for a `--phase spec` reserved-name preflight (WALL-001 class).

## D13 — Real end-user auth is an OPEN harness gap; MCP-built apps are anonymous-demo by default — 2026-06-18

**Gap (WALL-003, needs-human).** The build loop has **no story** for (a) provisioning end-user auth on a
fresh MCP-created app (a Portal step), nor (b) an **authenticated** runtime-verify channel. Consequence:
role-gated screens are **runtime-unreachable** until made anonymous, so MCP-built apps are currently
**anonymous-demo-only** and role-gated builds are **runtime-unverifiable under real auth**. Linear shipped by
clearing roles + `AnonymousAccess=true` on all 17 screens (rev 8) purely to enable the runtime/theme check.

**Resolution pattern (future work).** Mirrors D9 (missing-external-dependency): the harness should detect a
role-gated spec, **generate explicit OutSystems Portal steps** to provision a test end-user + role assignment,
ask the human to run them, then verify the authenticated runtime via the `chrome-cdp` session (login → screenshot),
not anonymous. Until built: spec-driven demos run anonymous; real-auth verification is deferred.
