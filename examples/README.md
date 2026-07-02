# Examples

## `task_tracker/app_spec.json`

A minimal but **complete** spec-driven build input: a two-screen task tracker
(`TaskList` → `Task`) with roles, navigation, capabilities, and acceptance assertions.

Unlike the illustrative excerpt embedded in
[`harness/schemas/app_spec.v0.json`](../harness/schemas/app_spec.v0.json) (which
intentionally references a screen it never defines and so *fails* full verification),
this example has no cross-reference holes — it passes the offline spec check:

```bash
harness-verify examples/task_tracker/app_spec.json --phase spec
#   → PASS — app_spec.json conforms to app_spec.v0 (schema + cross-refs).
```

Use it as the starting point for your own spec (see
[`docs/GETTING_STARTED.md`](../docs/GETTING_STARTED.md), Path A):

```bash
mkdir -p builds/my_app/spec
cp examples/task_tracker/app_spec.json builds/my_app/spec/app_spec.json
# edit, then re-validate as you go:
harness-verify builds/my_app/spec/app_spec.json --phase spec
```

## Verifying a *built* app (`--phase live`)

Once you've actually built the app, `--phase live` checks it against each screen's
acceptance assertions. It is **snapshot-fed**: the orchestrator (your Claude Code
session) fetches live state via the MCP and passes it in — the judge never opens its
own MCP client, and never returns a silent pass. Two saved snapshots ship with this
example:

- **`live_entities.json`** — the shape of a `context_entities` MCP response (drives
  `entityExists` / `attribute`).
- **`live_screens.json`** — a structured `applyModelApiCode` screen-walk (the contract
  for `componentPresent` / `binding` / `navigates`).

Both match `app_spec.json`, so all 9 live assertions pass:

```bash
harness-verify examples/task_tracker/app_spec.json --phase live \
  --entities examples/task_tracker/live_entities.json \
  --screens examples/task_tracker/live_screens.json
#   → 9x [pass] … exit 0
```

Change a `dataType` in `live_entities.json` (or a `toScreen` in `live_screens.json`) and
re-run — the verifier reports a real `[fail]` (exit 1). With no `--entities`/`--screens`
it's inconclusive (exit 3), never a false pass. In a real build, your session produces
these two files from the live app via the MCP.
