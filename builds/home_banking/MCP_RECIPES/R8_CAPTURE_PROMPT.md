# R8 — Strict screen-capture prompt (deterministic dialect)

## Why this exists

The original R8 captures were produced by free-form Mentor synthesis prompts
("describe this screen's widget tree"). Mentor formatted the output
differently per call, producing **three incompatible dialects**:

| Dialect | SourceBlock form | If form | Placeholder form | Path segments | Coverage |
|---|---|---|---|---|---|
| **A** | `SourceBlock="X"` | `If` | `Placeholder 'X'` (path) / `PLACEHOLDER` (marker) | numeric + T/F/I/L | clean |
| **B** | `Source=X` (bare) | `IfWidget` | `[Placeholder 'X']` (bracketed) | numeric + H/M/S/C/T/F | clean |
| **C** | `'Name' (X)` (parens) | `IfWidget` | `[Icon]` `[True]` `[False]` markers | mix of bracketed word-paths + **unbracketed indent lines** | **degrades** |

Dialects A and B parse cleanly (`tree_parser.py` handles both). Dialect C
mixes bracketed and unbracketed widget lines, so a path-based parser can only
see a fraction (personalloan: 12 of 295 widget lines = 4% coverage).

The fix is NOT a smarter parser — it's a **deterministic capture contract**.
This prompt forces Mentor to emit Dialect A every time. Re-capture any
low-coverage screen with this prompt.

## Which screens need re-capture

Run `parse_coverage()` (in `tree_parser.py`) on every `_raw/*.tree.md`. Any
file below 0.9 coverage needs re-capture. Currently:

- `portal-personalloan.tree.md` — 0.04
- `backoffice-personalloanofferletter.tree.md` — 0.70

## The capture prompt (send via `mentor_start`)

> Inspect the screen named `{{SCREEN_NAME}}` in this app. Output its widget
> tree as plain text following EXACTLY this format — do not add prose, do not
> summarize, do not collapse single-child containers:
>
> ```
> === Screen: {{SCREEN_NAME}} ===
> Inputs: <Name>:<DataType> [(mandatory)], ... | (none)
> Locals: <Name>:<DataType> [(default=<value>)], ... | (none)
> Aggregates: <Name> (source=<Entity>), ... | (none)
> --- WIDGETS (hierarchical) ---
> [<path>] <WidgetType> '<Name>'|(unnamed) <Prop>="<value>" <Prop>=null ...
>   [<path>.<n>] <ChildType> ...
> ```
>
> STRICT RULES:
> 1. Every widget MUST have a `[path]` prefix. The root is `[1]`. Children are
>    `[1.1]`, `[1.2]`, `[1.1.1]`, etc. NEVER emit a widget line without a
>    numeric `[path]` prefix.
> 2. Use numeric path segments only. Do NOT use word segments like
>    `[1.Header]` or letter shorthand like `[1.M.1]`. If a widget sits in a
>    named placeholder, still give it a numeric path and record the
>    placeholder name as a property: `PlaceholderName="Header"`.
> 3. For block instances, write `BlockInstance '<Name>' SourceBlock="<Source>"`.
>    Always use the `SourceBlock="..."` form with double quotes. Never `(X)`
>    or `Source=X`.
> 4. For conditionals, write `If '<Name>'|(unnamed) Condition="<expr>"`. Use
>    `If`, never `IfWidget`. Put the true-branch children under paths
>    `[<path>.T.1]`, `[<path>.T.2]`; false-branch under `[<path>.F.1]`, etc.
> 5. For block-instance input parameters, write them as properties on the
>    BlockInstance line: `BlockInstance 'X' SourceBlock="Y" ParamA="v1" ParamB="v2"`.
>    Do NOT use a separate `Args:` line.
> 6. Properties to always include when set: `Text`, `Value`, `Style`,
>    `CustomStyle`, `Source`, `Condition`, `Visible`, `Width`, `List`,
>    `Labels`, `Values`, `Variable`. Events: `OnClick=<Handler>` or
>    `OnClick→Destination=<Screen>`.
> 7. Indent children by 2 spaces per level. Indentation is cosmetic — the
>    `[path]` is the source of truth.
>
> Output ONLY the formatted block, nothing before or after.

## Verification after re-capture

```python
from pipeline.banking_runner.tree_parser import parse_coverage
cov = parse_coverage(open("portal-personalloan.tree.md").read())
assert cov["coverage"] >= 0.9, cov
```

Then move the filename from `DIALECT_C_CAPTURES` to `CLEAN_CAPTURES` in
`tests/test_tree_parser.py` and re-run the suite.

## Memory refs

- [[odc_mcp_r8_capture_dialect_drift]] — the non-determinism finding + fix
- [[mentor_phantom_authoring]] — trust runtime artifact over chat narration
