# Recipe 05 — Server Action (SQL Update/Insert/Delete with idempotency)

## Purpose

Create ONE Server Action that runs a parameterized SQL statement against one or more local entities. Use cases:

- Bulk UPDATE that's too narrow for a per-row Aggregate+Update pattern
- INSERT into a join table or audit log
- DELETE with non-trivial WHERE
- Atomic Read-Modify-Write that aggregate-then-update can't express

For per-row entity CRUD (Create one Customer, Update one Loan), use the auto-generated `EntityName_Create` / `EntityName_Update` actions — those don't need a recipe. Per `[[odc_mcp_entity_auto_actions_incomplete]]`, only Create + DeleteAll are auto-generated; Update/Delete by Id need user wrappers (use [06_action_workflow](./06_action_workflow.md) for those).

## When to use

- The SQL is the *whole* point of the action
- You need WHERE / GROUP BY / window functions that Aggregate doesn't support cleanly
- You're writing an idempotent server action (use exception-handler-and-retry pattern below)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ACTION_NAME}}` | PascalCase action name | `PackageAndSubmitReport` |
| `{{IS_PUBLIC}}` | `true` if cross-app callable | `false` |
| `{{INPUTS_BLOCK}}` | Input parameter declarations | `AddInput(a, "ReportId", reportEntity.IdentifierType, true);` |
| `{{OUTPUTS_BLOCK}}` | Output parameter declarations | (empty for fire-and-forget) |
| `{{SQL_STATEMENT}}` | The SQL statement, with `@ParamName` references | `UPDATE {Report} SET [Status]=2 WHERE [Id]=@ReportId` |
| `{{SQL_PARAMS_BLOCK}}` | Each line declares one SQL param + binds an expression | `BindSqlArg(sql, "ReportId", "ReportId");` |
| `{{EXCEPTION_HANDLERS_BLOCK}}` | Optional: per-exception handlers | (see workflow recipe for examples) |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    // Helpers
    void AddInput(OutSystems.Model.Logic.IServerAction act, string name,
                   OutSystems.Model.Types.ITypeSignature type, bool mandatory) {
        var p = act.CreateInputParameter(name);
        p.DataType = type;
        p.IsMandatory = mandatory;
    }
    void AddOutput(OutSystems.Model.Logic.IServerAction act, string name,
                    OutSystems.Model.Types.ITypeSignature type) {
        var p = act.CreateOutputParameter(name);
        p.DataType = type;
    }
    void BindSqlArg(OutSystems.Model.Logic.Nodes.ISQLNode sqlNode, string paramName, string expression) {
        var p = sqlNode.CreateInputParameter(paramName);
        var arg = sqlNode.Arguments.First(a => a.Parameter.Name == paramName);
        arg.SetValue(expression);
    }

    // Create action
    var a = eSpace.CreateServerAction("{{ACTION_NAME}}");
    a.Public = {{IS_PUBLIC}};

    {{INPUTS_BLOCK}}
    {{OUTPUTS_BLOCK}}

    // SQL node
    var sql = a.CreateNode<OutSystems.Model.Logic.Nodes.ISQLNode>("Exec_SQL");
    sql.Statement = @"{{SQL_STATEMENT}}";
    {{SQL_PARAMS_BLOCK}}

    // Wire flow: Start → SQL → End
    a.StartNode.Target = sql;
    sql.Target = a.EndNode;

    {{EXCEPTION_HANDLERS_BLOCK}}

    Console.WriteLine($"Recipe 05: {{ACTION_NAME}} | Created: action (1 SQL node, {a.InputParameters.Count()} in, {a.OutputParameters.Count()} out) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Logic
OutSystems.Model.Logic.Nodes
OutSystems.Model.Types
```

## SQL statement conventions

- Reference entities with `{EntityName}` braces — ODC resolves these at compile time to the actual physical table name.
- Reference attributes with `[AttributeName]` brackets.
- Parameters are `@ParameterName` — created via `sql.CreateInputParameter` then bound via `BindSqlArg` (the binding evaluates the expression at call time and substitutes).
- For multi-statement SQL (e.g., INSERT then UPDATE), separate with `;` — ODC executes as one batch.

## Expected stdout

```
Recipe 05: PackageAndSubmitReport | Created: action (1 SQL node, 1 in, 0 out, 3 nodes) | Status: OK
```

## Common failures

### ✗ `Invalid object name '{Report}'` at runtime

Cause: SQL is referencing an entity name that doesn't exist in this app's namespace. Most common: entity is in a referenced module but you used the unqualified name.
Fix: use `{ModuleName.EntityName}` for cross-module entity refs, OR pull the entity into local scope via Manage Dependencies (Studio-only).

### ✗ `Must declare the scalar variable "@ParamName"` at runtime

Cause: SQL references `@X` but no matching `sql.CreateInputParameter("X")` was made, or the parameter is declared but `BindSqlArg` didn't run to set its value expression.
Fix: every `@X` in the SQL needs both a `CreateInputParameter("X")` AND a `BindArg(sql, "X", "<expression>")`. The recipe's `BindSqlArg` does both.

### ✗ Action runs but no rows updated

Cause: WHERE clause doesn't match. Most common: type mismatch between attribute and parameter (e.g., comparing Long Integer to passed-in Integer).
Fix: explicit cast in SQL: `WHERE [Id] = LongIntegerToIdentifier(@ReportId)` per `[[odc_long_integer_to_identifier_cast]]`. Or fix the parameter type to match the column.

## Example: PackageAndSubmitReport (ComplianceOpsConsole — from prior session)

```csharp
// {{ACTION_NAME}}     = "PackageAndSubmitReport"
// {{IS_PUBLIC}}       = false
// {{INPUTS_BLOCK}}:
AddInput(a, "ReportId", reportEntity.IdentifierType, true);
AddInput(a, "SubmittedById", userIdentType, true);
// {{OUTPUTS_BLOCK}}:  (empty)
// {{SQL_STATEMENT}}:
UPDATE {Report}
SET    [Status]              = 2,    -- Submitted
       [SubmittedAt]          = CURRENT_TIMESTAMP,
       [SubmittedById]        = @SubmittedById,
       [PackagedBundleHash]   = LOWER(CONVERT(NVARCHAR(64), HASHBYTES('SHA2_256', CAST([Id] AS NVARCHAR(100))), 2))
WHERE  [Id]                   = @ReportId
  AND  [Status]               = 1     -- only Draft → Submitted
// {{SQL_PARAMS_BLOCK}}:
BindSqlArg(sql, "ReportId", "ReportId");
BindSqlArg(sql, "SubmittedById", "SubmittedById");
// {{EXCEPTION_HANDLERS_BLOCK}}: (empty)
```

## Memory refs

- [[odc_long_integer_to_identifier_cast]] — Long Integer → Identifier casts in SQL parameters
- [[odc_mcp_sql_node_api]] — ISQLNode Statement/CreateInputParameter/SetArgumentValue surface
- [[odc_mcp_entity_auto_actions_incomplete]] — only Create + DeleteAll auto-generated

## Related recipes

- [01_entity_server](./01_entity_server.md) — for the entity this SQL writes to
- [04_action_crud](./04_action_crud.md) — for non-SQL CRUD wrappers
- [06_action_workflow](./06_action_workflow.md) — for SQL inside a multi-step branching flow
