# Recipe 14 — Screen widget pack (Document upload — per-doc-type slot)

## Purpose

Add ONE document-upload slot to an existing screen. A slot consists of:

- Local variable typed as `DocumentStructure` (an app-specific Structure holding `Binary, Filename, ValidationProgress, ValidationResult, IsValid`)
- File-picker widget with OnChange wiring
- Validation-state UI (loading spinner / success badge / failure message)
- Per-doc-type label (e.g., "Pay Stubs", "Tax Form")

Pattern source: Portal/PersonalLoan has 4 named instances (`DocumentPayStubs`, `DocumentBankStatements`, `DocumentIdentification`, `DocumentTaxForm`) — one per `HBDocumentType` static entity record.

This is an ADDITIVE recipe — runs N times against an existing screen, once per document type the screen collects.

## When to use

- Multi-doc onboarding (loan applications, KYC verification)
- One named slot per logical doc type (NOT a generic "upload N files" list)
- Each slot has independent validation state visible in-line

For generic file-upload with no per-slot semantics, use a simpler `File Upload` block from OS UI directly.

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{TARGET_SCREEN}}` | PascalCase screen name | `PersonalLoan` |
| `{{DOC_TYPE_NAME}}` | PascalCase slot name (becomes `Document<X>` local) | `PayStubs` |
| `{{DOC_TYPE_LABEL}}` | Display label | `Pay Stubs` |
| `{{DOC_TYPE_IDENTIFIER}}` | Identifier of the HBDocumentType static entity record | `Entities.HBDocumentType.PayStubs` |
| `{{ON_VALIDATED_ACTION}}` | Screen action triggered when ValidationProgress becomes "Validated" | `OnDocumentValidated` |
| `{{VALIDATOR_SERVER_ACTION}}` | Server Action that takes a Binary + DocType, returns validation | `ValidateDocument` |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var mainFlow = eSpace.MobileFlows.First(f => f.Name == "MainFlow");
    var screen = mainFlow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{TARGET_SCREEN}}");

    if (screen == null) {
        Console.WriteLine($"Recipe 14: Document{{DOC_TYPE_NAME}} | FAILED: target screen {{TARGET_SCREEN}} not found");
        return;
    }

    // Resolve DocumentStructure — assumed to exist in app or referenced module
    var docStructure = eSpace.Structures.FirstOrDefault(s => s.Name == "DocumentStructure")
        ?? (OutSystems.Model.Data.IStructureSignature)eSpace.References
            .SelectMany(r => r.Structures).First(s => s.Name == "DocumentStructure");

    // Local for this doc slot
    var docLocal = screen.CreateLocalVariable("Document{{DOC_TYPE_NAME}}");
    docLocal.DataType = docStructure;

    // OnChange action — calls the validator server action with the new Binary
    var onChange = screen.CreateScreenAction("On{{DOC_TYPE_NAME}}Selected");
    var setProgress = onChange.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("Set_Validating");
    setProgress.CreateAssignment().SetVariable("Document{{DOC_TYPE_NAME}}.ValidationProgress")
        .SetValue("Entities.ValidationProgress.Validating");

    // Resolve validator
    var validator = eSpace.GetAllDescendantsOfType<OutSystems.Model.Logic.IServerActionSignature>()
        .FirstOrDefault(a => a.Name == "{{VALIDATOR_SERVER_ACTION}}")
        ?? eSpace.References.SelectMany(r => r.GetAllDescendantsOfType<OutSystems.Model.Logic.IServerActionSignature>())
            .First(a => a.Name == "{{VALIDATOR_SERVER_ACTION}}");

    var call = onChange.CreateNode<OutSystems.Model.Logic.Nodes.IExecuteServerActionNode>("Call_Validator");
    call.Action = validator;
    call.Arguments.First(arg => arg.Parameter.Name == "Binary")
        .SetValue("Document{{DOC_TYPE_NAME}}.Binary");
    call.Arguments.First(arg => arg.Parameter.Name == "Filename")
        .SetValue("Document{{DOC_TYPE_NAME}}.Filename");
    call.Arguments.First(arg => arg.Parameter.Name == "HBDocumentTypeId")
        .SetValue("{{DOC_TYPE_IDENTIFIER}}");
    call.Arguments.First(arg => arg.Parameter.Name == "LocaleId")
        .SetValue("Client.LocaleId");
    call.ServerRequestTimeout = 60;  // LLM call — per [[odc_server_request_timeout]]

    // After validation, project to ValidationResult + IsValid
    var assignResult = onChange.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("Set_Result");
    assignResult.CreateAssignment().SetVariable("Document{{DOC_TYPE_NAME}}.ValidationResult")
        .SetValue("Call_Validator.DocumentValidationResponse");
    assignResult.CreateAssignment().SetVariable("Document{{DOC_TYPE_NAME}}.IsValid")
        .SetValue("Call_Validator.DocumentValidationResponse.IsValid");
    assignResult.CreateAssignment().SetVariable("Document{{DOC_TYPE_NAME}}.ValidationProgress")
        .SetValue("Entities.ValidationProgress.Validated");

    onChange.StartNode.Target = setProgress;
    setProgress.Target = call;
    call.Target = assignResult;
    assignResult.Target = onChange.EndNode;

    Console.WriteLine($"Recipe 14: Document{{DOC_TYPE_NAME}} | Created: doc slot on {{TARGET_SCREEN}} (local + OnSelected action) | Status: OK");
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
```

## Expected stdout

```
Recipe 14: DocumentPayStubs | Created: doc slot on PersonalLoan (local + OnSelected action) | Status: OK
```

## Common failures

### ✗ File picker accepts the file but ValidationProgress stays "NotValidated"

Cause: file-picker widget's OnChange isn't wired to `On{{DOC_TYPE_NAME}}Selected`.
Fix: in the screen layout block, find the file-picker widget for this slot and set `OnChange = On{{DOC_TYPE_NAME}}Selected`.

### ✗ `CommunicationException` timeout on Call_Validator

Cause: LLM validation takes >10s but ServerRequestTimeout wasn't set.
Fix: recipe sets `call.ServerRequestTimeout = 60` — verify post-publish via `getScreenAction`. Per `[[odc_server_request_timeout]]`.

### ✗ Validation succeeds but UI still shows spinner

Cause: ValidationProgress isn't reset to `Validated` after the call returns. Check the `Set_Result` Assign node.
Fix: every successful path must assign `ValidationProgress = Entities.ValidationProgress.Validated`. Failure paths should set it back to `NotValidated`.

## Example: PersonalLoan — 4 document slots

Run the recipe 4 times against PersonalLoan, varying `DOC_TYPE_NAME`:

```yaml
# Slot 1
TARGET_SCREEN: PersonalLoan
DOC_TYPE_NAME: PayStubs
DOC_TYPE_LABEL: Pay Stubs
DOC_TYPE_IDENTIFIER: Entities.HBDocumentType.PayStubs
ON_VALIDATED_ACTION: OnDocumentValidated
VALIDATOR_SERVER_ACTION: ValidateDocument
---
# Slot 2 — same shape, different DOC_TYPE_NAME
DOC_TYPE_NAME: BankStatements
DOC_TYPE_LABEL: Bank Statements
DOC_TYPE_IDENTIFIER: Entities.HBDocumentType.BankStatements
---
# Slot 3
DOC_TYPE_NAME: Identification
DOC_TYPE_LABEL: Government ID
DOC_TYPE_IDENTIFIER: Entities.HBDocumentType.Identification
---
# Slot 4
DOC_TYPE_NAME: TaxForm
DOC_TYPE_LABEL: Most Recent Tax Return
DOC_TYPE_IDENTIFIER: Entities.HBDocumentType.TaxForm
```

After all 4 run, PersonalLoan has 4 `Document*` locals each typed as `DocumentStructure`.

## Memory refs

- [[odc_server_request_timeout]] — LLM validator needs extended timeout
- [[odc_mcp_record_literal_via_typed_local]] — `DocumentStructure` is a record-typed local

## Related recipes

- [06_action_workflow](./06_action_workflow.md) — for the ValidateDocument server action (AI pipeline)
- [12_screen_wizard](./12_screen_wizard.md) — doc upload is usually one step of a wizard
