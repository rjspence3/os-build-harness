# Rivian Supplier & Parts Onboarding — harness build plan (for tomorrow)

**Goal:** the HARNESS builds this app from scratch to **production-ready**, via **real recipes** and
**iteration to 100% completeness** (harness-gate green on every declared dimension). **The full UI/UX
must be genuinely USABLE** — navigable portals, styled case queues, forms, dashboards — like the clones,
NOT the bare table a skeleton spec produced for SLAOpsTracker. Source spec: `spec.txt` (`Rivian_Supplier_Onboarding_Spec.docx`).

## Non-negotiables (carried from today's SLAOpsTracker build)
1. **Harness executes, I oversee.** Drive every step from `plan_from_spec`-rendered recipe prompts —
   NEVER hand-improvise authoring. The intelligence is the recipes + gate, not me.
2. **RICH spec, not skeleton.** Today's "trash UI" was a thin hand-written spec (one bare `Table`, no
   `design`, no columns/layout). The clones looked rich because their specs carried `design.theme` +
   real product-UI components. Rivian's spec MUST carry the design layer + rich screens from the start.
3. **Walls are baked in** (R11 OS-DPL-50205: public actions can't write entities or carry entity-typed
   signatures; R12 cancel rolls back same-session edits; lean seeds). Trust independent reads over
   `change_applied`. Publish per unit.

## The app (from the spec)
- **8 entities** (FK-heavy): Supplier, Contact(→Supplier), Part(→Supplier), QualificationCase(→Supplier,→Part),
  ReviewTask(→Case), Document(→Supplier/Case), ScreeningResult(→Supplier), AuditEvent (immutable).
- **BPT workflow** (the core): intake → denied-party screening → tiered qualification (Tier 1 critical:
  facility audit + financial review; Tier 2 standard: cert/doc verification) → **parallel functional
  reviews** (procurement, quality, engineering, compliance) with SLAs + escalation → approval →
  activation (ERP vendor-master write) → requalification. Parallel + conditional paths.
- **Two end-user portals** (two actors): supplier self-service (intake, doc upload, status) + internal
  reviewer workspace (case queues, evaluations, approvals, dashboards).
- **Compliance screening** = an automated/AI step on submission (agent or rules) with review-on-match.
- **Integrations** PLM/ERP/SSO/screening/storage/notify — STUB for the demo (out of real-endpoint scope).
- **Audit trail** immutable AuditEvent on every state change; dashboards; role-based access.

## Harness pipeline for it
1. `decompose` a flat domain (entities+contexts+refs, actors, capabilities incl. the workflow + screening
   AI step, a generated design) → modular topology. Likely shape: **OnboardingCore** (data + logic) +
   **QualificationWorkflow** (BPT) + **ScreeningAgent** (AIAgent) + **SupplierPortal** (enduser) +
   **ReviewerWorkspace** (enduser). Run `harness-arch-gate` — must be MODULAR.
2. `expand` → per-app `app_spec.v0` ; `run_system` → topo-ordered master plan (producer-before-consumer;
   Core → Agent → Workflow → portals). `harness-system-gate` lists the cross-app runtime flows.
3. Execute the plan via rendered recipes, publishing per unit; iterate with `harness-gate` per app until
   every declared dimension (spec/structural/behavioral/role/render/pixel) is green.

## UI/UX is a GATE, not a nicety — AND WE HAVE THE DESIGN (the day-1 focus)
**A finished design reference is staged at `examples/rivian/design/`** (from "UIUX app design.zip"):
`Supplier Onboarding.dc.html` (full design markup — the CAPTURE source for tokens + per-screen layout),
`screenshots/` (case.png, queue.png, q3–q5.png), and `support.js`. This is a concrete target to MATCH —
exactly how the clones got rich UI. `design.source = "screenshots"`/reference; do NOT generate from
scratch — capture from the `.dc.html` (mine its CSS for the theme tokens, like the banking theme capture).

**Design language (from the reference):**
- **Dark enterprise theme**, near-black canvas; **Rivian yellow** accent (~#EDE000) for active nav, tier
  tags, primary CTA; green/blue/red status colors.
- **App-shell Sidebar**: brand ("RIVIAN" + "Supplier & Parts Onboarding / OUTSYSTEMS DEVELOPER CLOUD"),
  sections (OPERATIONS, SUPPLIER), nav items each with a **mono 3-letter tag chip** (DSH/QUE/CSE/SCR/PRT/INT)
  + **count badge** (Case Queue 47, Compliance 3, Part Release 4); active item = yellow left-border highlight.
  Footer = user avatar + name + role + online dot.
- **Top bar**: breadcrumb (Rivian Onboarding / <screen>), global search, "ODC · PROD" env chip, yellow
  "+ New request" CTA.
- **Status system**: tier tag `T1 · CRITICAL`, state badges `OVERDUE`/`APPROVED`/`IN REVIEW`/`CLEAR`,
  "SLA breached · +N day".
- **Case Detail** = the workflow made visual: a **horizontal stage stepper** (Intake✓ → Screening✓ Clear →
  Qualification✓ Score 92 → Functional Review → Approval → Activation), a **Parallel functional reviews**
  panel (Procurement/Quality/Engineering/Compliance with per-team state), and an **Activity & audit trail**
  timeline.

**Screens to build (from the nav):** Dashboard, Case Queue (styled table), Case Detail (stepper + parallel
reviews + audit), Compliance Screening, Part Release, Supplier Intake (form), Status Tracker.

- **Approach:** capture `.dc.html` → `design.theme` tokens + per-screen component structure; author rich
  screen specs (Sidebar shell, KPI dashboard, styled case-queue Table with chip/badge/avatar columns,
  the stage-stepper + parallel-review + audit-timeline blocks, intake Form with validation); render via
  the `theme` + product-UI recipes (`banking_runner/` `screen_renderer`/`block_renderer` path).
- **Acceptance:** browser-verify each screen matches the reference (navigable, dark theme, sidebar,
  status chips/badges, stepper) BEFORE it's "done"; add render/pixel gate dims against the screenshots.

## Prep gaps to close FIRST (before/early tomorrow — these blocked or would block quality)
- **[UI-A] Rich-UI recipes — ✅ CLOSED (2026-07-08).** The recipe layer now honors the rich shape the
  app_spec schema already defined (columnSpec.kind, Sidebar/Card, themeTokens.css). Changes in
  `harness/prompt_recipes.py` (+ schema + tests, full suite 392 green):
  - `list_screen` authors **styled cells** per `columns[].kind`: `chip`/`tag`/`badge` (value-tinted via
    `"chip chip-" + ToLower(Entity.Attr)`), `avatar` (initials), `glyph` (CSS-icon via data-value),
    `identifier` (mono). String columns still render as plain text (back-compat).
  - `nav_block` authors the **app-shell sidebar**: brand+subtitle, section groups, per-item mono **tag
    chip** + **count badge**, `is-active` highlight, user footer. Driven by `navigation.brand/subtitle/
    userLabel/userRole` + `navItem.tag/badge/section` (new schema fields).
  - **new `dashboard` recipe** — KPI cards (icon + live COUNT + label + trend), from `screen.dashboard`.
  - **new `detail` recipe** — the workflow made visual: **stage stepper** (done/active/pending) +
    **parallel-review grid** (per-team status chips) + **audit timeline**, from `screen.detail`.
  - **CSS class contract** documented as `UI_CLASS_CONTRACT` in `prompt_recipes.py` — the STABLE hook set
    the theme paints. Recipes emit STRUCTURE + hook; the theme paints. **Build-day action:** the Rivian
    `design.theme.css` (mined from `design/Supplier Onboarding.dc.html`) MUST define these classes
    (`.app-sidebar .nav-item .nav-tag .nav-badge .chip .chip-<v> .tag .badge .avatar .glyph .kpi-card
    .stepper .step.is-* .review-grid .timeline …`) so the hooks render as the dark Rivian look.
  - So the Rivian enduser app_specs must carry rich screens (nav tags/badges, styled `columns[].kind`,
    `screen.dashboard`, `screen.detail`) — NOT bare Tables. That is spec authoring, and the recipes are
    now ready to render it richly.
- **[SEED-A] `seed_entity` FK coordination — ✅ CLOSED (2026-07-08).** `plan_from_spec` now emits seed
  steps **parents-before-children** (topological sort over `references`, `_seed_topo_order`), and each
  child seed carries `fk_refs` so the recipe authors the FK wiring: a child `sampleData` row references
  its parent by a **natural key** (an attribute flagged `naturalKey:true`, else the first Text non-id/
  non-FK attr), and the seed **resolves that natural-key value to the parent's real Id at seed time**
  (aggregate lookup → `.Id` → Assign), skipping any row whose parent lookup is empty (never a dangling
  FK). Proven end-to-end on the Supplier→Part→QualificationCase chain: order is Supplier, Part,
  QualificationCase; the QualificationCase seed resolves BOTH `SupplierId→Supplier.Code` and
  `PartId→Part.Sku`. **Build-day action:** author each entity's `sampleData` with FK fields holding the
  parent's natural-key VALUE (not a fake Id), and flag each parent's `naturalKey` attribute. Keep row
  counts lean (~10-12/entity; the ≈200-node mega-seed choke rule still holds).
- **Confirm** the `workflow` (BPT) + `agent` recipes handle this scale (parallel reviews = multiple
  human-activity nodes; screening agent tools grounded on public entities — today's grounding pattern:
  producer entities Public + agent-app tool Server Actions querying referenced entities).

## Definition of done — PRODUCTION-READY ("hand it to Rivian and it works")
Not a demo. The bar:
- **Every in-scope functional requirement works end-to-end** (FR-01..FR-21): supplier intake w/ validation
  + doc upload; denied-party screening w/ review-on-match hold; tiered qualification (T1 audit+financial /
  T2 cert-verify); parallel functional reviews w/ SLA + escalation; multi-step approval w/ delegation +
  immutable history; part release gated on qualified supplier; ERP vendor-master write; requalification
  triggers; in-app feedback routed into the workflow; role-based dashboards + exportable audit.
- **Usable UI/UX matching the staged design** (dark Rivian theme, sidebar shell, styled queues, case
  stepper, parallel-review + audit panels) — verified in a browser, both portals.
- **Real platform posture:** SSO/role-based access enforced server-side, immutable AuditEvent on every
  state change, deployed + stable on ODC, `harness-gate` green on ALL declared dimensions (spec/structural/
  behavioral/role/render/pixel).
- **Honest integration boundary:** PLM / ERP / SSO-IdP / denied-party / doc-storage endpoints are Rivian's
  and are "TBD in discovery" per the spec — so build them as **governed, clearly-marked stub adapters**
  (an integration seam + a mock implementation) that exercise the full workflow end-to-end AND swap to
  real endpoints with NO rework. "Works in production" = the app is fully functional and releasable; the
  external connectors are wired to mocks pending Rivian's actual endpoints. Do NOT claim a live connection
  to Rivian's real PLM/ERP.

Iterate with the gate until 100% of the above holds — not before.
