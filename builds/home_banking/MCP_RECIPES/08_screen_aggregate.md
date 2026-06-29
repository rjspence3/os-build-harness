# Recipe 08 — Screen Aggregate

**Purpose**: Author an aggregate (data fetcher) on a screen so its widgets can bind to entity data. Without aggregates, screens render empty.

**When to use**: After Phase 5 (screens authored) and Phase 0 (references to producer entities). Per-screen, per-aggregate.

## Grammar (manifest extension)

Add to `screens.yaml`:

```yaml
- name: Dashboard
  uiflow: MainFlow
  capture: portal-dashboard.tree.md
  aggregates:
    - name: GetAccounts
      source: HBAccount               # entity name from producer
      source_producer: HomeBankingCore # optional — defaults to current app
      filters:
        - field: HBCustomerId
          op: equals
          value: GetUserId()           # expression
      order_by:
        - field: AccountName
          dir: Ascending
    - name: GetRecentTransactions
      source: Transaction
      max_records: 10
      order_by:
        - field: TransactionDate
          dir: Descending
```

## C# body

```csharp
eSpace => {
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{{FLOW_NAME}}");
    if (flow == null) { Console.WriteLine("FAIL: MainFlow not found"); return; }
    var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{SCREEN_NAME}}");
    if (screen == null) { Console.WriteLine("FAIL: Screen not found"); return; }
    
    // Find the entity to aggregate from
    var entity = eSpace.References
        .SelectMany(r => r.Entities)
        .FirstOrDefault(e => e.Name == "{{ENTITY_NAME}}")
        ?? eSpace.Entities.FirstOrDefault(e => e.Name == "{{ENTITY_NAME}}");
    if (entity == null) { Console.WriteLine("FAIL: Entity {{ENTITY_NAME}} not found"); return; }
    
    // Create the aggregate
    var aggregate = screen.CreateScreenAggregate("{{AGGREGATE_NAME}}");
    var dbAgg = aggregate.AsDatabaseAggregate;
    var source = dbAgg.CreateSource(entity);
    
    // Filters (one per filter declared in manifest)
    {{FILTERS_BLOCK}}
    
    // Order-by clauses
    {{ORDER_BY_BLOCK}}
    
    // Max records (if specified)
    {{MAX_RECORDS_LINE}}
    
    Console.WriteLine($"Recipe 08: {{SCREEN_NAME}}.{{AGGREGATE_NAME}} | Created from {{ENTITY_NAME}} | Status: OK");
}
```

## Substitution patterns

### FILTERS_BLOCK — one per filter

```csharp
var filter0 = dbAgg.CreateFilter();
filter0.Condition.SetValue("{{FIELD_NAME}} {{OP}} {{VALUE_EXPR}}");
```

### ORDER_BY_BLOCK — one per order-by clause

```csharp
var ob0 = dbAgg.CreateOrderBy();
ob0.OrderByAttribute = source.Attributes.First(a => a.Name == "{{FIELD_NAME}}");
ob0.OrderDirection = OutSystems.Model.Enumerations.AggregateOrderDirection.{{DIR}};  // Ascending or Descending
```

### MAX_RECORDS_LINE (if specified)

```csharp
dbAgg.MaxRecords = {{MAX_RECORDS}};
```

## Required imports

```
- System.Linq
- OutSystems.Model
- OutSystems.Model.Data
- OutSystems.Model.UI.Mobile
- OutSystems.Model.Enumerations
```

## Verification

After publish, probe via applyModelApiCode:

```csharp
var screen = ...;
foreach (var agg in screen.ScreenAggregates) {
    Console.WriteLine($"  {agg.Name}: source={agg.AsDatabaseAggregate.Sources.First().Entity.Name}");
}
```

Should list each authored aggregate with correct source entity.

## Notes

- **Aggregate scope**: ScreenAggregates are local to one screen. To share data across screens, factor the query into a ServiceAction returning a list of records.
- **Source must be public**: Producer entity must have `IsPublic=true` (Recipe 01/02 v2 bakes this; verify via `99_verify_entities`).
- **Filter expressions**: Can reference local variables, screen inputs, builtin functions (GetUserId, CurrDateTime, etc.). Avoid bare strings — wrap in `"value"`.
- **The order-by enum**: `OutSystems.Model.Enumerations.AggregateOrderDirection` has `Ascending` and `Descending` only.

## Followup recipes

After aggregates land:
- Recipe 23 chrome wrap can now bind BlockInstance inputs to `{{AGGREGATE_NAME}}.List.Current.{{FIELD}}` expressions
- Screen actions (Recipe 05a) can call `{{AGGREGATE_NAME}}.Refresh()` to re-query

## Related

- `[[odc_mcp_record_literal_via_typed_local]]` — when filter values need entity record creation
- `[[odc_server_request_timeout]]` — set ServerRequestTimeout high if aggregate calls slow producers
- `[[FRAMEWORK_REVIEW]]` — aggregates are P1 gap; this recipe closes it
