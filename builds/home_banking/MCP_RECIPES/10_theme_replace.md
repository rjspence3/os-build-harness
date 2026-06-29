# Recipe 10 — Theme (replace stylesheet with custom CSS)

## Purpose

Replace the app's theme stylesheet with custom CSS — typically:

- Brand colors (`--color-primary`, `--color-secondary`, `--color-accent`)
- Custom font face (loaded from CDN or self-hosted via Resource)
- Component-specific overrides (account cards, sidebar, popups)
- Dark mode rules (gated on `:root[data-theme="dark"]`)

The theme is the largest CSS payload in any app (Home Banking themes are 28-30 KB each). This recipe replaces the WHOLE stylesheet; for incremental edits, just write the new CSS verbatim.

## When to use

- First-time theme replacement (fresh app)
- Brand refresh (full CSS rewrite)
- Adding dark mode support

For per-screen StyleSheet edits, set `screen.StyleSheet` directly (see Recipe 09 example).

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{THEME_NAME}}` | Theme block name (usually `CustomStyleTheme`) | `CustomStyleTheme` |
| `{{CSS_CONTENT}}` | Full stylesheet CSS as a string literal | (paste from `theme-portal.css`) |
| `{{IS_DEFAULT}}` | Whether to set as app's default theme | `true` |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    // Empirical (T1.2, 2026-05-27): the IESpace API is `MobileThemes` and
    // `CreateMobileTheme` — NOT `Themes` / `CreateTheme`. This is true even
    // for WebApplication apps in ODC (the new Web stack is built on the
    // Mobile-prefixed surface). Recorded in [[odc_mcp_mobile_prefixed_api]].
    var theme = eSpace.MobileThemes.FirstOrDefault(t => t.Name == "{{THEME_NAME}}")
        ?? eSpace.CreateMobileTheme("{{THEME_NAME}}");

    // Replace the stylesheet. Per [[odc_mcp_theme_stylesheet_setter_same_call_read]],
    // the write-through to OML works but the getter returns pre-write snapshot in
    // the same applyModelApiCode call. Verify in a SECOND call if needed.
    theme.StyleSheet = @"{{CSS_CONTENT}}";

    if ({{IS_DEFAULT}}) {
        eSpace.DefaultMobileTheme = theme;
    }

    Console.WriteLine($"Recipe 10: {{THEME_NAME}} | Created: theme (default={ {{IS_DEFAULT}} }) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.UI.Mobile
```

## Expected stdout

```
Recipe 10: CustomStyleTheme | Created: theme (stylesheet=28341 chars, default=True) | Status: OK
```

## Common failures

### ✗ Stylesheet getter returns empty / stale after write

Cause: per `[[odc_mcp_theme_stylesheet_setter_same_call_read]]`, the same-call read of `theme.StyleSheet` returns the pre-write snapshot. The write IS persisted to OML.
Fix: don't read back in the same call. Verify with a separate `applyModelApiCode` call after a brief wait.

### ✗ `@import url(...)` strips on publish

Cause: per `[[odc_publish_strips_css_import]]`, CSS `@import` rules are stripped during the publish step. Common with external fonts.
Fix: replace `@import` with `@font-face` declarations referencing CDN URLs, OR self-host the font via `eSpace.CreateResource` and reference the runtime path. Per `[[odc_mcp_resource_api]]`.

### ✗ Custom CSS classes don't apply

Cause: forgot `CustomStyle` vs `Style` distinction per `[[odc_mcp_style_vs_customstyle]]`. `Style` is the `class="..."` attribute; `CustomStyle` is the inline `style="..."`.
Fix: define class rules in the theme + use `widget.SetStyle("class-name")` to attach. Inline declarations go via `widget.CustomStyle = "..."`.

### ✗ Theme replaced but dark mode doesn't trigger

Cause: CSS rules like `:root[data-theme="dark"] { ... }` are necessary but not sufficient — also need Layout-OnReady JS to read user pref + set the `data-theme` attribute.
Fix: per `[[odc_dark_mode_needs_js_toggle]]`, inject JS in Layout block's OnReady action.

## Example: replace theme with Home Banking Portal stylesheet

```yaml
THEME_NAME: CustomStyleTheme
CSS_CONTENT: (paste contents of apps/home_banking/theme-portal.css — ~28 KB)
IS_DEFAULT: true
```

The full Portal CSS is captured at `apps/home_banking/theme-portal.css` (28 KB). It includes:

- Brand variables (`--color-primary: #040d3f`, Sora font face)
- Account card styles (`.account-card.checking`, `.account-card.saving`, etc.)
- Floating AI chat button (`.float-chat-btn`)
- Demo access cookie popup (`.demo-access-popup`)
- Mobile-responsive breakpoints (`@media (max-width: 430px)` etc.)
- Dark mode neutral palette swaps

## Memory refs

- [[odc_mcp_theme_stylesheet_setter_same_call_read]] — write succeeds, same-call read stale
- [[odc_publish_strips_css_import]] — `@import` stripped at publish
- [[odc_dark_mode_needs_js_toggle]] — CSS alone insufficient
- [[odc_mcp_style_vs_customstyle]] — class vs inline-style assignment
- [[odc_mcp_resource_api]] — self-hosting fonts/images via CreateResource
- [[inline_styles_bypass_outsystems_ui_specificity]] — when class-based fails

## Related recipes

- [01_entity_server](./01_entity_server.md) — independent (themes have no entity deps)
- [09_screen_dashboard](./09_screen_dashboard.md) — dashboards typically need theme polish
- [11_default_screen](./11_default_screen.md) — wire DefaultScreen after theme is in place
