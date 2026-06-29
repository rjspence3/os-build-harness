# Recipe 24 — Navigation Wiring

**Purpose**: Wire screen-to-screen routing — Button OnClick → Navigate to target screen with input parameter bindings. Without this, screens render but the app isn't navigable.

**When to use**: After Phase 5 (screens) + Phase 6 (chrome wrap). Per-button-with-navigation.

## Grammar (manifest extension)

Add to `screens.yaml`:

```yaml
- name: Dashboard
  uiflow: MainFlow
  capture: portal-dashboard.tree.md
  navigation:
    - widget_name: TransferButton           # widget Name in the screen's tree
      target_screen: Transfer
      target_uiflow: MainFlow               # optional (same flow if omitted)
      input_bindings:                       # NEW — bind target screen's inputs
        - param: AccountId
          value: "GetAccounts.List.Current.Id"
    - widget_name: ViewRequestsLink
      target_screen: Requests
      input_bindings: []
```

## C# body

```csharp
eSpace => {
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{{FLOW_NAME}}");
    if (flow == null) { Console.WriteLine("FAIL: MainFlow not found"); return; }
    var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{SCREEN_NAME}}");
    if (screen == null) { Console.WriteLine("FAIL: Screen not found"); return; }
    
    // Find the target screen
    var targetFlow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{{TARGET_FLOW_NAME}}");
    if (targetFlow == null) { Console.WriteLine("FAIL: target flow {{TARGET_FLOW_NAME}} not found"); return; }
    var targetScreen = targetFlow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{TARGET_SCREEN_NAME}}");
    if (targetScreen == null) { Console.WriteLine("FAIL: target screen {{TARGET_SCREEN_NAME}} not found"); return; }
    
    // Find the source widget by Name
    var widget = screen.GetAllDescendantsOfType<ServiceStudio.Plugin.NRWidgets.IButton>()
        .FirstOrDefault(b => b.Name == "{{WIDGET_NAME}}")
        ?? (ServiceStudio.Plugin.NRWidgets.IWidget)screen.GetAllDescendantsOfType<ServiceStudio.Plugin.NRWidgets.ILink>()
        .FirstOrDefault(l => l.Name == "{{WIDGET_NAME}}");
    if (widget == null) { Console.WriteLine("FAIL: widget {{WIDGET_NAME}} not found"); return; }
    
    // Set the OnClick destination
    widget.OnClick.DestinationScreen = targetScreen;
    
    // Bind input parameters for the target screen
    {{INPUT_BINDINGS_BLOCK}}
    
    Console.WriteLine($"Recipe 24: {{SCREEN_NAME}}.{{WIDGET_NAME}} → {{TARGET_SCREEN_NAME}} | Status: OK");
}
```

## INPUT_BINDINGS_BLOCK pattern

One per binding declared in manifest:

```csharp
{
    var param = targetScreen.InputParameters.FirstOrDefault(p => p.Name == "{{PARAM_NAME}}");
    if (param != null) {
        widget.OnClick.SetArgumentValue(param, "{{VALUE_EXPR}}");
    } else {
        Console.WriteLine($"WARN: target screen has no parameter {{PARAM_NAME}}");
    }
}
```

## Required imports

```
- System.Linq
- OutSystems.Model
- OutSystems.Model.UI.Mobile
- ServiceStudio.Plugin.NRWidgets
```

## Verification

After publish:

```csharp
foreach (var btn in screen.GetAllDescendantsOfType<IButton>()) {
    if (btn.OnClick.DestinationScreen != null) {
        Console.WriteLine($"  {btn.Name} → {btn.OnClick.DestinationScreen.Name}");
    }
}
```

Should list each authored navigation with correct target.

## Notes

- **OnClick is on Button + Link widgets**: not on Text, Container, or BlockInstance. For chrome-wrapped BlockInstances containing buttons, the navigation must be set on the contained Button (post-chrome-wrap order matters).
- **Same flow vs cross-flow**: `targetFlow` can be the same as source. Cross-flow nav (MainFlow → Common) sometimes requires intermediate screen.
- **Anonymous targets**: navigating to a role-gated screen from anonymous source triggers Login redirect. For Login → Dashboard nav, target Dashboard which Mentor auto-handles auth.
- **Cancel destination**: `widget.OnClick.DestinationScreen = null` removes the navigation.

## Related

- `[[odc_mcp_screen_action_service_action_call]]` — when OnClick triggers a ServiceAction first then navigates
- `[[odc_mcp_menu_block_link_clone_blocked]]` — Common/Menu block widget-add wall (avoid for nav)
- `[[FRAMEWORK_REVIEW]]` — navigation is P1 gap; this recipe closes it
