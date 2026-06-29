# Warm-Session Dispatch Pattern

**Purpose**: Amortize Mentor's unsuppressable `get_app_summary` startup cost (3-5 min per fresh session) across multiple `applyModelApiCode` calls by reusing one session.

**Source**: Bug B1 (data/bug_reports/B1.md). Empirically confirmed 2026-06-09: fresh sessions always run `get_app_summary` as the first tool call regardless of prompt instructions; **resume turns skip it entirely**.

**Impact**: A 13-batch dispatch using fresh sessions per batch costs ~65 min in summary overhead alone. The same 13 batches using a warm session pay ~5 min once. **~5-10× throughput improvement**.

## How `mentor_start` supports session resume

The tool surface (verified 2026-06-09):
```
mentor_start({
  app_key: <UUID>,         // FIRST turn only
  prompt: <text>
})
→ returns { runId, status: "running", mentor_session_id, ... }

After mentor_get_run reaches terminal status, the result contains:
  mentor_session_id: <UUID>          (already known from start response)
  mentor_session_token: <signed JWT>  (24-hour TTL, refreshed per turn)

mentor_start({
  mentor_session_id: <from prior>,
  mentor_session_token: <from prior terminal>,
  prompt: <next batch>
})
→ resumes the same session, skips get_app_summary warmup
```

**Important constraints**:
- Pass `app_key` ONLY on the first call. Subsequent calls use `mentor_session_id` + `mentor_session_token`.
- `mentor_session_token` is refreshed on every terminal `mentor_get_run.result` — use the LATEST one.
- Only one in-flight run per session. If `mentor_start` returns `run_already_in_flight`, cancel the prior via `mentor_cancel` first.
- Session context accumulates over turns — at ~1.5M chars (memory `odc_mcp_session_context_wall.md`) the session crashes with `OS-AISA-40001`. Keep applyModelApiCode bodies small per turn; consider periodic session refresh after ~20-30 turns or when working with large screens.

## Dispatch pattern (subagent or orchestrator)

```python
# Phase 1: open warm session (pays get_app_summary cost once)
result = mentor_start({app_key: APP_KEY, prompt: batches[0]})
runId = result.runId
session_id = result.mentor_session_id

# Poll to terminal
final = poll_until_done(runId)
session_token = final.mentor_session_token  # refreshed

# Phase 2: dispatch remaining batches on the warm session
for batch_prompt in batches[1:]:
    result = mentor_start({
        mentor_session_id: session_id,
        mentor_session_token: session_token,
        prompt: batch_prompt
    })
    final = poll_until_done(result.runId)
    session_token = final.mentor_session_token  # always update

# Phase 3: one publish at end (or every K batches)
publish_start({
    mentor_session_id: session_id,
    mentor_session_token: session_token,
    env_key: ENV_KEY
})
```

## Subagent prompt template

When dispatching a multi-batch Mentor pipeline via a subagent, include this template:

```
## Warm-session dispatch (CRITICAL for budget)

The Mentor `get_app_summary` startup tool fires once per FRESH session (~3-5 min per session). Reuse one warm session across all batches:

1. Batch 1: mentor_start({app_key: "<UUID>", prompt: <verbatim>})
2. Capture mentor_session_id from the start response.
3. Poll mentor_get_run to terminal. Capture mentor_session_token from result.
4. Batches 2..N: mentor_start({mentor_session_id, mentor_session_token, prompt: <verbatim>}) — NO app_key.
5. After EACH batch's terminal result, UPDATE mentor_session_token to the new value (it refreshes per turn).
6. Publish ONCE at end (or every K batches) using the latest session_id + token.

If you see "run_already_in_flight" — call mentor_cancel(runId) then retry.
If you see OS-AISA-40001 session-context limit — refresh the session (start a new one with app_key) and continue from there.
```

## When NOT to use warm-session

- **Probe runs that intentionally test fresh-session behavior** (like the B1 probe itself).
- **Adversarial / refusal-mode prompts** — those can poison the session state. Use fresh sessions for prompts likely to be refused.
- **Long-running session approaching 1.5M chars** — refresh proactively.
- **Long pauses (> 24 hr)** — `mentor_session_token` expires after 24 hr TTL. Start fresh.

## Throughput estimate

| Pattern | Fresh per batch | Warm session |
|---|---|---|
| 13-batch Portal dispatch | ~85 min wall-clock | ~15-20 min |
| 69-batch Core dispatch | ~135 min (capped) | ~30-40 min |
| Per-batch overhead | 3-5 min summary + work | ~30 sec setup + work |

## Citations

- B1 bug report: `/data/bug_reports/B1.md`
- Memory: `[[odc_mcp_session_context_wall]]` for the 1.5M char ceiling
- Memory: `[[odc_mcp_publish_lifecycle]]` for publish_start field shapes (snake_case)
- Memory: `[[odc_mcp_publish_studio_warmup]]` for MCP-app_create skipping the Studio warmup wall (separate from this session warmup)
