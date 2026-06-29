# Build template

The starting skeleton for a new build root. **You normally don't copy this by hand** —
`harness/launch_build.sh <app> [spec-path]` does it for you: it creates
`builds/<app>/` with `spec/` and `out/`, renders `CLAUDE.md` from this template
(substituting `<APP_NAME>`), seeds an empty `WALLS.md`, copies your spec into `spec/`,
and starts a Claude Code session in the new build root.

```bash
# scaffold builds/my_app/ from a validated spec and launch the build session
harness/launch_build.sh my_app examples/task_tracker
```

What ends up in a build root:

| Path | Purpose |
|---|---|
| `CLAUDE.md` | This build's doctrine. `@import`s `harness/CLAUDE.md` (shared loop) + app-specific notes. |
| `spec/` | The source of truth (an `app_spec.json` for a spec-driven build). |
| `out/` | Build output. |
| `WALLS.md` | Blockers log, in the format the wall-cap hook counts (see `harness/CLAUDE.md`). |

Keep **shared** doctrine out of a build's `CLAUDE.md` — it lives in `harness/CLAUDE.md`
and is imported. Put only app-specific quirks, approved deviations, and known ODC walls
for *this* app in the build's `CLAUDE.md`.

See [`docs/GETTING_STARTED.md`](../../docs/GETTING_STARTED.md) for the full walkthrough.
