# Prior-Session Lessons — Mined 2026-06-10

Sources mined (surgical grep/jq, no full reads):

| Transcript | Size | What it actually is |
|---|---|---|
| `a8468d20` | 167 MB | **NOT the banking-runner build.** Original pipeline build (/audit→/rank, prototypes, Stage 10) **plus the entire GUI-driven Mentor era**: Playwright/CDP driving Mentor Web + ODC Studio IDE, CohortPlatformCore, the "clone the banking app as the learning method" goal statement. Ended 2026-05-15. Zero `OS-*` error codes — GUI-era failures were crashes/visual, structurally untracked. |
| `de0a987f` | 26 MB | First MCP-driven build: ShiftGuard (healthcare). MENTOR_MCP_DOCTRINE.md born here. |
| `9c9a4e39` | 17 MB | Second MCP build: QuoteForge (CPQ) + Gen-Z restyle + ODC_UIUX doctrine + first Home Banking Portal/BackOffice MCP inspection. |
| `b56d6f6c` | 2.6 MB | Home Banking theme-library extraction (Studio Mentor). Discovery done, **execution never started**. |
| `c9ff47b4` | 2.3 MB | Agent-authoring edge-probing ("verdict no ai agents?" — later CORRECTED in memory). |
| `d4c42392` | 3.9 MB | KYCScreening improvement plan via mentor grammar — apparently dropped. |

The R1–R12 `banking_runner` build lives only in the current session (`ef26a8d4`, 1,202 mentions; 0 in all prior files).

---

## 1. Abandoned approaches + why

| Approach | Fate | Why | Memorized? |
|---|---|---|---|
| **GUI-driving Mentor Web + ODC Studio via Playwright/cliclick** (second half of a8468d20, ~weeks of effort) | Abandoned for the MCP path | IDE crashes (quotforge2 crashed Studio repeatedly), Mac lock/sleep killed unattended runs, Mentor confirmation dialogs stalled runners, output truncation, "are you sure you are using the right chrome?", permission-prompt fatigue | Fragments only (SIGKILL, lock-check, gesture verbs). **The strategic lesson — never GUI-drive Mentor when MCP exists — is not an explicit memory entry.** |
| **Thin-shell prototypes + Railway data plane** (CohortPlatformCore: ODC app as Service-Action wrapper over Railway APIs) | Abandoned same-day. Rob: *"I want to revisit if what we are doing makes sense — it's taken all day to do what exactly?"* / *"So this app is just a wrapper on railway?"* | No standalone value; ShiftGuard rich-app pattern (own entities/screens/SAs) replaced it | Yes (`cohort_railway_data_plane` superseded) |
| **Service Actions first** | Reversed by Rob: *"First build server actions that use the APIs then we can call and test them. Then move to service actions when we are sure they work."* | Service Actions can't be smoke-tested before the wrapped thing works; many 404s ("Why did most of them 404?") | No |
| **Bundled rich-screen MCP prompts** (Phase 5 ShiftGuard: 20 compile errors) | Cancelled run → reformulated minimal-scope (CreateScreen + SetTitle only) → landed clean | Scope wall is API-surface novelty | Yes (`odc_mcp_screen_scope_wall`) |
| **Iterating Mentor Web post-Generate** | Locked-in finding: *"All mentor web changes need to be locked in before Generate is clicked"* | Mentor Web can't adjust a generated app; Studio Mentor sidesteps | Yes |
| **Home Banking theme-library extraction** (Theme_Foundation + Theme_Chatbot two-library plan, b56d6f6c) | Session killed; handoff written; **never resumed** | Superseded in practice by recipe `10_theme_replace.md` CSS-replace? Not formally decided | Handoff file only |
| **Old ODC Studio for agents** | Only Studio 2 (1.7.6.9953) supports Mentor + AI agents; older versions removed | Version confusion burned a session segment | Partially (studio lore) |

## 2. Error census

### Platform error codes (the only structured ones in the whole corpus)

| Code | a8468d20 | de0a987f | 9c9a4e39 | Meaning |
|---|---|---|---|---|
| `OS-AISA-40001` | 0 | 34 | 46 | Mentor session conversation-context limit (~1.5M chars). Each hit forfeits unpublished session OML. |

No uncovered codes found in prior sessions — but note the GUI era produced **zero structured error codes**, which is itself why it was unminable and got abandoned.

### Mentor's own C# compile errors against the Model API (the real dominant failure class)

| CSxxxx | de0a987f | 9c9a4e39 | Class |
|---|---|---|---|
| CS1061 (no such member) | **149** | **102** | Mentor hallucinates Model API members |
| CS0246/CS0234 (type/namespace) | 3/15 | 18/3 | Wrong namespaces (e.g. AggregationType) |
| CS1929/CS1503 (type mismatch) | 18/6 | 5/9 | `CreateNode<T>` inference, generic constraints |

Top hallucinated members (decoded from escaped payloads): `.Name` (~48), `InputParameters` (21), `Screens` (15 — it's `Nodes.OfType<IMobileScreen>()`), `UIFlows` (9), `Roles` (9), `SetArgumentValue` (9), `Style` (8), `CreateAssignment` (5), `DataSource`, `SetStartIndex`/`SetMaxRecords`, `MessageType`, `ServerEntities`/`ReferencedServerEntities`, `TargetAttribute`, `StaticEntities`.

**Implication: ~250 CS1061s across two builds is the empirical justification for the recipe framework — recipes carrying verified C# snippets remove the dominant failure class entirely.** A "hallucinated member → correct call" table belongs in `PROMPT_PREAMBLE.md`.

## 3. Unfinished walls register (hit, then never closed)

1. **Theme library extraction** — `HOME_BANKING_THEME_EXTRACTION_HANDOFF.md` says "Execution not started." Decide: execute, or formally retire in favor of `10_theme_replace.md`. `HBIcon` choke-point finding (5 dependents) is still relevant to the clone.
2. **Banking app agents: app-context vs workflow-context** — Rob twice: *"We need to check if in the banking app the ai agents are in the app context or just the apps workflow"* / *"Need to verify in workflow."* Never verified. Determines whether recipes 17–21 alone reproduce banking parity.
3. **The banking HITL chat surface** — Rob's reference UX, stated precisely: side chat with agents running; each agent gets a **results box + decision box with Approve/Cancel**; agent result **enriches the screen live**; Approve **triggers the next agent**. No recipe covers this composite surface (recipes are per-element).
4. **Workflows have no MCP/automation surface** — "Workflows require we pre-build all actions"; portal-Playwright workflow building was researched, never productionized. Confirmed MCP gap in memory; still a clone gap if banking uses workflows (see #2).
5. **Mentor → Railway connections** — *"use mentor to properly create connections to our railway server for the automations and CRUD APIs"* — deferred "Later", never done.
6. **Mentor Web stage-gating** — *"check what changes can happen at each stage of mentor web"* — partially probed (phase0_corruption), no doctrine verdict.
7. **Google Drive link → deterministic hallucinated school-management app** — curiosity finding (URL-in-prompt behaves as content injection), parked, never investigated.
8. **FRAMEWORK_REVIEW grammar gaps** (current, restated for completeness): screen aggregates, action bodies, navigation routing, anonymous-access flag, reference manifest, app-shell composite, seed data.

## 4. User correction patterns (repeated = system failure signals)

1. **Visual fidelity — most repeated correction across 3+ sessions.** *"the app doesn't look like an outsystems app at all"*, *"diagrams unprofessional and childish"*, *"really this is ready for gen-z users?"*, *"If we can make it look exactly OutSystems we should."* Builds keep passing functional gates and failing the eyeball gate.
2. **Knowledge persistence.** *"No! We solved this and did it many times already. Why is it not working today?"* and *"do we have the grammar… as doctrine files or are they buried"* → *"Yes we need those as first class files."* Lessons trapped in transcripts is exactly the failure this mining run is correcting.
3. **Goal restatement (verbatim, the project's north star):** *"The goal is to learn to use mentor flawlessly and we are using 'clone the banking app' as the learning method"* and *"We are basically building a playbook for Claude code to build an OS app from end to end."* Generality is the deliverable; banking is the test case.
4. **Mentor interactivity.** *"Make sure that we always confirm the mentor asks and plans"* — Mentor stopping to ask (e.g. waiting for "yes" on a deletion plan) silently stalled runners more than once.
5. **Honest status over victory laps.** *"is the app fully build"* → wanted the 8-item gap list. *"Why are you building quoteforge?"* — target drift to familiar apps.
6. **End-to-end or nothing.** *"If we don't run it end to end, then what was the point?"* + *"We will need to figure out a retest path for anything that fails."*
7. **Unattended operation.** Permission prompts, Mac lock, Mentor confirmations — anything requiring Rob mid-run is a defect.

## 5. The 5 highest-leverage changes

1. **Close the functional-grammar gaps before adding more element recipes.** Screen aggregates, action bodies, navigation, seed data, and the app-scoped `<app>.app.yaml` (per FRAMEWORK_REVIEW). Every prior "done" app was an empty shell until hand-wired — the demo-ready wiring was always 2+ extra manual turns. Seed data especially: native `LoadSampleDataFor<Entity>` pattern is already doctrine; make it a recipe.
2. **Weaponize the CS1061 census.** Add a "Model API anti-hallucination table" to `PROMPT_PREAMBLE.md` (the ~15 members above + correct calls). ~250 compile-error iterations across two builds were burned re-discovering the same wrong guesses; verified snippets convert 3–4-iteration auto-fix loops into first-attempt lands (proven: ShiftGuard Phase 5 retry and QuoteForge Demo-wire redo both landed first-attempt once constrained).
3. **Enforce session-budget discipline in the orchestrator, not in doctrine.** OS-AISA-40001 hit 80× across two sessions despite being memorized after the first. Hard rules in `mcp_client.py`/`orchestrator.py`: fresh session per screen-scale turn, publish immediately after every landed turn, never `getScreen` on rich screens, treat any 40001 as checkpoint-restore (re-dispatch from last published rev).
4. **Add a visual acceptance gate as a pipeline phase.** Automated CDP screenshot + rubric review against `ODC_UIUX_DOCTRINE.md` after each screen recipe lands. This is Rob's single most-repeated correction; today it only happens when he eyeballs the app, which means rework arrives in batches at the worst time.
5. **Verify banking's agent/HITL architecture before building more agent recipes.** Resolve unfinished walls #2 and #3 with one read-only MCP inspection pass of HomeBankingPortal/BackOffice/Core (where do agents live: app vs workflow; how is the chat HITL surface composed). The clone's "wow" is exactly that surface — Rob described it in detail and nothing in the 29 recipes reproduces it as a composite. One inspection session de-risks recipes 17–21 plus an eventual `25_hitl_chat_surface` recipe.

### Bonus hygiene
- Either resume or formally retire the theme-extraction handoff (it currently reads as live work).
- Add the "GUI-driving Mentor is a dead path; MCP only" lesson as an explicit memory entry — it's the largest abandoned investment in the corpus and only exists implicitly.
