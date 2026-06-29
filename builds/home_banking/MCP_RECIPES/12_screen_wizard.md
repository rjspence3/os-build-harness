# Recipe 12 — Screen (Multi-step wizard with StepNo gating)

## Purpose

Create ONE screen rendering a multi-step form/flow as ONE screen (not multiple). Step transitions happen client-side by mutating a `StepNo:Integer` local variable (or input parameter); each step's container is gated by `Visible="StepNo=N"`.

Pattern source: Portal/Transfer (2 steps, OTP + confirm), Portal/PersonalLoan (multi-step wizard with `StepNo` as input parameter to support deep-linking to a specific step).

## When to use

- Multi-step form (loan application, transfer, onboarding)
- Each step has distinct inputs/validations but shares parent state
- "Next" / "Back" buttons trigger client-side state changes, NOT screen navigation
- Optional: deep-linkable to a specific step (pass StepNo as input parameter)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{SCREEN_NAME}}` | PascalCase | `PersonalLoan` |
| `{{ROLE_NAME}}` | Required role | `HomeBankingPortal` |
| `{{STEP_COUNT}}` | Total steps | `4` |
| `{{STEP_AS_INPUT}}` | `true` if StepNo is an input parameter (deep-link support), else `false` (StepNo is a local var) | `true` |
| `{{STEP_LOCALS_BLOCK}}` | Per-step locals (Show* booleans, etc.) | (see example) |
| `{{STEP_BODIES_BLOCK}}` | One block per step: container w/ Visible="StepNo=N" + step contents | (see example) |
| `{{NAVIGATION_BLOCK}}` | Back/Next buttons + their OnClick actions | (see example) |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var mainFlow = eSpace.MobileFlows.First(f => f.Name == "MainFlow");
    var role = eSpace.Roles.FirstOrDefault(r => r.Name == "{{ROLE_NAME}}")
        ?? eSpace.References.SelectMany(r => r.Roles).First(r => r.Name == "{{ROLE_NAME}}");

    var screen = mainFlow.CreateScreen("{{SCREEN_NAME}}");
    screen.SetTitle("Wizard");
    screen.Roles.Add(role);

    // StepNo: input parameter (deep-linkable) OR local variable
    if ({{STEP_AS_INPUT}}) {
        var stepInput = screen.CreateInputParameter("StepNo");
        stepInput.DataType = eSpace.IntegerType;
        stepInput.IsMandatory = true;
    } else {
        var stepLocal = screen.CreateLocalVariable("StepNo");
        stepLocal.DataType = eSpace.IntegerType;
        stepLocal.SetDefaultValue("1");  // start at step 1
    }

    // Per-step locals + body containers
    {{STEP_LOCALS_BLOCK}}
    {{STEP_BODIES_BLOCK}}

    // Navigation: Back + Next buttons + screen actions GoBack / GoNext
    var goNext = screen.CreateScreenAction("GoNext");
    var assignNext = goNext.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("IncrementStepNo");
    assignNext.CreateAssignment().SetVariable("StepNo").SetValue("StepNo + 1");
    goNext.StartNode.Target = assignNext;
    assignNext.Target = goNext.EndNode;

    var goBack = screen.CreateScreenAction("GoBack");
    var assignBack = goBack.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("DecrementStepNo");
    assignBack.CreateAssignment().SetVariable("StepNo").SetValue("StepNo - 1");
    goBack.StartNode.Target = assignBack;
    assignBack.Target = goBack.EndNode;

    {{NAVIGATION_BLOCK}}

    Console.WriteLine($"Recipe 12: {{SCREEN_NAME}} | Created: wizard ({{STEP_COUNT}} steps, StepNoAsInput={ {{STEP_AS_INPUT}} }, role={role.Name}) | Status: OK");
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
Recipe 12: PersonalLoan | Created: wizard (4 steps, StepNoAsInput=True, role=HomeBankingPortal) | Status: OK
```

## Common failures

### ✗ All steps visible simultaneously

Cause: forgot to set `Visible` on the step containers. Default Visible is `True`.
Fix: every step body must set `stepContainer.Visible = "StepNo=N"` (where N is the step number).

### ✗ "Next" button increments past last step

Cause: `IncrementStepNo` has no guard.
Fix: in `GoNext`, add an `If` node — `StepNo < {{STEP_COUNT}}` → increment, else → submit/done. Mirror for `GoBack` with `StepNo > 1`.

### ✗ Browser back button skips wizard steps

Cause: wizard is one screen — browser back goes to whatever screen preceded the wizard. The platform doesn't track in-screen state mutations as history entries.
Fix: this is intentional. If you need step-history-as-URL, use a different pattern: separate screen per step + `RedirectTo(NextStep)` actions. But that breaks the "one screen" pattern this recipe codifies.

## Example: Portal/PersonalLoan (4 steps)

```yaml
SCREEN_NAME: PersonalLoan
ROLE_NAME: HomeBankingPortal
STEP_COUNT: 4
STEP_AS_INPUT: true
STEP_LOCALS_BLOCK: |
  // step-shared state
  var selAccountLabel = screen.CreateLocalVariable("SelectedAccountLabel");
  selAccountLabel.DataType = eSpace.TextType;
  var initialRate = screen.CreateLocalVariable("InitialEffectiveInterestRatePercent");
  initialRate.DataType = eSpace.DecimalType;
  var termsConfirm = screen.CreateLocalVariable("TermAndConditionsConfirm");
  termsConfirm.DataType = eSpace.BooleanType;
  // popup-state booleans
  var showPopup = screen.CreateLocalVariable("ShowPopup");
  showPopup.DataType = eSpace.BooleanType;
  // 4 document-structure locals (one per HBDocumentType)
  var docPayStubs = screen.CreateLocalVariable("DocumentPayStubs");
  docPayStubs.DataType = documentStructure;
  var docBankStatements = screen.CreateLocalVariable("DocumentBankStatements");
  docBankStatements.DataType = documentStructure;
  var docId = screen.CreateLocalVariable("DocumentIdentification");
  docId.DataType = documentStructure;
  var docTax = screen.CreateLocalVariable("DocumentTaxForm");
  docTax.DataType = documentStructure;
STEP_BODIES_BLOCK: |
  // Step 1: account selection
  var step1 = screen.CreateContainer("Step1");
  step1.Visible = "StepNo=1";
  // ... step1 form widgets

  // Step 2: amount + term
  var step2 = screen.CreateContainer("Step2");
  step2.Visible = "StepNo=2";
  // ... step2 form widgets

  // Step 3: document upload (see Recipe 14 for the upload pattern)
  var step3 = screen.CreateContainer("Step3");
  step3.Visible = "StepNo=3";
  // ... 4 upload widgets, one per HBDocumentType

  // Step 4: confirmation + terms
  var step4 = screen.CreateContainer("Step4");
  step4.Visible = "StepNo=4";
  // ... summary + terms checkbox + submit button
NAVIGATION_BLOCK: |
  // Add "Back" + "Next/Submit" buttons gated on StepNo
  // (typical: button label changes "Next" → "Submit" on last step)
```

## Memory refs

- [[odc_mcp_screen_scope_wall]] — wizards have many widgets; watch session context

## Related recipes

- [13_screen_modal](./13_screen_modal.md) — for in-wizard confirmation popups (terms, OTP)
- [14_screen_document_upload](./14_screen_document_upload.md) — for wizard steps that collect documents
- [01_entity_server](./01_entity_server.md) — for the entity the wizard ultimately submits to
