# Recipe 27 — Theme-Anchoring an OS Element

**Purpose**: style an element so it ANCHORS to the theme — responds to the
theme's responsive classes + design tokens + dark mode — instead of being frozen
by a static literal or inline hardcoded CSS. This is the difference between a
clone that looks right and one that *stays* right when the theme moves
(see the theme-anchoring rule in `DISPATCH_PLAYBOOK.md`).

Harvested via Beat 0 (Mentor, verified against HomeBankingPortal4 rev 44,
2026-06-12). Session `a41d22a0`.

## The mechanism (Model API)

| Widget type | Setter | Read-back |
|---|---|---|
| `IContainer`, `IExpression`, `IButton` | **`w.SetStyle(<expr-string>)`** | `w.Style` (IExpression, read-only — cannot assign) |
| `ITextWidget`, text-only widgets | **`w.SetStyleClasses(<expr-string>)`** | `w.StyleClasses.Text` |

- The argument is the **OutSystems expression source text** — exactly what you'd
  type in the Studio Style editor — passed as a C# string. `ExpressionDefinition`
  converts implicitly from `string`, so a raw string works; `ExpressionDefinition.Parse(...)`
  is equivalent.
- **Escaping**: CSS class names are STRING LITERALS in the expression, so their
  double-quotes escape as `\"` in the C# string. A bare identifier (no quotes)
  is read as a VARIABLE name, not a class — this is the #1 mistake.
- `If(...)`, `IsDesktop()`, and other built-in client functions are written
  **verbatim** — always in scope, no reference/import.

## Static class (simplest anchor)
```csharp
container.SetStyle("\"balance-cntr\"");          // OS expr: "balance-cntr"
textWidget.SetStyleClasses(ExpressionDefinition.Parse("\"hb-icon\""));  // V22 icon fix
```

## Conditional class (responsive anchor — the one the renderer was dropping)
```csharp
// OS expr: If(IsDesktop(), "display-flex justify-content-space-between", "display-grid gap-s")
c9.SetStyle("If(IsDesktop(), \"display-flex justify-content-space-between\", \"display-grid gap-s\")");
```
Locate the container first:
```csharp
var dashboard = eSpace.MobileFlows.Named("MainFlow")
    .Nodes.OfType<OutSystems.Model.UI.Mobile.IMobileScreen>().Named("Dashboard");
var c9 = dashboard.Widgets.OfType<ServiceStudio.Plugin.NRWidgets.IContainer>()
    .First(w => w.Name == "c9");
```

## The renderer bug this fixes (screen_renderer.py `_apply_props`)
The renderer emits only the STATIC leading literal and drops the conditional
suffix (line ~870: "Style conditional suffix dropped — LOGIC phase"). The
original's layout/theme anchoring IS that conditional, so the clone renders a
single column with the theme inert. **Fix**: emit the FULL captured Style
expression verbatim via `SetStyle("<expr>")` — conditionals included — not the
degraded literal. The expression text is already in the `.tree.md` captures
(e.g. `portal-dashboard.tree.md`).

## Do / Don't
- DO anchor via `SetStyle`/`SetStyleClasses` with theme classes + `var(--token)`s.
- DON'T set inline `CustomStyle` with literal colors/px — it won't flip in dark
  mode (`inline_colored` metric flags these; the dark-mode-flip test catches them).
- DON'T drop conditional Style expressions — the conditional is the anchor.
- The class must EXIST in the theme; if missing, capture+inject it (hb-icons /
  layout-utility precedent) — anchoring to an absent class renders nothing.

## Validation
1. CDP gate `inline_colored` near 0.
2. dark-mode-flip test: toggle `.dark-mode`, confirm the element's computed color changes.
3. The element's runtime `class` attribute carries the expected theme class(es).
