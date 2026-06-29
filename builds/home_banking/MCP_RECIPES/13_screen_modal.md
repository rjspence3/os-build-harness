# Recipe 13 — Modal / Popup (overlay dialog gated on boolean local)

## Purpose

Add a modal popup to an EXISTING screen — overlay dialog gated on a `Show*:Boolean` local. The widget is an OS UI `Popup` widget (NOT a separate screen).

Pattern source: Portal/Transfer (OTP confirmation popup, `ShowPhoneNumberPopup`), Portal/PersonalLoan (terms-and-conditions popup, `ShowPopup`), Backoffice/RequestDetail (rejection popup, `ShowRejectionPopup`).

This is an ADDITIVE recipe — runs against an already-created screen. For new screens that need a modal as part of their initial layout, use [12_screen_wizard](./12_screen_wizard.md) or [15_screen_master_detail_sidebar](./15_screen_master_detail_sidebar.md) which include modal slots.

## When to use

- Confirmation dialog (terms, "Are you sure?", OTP entry)
- Inline form (new note, edit attribute) without leaving the parent screen
- Error/success notification (use OS UI Notification block if non-blocking)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{TARGET_SCREEN}}` | PascalCase screen name to add the modal to | `Transfer` |
| `{{MODAL_NAME}}` | PascalCase modal local name (no `Show` prefix; recipe adds it) | `PhoneNumber` |
| `{{TRIGGER_LABEL}}` | Label of the button that opens the modal | `Confirm Phone Number` |
| `{{MODAL_TITLE}}` | Heading text inside the modal | `Verify your phone number` |
| `{{MODAL_BODY_BLOCK}}` | Widgets that compose the modal body (form fields, expressions) | (see example) |
| `{{CONFIRM_ACTION_NAME}}` | Screen action triggered on "Confirm" click | `ConfirmPhoneNumberOnClick` |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var mainFlow = eSpace.MobileFlows.First(f => f.Name == "MainFlow");
    var screen = mainFlow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{TARGET_SCREEN}}");

    if (screen == null) {
        Console.WriteLine($"Recipe 13: {{MODAL_NAME}} | FAILED: target screen {{TARGET_SCREEN}} not found");
        return;
    }

    // Show* boolean local — controls modal visibility
    var showLocal = screen.CreateLocalVariable("Show{{MODAL_NAME}}");
    showLocal.DataType = eSpace.BooleanType;
    showLocal.SetDefaultValue("False");

    // Popup widget — gated on Show*
    // (Actual widget creation requires the OS UI Popup widget API; placeholder shape:)
    var popup = screen.CreatePopup("{{MODAL_NAME}}Popup");
    popup.Visible = "Show{{MODAL_NAME}}";
    popup.Title = "{{MODAL_TITLE}}";

    {{MODAL_BODY_BLOCK}}

    // Open action — sets Show* = True
    var open = screen.CreateScreenAction("Open{{MODAL_NAME}}");
    var openAssign = open.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("ShowModal");
    openAssign.CreateAssignment().SetVariable("Show{{MODAL_NAME}}").SetValue("True");
    open.StartNode.Target = openAssign;
    openAssign.Target = open.EndNode;

    // Close action — sets Show* = False
    var close = screen.CreateScreenAction("Close{{MODAL_NAME}}");
    var closeAssign = close.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("HideModal");
    closeAssign.CreateAssignment().SetVariable("Show{{MODAL_NAME}}").SetValue("False");
    close.StartNode.Target = closeAssign;
    closeAssign.Target = close.EndNode;

    Console.WriteLine($"Recipe 13: {{MODAL_NAME}} | Created: modal added to {{TARGET_SCREEN}} (open + close actions wired) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Logic
OutSystems.Model.Logic.Nodes
OutSystems.Model.UI.Mobile
OutSystems.Model.Types
```

## Expected stdout

```
Recipe 13: PhoneNumber | Created: modal added to Transfer (open + close actions wired) | Status: OK
```

## Common failures

### ✗ Modal opens but doesn't close

Cause: Close action assigns `Show* = False` but the popup widget's Visible expression is referring to the wrong variable.
Fix: check Visible expression on the Popup widget. Should be exactly `Show<ModalName>` (no `=True` suffix; the boolean is the condition).

### ✗ Modal blocks underlying screen interactions even when closed

Cause: Popup widget z-index defaults to a covering overlay. When `Show*=False`, the widget removes from DOM but on some OS UI versions a transparent backdrop persists.
Fix: in CSS theme, set `.osui-popup:not(.osui-popup--visible) { display: none !important; }`.

### ✗ Multiple modals can be open at once

Cause: each modal has independent Show* boolean. Opening modal B while modal A is open results in stacked overlays.
Fix: in each Open action, first set all OTHER Show* booleans to False. Or use a single `ActiveModal:Text` local where modals gate on `ActiveModal="<ModalName>"`.

## Example: Transfer/PhoneNumber modal (OTP entry)

```yaml
TARGET_SCREEN: Transfer
MODAL_NAME: PhoneNumber
TRIGGER_LABEL: Confirm Phone Number
MODAL_TITLE: Verify your phone number
MODAL_BODY_BLOCK: |
  // OTP entry input
  // SMS resend link
  // Confirm/Cancel buttons
CONFIRM_ACTION_NAME: ConfirmPhoneNumberOnClick
```

## Memory refs

- [[odc_mcp_screen_scope_wall]] — modals are inline; they DON'T need their own screen scope

## Related recipes

- [12_screen_wizard](./12_screen_wizard.md) — wizards often spawn modals at step transitions
- [15_screen_master_detail_sidebar](./15_screen_master_detail_sidebar.md) — admin screens often have rejection / reassign modals
