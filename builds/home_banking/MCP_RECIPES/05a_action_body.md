# Recipe 05a — Action Body Authoring (from capture)

**Purpose**: Author the real C# logic body of a Service Action from a captured flow tree. Replaces Recipe 04's Start→End stub with real work.

**When to use**: After Recipe 04 (action stub exists). Per-action. Requires `<ActionName>.action.tree.md` capture file.

## Grammar (manifest extension)

Add to `actions.yaml`:

```yaml
- name: SubmitTransfer
  app: home_banking_core
  kind: service                        # service_action; recipe forces Public=true
  inputs:
    - name: FromAccountId
      type: HBAccount Identifier
      mandatory: true
    - name: ToAccountId
      type: HBAccount Identifier
      mandatory: true
    - name: Amount
      type: Currency
      mandatory: true
  outputs:
    - name: TransactionId
      type: Transaction Identifier
    - name: Success
      type: Boolean
  body_capture: SubmitTransfer.action.tree.md   # NEW — path to captured flow tree
```

## Capture format expected

`<ActionName>.action.tree.md` contains the captured flow as a tree of typed nodes:

```
- Start
- Assign
    - Variable: TransactionId
    - Value: NullIdentifier()
- ExecuteAction (HBCore/CreateTransaction)
    - From: FromAccountId
    - To: ToAccountId
    - Amount: Amount
    - Out: NewTransactionId
- Assign
    - Variable: TransactionId
    - Value: NewTransactionId
- Assign
    - Variable: Success
    - Value: True
- End
```

(Capture playbook details in CAPTURE_PLAYBOOK.md.)

## C# body (skeleton — actual emits per-node from capture parser)

```csharp
eSpace => {
    var action = eSpace.ServiceActions.FirstOrDefault(a => a.Name == "{{ACTION_NAME}}");
    if (action == null) { Console.WriteLine("FAIL: action not found"); return; }
    
    // Clear stub body (Start → End from Recipe 04)
    var startNode = action.Nodes.OfType<OutSystems.Model.Logic.Nodes.IStartNode>().First();
    foreach (var existing in action.Nodes.OfType<OutSystems.Model.Logic.Nodes.IEndNode>().ToArray()) {
        existing.Delete();
    }
    
    // Per-node emit from captured tree (renderer generates these from .action.tree.md)
    {{NODE_EMIT_BLOCK}}
    
    Console.WriteLine($"Recipe 05a: {{ACTION_NAME}} | body authored, {action.Nodes.Count()} nodes | Status: OK");
}
```

## NODE_EMIT_BLOCK patterns

### Assign node

```csharp
var assign0 = action.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>().ConnectedBelow(prevNode);
assign0.CreateAssignment("{{VAR_NAME}}", "{{VALUE_EXPR}}");
var prevNode = assign0;
```

### ExecuteAction (call another action)

```csharp
var calledAction = eSpace.References
    .SelectMany(r => r.ServiceActions)
    .FirstOrDefault(a => a.Name == "{{CALLED_ACTION_NAME}}")
    ?? eSpace.ServiceActions.FirstOrDefault(a => a.Name == "{{CALLED_ACTION_NAME}}");
if (calledAction == null) { Console.WriteLine($"FAIL: called action not found"); return; }
var exec0 = action.CreateNode<OutSystems.Model.Logic.Nodes.IExecuteActionNode>().ConnectedBelow(prevNode);
exec0.Action = calledAction;
// Bind inputs
foreach (var ip in calledAction.InputParameters) {
    exec0.SetArgumentValue(ip, "{{INPUT_BINDINGS[ip.Name]}}");
}
// Bind outputs (assign to action's local vars)
foreach (var op in calledAction.OutputParameters) {
    // Output bindings go via target Variable assignment
}
var prevNode = exec0;
```

### If node (branching)

```csharp
var if0 = action.CreateNode<OutSystems.Model.Logic.Nodes.IIfNode>().ConnectedBelow(prevNode);
if0.Condition.SetValue("{{CONDITION_EXPR}}");
// True branch
var trueBranch0 = action.CreateNode<...>().ConnectedToTheTrueBranchOf(if0);
// False branch
var falseBranch0 = action.CreateNode<...>().ConnectedToTheFalseBranchOf(if0);
```

### End node (final)

```csharp
var endNode = action.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>().ConnectedBelow(prevNode);
```

## Required imports

```
- System.Linq
- OutSystems.Model
- OutSystems.Model.Logic
- OutSystems.Model.Logic.Nodes
- OutSystems.Model.Data
```

## Verification

After publish:

```csharp
var action = eSpace.ServiceActions.First(a => a.Name == "{{ACTION_NAME}}");
Console.WriteLine($"Node count: {action.Nodes.Count()}");
Console.WriteLine($"Has End: {action.Nodes.OfType<IEndNode>().Any()}");
// Expected: node count > 2 (Start + at least one operation + End)
```

## Limitations / gaps

- **Aggregate creation from action bodies**: action bodies can't reference screen aggregates (different scope). Use ServiceActions returning Lists instead.
- **Async / Long-running**: ServiceActions can't be async in ODC. For long-running, factor into a BusinessProcess (separate app kind).
- **Per-node renderer**: this recipe is a TEMPLATE. The renderer needs a `render_action_body(action_tree)` Python function that walks the captured tree and emits the per-node C# above. Renderer-side work is non-trivial.

## Related

- `[[odc_mcp_screen_action_service_action_call]]` — screen action vs service action wall
- `[[odc_long_integer_to_identifier_cast]]` — cast needed for Identifier values
- `[[odc_mcp_expression_vs_text_widget]]` — expression vs literal handling
- `[[odc_mcp_record_literal_via_typed_local]]` — when emitting Record literal values
- `[[FRAMEWORK_REVIEW]]` — action bodies are P1 gap; this recipe closes it
