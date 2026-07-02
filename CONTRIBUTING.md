# Contributing

Thanks for your interest in improving the harness. This is a curated extract of a working
lab, so a few conventions keep it coherent. If anything here is unclear or wrong, open an
issue — that's a contribution too.

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest tests/ -q          # → 213 passed
```

No tenant is needed for development: the renderers are **pure** (AST → C# string), so the
whole unit suite runs offline with no live Mentor dispatch. New to the project? Read
[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) and
[`HARNESS_DECISIONS.md`](HARNESS_DECISIONS.md) first.

## Keep the suite green

`pytest tests/ -q` must pass before you push. Because the renderers are pure, a behavior
change shows up as a changed C# string — so when you change a renderer **on purpose**, update
the asserting test in the same commit, and say *why* in the test comment (the existing tests
cite the live finding or OML error that drove each shape — match that style). Don't loosen an
assertion to make red go green; that erases a hard-won invariant.

## Where things belong

- **Shared build doctrine** → `harness/CLAUDE.md`. It is `@import`ed by every build's
  `CLAUDE.md`. Don't duplicate doctrine into a build root.
- **Build-specific notes** (quirks, approved deviations, known ODC walls for *that* app) →
  `builds/<app>/CLAUDE.md` only.
- **The recipe library** (`builds/home_banking/MCP_RECIPES/`) is the debugged, hard-won plan.
  Treat a recipe as load-bearing: "improving" one often reintroduces a wall it was shaped to
  avoid. Change a recipe only with a clear reason and, ideally, a live re-validation note.
- **Vendored code** (`harness/cdp_helpers.py`, `assets/`) carries a provenance header / its own
  upstream license. Sync from upstream rather than diverging silently.

## Adding a build

Mirror the existing layout — don't hardcode `home_banking`:

```bash
harness/launch_build.sh <app> <spec-path>   # scaffolds builds/<app>/ from _template
```

For a spec-driven build, start from the validated example and check it as you go:

```bash
cp examples/task_tracker/app_spec.json builds/<app>/spec/app_spec.json
harness-verify builds/<app>/spec/app_spec.json --phase spec
```

See [`builds/_template/README.md`](builds/_template/README.md) and
[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md).

## Code style

- Match the surrounding code — naming, comment density, and idiom. The house style favors
  **complete words** over abbreviations and comments that explain *why* (a live finding, an
  OML error, a non-obvious caveat), not *what*.
- Renderers stay **pure and offline-testable** — no network or live MCP calls in
  `harness/banking_runner/`. Live concerns live in the CLIs / capture scripts.
- Don't commit secrets. `.env` is gitignored; put tenant/credentials there, never in code or
  the recipe library. Use placeholder identifiers (`your-tenant.outsystems.dev`) in docs.

## Pull requests

1. Branch off `main`.
2. Keep the change focused; update docs and tests alongside code.
3. Run `pytest tests/ -q` (green) and, if you touched a spec or the schema,
   `harness-verify examples/task_tracker/app_spec.json --phase spec` (PASS).
4. In the PR description, explain the *why* and note any live re-validation you did against a
   tenant (or that the change is offline-only).

## Reporting blockers / bugs

If you hit a genuine ODC/MCP limitation while building, that's a **wall** — the doctrine in
`harness/CLAUDE.md` describes the format and the escalation protocol. For harness bugs (the
Python tooling itself), open an issue with the failing command and its output.
