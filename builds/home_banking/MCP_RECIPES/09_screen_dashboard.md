# Recipe 09 — Screen (Dashboard — KPIs + chart + recent-activity feed)

## Purpose

Create ONE dashboard screen — the customer/admin home screen with:

- 3-6 KPI cards across the top (Total Balance, Total Assets, Total Debt, etc.)
- A primary chart in the middle (line/column over time, e.g., income vs expenses)
- A scrollable recent-activity feed (last N transactions, last N notifications)
- A side panel of cards for "For you" / "Action items"

Maps to Portal/Dashboard (7 aggregates, 14 locals, ~250 widgets visible) and Backoffice/Dashboard (queue counters + recent activity for underwriters).

## When to use

- Top-level app home screen
- Hosts multiple aggregates (5+) feeding diverse widgets (KPIs, lists, charts)
- Has multiple visible-when conditions tied to user role / device size

For single-source list screens, use [07_screen_table](./07_screen_table.md).

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{SCREEN_NAME}}` | PascalCase | `Dashboard` |
| `{{ROLE_NAME}}` | Required role | `HomeBankingPortal` |
| `{{TITLE_EXPR}}` | Title (often `""` for dashboard) | `""` |
| `{{LOCALS_BLOCK}}` | Screen local variables | `AddLocal(s, "SelectedAccountId", hbAccount.IdentifierType);` |
| `{{AGGREGATES_BLOCK}}` | Multi-entity aggregates feeding the dashboard | (see example) |
| `{{KPI_BLOCK}}` | KPI card definitions | (see example) |
| `{{CHART_BLOCK}}` | Chart widget config | (see example) |
| `{{ACTIVITY_FEED_BLOCK}}` | Feed widget config | (see example) |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var mainFlow = eSpace.MobileFlows.First(f => f.Name == "MainFlow");
    var role = eSpace.Roles.FirstOrDefault(r => r.Name == "{{ROLE_NAME}}")
        ?? eSpace.References.SelectMany(r => r.Roles).First(r => r.Name == "{{ROLE_NAME}}");

    var screen = mainFlow.CreateScreen("{{SCREEN_NAME}}");
    screen.SetTitle({{TITLE_EXPR}});
    screen.Roles.Add(role);

    // Helpers
    void AddLocal(string name, OutSystems.Model.Types.ITypeSignature type) {
        var v = screen.CreateLocalVariable(name);
        v.DataType = type;
    }
    OutSystems.Model.UI.Mobile.IScreenAggregate AddAggregate(string name,
            OutSystems.Model.Data.IServerEntitySignature entity,
            int maxRecords) {
        var a = screen.CreateScreenAggregate(false, name);
        a.Fetch = OutSystems.Model.Enumerations.DataSourceFetch.AtStart;
        a.SetMaxRecords(maxRecords.ToString());
        a.AsDatabaseAggregate.CreateSource(entity);
        return a;
    }

    {{LOCALS_BLOCK}}
    {{AGGREGATES_BLOCK}}

    // Layout blocks — caller fills in OS UI widget composition
    // (these are placeholders for the actual widget tree;
    // the recipe focuses on the data + aggregates layer)
    {{KPI_BLOCK}}
    {{CHART_BLOCK}}
    {{ACTIVITY_FEED_BLOCK}}

    Console.WriteLine($"Recipe 09: {{SCREEN_NAME}} | Created: dashboard ({screen.Aggregates.Count()} aggs, {screen.LocalVariables.Count()} locals, role={role.Name}) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Enumerations
OutSystems.Model.UI.Mobile
OutSystems.Model.Types
```

## Expected stdout

```
Recipe 09: Dashboard | Created: dashboard (7 aggs, 14 locals, role=HomeBankingPortal) | Status: OK
```

## Common failures

### ✗ Dashboard loads slowly (>3s TTI)

Cause: 7+ aggregates running at-start in parallel + N+1 on related entities.
Fix: convert non-critical aggregates to `Fetch = OnDemand` or `OnVisibilityChange`. Per `[[odc_server_request_timeout]]`, extend timeout to 30s if any aggregate is genuinely slow.

### ✗ KPI card shows "0" instead of computed value

Cause: aggregate fetched but the calculated attribute expression is wrong or refers to a missing column.
Fix: probe the aggregate via Mentor with `applyModelApiCode` reading `agg.AsDatabaseAggregate.CalculatedAttributes` — verify the expression.

### ✗ Chart widget doesn't render

Cause: data-action returns `null` or wrong shape. ColumnChart expects `ChartDataPoints` (List of ChartDataPoint records).
Fix: add a data-action that wraps the chart aggregate + projects to the OS Charts library's data-point shape.

## Example: Portal/Dashboard

```yaml
SCREEN_NAME: Dashboard
ROLE_NAME: HomeBankingPortal
TITLE_EXPR: '""'
LOCALS_BLOCK: |
  AddLocal("SelectedAccountId", hbAccount.IdentifierType);
  AddLocal("SelectedChartDataOptionId", chartDataOption.IdentifierType);
  AddLocal("Accounts", listOfHBAccount);
  AddLocal("ChartHeight", eSpace.IntegerType);
  AddLocal("TotalBalance", eSpace.CurrencyType);
  AddLocal("TotalAssets", eSpace.CurrencyType);
  AddLocal("TotalDept", eSpace.CurrencyType);
  AddLocal("IsDeptConsolidatedPositionOption", eSpace.BooleanType);
  AddLocal("HideChart", eSpace.BooleanType);
  AddLocal("DeptList", listOfDeptRecord);
  AddLocal("ChartCardsValue", chartCardsValueStruct);
  AddLocal("IsPortrait", eSpace.BooleanType);
  AddLocal("ChatMessages", listOfChatMessage);
  AddLocal("IsWaitingForResponse", eSpace.BooleanType);
  AddLocal("ChartOptionList", listOfChartOption);
AGGREGATES_BLOCK: |
  var aGetAccounts = AddAggregate("GetAccounts", hbAccount, 6);
  // [filters/joins/group-by configured here per Portal Dashboard sample — see _raw/portal-dashboard.summary.md]
  var aGetAssets = AddAggregate("GetAssets", hbAccount, 999);
  var aGetCreditCardsDept = AddAggregate("GetCreditCardsDept", hbAccount, 999);
  var aGetChartDataOptions = AddAggregate("GetChartDataOptions", chartDataOption, 10);
  var aGetCustomerGoals = AddAggregate("GetCustomerGoals", customerGoal, 50);
  var aGetCustomerLoans = AddAggregate("GetCustomerLoans", customerLoan, 50);
  var aGetLastTransactions = AddAggregate("GetLastTransactions", transaction, 10);
```

## Memory refs

- [[mentor_web_one_dashboard_per_app]] — Mentor Web refuses multiple Dashboards
- [[odc_dark_mode_needs_js_toggle]] — dashboards usually want dark mode toggle
- [[odc_mcp_screen_scope_wall]] — keep dashboard widget count below the session wall

## Related recipes

- [07_screen_table](./07_screen_table.md) — for the "View All" destinations
- [10_theme_replace](./10_theme_replace.md) — dashboard typically needs custom theme polish
