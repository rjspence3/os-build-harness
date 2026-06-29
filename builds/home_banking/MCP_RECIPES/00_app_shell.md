# Recipe 00 — App Shell (composite)

**Purpose**: Create the app's coherent shell as a single coordinated dispatch — theme + layout wrapping + default screen pointer + Login as anonymous landing. After this recipe lands, every subsequent dispatch builds INTO this shell rather than producing free-floating fragments.

**When to use**: First recipe dispatched after `app_create` + references setup. Before any other screen/block/action dispatch.

**Why composite**: theme, layout block, default screen, and Login form a gestalt. Authoring them in separate dispatches creates a temporary in-between state where the app has no entrypoint and runtime URL errors. This recipe authors them atomically.

## Required prior state

- App created via `app_create` (assetKey known)
- Phase 0 references already added via `addReferenceToElements` (OS UI minimum; HBCore/Charts/Agents/AppsCommon as needed). Cache-warmed per chrome_wrap v9 IMPORT PREREQUISITES.
- MainFlow may or may not exist (recipe creates it self-healing if missing)

## What this recipe does

1. **Theme** — `eSpace.CreateMobileTheme("{{THEME_NAME}}")` + `.StyleSheet = {{CSS_VERBATIM}}` + `eSpace.DefaultMobileTheme = theme`
2. **Login screen** — `flow.CreateScreen("Login")` with `AnonymousAccess=true` + `Roles.Clear()` — anonymous entrypoint
3. **DefaultScreen** — `eSpace.DefaultScreen = login` initially (replaced post-Dashboard-author)
4. **MainFlow guard** — creates flow if missing (greenfield MCP-create apps lack MainFlow)

Subsequent recipes can rely on these existing.

## C# body

```csharp
eSpace => {
    // ─── App Shell Recipe 00 ─────────────────────────────────────────────
    
    // ─── Step 1: Ensure MainFlow exists ─────────────────────────────────
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "MainFlow");
    if (flow == null) { 
        flow = eSpace.CreateMobileFlow("MainFlow"); 
        Console.WriteLine($"Created MobileFlow MainFlow"); 
    }
    
    // ─── Step 2: Theme ──────────────────────────────────────────────────
    var existingTheme = eSpace.MobileThemes.FirstOrDefault(t => t.Name == "{{THEME_NAME}}");
    if (existingTheme != null) existingTheme.Delete();
    var theme = eSpace.CreateMobileTheme("{{THEME_NAME}}");
    theme.StyleSheet = @"{{CSS_VERBATIM}}";
    eSpace.DefaultMobileTheme = theme;
    Console.WriteLine($"Theme: {{THEME_NAME}} created ({theme.StyleSheet.Length} chars CSS)");
    
    // ─── Step 3: Login screen (anonymous entrypoint) ─────────────────────
    var existingLogin = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "Login");
    if (existingLogin != null) existingLogin.Delete();
    var login = flow.CreateScreen("Login");
    login.Roles.Clear();
    login.AnonymousAccess = true;
    Console.WriteLine($"Login screen created (anonymous, roles cleared)");
    
    // ─── Step 4: DefaultScreen → Login initially ─────────────────────────
    // After Dashboard is authored in a later recipe, set DefaultScreen = Dashboard.
    eSpace.DefaultScreen = login;
    Console.WriteLine($"DefaultScreen set to Login");
    
    Console.WriteLine($"Recipe 00: App shell ready | Status: OK");
}
```

## Required imports

```
- System.Linq
- OutSystems.Model
- OutSystems.Model.UI.Mobile
```

## Verification

After publish:
```
context_screens({app: "{{APP_NAME}}"}) — should show Login with roles:[] and AnonymousAccess:true
app_info({key: "{{APP_KEY}}"}) — should show rev bump
```

Then visit runtime URL — should show Login screen (anonymous), not _error.html.

## Followup recipes

After 00 lands:
- Recipe 01/02: entities
- Recipe 04: actions (stubs initially)
- Recipe 06: custom blocks (layout blocks FIRST — they wrap screens)
- Recipe 07: remaining screens (dechromed; renderer auto-applies role gate for non-anon screens)
- Recipe 23: chrome wrap (replaces dechromed Container markers with BlockInstance widgets)
- Recipe 10 if theme is large enough to need chunked dispatch
- Recipe 11 to re-point DefaultScreen = Dashboard (or your main view)

## Related
- `[[odc_mcp_app_create_no_mainflow]]` — greenfield MCP apps lack MainFlow
- `[[mentor_auto_applies_role_filter_to_new_screens]]` — Mentor adds role to every new screen; this recipe overrides for Login
- `[[odc_mcp_publish_lifecycle]]` — publish_start lifecycle after this recipe
