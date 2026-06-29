# Recipe 06 — Server Action (Multi-step workflow with branches + exception handlers)

## Purpose

Create ONE Server Action whose flow is a directed graph of nodes — typical shape:

```
Start
  ↓
Aggregate (load context)
  ↓
ExecuteAction (do work A)
  ↓
If (branch on condition)
  ├ True  → ExecuteAction (do work B)
  ├ False → Assign (do nothing, set flag)
  ↓
ExecuteAction (do work C)
  ↓
End
```

Covers two real Home Banking patterns:
- **Aggregate-then-branch** (Sidebar_ChangeStatus): load lookup data, then branch on input flags, conditionally call notification services
- **AI pipeline** (ValidateDocument): aggregate context → external LLM call → regex strip → JSON deserialize → assign

For straight-line wrappers, use [04_action_crud](./04_action_crud.md). For SQL-heavy actions, use [05_action_sql_update](./05_action_sql_update.md). For list-iteration, use [16_action_foreach_list](./16_action_foreach_list.md).

## When to use

- Action has 4+ nodes including at least one IF or ExceptionHandler
- Flow depends on input flags (NotifyUser, IsPushEnabled, etc.)
- AI/LLM call requires post-processing (regex strip, JSON deserialize)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ACTION_NAME}}` | PascalCase | `Sidebar_ChangeStatus` |
| `{{IS_PUBLIC}}` | `true` if cross-app | `false` |
| `{{INPUTS_BLOCK}}` | All input parameters | (see example) |
| `{{OUTPUTS_BLOCK}}` | All output parameters | (see example) |
| `{{LOCALS_BLOCK}}` | Local variables for intermediate values | `AddLocal(a, "FirebaseUrl", eSpace.TextType);` |
| `{{NODES_AND_WIRING}}` | The node graph (see Flow-DSL below) | (see example) |

## Flow-DSL for `{{NODES_AND_WIRING}}`

Each node-creation line takes one of these shapes:

```csharp
// Aggregate
var agg = CreateAgg(a, "GetX", <entityRef>, "FilterCond", "SortAttr");

// ExecuteAction (Server or Service)
var call = CreateCall(a, "Call_Name", targetActionRef);
BindArg(call, "ParamName", "value-expression");

// If
var ifNode = CreateIf(a, "BranchName", "ConditionExpression");

// Assign
var assign = CreateAssign(a, "AssignName");
AddAssignment(assign, "VarName", "expression");

// SQL (use 05_action_sql_update for SQL-heavy; here only for inline mutations)
var sql = CreateSql(a, "Name", "SQL statement");
BindSqlArg(sql, "ParamName", "expression");

// Exception handler
var eh = CreateEH(a, "OnError", exceptionType, abortTransaction: false);
```

Wiring uses `node.Target = nextNode` for unconditional edges, and `ifNode.TrueTarget = X; ifNode.FalseTarget = Y` for branches.

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    // Helpers — generic, all action types
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
    void AddLocal(OutSystems.Model.Logic.IServerAction act, string name,
                   OutSystems.Model.Types.ITypeSignature type) {
        var v = act.CreateLocalVariable(name);
        v.DataType = type;
    }
    OutSystems.Model.Logic.Nodes.IExecuteServerActionNode CreateCall(
            OutSystems.Model.Logic.IServerAction act, string name,
            OutSystems.Model.Logic.IServerActionSignature target) {
        var n = act.CreateNode<OutSystems.Model.Logic.Nodes.IExecuteServerActionNode>(name);
        n.Action = target;
        return n;
    }
    void BindArg(OutSystems.Model.Logic.Nodes.IExecuteServerActionNode node,
                  string paramName, string valueExpression) {
        var arg = node.Arguments.First(a => a.Parameter.Name == paramName);
        arg.SetValue(valueExpression);
    }
    OutSystems.Model.Logic.Nodes.IIfNode CreateIf(
            OutSystems.Model.Logic.IServerAction act, string name, string condition) {
        var n = act.CreateNode<OutSystems.Model.Logic.Nodes.IIfNode>(name);
        n.SetCondition(condition);
        return n;
    }
    OutSystems.Model.Logic.Nodes.IAssignNode CreateAssign(
            OutSystems.Model.Logic.IServerAction act, string name) {
        return act.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>(name);
    }
    void AddAssignment(OutSystems.Model.Logic.Nodes.IAssignNode node, string varName, string expression) {
        var asn = node.CreateAssignment();
        asn.SetVariable(varName);
        asn.SetValue(expression);
    }

    // Create action
    var a = eSpace.CreateServerAction("{{ACTION_NAME}}");
    a.Public = {{IS_PUBLIC}};

    {{INPUTS_BLOCK}}
    {{OUTPUTS_BLOCK}}
    {{LOCALS_BLOCK}}

    {{NODES_AND_WIRING}}

    Console.WriteLine($"Recipe 06: {{ACTION_NAME}} | Created: action ({a.Nodes.Count()} nodes, {a.InputParameters.Count()} in, {a.OutputParameters.Count()} out, {a.LocalVariables.Count()} locals) | Status: OK");
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

## Expected stdout

```
Recipe 06: Sidebar_ChangeStatus | Created: action (8 nodes, 8 in, 0 out, 0 locals) | Status: OK
```

## Common failures

### ✗ `End node has no incoming edge` at publish

Cause: a branch (TrueTarget or FalseTarget on an If) doesn't terminate in End. Or an extension created orphan nodes (see `[[studio_mentor_extension_orphans_end_nodes]]`).
Fix: every leaf of every branch must `.Target = a.EndNode`. The recipe's wiring section must end every flow path.

### ✗ `Variable 'X' is read before written` at publish

Cause: an Assign or argument references a local that hasn't been written by an upstream node.
Fix: trace the flow — every variable used in an If condition or Assign expression must be set by a previous node on the same path.

### ✗ Aggregate-then-If but If can't see aggregate output

Cause: aggregates are computed inline; their `.List.Current.*` references are scoped to the aggregate's iteration, not the screen.
Fix: when filtering a single record, use `.List[0].<Entity>.<Attr>` or wrap the load in a SQL node that returns a scalar.

## Example: Sidebar_ChangeStatus (Home Banking Backoffice)

```csharp
// {{ACTION_NAME}}      = "Sidebar_ChangeStatus"
// {{INPUTS_BLOCK}}:
AddInput(a, "RequestId", loanRequest.IdentifierType, true);
AddInput(a, "NewStatusId", loanRequestStatus.IdentifierType, true);
AddInput(a, "Comment", eSpace.TextType, false);
AddInput(a, "NotifyUser", eSpace.BooleanType, true);
AddInput(a, "SendPush", eSpace.BooleanType, true);
AddInput(a, "AgentTypeId", hbAgentType.IdentifierType, false);
AddInput(a, "FromEmployeeId", employee.IdentifierType, false);
AddInput(a, "Reason", eSpace.TextType, false);
// {{NODES_AND_WIRING}}:
var firebaseLookup = CreateCall(a, "ServiceSidebar_ChangeStatusGetFirebase", svcGetFirebase);
BindArg(firebaseLookup, "RequestId", "RequestId");
var ifNotify = CreateIf(a, "IfNotify", "NotifyUser");
var emailCall = CreateCall(a, "Notify_Email", svcNotifyEmail);
BindArg(emailCall, "RequestId", "RequestId");
BindArg(emailCall, "Comment", "Comment");
var ifPush = CreateIf(a, "IfPush", "SendPush");
var pushCall = CreateCall(a, "Notify_Push", svcNotifyPush);
BindArg(pushCall, "RequestId", "RequestId");
BindArg(pushCall, "FirebaseUrl", "ServiceSidebar_ChangeStatusGetFirebase.FirebaseUrl");
var skipPush = CreateAssign(a, "SkipPush");  // no-op
// Wire it up:
a.StartNode.Target = firebaseLookup;
firebaseLookup.Target = ifNotify;
ifNotify.TrueTarget = emailCall;
ifNotify.FalseTarget = a.EndNode;
emailCall.Target = ifPush;
ifPush.TrueTarget = pushCall;
ifPush.FalseTarget = skipPush;
pushCall.Target = a.EndNode;
skipPush.Target = a.EndNode;
```

### Example: ValidateDocument AI-pipeline

```csharp
// 5-node pipeline: Aggregate → Call (LLM) → Call (Regex) → Call (JSON Deserialize) → Assign
var docTypeLookup = CreateAgg(a, "GetDocType", hbDocumentTypeEntity, "HBDocumentType.Id = HBDocumentTypeId", null);
var llmCall = CreateCall(a, "Call_DocumentValidator", svcDocValidator);
BindArg(llmCall, "AgentsConsumerApp", "Entities.AgentsConsumerApp.HomeBanking");
BindArg(llmCall, "Binary", "Binary");
BindArg(llmCall, "LocaleId", "LocaleId");
BindArg(llmCall, "Filename", "Filename");
BindArg(llmCall, "UserMessage", "\"Validate this \" + GetDocType.List.Current.HBDocumentType.Label");
llmCall.ServerRequestTimeout = 60;  // LLM call — extend per [[odc_server_request_timeout]]
var regexCall = CreateCall(a, "Regex_Strip", svcRegexReplace);
BindArg(regexCall, "InputText", "Call_DocumentValidator.ResponseText");
BindArg(regexCall, "Pattern", "\"^.*?(\\[\\{.*?\\}\\]).*$\"");
BindArg(regexCall, "Replacement", "\"$1\"");
var jsonCall = CreateCall(a, "JSON_Deserialize", svcJsonDeserialize);
BindArg(jsonCall, "Json", "Regex_Strip.Output");
var setOutput = CreateAssign(a, "SetOutput");
AddAssignment(setOutput, "DocumentValidationResponse", "JSON_Deserialize.Data");
// Wire:
a.StartNode.Target = docTypeLookup;
docTypeLookup.Target = llmCall;
llmCall.Target = regexCall;
regexCall.Target = jsonCall;
jsonCall.Target = setOutput;
setOutput.Target = a.EndNode;
```

## Memory refs

- [[odc_server_request_timeout]] — set ServerRequestTimeout for LLM/Bedrock calls
- [[studio_mentor_extension_orphans_end_nodes]] — workflow editing wall to avoid
- [[odc_mcp_mentor_diagnose_before_fix]] — when runtime fails, diagnose first
- [[odc_mcp_record_literal_via_typed_local]] — for inline entity-record args

## Related recipes

- [04_action_crud](./04_action_crud.md) — light wrappers without branches
- [05_action_sql_update](./05_action_sql_update.md) — SQL-heavy actions
- [16_action_foreach_list](./16_action_foreach_list.md) — list-iteration pattern
