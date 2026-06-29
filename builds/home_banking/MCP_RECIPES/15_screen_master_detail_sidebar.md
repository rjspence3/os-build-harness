# Recipe 15 — Screen (Master-detail + collapsible sidebar w/ workflow actions)

## Purpose

Create ONE screen rendering a single entity record + a collapsible right-side action sidebar. The sidebar holds workflow operations (Approve, Reject, Reassign, Add Note) that mutate the parent record. Visibility of sidebar sections is gated by per-record boolean flags from related entities.

Pattern source: Backoffice/RequestDetail (LoanRequest master, sidebar with status-change/assign/reject actions, 10 boolean locals for workflow state).

Differs from [08_screen_detail](./08_screen_detail.md) by being write-heavy (sidebar mutates the record) and having an `IsSidebarOpen:Boolean` input parameter so other apps can deep-link with the sidebar pre-opened.

## When to use

- Admin/underwriter work surface for a single workflow record
- 3-6 distinct workflow actions visible in sidebar
- Sidebar visibility toggles on demand AND deep-linkable

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{SCREEN_NAME}}` | PascalCase | `RequestDetail` |
| `{{ROLE_NAME}}` | Required role | `HomeBankingBackoffice` |
| `{{IS_PUBLIC}}` | `true` if cross-app deep-linkable | `true` |
| `{{PARENT_ENTITY}}` | Top-level entity | `LoanRequest` |
| `{{PARENT_MODULE}}` | Module owning parent | `HomeBankingCore` |
| `{{PARENT_INPUT_NAME}}` | Input parameter for the parent ID | `RequestId` |
| `{{WORKFLOW_FLAGS_BLOCK}}` | Boolean locals for sidebar section visibility | (see example) |
| `{{CHILD_AGGREGATES_BLOCK}}` | Aggregates feeding the detail body | (see example) |
| `{{SIDEBAR_SECTIONS_BLOCK}}` | One block per workflow action (button + confirmation modal) | (see example) |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var mainFlow = eSpace.MobileFlows.First(f => f.Name == "MainFlow");
    var parentModule = "{{PARENT_MODULE}}" == "Local"
        ? (OutSystems.Model.IModule)eSpace
        : eSpace.References.Named("{{PARENT_MODULE}}");
    var parentEntity = parentModule.Entities.OfType<OutSystems.Model.Data.IServerEntitySignature>()
        .Named("{{PARENT_ENTITY}}");
    var role = eSpace.Roles.FirstOrDefault(r => r.Name == "{{ROLE_NAME}}")
        ?? eSpace.References.SelectMany(r => r.Roles).First(r => r.Name == "{{ROLE_NAME}}");

    var screen = mainFlow.CreateScreen("{{SCREEN_NAME}}");
    screen.SetTitle("");  // typically dynamic per record
    screen.Roles.Add(role);
    screen.Public = {{IS_PUBLIC}};

    // Inputs
    var parentInput = screen.CreateInputParameter("{{PARENT_INPUT_NAME}}");
    parentInput.DataType = parentEntity.IdentifierType;
    parentInput.IsMandatory = true;
    var sidebarInput = screen.CreateInputParameter("IsSidebarOpen");
    sidebarInput.DataType = eSpace.BooleanType;
    sidebarInput.IsMandatory = false;
    sidebarInput.SetDefaultValue("False");

    // Parent aggregate
    var parentAgg = screen.CreateScreenAggregate(false, "Get{{PARENT_ENTITY}}");
    parentAgg.Fetch = OutSystems.Model.Enumerations.DataSourceFetch.AtStart;
    parentAgg.SetMaxRecords("1");
    parentAgg.AsDatabaseAggregate.CreateSource(parentEntity);
    parentAgg.AsDatabaseAggregate.CreateFilter("{{PARENT_ENTITY}}.Id = {{PARENT_INPUT_NAME}}");

    // Workflow-state booleans + per-record agent-completion flags
    {{WORKFLOW_FLAGS_BLOCK}}

    // Child aggregates feeding detail body
    {{CHILD_AGGREGATES_BLOCK}}

    // Sidebar sections (one per workflow action)
    {{SIDEBAR_SECTIONS_BLOCK}}

    Console.WriteLine($"Recipe 15: {{SCREEN_NAME}} | Created: screen ({screen.Aggregates.Count()} aggs, {screen.LocalVariables.Count()} locals, Public={screen.Public}) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Enumerations
OutSystems.Model.Logic
OutSystems.Model.Logic.Nodes
OutSystems.Model.UI.Mobile
OutSystems.Model.Types
```

## Expected stdout

```
Recipe 15: RequestDetail | Created: screen (5 aggs, 10 locals, Public=True) | Status: OK
```

## Common failures

### ✗ Sidebar always visible / always hidden

Cause: layout block forgot to gate sidebar Container on `IsSidebarOpen`.
Fix: in the layout, sidebar container's Visible = `IsSidebarOpen`.

### ✗ Sidebar action runs but UI doesn't refresh

Cause: action mutated server-side but screen aggregates were already fetched at AtStart. They don't re-fetch on action completion by default.
Fix: in the action's end branch, call `<AggregateName>.Refresh()` or use a client action `RefreshData()` that explicitly re-runs the parent agg.

### ✗ Deep-link from another app doesn't open sidebar

Cause: the consumer is passing `IsSidebarOpen=True` but Mentor stripped the parameter binding.
Fix: verify post-publish that the screen's `IsSidebarOpen` input is still present + that the link from the producer app carries it. Per `[[mentor_phantom_authoring]]`.

## Example: Backoffice/RequestDetail

```yaml
SCREEN_NAME: RequestDetail
ROLE_NAME: HomeBankingBackoffice
IS_PUBLIC: true
PARENT_ENTITY: LoanRequest
PARENT_MODULE: HomeBankingCore
PARENT_INPUT_NAME: RequestId
WORKFLOW_FLAGS_BLOCK: |
  var v1 = screen.CreateLocalVariable("ShowNewNoteForm");
  v1.DataType = eSpace.BooleanType;
  var v2 = screen.CreateLocalVariable("SelectedLogId");
  v2.DataType = historyLog.IdentifierType;
  var v3 = screen.CreateLocalVariable("ShowRejectionPopup");
  v3.DataType = eSpace.BooleanType;
  var v4 = screen.CreateLocalVariable("isResubmission");
  v4.DataType = eSpace.BooleanType;
  var v5 = screen.CreateLocalVariable("NotificationCount");
  v5.DataType = eSpace.IntegerType;
  var v6 = screen.CreateLocalVariable("IsEnrichmentAgentCompleted");
  v6.DataType = eSpace.BooleanType;
  var v7 = screen.CreateLocalVariable("IsRequestCompleted");
  v7.DataType = eSpace.BooleanType;
  var v8 = screen.CreateLocalVariable("HasCreditScore");
  v8.DataType = eSpace.BooleanType;
  var v9 = screen.CreateLocalVariable("LoadingDateTime");
  v9.DataType = eSpace.DateTimeType;
  var v10 = screen.CreateLocalVariable("ShowSSN");
  v10.DataType = eSpace.BooleanType;
CHILD_AGGREGATES_BLOCK: |
  // Customer (joined via FK)
  // History log (timeline)
  // Agents responses (AI agent decisions)
  // Documents (per HBDocumentType)
  // (see GetX patterns)
SIDEBAR_SECTIONS_BLOCK: |
  // Section 1: Change Status — gated on IsRequestCompleted=false
  // Section 2: Reassign Employee — modal with Employee dropdown
  // Section 3: Reject (with reason) — opens ShowRejectionPopup
  // Section 4: Add Note — toggles ShowNewNoteForm inline form
```

## Memory refs

- [[mentor_phantom_authoring]] — verify post-publish for sidebar input persistence
- [[mentor_web_fk_blocks_standalone_list]] — child aggregate filters

## Related recipes

- [08_screen_detail](./08_screen_detail.md) — for read-only master-detail
- [06_action_workflow](./06_action_workflow.md) — for the sidebar's status-change actions (Sidebar_ChangeStatus pattern)
- [13_screen_modal](./13_screen_modal.md) — for the per-action confirmation popups
