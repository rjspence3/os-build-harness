# Capture Playbook — Pull Captures from Any Source App

**Purpose**: Systematically extract entities, actions, screens, blocks, and theme CSS from a source OutSystems app via Mentor probes. Output: `.tree.md` and `.yaml` files ready for the renderer to consume.

**Audience**: Claude (in main context) driving the capture. Or a subagent ONLY if the prompt strictly enforces the per-block-per-turn pattern below.

**When to use**: Bootstrapping a new app to clone. Banking was the test case; this playbook generalizes.

## Empirical capture rules (from this session's painful learnings)

1. **`getScreen` returns 277K-char dumps** on complex screens — Mentor's session synthesis can't handle. Use direct `applyModelApiCode` walking `IMobileScreen` instead.

2. **Per-block-per-turn**: stdout truncates at ~29K chars. Batching multiple blocks per turn drops some silently. One block per turn = one capture per file.

3. **Mentor narrative synthesis tax: 60-180s per turn AFTER applyModelApiCode returns.** Workaround: call `mentor_cancel(runId)` immediately after `tool_end` event — session stays alive, narrative phase skipped.

4. **Sandbox import allowlist**: `System`, `System.Linq`, `OutSystems.Model.*`, `ServiceStudio.Plugin.*` ONLY. `System.Collections.Generic` BLOCKED. `System.Collections.IEnumerable` BLOCKED. Use typed arrays via `.ToArray()`.

5. **Correct widget interface**: `OutSystems.Model.UI.Mobile.Widgets.IMobileWidgetSignature` (NOT `IMobileWidget`).

6. **ParsedExpression values**: Read `.DisplayName` via reflection for clean source text (NOT `.ToString()` which yields ugly suffixes like `[ValueExpression[ServiceStudio.Expressions.AbstractExpression]]`).

7. **Warm-session pattern**: First turn pays ~70s get_app_summary; resume turns skip it. Use mentor_session_id + mentor_session_token from prior terminal result.

## The proven capture recipe (validated 2026-06-09)

### For blocks

```csharp
eSpace => {
    var block = eSpace.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileBlock>()
        .FirstOrDefault(b => b.Name == "{{BLOCK_NAME}}");
    if (block == null) { Console.WriteLine("FAIL: block not found"); return; }
    
    Console.WriteLine($"=== Block: {{BLOCK_NAME}} ===");
    Console.WriteLine($"Input parameters:");
    foreach (var ip in block.InputParameters) {
        Console.WriteLine($"  - {ip.Name}: {ip.DataType} (mandatory={ip.IsMandatory})");
    }
    
    Console.WriteLine($"Widget tree:");
    var allWidgets = ((OutSystems.Model.IModelObject)block)
        .GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.Widgets.IMobileWidgetSignature>()
        .ToArray();
    
    foreach (var w in allWidgets) {
        // Walk parent chain for depth
        int depth = 0;
        OutSystems.Model.IModelObject node = ((OutSystems.Model.IModelObject)w).Parent;
        while (node != null && !(node is OutSystems.Model.UI.Mobile.IMobileBlock)) {
            depth++;
            node = node.Parent;
        }
        string indent = new string(' ', depth * 2);
        
        // Type detection by GetType().Name (interfaces like IMobileBlockInstance don't exist)
        string typeName = w.GetType().Name;
        string extra = "";
        if (typeName == "WebBlockInstance") {
            // BlockInstance — capture source_block via reflection
            var srcProp = w.GetType().GetProperty("SourceBlock") ?? w.GetType().GetProperty("SourceWebBlock");
            var src = srcProp?.GetValue(w);
            if (src != null) extra = $" src={(src as dynamic)?.Name ?? "(unknown)"}";
        } else if (typeName == "Container") {
            // Container — capture Style/CustomStyle via reflection's .DisplayName
            var styleProp = w.GetType().GetProperty("Style");
            var styleVal = styleProp?.GetValue(w);
            var displayName = styleVal?.GetType().GetProperty("DisplayName")?.GetValue(styleVal);
            if (displayName != null) extra = $" style={displayName}";
        }
        // Text widgets, Expressions, etc — extend similarly
        
        Console.WriteLine($"{indent}- {w.Name}: {typeName}{extra}");
    }
}
```

### For screens

Same pattern but search `IMobileScreen.FirstOrDefault(s => s.Name == "{{SCREEN_NAME}}")` and walk widgets within. Note: action-flow ancestors (`ClientScreenActionFlow`, `DataScreenActionFlow`) appear in the descendants list — filter them out.

### For actions (LOGIC body capture — needed for Recipe 05a)

```csharp
eSpace => {
    var action = eSpace.ServiceActions.FirstOrDefault(a => a.Name == "{{ACTION_NAME}}")
        ?? eSpace.ServerActions.FirstOrDefault(a => a.Name == "{{ACTION_NAME}}");
    if (action == null) { Console.WriteLine("FAIL: action not found"); return; }
    
    Console.WriteLine($"=== Action: {{ACTION_NAME}} ===");
    Console.WriteLine($"Inputs:");
    foreach (var ip in action.InputParameters) Console.WriteLine($"  - {ip.Name}: {ip.DataType}");
    Console.WriteLine($"Outputs:");
    foreach (var op in action.OutputParameters) Console.WriteLine($"  - {op.Name}: {op.DataType}");
    
    Console.WriteLine($"Nodes (flow):");
    foreach (var node in action.Nodes.ToArray()) {
        string typeName = node.GetType().Name;
        Console.WriteLine($"  - {typeName}: {node.Name}");
        // Per-type details: Assign target+value, ExecuteAction.Action, If.Condition, etc.
    }
}
```

## Dispatch pattern

```
1. mentor_start (warm session — first turn with app_key, rest resume)
2. Wait 30s, mentor_get_run, capture stdout from tool_end event
3. IMMEDIATELY: mentor_cancel(runId) ← skip narrative synthesis
4. Parse stdout into .tree.md format, write to data/MCP_RECIPES/apps/<app>/_raw/
5. Next capture
```

Estimate: 1-2 minutes per capture in warm session. 30 blocks + 5 screens = ~60 min for a full app like Banking Portal.

## Output file naming

| Source | Output filename |
|---|---|
| Screen `Dashboard` of app `home_banking_portal` | `portal-dashboard.tree.md` |
| Block `LayoutTopMenuLeftSide` | `LayoutTopMenuLeftSide.block.tree.md` |
| Action `SubmitTransfer` (with body) | `SubmitTransfer.action.tree.md` |
| Theme CSS | `theme-<app_kind>.css` |

## Discovery phase (before capture)

Use context_search to enumerate scope:

```
context_search({query: "*", objects: ["Screens"], app: <APP>, search_type: "full-text", limit: 100})
context_search({query: "*", objects: ["Blocks"], app: <APP>, search_type: "full-text", limit: 100})
context_search({query: "*", objects: ["Actions"], app: <APP>, search_type: "full-text", limit: 100})
app_refs({key: <APP>})
context_themes({app: <APP>})
```

Output to `SCOPE.md` per app. Now you know what to capture.

## Manifest derivation (after capture)

For each captured `.tree.md`, generate a manifest entry. Could be:
- Manual: read the captured tree, write the YAML entry
- Programmatic: a `derive_manifest.py` script that parses `_raw/` and emits `screens.yaml` / `actions.yaml` / `entities.yaml` (NOT YET BUILT — future P2 work)

Until programmatic, hand-edit the manifest YAMLs to match captures.

## Failure modes

| Failure | Symptom | Fix |
|---|---|---|
| `getScreen` returns 277K dump | Mentor stalls 15+ min | Use direct applyModelApiCode walk (see proven recipe above) |
| Stdout truncation | Capture cuts off mid-tree | One block per turn — don't batch |
| Mentor narrative stall | 5-15 min per turn after tool_end | mentor_cancel immediately after tool_end |
| Reflection returns null on SourceBlock | `src=` field empty in captures | Try `SourceWebBlock` as alternate property name; or fall back to "(unnamed)" + manual fix |
| `IEnumerable` validation block | CS-error on collection types | Use `.ToArray()`, iterate as typed array |
| Wrong namespace | CS0234 on `IMobileWidget` | Use `OutSystems.Model.UI.Mobile.Widgets.IMobileWidgetSignature` |

## Related

- `[[WARM_SESSION_DISPATCH]]` — session resume pattern
- `[[odc_mcp_session_context_wall]]` — 1.5M char session limit + getScreen 277K stall
- `[[odc_mcp_addreferencetoelements_silent_noop]]` — captures don't need this, but dispatch does
- `[[DISPATCH_PLAYBOOK]]` — what to do AFTER captures land
- `[[FRAMEWORK_REVIEW]]` — capture playbook is P2 gap; this doc closes it
