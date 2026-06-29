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
