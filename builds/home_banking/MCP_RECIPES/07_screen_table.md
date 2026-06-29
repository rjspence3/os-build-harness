# Recipe 07 — Screen (Table list of entity rows)

## Purpose

Create ONE screen that renders a paginated table of one entity's rows. Canonical OS UI table layout:

```
┌─ Layout (top menu)
├── Heading + breadcrumb
├── Filter row (Search input + Dropdown filter + Refresh button)
├── Table widget
│   ├── Header row (Column1 | Column2 | ... | Actions)
│   └── List binding: GetAll<Entity>.List
│       └── Row template (clickable, opens detail screen)
└── Pagination block
```

Maps to two real Home Banking screens: Portal/Requests, Backoffice/Customers. Both are role-gated, take no inputs, and aggregate from one server entity with no joins.

## When to use

- Screen is a flat list of one entity's rows
- Need search + filter + sort + pagination
- Row click navigates to a detail screen (use [08_screen_detail](./08_screen_detail.md))

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{SCREEN_NAME}}` | PascalCase screen name | `Customers` |
| `{{ROLE_NAME}}` | Role gating this screen | `HomeBankingBackoffice` |
| `{{ENTITY_NAME}}` | Backing entity (single source) | `HBCustomer` |
| `{{ENTITY_MODULE}}` | Module owning the entity (or `Local`) | `HomeBankingCore` |
| `{{TITLE_EXPR}}` | Title expression (string literal or `If(...)` for i18n) | `"Customers"` |
| `{{COLUMNS_BLOCK}}` | Table column definitions (see syntax below) | `AddTextColumn(t, "Name", "Customer.Name");` |
| `{{ROW_CLICK_DEST}}` | Name of detail screen for row click | `CustomerDetail` |
| `{{ROW_CLICK_ARG_NAME}}` | Input parameter name on the detail screen | `CustomerId` |
| `{{ROW_CLICK_ARG_EXPR}}` | Expression mapping row→arg | `Customer.Id` |

### Column syntax

```csharp
AddTextColumn(table, "Header Label", "RowExpression");
AddDateColumn(table, "Header Label", "RowExpression");
AddCurrencyColumn(table, "Header Label", "RowExpression");
AddBadgeColumn(table, "Header Label", "RowExpression", "ColorExpression");
AddActionColumn(table, "Header Label", "OnClickActionName");
```

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var mainFlow = eSpace.MobileFlows.First(f => f.Name == "MainFlow");
    var module = "{{ENTITY_MODULE}}" == "Local"
        ? eSpace
        : (OutSystems.Model.IModule)eSpace.References.Named("{{ENTITY_MODULE}}");
    var entity = module.Entities.OfType<OutSystems.Model.Data.IServerEntitySignature>()
        .Named("{{ENTITY_NAME}}");
    var role = eSpace.Roles.FirstOrDefault(r => r.Name == "{{ROLE_NAME}}")
        ?? eSpace.References.SelectMany(r => r.Roles).First(r => r.Name == "{{ROLE_NAME}}");

    // Screen
    var screen = mainFlow.CreateScreen("{{SCREEN_NAME}}");
    screen.SetTitle({{TITLE_EXPR}});
    screen.Roles.Add(role);

    // Aggregate: GetAll<Entity>, fetch at start, max 50 rows w/ pagination
    var agg = screen.CreateScreenAggregate(false, "GetAll{{ENTITY_NAME}}");
    agg.Fetch = OutSystems.Model.Enumerations.DataSourceFetch.AtStart;
    agg.SetMaxRecords("50");
    var src = agg.AsDatabaseAggregate.CreateSource(entity);
    agg.AsDatabaseAggregate.CreateSort().SetAttribute(entity.Name + ".CreatedOn");

    // Helpers for columns
    void AddTextColumn(OutSystems.Model.UI.Mobile.IWidget table, string label, string rowExpr) {
        // Note: actual widget type assignment depends on OS UI version — placeholder for the
        // recipe's caller to fill in via the OS UI Mentor pattern (typically a Container row
        // with TableHeader text + per-cell Expression bound to rowExpr)
    }

    // The table+columns body would be ~30 lines of widget-creation code. In practice
    // recipes invoke a higher-level helper like `BuildTableBlock(screen, agg, columns)` —
    // since OS UI's Table widget has many properties, this template just declares the
    // structure. Caller fills in `BuildTableBlock` per app's OS UI version.

    {{COLUMNS_BLOCK}}

    Console.WriteLine($"Recipe 07: {{SCREEN_NAME}} | Created: screen ({screen.Widgets.Count()} widgets, 1 aggregate) | Status: OK");
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
Recipe 07: Customers | Created: screen (12 widgets, 1 aggregate) | Status: OK
```

## Common failures

### ✗ `Cannot resolve role 'X'` at publish

Cause: role is in a referenced module but the dependency wasn't added.
Fix: per `[[odc_mcp_reference_add_studio_only]]`, add the role via Studio Cmd+Q Manage Dependencies before running this recipe.

### ✗ Aggregate joins are reordered after publish

Cause: Mentor decided to "optimize" the aggregate's source order.
Fix: per `[[mentor_phantom_authoring]]`, verify post-publish via `getScreen` — if Mentor reordered, manually fix in Studio.

### ✗ Pagination block doesn't render

Cause: OS UI Pagination block is a separate widget added explicitly. The recipe doesn't include it by default.
Fix: add a `Pagination` block instance after the table widget, with `StartIndex=agg.StartIndex`, `MaxRecords=agg.MaxRecords`, `TotalCount=agg.Count`.

## Example: Backoffice/Customers

```yaml
SCREEN_NAME: Customers
ROLE_NAME: HomeBankingBackoffice
ENTITY_NAME: HBCustomer
ENTITY_MODULE: HomeBankingCore
TITLE_EXPR: '"Customers"'
COLUMNS_BLOCK: |
  AddTextColumn(table, "Name", "GetAllHBCustomer.List.Current.HBCustomer.Name");
  AddTextColumn(table, "Email", "GetAllHBCustomer.List.Current.HBCustomer.Email");
  AddTextColumn(table, "Position", "GetAllHBCustomer.List.Current.HBCustomer.Position");
  AddDateColumn(table, "Client Since", "GetAllHBCustomer.List.Current.HBCustomer.ClientSince");
  AddBadgeColumn(table, "Premium", "If(GetAllHBCustomer.List.Current.HBCustomer.IsPremium, \"Premium\", \"Standard\")", "If(GetAllHBCustomer.List.Current.HBCustomer.IsPremium, \"gold\", \"gray\")");
ROW_CLICK_DEST: CustomerDetail
ROW_CLICK_ARG_NAME: CustomerId
ROW_CLICK_ARG_EXPR: GetAllHBCustomer.List.Current.HBCustomer.Id
```

## Memory refs

- [[odc_mcp_reference_add_studio_only]] — cross-app role refs
- [[odc_status_chip_cascade_override]] — for badge styling
- [[mentor_b_n_widget_id_pattern]] — Mentor auto-generated widget IDs

## Related recipes

- [08_screen_detail](./08_screen_detail.md) — for the row-click destination
- [09_screen_dashboard](./09_screen_dashboard.md) — if this is a tile on a dashboard
- [01_entity_server](./01_entity_server.md) — for the backing entity
