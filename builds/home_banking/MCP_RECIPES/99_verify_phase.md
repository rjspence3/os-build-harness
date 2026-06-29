# Recipe 99 — Phase Verification

**Purpose**: Inter-phase verification probes that confirm published OML state matches expected state before the next phase dispatches. Replaces "trust Mentor's Status: OK output" with "verify against OS-side context_search / app_refs."

**Usage**: Call after every phase's final publish, BEFORE the next phase's first dispatch. If verification fails, HALT — do not proceed (see DISPATCH_PLAYBOOK.md halt conditions).

## Variants

### 99_verify_refs

After Phase 0 (references). MCP-only — no Mentor session needed.

```
app_refs({key: <APP>})
```

Pass: every required producer name appears in `references[]`.
Fail: any missing → HALT.

### 99_verify_entities

After Phase 1 (entities).

```
For each entity in manifest:
  context_search({
    query: <EntityName>,
    objects: ["Entities"],
    app: <APP_NAME>,
    search_type: "full-text"
  })
```

Pass: each entity returned, isPublic=true.
Fail: missing entity → HALT.

### 99_verify_actions

After Phase 2 (actions).

```
For each action in manifest:
  context_search({
    query: <ActionName>,
    objects: ["Actions"],
    app: <APP_NAME>,
    search_type: "full-text"
  })
```

Note: context_search cache lag ~30s after publish. If first check returns empty, wait 30s and retry. Data presence in result = success (don't trust isPublic field — it may be stale).

### 99_verify_blocks

After Phase 3 (custom blocks).

```
For each block in APP_BLOCK_WHITELIST:
  context_search({
    query: <BlockName>,
    objects: ["Blocks"],
    app: <APP_NAME>,
    search_type: "full-text"
  })
```

### 99_verify_theme

After Phase 4 (theme). Probe via applyModelApiCode:

```csharp
eSpace => {
    var theme = eSpace.MobileThemes.FirstOrDefault(t => t.Name == "{{THEME_NAME}}");
    if (theme == null) { Console.WriteLine("FAIL: theme not found"); return; }
    Console.WriteLine($"Theme {{THEME_NAME}}: CSS length = {theme.StyleSheet.Length} chars");
    Console.WriteLine($"DefaultMobileTheme matches? {eSpace.DefaultMobileTheme == theme}");
}
```

Pass: StyleSheet.Length within ±5% of expected (e.g. 35KB Banking theme → expect 33-37K).

### 99_verify_screens

After Phase 5 (screens).

```
context_screens({app: <APP_NAME>})
```

Pass: every screen in manifest is in result. Login + InvalidPermissions have `roles:[]` and `AnonymousAccess:true`. Other screens have the expected role.

Fail: missing screen OR Login still gated → HALT.

### 99_verify_chrome

After Phase 6 (chrome wrap). Probe via applyModelApiCode:

```csharp
eSpace => {
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "MainFlow");
    if (flow == null) { Console.WriteLine("FAIL: MainFlow not found"); return; }
    foreach (var screen in flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()) {
        var biCount = screen.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget>().Count();
        Console.WriteLine($"Screen {screen.Name}: {biCount} BlockInstance widgets");
    }
}
```

Pass: each screen has at least N BlockInstance widgets (compare against `chrome_wrap_manifest` count from renderer output).

Fail: zero BlockInstance widgets on a screen that should have N → HALT.

### 99_verify_runtime

After Phase 7 (DefaultScreen + final publish).

```
env_app({env_key, application_key: <APP>})
```

Capture the runtime URL.

**Manual step**: visit the URL in a browser.
- Pass: app shows the DefaultScreen (or Login if DefaultScreen is role-gated)
- Fail: shows `_error.html` → HALT, run runtime diagnostics

If `_error.html`: check that DefaultScreen is anonymous-accessible. If not, dispatch a quick fix turn that clears roles + sets AnonymousAccess on DefaultScreen (or sets DefaultScreen = Login if Dashboard requires auth).

## Halt protocol

When any verification fails:
1. Capture verbatim error
2. Identify which phase the failure traces to
3. Do NOT proceed to next phase
4. Either:
   - Fix the renderer/recipe so the next dispatch produces correct state (preferred)
   - Document the wall as a framework gap in GAPS.md (if recipe can't fix)

Never "skip past" a verification failure. The cascade compounds errors.

## Related

- `[[DISPATCH_PLAYBOOK]]` — calls these between every phase
- `[[FRAMEWORK_REVIEW]]` — why verification is the linchpin (state desync was a recurring failure mode)
- `[[odc_mcp_context_entities_cache_lag]]` — context_search lag pattern
