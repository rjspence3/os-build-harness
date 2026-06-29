# R12 Rebuild Runbook — operational protocol for OutSystems MCP authoring

This runbook captures the dispatch-time rules that the renderer code can't
enforce on its own. Apply these every time you author a new app (Portal,
Backoffice, the 5 agents, or any future build).

Renderer-side rules (Public=false default, topological FK ordering, placeholder
gating, automatic batching) are **already baked into the code** — see
`pipeline/banking_runner/recipe.py` and `scripts/build_banking.py`. This doc
covers the dispatcher-side protocol that lives in agent prompts and the
human-driver workflow.

---

## 1. Mentor session-cap hygiene (the biggest lever)

The OutSystems tenant enforces a per-tenant Mentor session concurrency cap.
Sessions are **not** released automatically when the publish reaches Finished —
they hold their cap slot until you `mentor_cancel(runId)`. In R12 we
accumulated 115 leaked sessions before the cap saturated; recovery required a
bulk-cancel sweep.

**Cancel-after-publish, EVERY session.** Every dispatch loop ends with:

```
1. publish_status returns Finished
2. mentor_cancel(runId)   ← MANDATORY, before starting the next session
```

**Bulk-cancel on cap-saturation.** When you hit `per_tenant_cap_reached`:

1. Grep all run IDs from the agent transcript directory
   (`/private/tmp/claude-501/.../tasks/`) — pattern `"runId":"<uuid>"`.
2. Fire `mentor_cancel(runId)` on every match. No-op on terminal, releases
   leaked. Wait ~90s for drain.
3. Re-probe with the next real recipe — if it accepts, cap is clear.

**Periodic preventive sweep.** After every ~10 sessions, do a bulk-cancel
pass even if you haven't hit saturation. Keeps the slot pool healthy.

---

## 2. Batched dispatch (use the renderer's batches/ output)

`build_banking.py --app <name> --dry-run` now emits per-phase batched prompts
under `<out>/<app>/batches/`. Dispatch these, **not** the per-recipe
`*.prompt.txt` files. 10 actions per Mentor session = 10× less cap pressure
than one-recipe-per-session.

Within each batch, the merged C# uses block-scoped `{ ... }` per recipe so
local helpers/vars don't collide. **Caveat:** a batch is all-or-nothing at
compile time. If one recipe in a 10-recipe batch has a bad line, the entire
batch fails. Use known-good shapes (the renderer's output qualifies).

---

## 3. Agent prompt rules (avoid derail)

In R12, three subagents derailed mid-batch by hallucinating "waiting for
DRAIN_DONE event" during `sleep` steps. The root cause: agents conflate
`sleep` with an event-await pattern and exit early.

**No `sleep` in agent prompts.** The natural latency of `mentor_get_run`
polling (~35s first call, ~25s subsequent) is enough pacing. If you need a
drain wait, do it in Bash from the main loop with `Bash run_in_background`,
not inside the agent.

**Fail-fast on per_tenant_cap_reached.** Don't have the agent retry inside
its own prompt with backoff. The agent should `mentor_cancel(runId)` and
exit; the main loop handles bulk-cancel + retry orchestration.

**Read events, not summary.** Mentor's chat-message summary may say "Sorry,
the model can't fulfill" while the `applyModelApiCode` tool_end stdout
contains the real result. Per-recipe agents must inspect events directly.

---

## 4. Diagnostic probe discipline

In R12, a "does X work?" probe against the production target app
(`HomeBankingCoreSandbox`) silently committed actions that the publish
rejected — leaving collision-rename `*2` pollution we then had to clean up
with `IServerAction.Delete()`.

**Probe APIs on a throwaway sandbox**, never the production target. Create
a `_Probe<Date>` app in Portal, probe there, delete or ignore after.

**If you must probe against the target**, plan the cleanup BEFORE running
the probe. Failed publishes commit actions but not the build — assume any
authoring attempt will persist regardless of publish status.

---

## 5. Known walls and their solutions (R12 lessons baked in)

| Wall | Symptom | Fix |
|---|---|---|
| `per_tenant_cap_reached` | New mentor_start fails after ~2-3 sessions | Cancel-after-publish hygiene; bulk-cancel on block. |
| `OS-BLD-40409` removed feature | Publish fails with `ModelFeature_ServerActionPublicPropertyApp` removed | NEVER set `a.Public = true` on `CreateServerAction`. Renderer forces false. (v2: probe modern `CreateServiceAction` API.) |
| `OS-APPS-40028` invalid OML | Public action references private entity record | Either set entity.Public=true OR keep action Public=false. The renderer keeps everything Public=false in v1. |
| `/* unsupported X */` placeholder | Recipe contains a List-of-record or Structure-typed param | Renderer's placeholder gate moves it to `_deferred/`. (v2: probe modern List + Structure param APIs.) |
| FK NPE at `.Named("X").IdentifierType` | Server entity references another server entity not yet published | Renderer's `topologically_order_server_entities()` (Kahn's algorithm) — entity dispatch order is topological, not manifest order. |
| Polluted `*2` collision-rename actions | Failed publish committed action; retry collision-renamed | `IServerAction.Delete()` works for cleanup — see `cleanup_polluters.prompt.txt` pattern. |
| Token expired | Any MCP call returns `requires re-authorization` | Interactive `/mcp` re-auth from the human; agents stop and report. |
| `context_*` index lag | Search index doesn't reflect just-published changes | Trust `app_info.revision` bump as the persistence oracle, not `context_actions`. Index catches up in ~tens of seconds to minutes. |

---

## 6. Canonical workflow for a new app

```
1. Portal: create the app (Studio gate — can't be automated; see
   [[odc_mcp_no_app_creation]]).
2. Studio: do ONE manual publish on the new app to warm it for MCP
   (see [[odc_mcp_publish_studio_warmup]]).
3. Studio: add references via Manage Dependencies — e.g., AppsCommonCore,
   Agents Common Resources (see [[odc_mcp_reference_add_studio_only]]).
4. Local: `python scripts/build_banking.py --app <name> --dry-run --out <dir>`
   This emits per-phase batched prompts in <dir>/<name>/batches/.
5. Dispatch the batches in phase order: 02_static → 03_role → 01_server
   (in topo order) → 04_serveraction → 04_serviceaction.
   One Mentor session per batch. Cancel after each publish.
6. Verify: app_info revision bumps + Recipe 99 verification probe.
```

---

## 7. v2 TODO — known API gaps

1. **Modern `CreateServiceAction`** — current renderer keeps every action
   Public=false because the legacy `CreateServerAction + Public=true` pattern
   is removed (OS-BLD-40409). Cross-app service surface needs this.
2. **List-of-record and Structure-typed params** — the renderer's
   `_render_action_param` emits `/* unsupported */` for these. 4 R12 recipes
   parked in `_deferred/` pending this.
3. **`entity.IsPublic`-style v2 ServiceAction-aware closure** — modern Service
   Actions may have their own public/private flag separate from `entity.Public`.

---

Related memories: `[[odc_mcp_publish_lifecycle]]` (cancel mechanics + OS-BLD-40409
+ closure rules), `[[odc_mcp_record_literal_via_typed_local]]` (entity-as-record
DataType for params), `[[odc_mcp_screen_widget_authoring_api]]` (import allow-list,
the Model API patterns that work).
