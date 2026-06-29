# Mining Synthesis — What Makes the System Better (2026-06-10)

Synthesis of three transcript-mining reports (~295MB corpus):
- `DRIFT_FORENSICS.md` — this session's subagent failures
- `OSMCP_RAW_EXTRACTS.md` — verbatim working API sequences from the 55-probe retest
- `PRIOR_SESSION_LESSONS.md` — the 167MB GUI-era + ShiftGuard/QuoteForge MCP builds

Goal stack (restated): a recipe framework + grammar that lets the MCP clone any app; Home Banking Portal is the validation case.

---

## The revised causal model of failure

Three distinct failure classes — each previously conflated:

| Class | Mechanism | Evidence | Fix lives in |
|---|---|---|---|
| **Subagent drift** | budget arithmetic in prompt + escape-hatch clause + an early 10-22 min stall → "strategy reset" within 1-2 turns | Portal2/Portal3 verbatim rationales quote budget numbers, not goals; identical goal-framed redispatch with 30-50s batches had ZERO drift | Prompt template (orchestrator keeps the clock) |
| **Mentor API hallucination** | Mentor invents Model-API members; CS1061 ×251 across ShiftGuard+QuoteForge; top-15 hallucinated members decoded | `.Name` on ITypeSignature, `.InputParameters`, `.Screens`, `.UIFlows`, `SetArgumentValue` on wrong types… | Recipe framework (exact C#) + anti-hallucination table in PROMPT_PREAMBLE |
| **Doctrine non-enforcement** | memorized rules recur as failures anyway (OS-AISA-40001 hit 46× AFTER being memorized) | session-context wall, role auto-apply, budget discipline | Code-level enforcement (renderer emits, orchestrator guards) — never docs alone |

**Meta-lesson**: every failure class traces to *judgment latitude where determinism was possible*. The framework's purpose is to convert judgment into literals.

---

## Ranked improvements

### P0 — bake now (each <30 min, all offline)

1. **chrome_wrap v12: constructible globalKeys.** osMCP proved globalKey = `<producerModulePrefix>*<elementKey>`. Add `module_prefix` per producer to library_element_keys.yaml; emit literal `eSpace.AddDependency(Services.ModelServices.ParseGlobalKey("<prefix>*<elementKey>"))` lines in IMPORT PREREQUISITES. Removes getWebBlock round-trips AND the last Mentor-judgment surface in reference wiring.

2. **PROMPT_PREAMBLE: CS1061 anti-hallucination table.** Top hallucinated members with corrections (`.Name` on ITypeSignature → use reflection `.DisplayName`; `IMobileWidget` → `IMobileWidgetSignature`; `.AutoNumber` → `IsAutoNumber`; `eSpace.Actions` → `.ServerActions`/`.ServiceActions`; `Reference.MobileBlocks` → `GetAllDescendantsOfType<IMobileBlockSignature>()`; `.Append()` → `ListAppend`; `TryParseKey` is `out` not `ref`). 251 compile errors say this table pays for itself in one batch.

3. **Subagent dispatch template rules** (into DISPATCH_PLAYBOOK):
   - NO wall-clock budgets in subagent prompts — orchestrator keeps the clock and kills, agent never self-rations
   - NO "document gaps and continue" escape hatches scoped wider than a single batch ("you may not skip un-failed batches")
   - Every constraint ships WITH its rationale (Core2 agent stopped instead of drifting because the prompt explained why fidelity mattered)
   - Per-step error policy (on auth-expiry → STOP; on tool-deny → report, don't substitute)
   - Bulk-ref calls ≤10 element keys (removes the stall that triggers the budget reflex)

4. **Memory corrections**: deploy_impact "safe to call" → 404 regression; "GUI-driving Mentor abandoned for MCP" strategic lesson (weeks of investment, never memorized); GAP-entry contagion warning (gap docs from drifted runs become citable precedent — mark provenance).

### P1 — before/with the next dispatch

5. **Q23 PK lint in 99_verify + entity recipes.** Verbatim CRASH pattern (Delete auto-Id + custom IdentifierAttribute non-auto) vs SAFE pattern (`IsAutoNumber = AutoNumber.Yes` in-create). Publish ONE entity in isolation on any new manifest before batching.

6. **Action-body renderer gets the verbatim GetOrCreateListType + ForEach wiring trio** (CycleTarget / back-Target / exit-Target) from OSMCP_RAW_EXTRACTS — list-typed params and loops are now copy-paste, not Mentor-discovered.

7. **Visual gate per screen** — Rob's most-repeated correction across 3+ sessions is "doesn't look like an OutSystems app." Add a CDP/Playwright screenshot step after each screen publish; eyeball or pixel-diff vs original. This is the acceptance loop the pipeline never had.

### P2 — finish-the-goal sequence (the actual remaining work)

8. **Functional grammar execution** — aggregates, action bodies, navigation, seed data are recipes-without-renderers. These four are what separate "renders text" from "looks/works like the original." Build the Python renderers for 08/05a/24 + seed-data recipe (native LoadSampleData pattern is already memorized).

9. **Read-only inspection of the original suite's agent/HITL architecture** before authoring agent recipes (asked twice in prior sessions, never done).

10. **The disciplined Portal4 dispatch** with all of the above: v12 chrome_wrap, no-budget execute-only prompts, per-phase verification, visual gate. This is the framework's validation run.

---

## What we now know that we didn't this morning

- The reference-add mystery is fully solved (2-step contract + constructible globalKey)
- Drift is preventable with prompt mechanics (budget removal + scoped hatches + rationale)
- Mentor's hallucination surface is enumerable (CS1061 census) — the recipe framework attacks exactly the right problem
- Doctrine without code enforcement does not change outcomes (OS-AISA-40001 recurrence proves it)
- The visual-fidelity acceptance gap is the longest-running unaddressed correction
