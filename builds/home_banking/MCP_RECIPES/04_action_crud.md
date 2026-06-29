# Recipe 04 — Server Action (CRUD wrapper / multi-output projection)

## Purpose

Create ONE Server Action that does light-weight work — a thin wrapper around another Service Action, OR a multi-output config-load that combines several upstream outputs into local outputs. Covers two patterns observed in Home Banking:

- **Thin wrapper** (CheckAndGrantRole): Start → ExecuteAction → End. 2 nodes.
- **Multi-output projection** (Get_Settings): Start → ExecuteAction(s) → Assign mapping → End. 3-4 nodes.

For multi-step branching workflows, use [06_action_workflow](./06_action_workflow.md) instead. For SQL-heavy actions, use [05_action_sql_update](./05_action_sql_update.md).

## When to use

- Thin Service-Action delegation (auth gate, role grant, simple lookup)
- Loading config from multiple upstream sources and projecting to local outputs

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ACTION_NAME}}` | PascalCase action name | `CheckAndGrantRole` |
| `{{IS_PUBLIC}}` | `true` if cross-app callable | `false` |
| `{{INPUTS_BLOCK}}` | Input parameter declarations (see syntax) | `AddInput(a, "UserId", userIdentType, true);` |
| `{{OUTPUTS_BLOCK}}` | Output parameter declarations | `AddOutput(a, "Currency", eSpace.TextType);` |
| `{{TARGET_SERVICE_ACTION}}` | Name of the producer-app Service Action being wrapped | `GrantHBPortalRole` |
| `{{PRODUCER_MODULE}}` | Module name where the Service Action lives | `HomeBankingCore` |
| `{{ARG_BINDINGS}}` | Inline `arg.Parameter.Name = "value"` per upstream input arg | `BindArg(call, "UserId", "UserId");` |
| `{{OUTPUT_ASSIGNMENTS_BLOCK}}` | Optional Assign-node mappings (multi-output projection only) | `assign.CreateAssignment().SetVariable("Currency").SetValue("ServiceGetSettings.Currency");` |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    // FK/identifier resolution (only if your inputs reference identities)
    var userIdentType = eSpace.References.SelectMany(r => r.Entities)
        .First(e => e.Name == "User").IdentifierType;

    // Producer module reference (for the Service Action being wrapped)
    var producer = eSpace.References.Named("{{PRODUCER_MODULE}}");
    var targetSA = producer.ServerActions.Named("{{TARGET_SERVICE_ACTION}}");

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
    void BindArg(OutSystems.Model.Logic.Nodes.IExecuteServerActionNode node,
                  string paramName, string valueExpression) {
        var arg = node.Arguments.First(a => a.Parameter.Name == paramName);
        arg.SetValue(valueExpression);
    }

    // Create action
    var a = eSpace.CreateServerAction("{{ACTION_NAME}}");
    a.Public = {{IS_PUBLIC}};

    {{INPUTS_BLOCK}}
    {{OUTPUTS_BLOCK}}

    // Flow: Start → ExecuteAction → (optional Assign) → End
    var call = a.CreateNode<OutSystems.Model.Logic.Nodes.IExecuteServerActionNode>("Call_{{TARGET_SERVICE_ACTION}}");
    call.Action = targetSA;
    {{ARG_BINDINGS}}

    // Optional: multi-output projection — uncomment + fill if you have outputs to assign
    // var assign = a.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>("Set Outputs");
    // {{OUTPUT_ASSIGNMENTS_BLOCK}}
    // call.Target = assign;
    // assign.Target = a.EndNode;

    // Without an Assign (thin wrapper): create Start + End nodes and wire
    // via call.Target.
    //
    // Empirical: IServerAction.StartNode/EndNode properties don't exist;
    // newly-created actions have empty .Nodes collection. Use:
    //   var startNode = a.CreateNode<IStartNode>();
    //   var endNode   = a.CreateNode<IEndNode>();
    //   startNode.Target = call;
    //   call.Target = endNode;
    // For STUB (no intermediate): endNode.ConnectedBelow(startNode);
    var startNode = a.CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>();
    var endNode   = a.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>();
    startNode.Target = call;
    call.Target = endNode;

    Console.WriteLine($"Recipe 04: {{ACTION_NAME}} | Created: action (Public={a.Public}, {a.InputParameters.Count()} in, {a.OutputParameters.Count()} out, {a.Nodes.Count()} nodes) | Status: OK");
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
Recipe 04: CheckAndGrantRole | Created: action (Public=False, 1 in, 0 out, 3 nodes) | Status: OK
```

## Common failures

### ✗ `Could not find Server Action 'X' in module 'Y'`

Cause: the producer Service Action isn't visible to this app. Either the producer's Service Action isn't Public, or the consumer hasn't added a reference via Manage Dependencies.
Fix: per `[[odc_mcp_reference_add_studio_only]]`, open the consumer in Studio (Cmd+Q) and add the dependency. Then re-run.

### ✗ `Argument 'X' has no value expression`

Cause: forgot to call `BindArg(...)` for a mandatory input arg.
Fix: every mandatory parameter on the target action needs an explicit `BindArg`. Use the producer's signature from `app_refs` to verify.

### ✗ ServerRequestTimeout

Cause: target action is an LLM/Bedrock call exceeding 10s.
Fix: set `call.ServerRequestTimeout = 60` (60 seconds). Per `[[odc_server_request_timeout]]`.

## Examples

### Thin wrapper — CheckAndGrantRole (Home Banking Portal)

```csharp
// {{ACTION_NAME}}              = "CheckAndGrantRole"
// {{IS_PUBLIC}}                = false
// {{TARGET_SERVICE_ACTION}}    = "GrantHBPortalRole"
// {{PRODUCER_MODULE}}          = "HomeBankingCore"
// {{INPUTS_BLOCK}}:
AddInput(a, "UserId", userIdentType, true);
// {{OUTPUTS_BLOCK}}:           (empty — no outputs)
// {{ARG_BINDINGS}}:
BindArg(call, "UserId", "UserId");
// {{OUTPUT_ASSIGNMENTS_BLOCK}}: (empty — no assign)
```

### Multi-output projection — Get_Settings (Home Banking Portal)

```csharp
// {{ACTION_NAME}}              = "Get_Settings"
// {{IS_PUBLIC}}                = false
// {{TARGET_SERVICE_ACTION}}    = "ServiceGetSettings"
// {{PRODUCER_MODULE}}          = "HomeBankingCore"
// {{INPUTS_BLOCK}}:            (empty)
// {{OUTPUTS_BLOCK}}:
AddOutput(a, "Currency", eSpace.TextType);
AddOutput(a, "GroupSeparator", eSpace.TextType);
AddOutput(a, "DecimalSeparator", eSpace.TextType);
AddOutput(a, "SessionId", eSpace.TextType);
AddOutput(a, "GoogleAnalyticsTrackingID", eSpace.TextType);
AddOutput(a, "IsDemoAccessCookieEnabled", eSpace.BooleanType);
// {{ARG_BINDINGS}}:            (empty — ServiceGetSettings takes no inputs)
// {{OUTPUT_ASSIGNMENTS_BLOCK}}:
assign.CreateAssignment().SetVariable("Currency").SetValue("Call_ServiceGetSettings.Currency");
assign.CreateAssignment().SetVariable("GroupSeparator").SetValue("Call_ServiceGetSettings.GroupSeparator");
assign.CreateAssignment().SetVariable("DecimalSeparator").SetValue("Call_ServiceGetSettings.DecimalSeparator");
assign.CreateAssignment().SetVariable("SessionId").SetValue("NewGuid()");
assign.CreateAssignment().SetVariable("GoogleAnalyticsTrackingID").SetValue("Settings.AnalyticsTrackingID");
assign.CreateAssignment().SetVariable("IsDemoAccessCookieEnabled").SetValue("Settings.IsDemoAccessCookieEnabled");
```

## Memory refs

- [[odc_mcp_reference_add_studio_only]] — cross-app references require Studio
- [[odc_server_request_timeout]] — 10s default timeout on screen→server calls
- [[odc_mcp_record_literal_via_typed_local]] — when wrapping needs to construct a record arg

## Related recipes

- [05_action_sql_update](./05_action_sql_update.md) — for actions doing SQL writes
- [06_action_workflow](./06_action_workflow.md) — for multi-step workflows with branches
- [16_action_foreach_list](./16_action_foreach_list.md) — for actions that batch over a list
