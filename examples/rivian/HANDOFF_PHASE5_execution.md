# Rivian Production Build — Phase 5–6 Execution Handoff (2026-07-09)

Single best-context doc to drive the **cap-heavy 5-app build to production**. The offline foundation
(design layer + MODULAR blueprint + master plan) is DONE and committed. This handoff is the plan to
build + gate + pixel the system. Written at full context; trust it + verify against live state.

## Where things stand (verified)
- **Branch:** `feat/autonomous-harness-and-rivian`. **Tests: 442 green** (`python -m pytest -q`).
- **8 commits this session** (latest first): production blueprint `fbab0ae` · live-verify gate accuracy
  `38beb02` · create-form edit-prefill `78be45f` · rivian Edit→navigate `f1ad562` · gate verdict taxonomy
  `ea9b416` · run_build session-cap resilience `493723f` (+ 2 earlier).
- **The gate is now TRUSTWORTHY** (two-class DEFECT/UNVERIFIED taxonomy; DONE ⟺ zero DEFECT and zero
  INCOMPLETE). It catches real defects and no longer false-fails working UX. Use it as the definition of done.
- **RivianReviewer8** (hero-app proof) gates **DONE** (spec/structural/behavioral 2/2/render 4/4; pixel OMIT).
  app_key `5da30f52-b008-4371-9952-39686cae9dea`, https://robertjspencedemos-dev.outsystems.app/RivianReviewer8.
  Keep as the regression baseline for the single rich reviewer app.

## The production bar (do not lower)
PLAN.md definition-of-done: every FR-01..21 works end-to-end AND **100% fidelity to the Claude design**
(pixel-green against `design/rivian-design-system/mockups/`). The **5-app modular system** (Path B), both
portals server-side role-gated, immutable AuditEvent, integration STUBS (governed seam + mock, swap-to-real
with no rework — never claim a live PLM/ERP connection).

## The blueprint (all committed, offline-regenerable)
- `examples/rivian/domain_spec.json` — 8 entities, 2 actors, Qualify BPT orchestrator + DeniedPartyScreen AI
  step, 5 integration stubs.
- `examples/rivian/system_spec.json` — decompose output; `harness-system-gate` reads **◻ MODULAR** (24 flows).
- `examples/rivian/master_plan.json` — topo order (producer-before-consumer).
- `examples/rivian/apps/{OnboardingCore,DeniedPartyScreenAgent,QualifyWorkflow,ReviewerApp,SupplierApp}.app_spec.json`
  — expand v0 specs. **Portals are THIN — enrich before building (see Step A).**
- `examples/rivian/design/rivian-design-system/` — `/design-layer` output: `tokens/tokens.css` (theme payload
  + @font-face + component-class contract), `tokens.ts`, `src/components/*`, `mockups/{case-queue,case-detail}.html(.png)`.
  This is the **pixel target** + the ODC `theme.StyleSheet`. Regenerate offline: `python examples/rivian/gen_reviewer_spec.py` is the SINGLE-APP spec; the design system is standalone.

## Master build order (topo; producer-before-consumer)
```
1. RivianDesignSystem     Library          (design layer — already authored)
2. OnboardingCore         WebApplication   9 steps  (8 entities + 6 service actions + 2 events)
3. DeniedPartyScreenAgent AIAgent          2 steps  ⟵ after Core
4. QualifyWorkflow        BusinessProcess  3 steps  ⟵ after Core + Agent
5. ReviewerApp            WebApplication   7 steps  ⟵ after Core + DesignSystem   (ENRICH first)
6. SupplierApp            WebApplication   5 steps  ⟵ after Core + DesignSystem   (ENRICH first)
```

## THE HARD CONSTRAINT — the Mentor session cap (read before building)
Per-tenant **100 concurrent Mentor sessions**, enforced **cluster-wide** (Redis, all MCP replicas), reaped
after **24h inactivity**. The harness opens **1 session per authoring step** and does NOT free it:
`mentor_cancel` is a **no-op on a terminal (succeeded) run** — proven, so cancel-after-publish frees nothing.
The user's **other machine shares the same cap** (both compete). User has **NO cap-raise control**. So:
- A big day saturates the cap for ~24h; builds HALT on `per_tenant_cap_reached` (non-retryable → clean halt).
- **`run_build` is resumable** from `--state`; the **cap-cascade** (shipped) waits 8s and re-fires the same
  step in-build (capped starts are rejected pre-admission, no slot taken) so a build rides freed slots.
- **Drive every build through a resume poller** (pattern below). To go faster: pause the other machine's Mentor work.
- **Durable fix NOT yet done:** session-reuse + `fresh_context:true` (one session/build). See memory
  `[[harness-leaks-mentor-session-per-step]]`.
- **Also open:** `classify_terminal` hard-halts a *transient* source-control 401 as "unauthorized" (R8 hit this
  at step 9; the token was actually valid — `app_list` worked). The Phase-5 resume poller retries 401s. Consider
  fixing classify_terminal to distinguish transient 401 from real auth failure.

## Build + gate mechanics (proven)
**Build one app** (fresh):
```bash
python -m harness.run_build examples/rivian/apps/<App>.app_spec.json \
  --create --name Rivian<App> --kind <CrossDevice|AIAgent|BusinessProcess> \
  --tenant robertjspencedemos.outsystems.dev \
  --state examples/rivian/apps/<app>.state.json --prompts-dir examples/rivian/apps/_prompts_<app>
```
Resume (after cap halt): same but `--app-key <key>` (grep `app_key=` from the first run's output).
**Resume poller** (retries cap + transient 401; see `/tmp/resume_r8.sh` for the exact shape) — loop
run_build, on `per_tenant_cap|unauthorized|401` sleep 120–600s and retry, exit on `Build OK` or a genuine halt.
Run it `run_in_background: true` + a `Monitor` on the output for `✓ /✗ /Build (OK|HALTED)`.

**Gate one app** (the definition of done):
```bash
python -m harness.gate examples/rivian/apps/<App>.app_spec.json \
  --base-url https://robertjspencedemos-dev.outsystems.app/Rivian<App> \
  --pixel examples/rivian/design/rivian-design-system/mockups --pixel-tol 16 \
  --out examples/rivian/apps/_gate_<app> --json
```
Green = `VERDICT DONE`. Read `dimension_state` (PASS/FAILED/INCOMPLETE). **FAILED = real app defect → fix.
INCOMPLETE = the gate couldn't drive it → fix the driver/spec, not the app.** For each defect, drive it
manually with Playwright first (fill form / click row) to confirm real-vs-driver BEFORE re-authoring — this
is how R8 got to green (the "defects" were mostly gate-driver gaps: `_COUNT_JS` miscount, always-visible
form, edit-via-nav, KPI-vs-sampleData, `_SET_FIELD_JS` fallback — all now fixed).

## The execution plan (in order)
**Step A — enrich the two portal specs (offline).** The expand v0 portals are thin. Author rich screens on
`ReviewerApp` + `SupplierApp` app_specs matching the design (nav sidebar, KPI dashboard, styled `columns[].kind`
queues, `screen.detail` stepper+reviews+timeline, intake `Form` w/ validation, doc-upload, status tracker) +
`design.theme` from `tokens/tokens.css`. **Use `apps/ReviewerWorkspace.app_spec.json` (the R8 rich spec, gate-green)
as the component template** — but portals REFERENCE OnboardingCore's entities (not own them; the FK-target/
producer-import fallout pattern in harness/CLAUDE.md applies). Re-run `harness-verify --phase spec` to keep PASS.
Cover: FR-01 supplier intake (company/contacts/tax/part) · FR-11 parallel reviews · FR-13 multi-step approval +
immutable history · FR-14 in-app feedback (CaptureFeedback) · FR-19 role dashboards. Server-side roles: add an
`auth`/`access` block so the gate's **role** dimension is exercised (BLOCKS_ANON + ALLOWS_MEMBER).

**Step B — build in topo order, gate each to green.** DesignSystem (theme) → OnboardingCore → Agent →
Workflow → ReviewerApp → SupplierApp. After each: `harness-gate` DONE incl. role. Publish-per-unit; trust
independent reads over Mentor "success". For cross-app refs, use the import-instructions fallout pattern.

**Step C — 100% pixel fidelity.** Gate the two portals with `--pixel …/mockups`; iterate theme/layout to
parity. Known cosmetic: R8's dashboard KPI cards render barer than the mockup (values correct; card chrome thin)
— fix the dashboard recipe to wrap values in the full `.kpi-card` when driving pixel parity.

**Definition of done:** every app gates DONE incl. role + pixel; both portals pixel-match the mockups; the
QualifyWorkflow drives Screen→Review→Approve→Activate; audit immutable; integrations are marked stubs.

## Housekeeping
- Throwaway Dev apps to delete when convenient: RivianReviewer2–8, RivianReviewerWorkspace, HarnessCanary*.
- Uncommitted scratch: `apps/_prompts*`, `apps/*.state.json`, `.claude/plans/gate-accuracy-fixes/` — ignore.
- Tenant is Dev-centric; disposable Dev apps are fine; only deploy/delete/push asks once.
