# Recipe 08 — Screen (Master-detail: one entity row with related lists)

## Purpose

Create ONE screen that displays a single entity record + its FK-related children. Takes one ID input parameter, fetches the parent record + all related child records in one screen-level aggregate fan-out.

Canonical shape (Home Banking Backoffice/CustomerDetail):

```
Header
  ↓ Breadcrumb (Customers > {Customer.Name})
  ↓ Avatar + key metadata grid

Body — Tabs or sections:
  ├── Overview (form fields, read-only)
  ├── Accounts (table of HBAccount rows where CustomerId = input)
  ├── Loans (table of CustomerLoan rows where CustomerId = input)
  ├── Documents (table of HBDocument rows joined via HistoryLog)
  └── Activity (table of HistoryLog entries)

Side panel — actions:
  Edit · Suspend · Verify Identity
```

## When to use

- Screen receives one `<Entity>Identifier` input
- Renders the parent record + 1-5 related lists
- Lists are read-only or have row-level click → other screens

For master-detail-with-side-panel (RequestDetail shape), use [15_screen_master_detail_sidebar](./15_screen_master_detail_sidebar.md).

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{SCREEN_NAME}}` | PascalCase | `CustomerDetail` |
| `{{ROLE_NAME}}` | Required role | `HomeBankingBackoffice` |
| `{{PARENT_ENTITY}}` | Top-level entity | `HBCustomer` |
| `{{PARENT_MODULE}}` | Module owning parent entity | `HomeBankingCore` |
| `{{INPUT_PARAM_NAME}}` | Input param name on screen | `CustomerId` |
| `{{TITLE_EXPR}}` | Title (often `Get{{PARENT_ENTITY}}.List.Current.{{PARENT_ENTITY}}.Name`) | `"Customer Detail"` |
| `{{CHILD_AGGREGATES_BLOCK}}` | One block per child relation (see syntax) | (see example) |
| `{{LAYOUT_BLOCK}}` | Widget tree — sections/tabs/forms | (use the `BuildDetailLayout` helper) |

### Child aggregate syntax

```csharp
AddChildAggregate(screen, "Get<Child>",
    childEntityRef,
    "ChildEntity.{{INPUT_PARAM_NAME}} = {{INPUT_PARAM_NAME}}",
    "ChildEntity.CreatedOn",  // sort attribute, can be null
    50);                       // max records
```

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
    screen.SetTitle({{TITLE_EXPR}});
    screen.Roles.Add(role);

    // Input parameter
    var inp = screen.CreateInputParameter("{{INPUT_PARAM_NAME}}");
    inp.DataType = parentEntity.IdentifierType;
    inp.IsMandatory = true;

    // Parent aggregate — Get<ParentEntity> filtered by input
    var parentAgg = screen.CreateScreenAggregate(false, "Get{{PARENT_ENTITY}}");
    parentAgg.Fetch = OutSystems.Model.Enumerations.DataSourceFetch.AtStart;
    parentAgg.SetMaxRecords("1");
    var parentSrc = parentAgg.AsDatabaseAggregate.CreateSource(parentEntity);
    parentAgg.AsDatabaseAggregate.CreateFilter("{{PARENT_ENTITY}}.Id = {{INPUT_PARAM_NAME}}");

    // Child aggregate helper
    void AddChildAggregate(string aggName,
            OutSystems.Model.Data.IServerEntitySignature childEntity,
            string filter, string sortAttr, int maxRecords) {
        var ca = screen.CreateScreenAggregate(false, aggName);
        ca.Fetch = OutSystems.Model.Enumerations.DataSourceFetch.AtStart;
        ca.SetMaxRecords(maxRecords.ToString());
        ca.AsDatabaseAggregate.CreateSource(childEntity);
        ca.AsDatabaseAggregate.CreateFilter(filter);
        if (sortAttr != null) ca.AsDatabaseAggregate.CreateSort().SetAttribute(sortAttr);
    }

    {{CHILD_AGGREGATES_BLOCK}}

    {{LAYOUT_BLOCK}}

    Console.WriteLine($"Recipe 08: {{SCREEN_NAME}} | Created: screen (1 parent agg + {screen.Aggregates.Count() - 1} child aggs, role={role.Name}) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Enumerations
OutSystems.Model.UI.Mobile
```

## Expected stdout

```
Recipe 08: CustomerDetail | Created: screen (1 parent agg + 4 child aggs, role=HomeBankingBackoffice) | Status: OK
```

## Common failures

### ✗ "Parent record not found" empty-state at runtime

Cause: aggregate's MaxRecords=1 + filter that doesn't match any row. Either bad input ID or filter expression typo.
Fix: add a server-side guard or `If(GetParent.List.Empty, redirect to InvalidPermissions, render content)`.

### ✗ N+1 query problem on child lists

Cause: each child aggregate runs a separate SQL query. With 5 children = 6 queries on each screen load.
Fix: acceptable for low-traffic admin screens. For high-traffic, replace per-child aggregates with a single SQL node returning a joined record set, then iterate in-memory.

## Example: Backoffice/CustomerDetail

```yaml
SCREEN_NAME: CustomerDetail
ROLE_NAME: HomeBankingBackoffice
PARENT_ENTITY: HBCustomer
PARENT_MODULE: HomeBankingCore
INPUT_PARAM_NAME: CustomerId
TITLE_EXPR: 'GetHBCustomer.List.Current.HBCustomer.Name'
CHILD_AGGREGATES_BLOCK: |
  AddChildAggregate("GetCustomerAccounts", hbAccount, "HBAccount.CustomerId = CustomerId AND HBAccount.IsActive", "HBAccount.CreatedOn", 50);
  AddChildAggregate("GetCustomerLoans", customerLoan, "CustomerLoan.CustomerId = CustomerId AND CustomerLoan.IsActive", "CustomerLoan.CreatedOn", 50);
  AddChildAggregate("GetCustomerGoals", customerGoal, "CustomerGoal.CustomerId = CustomerId AND CustomerGoal.IsActive", null, 50);
  AddChildAggregate("GetCustomerHistory", historyLog, "HistoryLog.CustomerId = CustomerId", "HistoryLog.CreatedOn", 100);
```

## Memory refs

- [[odc_long_integer_to_identifier_cast]] — for the ID-filter expression
- [[mentor_web_fk_blocks_standalone_list]] — Mentor Web wall on FK-bearing entities

## Related recipes

- [07_screen_table](./07_screen_table.md) — for parent list that navigates here
- [15_screen_master_detail_sidebar](./15_screen_master_detail_sidebar.md) — variant w/ side panel
- [11_default_screen](./11_default_screen.md) — for setting this as the default
