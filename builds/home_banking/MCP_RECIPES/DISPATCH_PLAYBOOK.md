# Dispatch Playbook — How to Execute an App Build

**Purpose**: Replace autonomous subagent dispatches with a disciplined foreground driver. Subagents have drifted on 4 separate attempts this session, skipping phases for "budget" or improvising when given goal-framed prompts. This playbook eliminates drift by encoding every decision point.

**Audience**: Claude (in main context) or a human driving an MCP-tool-equipped session.

**Output**: Working app at runtime URL OR explicit halt-with-failure at first state-divergence (NOT another speculative report).

---

## Core principles (NON-NEGOTIABLE)

0. **Subagent prompt mechanics (drift forensics, 2026-06-10).** Drift's causal trigger is
   budget arithmetic + escape hatches, not goal wording. When a subagent IS used
   (single-phase, execute-only):
   - **NO wall-clock budgets in the prompt** — the orchestrator keeps the clock and
     kills; the agent must never self-ration. (Every drifted run quoted budget math
     verbatim in its skip rationale.)
   - **NO escape hatch wider than one batch** — "document gaps and continue" became
     citable authority to skip whole phases. Allowed form: "if THIS batch fails twice,
     report and halt"; forbidden form: "skip what doesn't fit."
   - **Ship every constraint WITH its rationale** — the one near-drift that self-arrested
     did so because the prompt explained WHY verbatim fidelity mattered.
   - **Per-step error policy** — on auth-expiry: STOP; on tool-denial: report, never
     substitute; on missing prior-step output: mark dependent steps NOT EXECUTED.
   - **Bulk-ref calls ≤10 element keys** — removes the 10-22 min stall that fires the
     budget reflex in the first place.
   - **Mark gap-register provenance** — GAP entries written by drifted runs must be
     labeled as such; later agents cite them as precedent ("V7 documented these as
     non-essential").

1. **No autonomous subagents for build dispatch.** Subagents drift. Drive in main context.
2. **No "Status: OK" trust.** Every batch is verified via `context_screens` / `context_search` / `app_refs` BEFORE the next batch dispatches.
3. **No phase skipping for "budget."** If a phase can't complete in budget, HALT and report — don't skip ahead.
4. **No improvisation.** The renderer's output is the source of truth. If Mentor refuses or fails, document and HALT.
5. **No success summaries that don't match published OML.** Every report cross-checks against the OS-side state.

---

## Phase 0 option — recipe-shaped generation (doctrine, 2026-06-11)

A Mentor one-shot at the start is allowed — and often fastest — under one contract:
**the generation prompt is derived FROM the manifest/recipes**, so the baseline it
produces is exactly the scaffolding later recipe turns expect (entity names, flow
names, role gates, screen names, theme). Everything after the shot is ADDITIVE.

The test: if any later recipe turn must UNDO something the generation invented
(rename a screen, strip a structure, re-route a pattern), the generation prompt
was wrong — fix the prompt, not the app. Consigli's lesson cuts both ways: a
working baseline on day one accelerated everything, but its unconstrained V1
generation was thrown away entirely, and free-form generation cost many turns
of undo/redo. We know the full build order before we start because the design
is already decomposed into recipes; the one-shot is the executor of phase one,
never a replacement for the plan.

---

## Required prep before dispatch

| Step | Check | Halt if fails |
|---|---|---|
| 1 | App created via `app_create` — captured assetKey + env_key | YES |
| 2 | Recipes rendered at `/tmp/<build_id>/<app>/batches/` | YES |
| 3 | `library_element_keys.yaml` exists with required producer UUIDs | YES |
| 4 | All required `_raw/*.tree.md` captures present | YES |
| 5 | `auth_status` returns OK | YES (re-auth then resume) |

---

## The canonical turn loop (doctrine, 2026-06-11)

Every build turn runs this loop:

```
[ask "how would you?"] → recipe → prompt → mentor turn → "what did you do" → "what is broken" → publish gate → snapshot + spec-diff → next
```

0. **"How would you do this?"** (discovery — read-only, CONDITIONAL). Before
   prescribing a recipe, ask Mentor — which holds the LIVE model and the real
   Model API — how it would accomplish the goal + captured spec against THIS app.
   One read-only turn that does three things a blind recipe can't: (a) diagnoses
   real state — e.g. surfaces that `Accounts` is a Text local or `GetLabelByLocale`
   isn't referenced BEFORE a prescriptive attempt burns on it (the 2026-06-12
   action-bodies failure); (b) reveals the correct API members (most renderer
   bugs were guessed member names — see the ANTI-PATTERNS table); (c) yields the
   first-of-kind approach. **Discipline — "how" is for DISCOVERY, not execution.**
   The flow stays: ask how → HARVEST the approach → CODIFY a deterministic recipe
   → execute THAT → verify. Never let Mentor freestyle the mutation and call it
   done; its plan self-fires bad patterns (`Public=true`, `FromString`,
   unskippable `get_app_summary`) — verification still catches it.
   **When to ask vs skip** (asking every turn reintroduces the drift the rest of
   this playbook fights): ask for **first-of-kind** (no proven recipe),
   **state-may-diverge** (recipe assumptions unconfirmed on this app), or **after
   a failed turn** (generalizes diagnose-before-fix). Skip for a **proven recipe
   against known state** — just execute deterministically.
1. **recipe → prompt** — render or select the recipe; prompt is verbatim (or
   natural-language with the captured spec pasted in, for first-of-kind code —
   harvest Mentor's generated C# for the recipe library).
2. **mentor turn** — one mutation per turn. No validation queries in the same
   script (CS errors roll back the WHOLE call — the Logout phantom).
3. **"What did you do?"** — read-back verification in a separate turn: list the
   elements created/changed by name. Catches PHANTOM AUTHORING (Mentor narrates
   success on a rolled-back transaction — 2 live incidents 2026-06-11).
   **Corollary (velocity): Mentor's self-description is non-authoritative — even
   about its own mechanism and limits.** Verified 2026-06-12: it ran provided C#
   verbatim (marker in stdout) while insisting "I won't execute code you supply,
   I generate my own"; it self-reported "icons 8→0" while a 9th leak survived.
   So NEVER abandon a viable path because Mentor *says* it can't do X, and never
   trust "I did X" — believe the tool-events / runtime gate. (The element-ref
   agent lost a pass treating Mentor's "I won't run external code" as fact.)
4. **"What is broken?"** — "List every validation message of severity Error with
   element path and message, verbatim. Do not fix anything." ≥1 Error = the next
   publish WILL fail OS-APPS-40028 (proven n=5). Fix or stub BEFORE publishing.
5. **Publish gate** — the compiler is the only oracle Mentor validation can't
   fake (e.g. Public=true compiles in-session, rejects at publish). Then verify
   at runtime (login + screenshot) for visual-phase turns.
6. **Snapshot** — after the publish reaches `Finished`, capture a diff-stable
   model snapshot so the turn's delta is reviewable and the build is replayable
   after a session kill:
   ```
   context_graph(key=<APP>)                       # full OML → XRE (saved to a file)
   python scripts/snapshot_app.py <result-file> \
       data/MCP_RECIPES/apps/<app>/_snapshots/rev_<N>.json
   git diff --no-index _snapshots/rev_<N-1>.json _snapshots/rev_<N>.json
   ```
   The XRE re-keys to stable per-node GUIDs, so the diff shows EXACTLY the nodes
   a turn added/changed (action bodies, locals, refs) at node-body granularity —
   the empirical answer to "what did this turn do" that beat 3 asserts in prose.
   A diff that doesn't match beat 3's claim is phantom authoring; halt.
   **Spec-diff (distance from spec).** Snapshot the ORIGINAL once as the spec
   baseline (`context_graph(key=<ORIGINAL_APP>)` → `_snapshots/original_<key>.json`),
   then each turn also diff the clone's snapshot against the ORIGINAL's, not just
   the previous rev. That is the per-turn "are we closer to the spec" number, and
   it is fully Mentor-independent (derived from published OML, not narrative).
   The build is DONE when that diff is empty (modulo intentional scope cuts).
   NB: node `_key`s differ between two DISTINCT apps, so cross-app spec-diff
   compares by structural shape (type + Name + edges), not raw `_key` — same-app
   rev-to-rev diff still uses `_key` directly.

7. **CDP runtime gate (HARD — visual turns).** Publish + snapshot prove the model
   changed and compiles; they do NOT prove it RENDERED. The turn declares its
   EXPECTED runtime delta and asserts it against the live DOM:
   ```
   .venv/bin/python scripts/cdp_login_screenshot.py compare/<name>.png \
       --assert "leaked_icons=0,text_stubs=0,button_logout_raw=0"
   ```
   Exit 5 = the assertion failed → the turn is NOT done, regardless of a green
   publish. RATIONALE: rev 38 published clean + snapshot-clean but rendered
   "LogoutLogout"; V22 self-reported "icons 8→0" but a 9th leak survived — both
   invisible to publish/snapshot, both caught here. This is the only Mentor-AND-
   self-report-independent oracle. Assert ABSOLUTE targets (`=0`), never the
   agent's self-counted delta (that's what missed the 9th icon).

**Loop-control rule (doctrine, 2026-06-12, Rob): VALIDATE-BEFORE-ADVANCE.**
The CDP gate defines "done" for a surface. If the gate shows ANYTHING expected
that was not built or did not render, THAT becomes the next loop — you do NOT
move on to new content (other screens, new features) until the current surface
is 100% CDP-validated (all visual assertions pass against absolute targets, data
0s excepted where explicitly out of scope). A precisely-defined wall is a finding,
not a license to advance: it just means the next loop's job is to make the wall
fall (e.g. capture the original's missing CSS and inject it — see the hb-icons
font precedent), not to skip ahead. Lock it down first.

**Theme-anchoring rule (doctrine, 2026-06-12, Rob).** Elements must ANCHOR to the
theme — style them via theme CSS classes + design tokens (`Style` /
`SetStyleClasses` referencing theme classes; `var(--color-*)` / `var(--space-*)`),
NOT inline hardcoded values (`CustomStyle` with literal colors/px). RATIONALE: a
hardcoded element does not respond to the theme — when `dark-mode` activates an
anchored element flips to navy while a hardcoded one stays light, and parity
breaks. The renderer reaches for inline styles when a class "won't take" (memory:
inline styles bypass OS UI specificity) — that shortcut is a parity bug, not a fix:
make the CLASS take. Validate anchoring two ways: (1) the `inline_colored` metric
near 0 (few/no elements carry inline color/background); (2) the dark-mode-flip
test — toggle the `dark-mode` class and confirm content elements actually change
computed color (anchored) vs stay put (hardcoded → fix those). A green leak/stub
gate over hardcoded elements is a FALSE pass: it looks right in light mode and
wrong the instant the theme moves.

Steps 3+4 are cheap read-only turns on the warm session; they convert publish
failures (~4 min + diagnosis) into in-session findings (~30s). Beat 0 is also
read-only; it converts a burned prescriptive attempt (~4 min publish + rollback)
into a 30s plan that already accounts for the live state.

---

## Dispatch sequence (strict order)

### Phase 0 — References

**Goal**: All producer libraries imported + verified in `app_refs`.

```
1. mentor_start({app_key: <APP>, prompt: <Phase 0 reference setup prompt>})
2. Capture mentor_session_id from response
3. Poll mentor_get_run({runId}) until terminal
4. IMMEDIATELY: mentor_cancel(runId) ← skips narrative synthesis (60-180s save)
   ⚠️ MUTATION SAFETY (2026-06-12): cancelling a turn that MUTATED the model
   BEFORE it reaches terminal ROLLS THE MUTATION BACK (observed `REVERTED…`).
   The synthesis-skip cancel is safe ONLY for READ-ONLY turns (captures,
   "what-is-broken" probes). For ANY authoring/mutation turn, let it reach
   terminal `succeeded` (pay the synthesis tax) — THEN it's committed. A
   cancelled mutation that Mentor still narrates as success = phantom authoring.
5. Capture mentor_session_token from terminal result
6. publish_start({mentor_session_id, mentor_session_token, env_key})
7. Wait 35s, publish_status — expect Finished
```

**The two-step reference contract (MCP retest B2-rerun, 2026-06-10)**: `addReferenceToElements` returning `null` only STAGES the import. The reference materializes after `applyModelApiCode` runs `eSpace.AddDependency(Services.ModelServices.ParseGlobalKey("<globalKey>"))` per element (globalKey from `getWebBlock`'s stub). Both steps are required.

**VERIFICATION (MANDATORY before Phase 1)**:
```
app_refs({key: <APP>}) — must contain every producer required for downstream phases
```
If any required producer is missing → HALT, document specific missing producer.

**Publish-shape gate (MCP retest Q23/O01 — #1 scale blocker)**: entities with a custom (non-platform) `IdentifierAttribute` shape author fine in-session but CRASH publish at DB-script generation (`OS-BEW-CODE-50008` / `OS-RDBS-GEN-40002`). Renderer's `Id` LongInteger AutoNumber shape conforms. Before any entity phase on a new manifest: publish ONE entity in isolation first to confirm the shape deploys, then batch the rest.

**Freshness gate**: `context_*` staleness is >4 min post-publish (NOT ~30s). Gate phase verification on `app_info.revision`/`modelDigest` first; treat context_search presence as eventual confirmation only.

**Concurrency lock**: concurrent Mentor sessions on one app silently fork — last publish wins with no warning (MCP retest Q20). ONE in-flight Mentor session per app, always.

---

### Phase 1 — Entities (if app owns entities)

For each entity batch:
```
1. Read batch prompt file
2. mentor_start({mentor_session_id, mentor_session_token, prompt: <batch verbatim>})
3. Wait, mentor_get_run, mentor_cancel-immediately
4. Update mentor_session_token
```

Publish at end of phase.

**VERIFICATION**:
```
For each expected entity:
  context_search({query: "<EntityName>", objects: ["Entities"], app: <APP_NAME>, search_type: "full-text"})
  — must return result with isPublic: true
```
(Allow ~30s cache lag — data presence in result counts as success.)

If any entity missing from results after 60s → HALT.

---

### Phase 2 — Roles, Actions (stubs)

Same pattern. Verify via context_search objects:["Roles"] and objects:["Actions"].

---

### Phase 3 — Custom blocks (LAYOUT FIRST)

Critical: layout blocks (LayoutBase, LayoutTopMenu, LayoutTopMenuLeftSide) must be authored BEFORE screens that reference them.

Dispatch order:
1. Layout family
2. Common UI blocks (Menu, MenuIcon, ApplicationTitle, etc.)
3. Domain blocks (AccountCard, FormInfoField, etc.)
4. AI/chat blocks (if any)

Each batch: mentor_start → mentor_get_run → mentor_cancel → next batch.

Publish after all blocks dispatched.

**VERIFICATION**:
```
For each block: context_search({query: "<BlockName>", objects: ["Blocks"], app: <APP_NAME>, search_type: "full-text"})
```

---

### Phase 4 — Theme

If theme CSS is <30KB: single batch dispatch.
If theme CSS is ≥30KB: chunked dispatch (Recipe 10 chunked variant).

**VERIFICATION**:
Verify via applyModelApiCode probe: `eSpace.MobileThemes.First(t => t.Name == "<THEME>").StyleSheet.Length` matches expected.

---

### Phase 5 — Screens (dechromed, with role/anon flags baked in)

For each screen batch, dispatch verbatim from renderer. Renderer must have applied the anonymous-screen pattern for Login/InvalidPermissions (v3 bake).

**VERIFICATION (per screen)**:
```
context_screens({app: <APP_NAME>}) — verify each screen exists
  - Login + InvalidPermissions: roles:[] AND AnonymousAccess:true
  - Other screens: roles:[<app_role>]
```
If Login still gated → HALT (renderer bake didn't take).

---

### Phase 6 — Chrome wrap (v10, typed SourceBlock)

Each chrome batch has IMPORT PREREQUISITES section (cache-warm + addReferenceToElements + verify).

Dispatch + watch for: `wrapped=N/N` AND publish accepts.

**PUBLISH GATE PER CHROME TURN (NON-NEGOTIABLE — learned 2026-06-11, Portal4 rev-13 stall).**
Chrome-wrap corruption is SILENT: a corrupt source bind produces zero in-session
validation errors and only surfaces as OS-APPS-40028 at publish. Batching N chrome
turns into one publish makes the failure non-localizable and traps all N turns'
work in an unpublishable session. Therefore: publish after EVERY chrome turn
(including each part of a split screen). On OS-APPS-40028, the just-applied turn
is the corruptor; abandon the session (a fresh session restarts from the last good
revision — every prior turn was gated, so nothing is lost), skip or sub-bisect
the corruptor, continue. Revision-number inflation is free; trapped sessions are not.

**VERIFICATION (per screen)**:
```
For each chrome-wrapped screen, dispatch a probe applyModelApiCode that walks the
screen and counts IMobileBlockInstanceWidget descendants:
  - Should match expected wrap count from manifest
```

If publish rejects OS-APPS-40028 → HALT, document the screen + verbatim error.

---

### Phase 7 — DefaultScreen → main view

Final recipe: `eSpace.DefaultScreen = <MainViewScreen>`. For Banking: Dashboard.

Publish. Should be the final rev bump.

**VERIFICATION**:
```
env_app({env_key, application_key: <APP>}) — capture runtime URL
Open the URL in browser:
  - Should show <MainViewScreen> (or Login if MainView is role-gated)
  - Should NOT show _error.html
```

If URL errors → HALT, run runtime diagnostics:
1. context_screens — verify DefaultScreen is set + accessible
2. Check publish_logs for any warnings missed
3. Check that all referenced entities/actions exist

---

## Halt conditions (full list)

- Auth expiry → re-auth, resume from last published rev
- Mentor session crashes OS-AISA-40001 → start new fresh session, continue
- Validation Error (OS-BLD-*, OS-APPS-40028) → HALT — root cause is usually a renderer bug, fix the recipe
- 3 consecutive batches with publish FAIL → HALT — likely systemic issue
- VERIFICATION step fails 2x with retry → HALT — state divergence
- Any subagent or recipe behavior not matching expectations → HALT and report

**Do NOT skip ahead. Do NOT improvise. Do NOT trust narrative summaries.**

---

## Resume from halt

When halt occurs, capture state:
1. Final rev
2. Which phase + batch was last successful
3. What verification failed (verbatim error)
4. Resume by fixing the renderer/recipe THEN re-dispatching ONLY from the failed batch onward

Do not re-dispatch successful batches (they'd re-author entities and cascade).

---

## Cost estimates (with warm-session + mentor_cancel-immediately patterns)

| Phase | Batches | Time/batch | Total |
|---|---|---|---|
| 0 Refs | 1 | ~3 min | 3 min |
| 1 Entities | ~9 | ~30 sec | 5 min |
| 2 Actions | ~10 | ~30 sec | 5 min |
| 3 Blocks | ~15 | ~45 sec | 12 min |
| 4 Theme | 1 | 1 min | 1 min |
| 5 Screens | ~5 | ~45 sec | 4 min |
| 6 Chrome | ~5 | ~1 min | 5 min |
| 7 Default | 1 | ~30 sec | 1 min |
| Verifications between phases | ~7 | ~30 sec each | 4 min |
| Publishes | ~5 | ~40 sec each | 4 min |
| **Total** | ~52 turns | | **~45 min** |

If exceeding 90 min, investigate Mentor latency before continuing.

---

## Related

- `[[WARM_SESSION_DISPATCH]]` — session resume pattern (skip get_app_summary)
- `[[mentor_cancel-immediately-after-tool_end]]` — second cost workaround (skip narrative synthesis)
- `[[odc_mcp_addreferencetoelements_silent_noop]]` — third workaround (cache-warm before reference add)
- `[[FRAMEWORK_REVIEW]]` — broader framework health
- `[[GAPS]]` — known gaps in the renderer pipeline
