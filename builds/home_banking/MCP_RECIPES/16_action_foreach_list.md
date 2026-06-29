# Recipe 16 — Server Action (ForEach over input list, per-item Service Action call)

## Purpose

Create ONE Server Action that takes a list of records as input and calls a producer Service Action once per item. Pattern source: Home Banking Backoffice `RequestAssignEmployeeBulk` — given a `RequestList` (List of LoanRequest) and an `EmployeeId`, iterate and call `ServiceRequestAssigned(RequestId, EmployeeId)` per item.

For single-row CRUD use the auto-generated `EntityName_Create`/`EntityName_Update` actions. For multi-step branching workflows use [06_action_workflow](./06_action_workflow.md).

## When to use

- Bulk operation triggered from a multi-select UI (assign N requests to Employee X)
- Each item runs the same Service Action with a per-item argument
- Don't care about per-item failure isolation (use [06_action_workflow](./06_action_workflow.md) with an exception handler instead for fault-tolerant bulk)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ACTION_NAME}}` | PascalCase | `RequestAssignEmployeeBulk` |
| `{{IS_PUBLIC}}` | `true` if cross-app callable | `false` |
| `{{LIST_INPUT_NAME}}` | Name of the input list parameter | `RequestList` |
| `{{LIST_ELEMENT_TYPE}}` | C# expression resolving the list-of-X type signature | `eSpace.GetListType(loanRequest.IdentifierType)` |
| `{{PER_ITEM_ARG_BLOCK}}` | Additional inputs that are passed per-item to the target action | `AddInput(a, "EmployeeId", employee.IdentifierType, true);` |
| `{{TARGET_SERVICE_ACTION}}` | The Service Action called per-item | `ServiceRequestAssigned` |
| `{{PRODUCER_MODULE}}` | Module hosting the Service Action | `HomeBankingCore` |
| `{{PER_ITEM_ARGS_BINDING}}` | How the per-item args are bound on the ExecuteAction node | `BindArg(call, "RequestId", "RequestList.Current"); BindArg(call, "EmployeeId", "EmployeeId");` |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    // Resolve target Service Action
    var producer = eSpace.References.Named("{{PRODUCER_MODULE}}");
    var targetSA = producer.ServerActions.Named("{{TARGET_SERVICE_ACTION}}");

    // Helpers (same as other action recipes)
    void AddInput(OutSystems.Model.Logic.IServerAction act, string name,
                   OutSystems.Model.Types.ITypeSignature type, bool mandatory) {
        var p = act.CreateInputParameter(name);
        p.DataType = type;
        p.IsMandatory = mandatory;
    }
    void BindArg(OutSystems.Model.Logic.Nodes.IExecuteServerActionNode node,
                  string paramName, string valueExpression) {
        var arg = node.Arguments.First(a => a.Parameter.Name == paramName);
        arg.SetValue(valueExpression);
    }

    // Create action
    var a = eSpace.CreateServerAction("{{ACTION_NAME}}");
    a.Public = {{IS_PUBLIC}};

    // List input
    var listInput = a.CreateInputParameter("{{LIST_INPUT_NAME}}");
    listInput.DataType = {{LIST_ELEMENT_TYPE}};
    listInput.IsMandatory = true;

    // Per-item args (additional inputs not in the list)
    {{PER_ITEM_ARG_BLOCK}}

    // ForEach node — iterates the list input
    var loop = a.CreateNode<OutSystems.Model.Logic.Nodes.IForEachNode>("ForEach_{{LIST_INPUT_NAME}}");
    loop.SetRecordList("{{LIST_INPUT_NAME}}");

    // Per-item ExecuteAction — wired as the loop's body (NOT loop.Target;
    // body is reached via the back-edge per [[odc_foreach_body_back_edge]])
    var call = a.CreateNode<OutSystems.Model.Logic.Nodes.IExecuteServerActionNode>("Call_{{TARGET_SERVICE_ACTION}}");
    call.Action = targetSA;
    {{PER_ITEM_ARGS_BINDING}}

    // Wire ForEach: Start → loop ; loop body cycles back into call → loop ; loop → End on completion
    a.StartNode.Target = loop;
    loop.CycleTarget = call;   // back-edge — runs once per item
    call.Target = loop;         // call completes → next iteration
    loop.Target = a.EndNode;    // loop completes → end

    Console.WriteLine($"Recipe 16: {{ACTION_NAME}} | Created: foreach ({a.Nodes.Count()} nodes, list={a.InputParameters.First().Name}) | Status: OK");
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
Recipe 16: RequestAssignEmployeeBulk | Created: foreach (3 nodes, list=RequestList) | Status: OK
```

## Common failures

### ✗ ForEach body runs 0 times

Cause: misunderstood the ForEach API — `loop.Target` is the EXIT edge (loop done), not the body. The body is reached via `loop.CycleTarget` (back-edge).
Fix: per `[[odc_foreach_body_back_edge]]`, use `loop.CycleTarget = body` for per-item execution. The recipe sets this correctly; the failure happens when someone "fixes" the recipe to use `loop.Target`.

### ✗ ForEach body runs once for ALL items at once (not per-item)

Cause: the per-item ExecuteAction is treated as a single bulk call. Usually because the per-item argument expression refers to the whole list, not `<ListName>.Current`.
Fix: ensure all per-item arguments use `<ListName>.Current.<field>` (or just `<ListName>.Current` if the list is a list of identifiers).

### ✗ Long-running bulk operations hit timeout

Cause: 100+ item list with each call taking 200ms = 20s total, exceeds default 10s.
Fix: set `call.ServerRequestTimeout = 60` if the per-item call is slow. For very long lists (1000+), batch into chunks of ~50 via SQL or split into multiple async invocations.

## Example: RequestAssignEmployeeBulk (Home Banking Backoffice)

```yaml
ACTION_NAME: RequestAssignEmployeeBulk
IS_PUBLIC: false
LIST_INPUT_NAME: RequestList
LIST_ELEMENT_TYPE: 'eSpace.GetListType(loanRequest.IdentifierType)'
PER_ITEM_ARG_BLOCK: |
  AddInput(a, "EmployeeId", employee.IdentifierType, true);
TARGET_SERVICE_ACTION: ServiceRequestAssigned
PRODUCER_MODULE: HomeBankingCore
PER_ITEM_ARGS_BINDING: |
  BindArg(call, "RequestId", "RequestList.Current");
  BindArg(call, "EmployeeId", "EmployeeId");
```

## Memory refs

- [[odc_foreach_body_back_edge]] — `loop.CycleTarget` is the body, NOT `loop.Target`
- [[odc_long_integer_to_identifier_cast]] — when list-of-Long-Integer needs to cast to Identifier inside the binding

## Related recipes

- [04_action_crud](./04_action_crud.md) — single-item wrapper that this recipe iterates
- [06_action_workflow](./06_action_workflow.md) — for fault-tolerant bulk (with exception handler)
