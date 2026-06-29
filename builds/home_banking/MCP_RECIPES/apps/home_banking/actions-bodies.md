# Home Banking — Action Bodies (deep-dive samples)

Captured via Mentor `applyModelApiCode` flow-introspection probes against the
HomeBanking apps. The samples here inform recipes 04 (CRUD), 05 (SQL update),
06 (multi-step workflow), and the ForEach/list-batch pattern (recipe TBD).

Each section dumps an action's signature + flow nodes in declared order. Note
that **declared order is NOT execution order** — execution follows the
Start node's `Target` chain through `Target` / `TrueTarget` / `FalseTarget`
properties. See memory `[[odc_mcp_assign_node_iteration_not_flow_order]]`.

The probe code that produced these dumps lives in this file's "Probe source"
section at the bottom — replay it on a fresh app to extract the same shape.

---

## Sample 1 — `Sidebar_ChangeStatus` (Backoffice)

**Pattern**: multi-input business action that calls a Service Action for core
logic, then conditionally branches based on an input flag to perform a
side-effect (push notification + Firebase event).

### Signature

```
Action: Sidebar_ChangeStatus
ActionType: ServerAction
Public: false

Inputs (8, all mandatory):
  RequestId            : LoanRequest Identifier
  RequestStatusId      : LoanRequestStatus Identifier
  Reason               : Text
  UserId               : User Identifier
  AgentTypeId          : HBAgentType Identifier
  AgentDecisionStatusId: HBAgentDecisionStatus Identifier
  RequestInfoOptionId  : LoanRequestInfoOption Identifier  (optional)
  NotifyUser           : Boolean

Outputs: (none — fire-and-forget mutation)
Locals : (none)
```

### Flow (execution order)

```
Start
  ↓
[7] ExecuteAction ServiceSidebar_ChangeStatusGetFirebase  (core status-change logic
      — note this is a Service Action, not a Server Action; its outputs include
        DatabaseURL, Target, Token which are used downstream)
      args: AgentTypeId, AgentDecisionStatusId, RequestStatusId, RequestId,
            RequestInfoOptionId, Reason, UserId
  ↓
[6] If "Pending and has DeviceId?"
      cond: RequestStatusId = Entities.LoanRequestStatus.Pending
            AND GetRequestById.List.Current.LoanRequest.DeviceId <> ""
   ├── True ──→ [3] ExecuteAction ServiceSendPushNotification
   │                   args: RequestId, Title="Loan Request Update",
   │                         DeviceId = GetRequestById.List.Current.LoanRequest.DeviceId,
   │                         Message="We couldn't approve your request at this time…"
   │                ↓
   │              [1] ExecuteAction FirebaseNotifyEvent_Server
   │                   args: Request = {EventIdentifier=RequestId, EventDateTime=CurrDateTime(), …},
   │                         DataBaseURL = ServiceSidebar_ChangeStatusGetFirebase.DatabaseURL,
   │                         Target      = ServiceSidebar_ChangeStatusGetFirebase.Target + "_" +
   │                                       GetRequestById.List.Current.HBCustomer.UserId,
   │                         Token       = ServiceSidebar_ChangeStatusGetFirebase.Token
   │                ↓
   │              End
   └── False ──→ End  (NotifyUser=false path skips push + Firebase; status change still happened in [7])

Wait — re-reading: there's a SECOND If [4] earlier in the flow with cond=NotifyUser
that gates the aggregate [5] (GetRequestById = LoanRequest + HBCustomer joined on
LoanRequest.Id = RequestId). The aggregate result feeds the [6] If condition.
The path traced from Start should likely be: Start → [7] → [5] aggregate (only if [4]
is true) → [6] branch. Detailed re-trace in Studio recommended; this dump captures
declared-order, not execution-order.
```

### Recipe template implications

- **Service Action handoff pattern**: when a business action needs to share
  outputs across multiple downstream calls, encapsulate the producing logic in
  a Service Action whose outputs (DatabaseURL, Target, Token here) flow into
  subsequent ExecuteAction args by name reference.
- **Aggregate-then-branch**: a screen aggregate or action aggregate (DataSet
  node) loads the entities involved, then an If node branches on the loaded
  record's state combined with input flags. The aggregate `GetRequestById`
  joins `LoanRequest` + `HBCustomer` via FK.
- **Multi-arg record literal in ExecuteAction**: the FirebaseNotifyEvent_Server
  takes a `Request` argument constructed inline as a record literal:
  `{ EventIdentifier: RequestId, EventDateTime: CurrDateTime(), EventText: "", EventType: "" }`.
  Per memory `[[odc_mcp_record_literal_via_typed_local]]`, this inline form is
  the syntax the platform accepts (via expression compiler), even though the
  Model API direct path requires a typed local. Look up the inline-record
  semantics before authoring.

---

## Sample 2 — `RequestAssignEmployeeBulk` (Backoffice)

**Pattern**: ForEach loop over a list input, calling a per-item Service Action.

### Signature

```
Action: RequestAssignEmployeeBulk
ActionType: ServerAction
Public: false

Inputs (2, both mandatory):
  RequestIds : LoanRequest Identifier List
  EmployeeId : Employee Identifier

Outputs: (none)
Locals : (none)
```

### Flow

```
Start
  ↓
[4] ForEach (RecordList = RequestIds)
  │
  ├── body (each iteration)
  │     ↓
  │   [1] ExecuteAction ServiceRequestAssigned
  │         args: EmployeeId = EmployeeId,
  │               RequestId  = RequestIds.Current   ← `<List>.Current` is the iterator var
  │     ↓
  │   (loop back to [4])
  │
  └── after all iterations → End
```

### Recipe template implications

- **ForEach over a list parameter**: `RecordList` property = the list variable.
  `<List>.Current` inside the body resolves to the current iteration's record.
- **Per-item Service Action call**: the cycle body is just one ExecuteAction
  node. No accumulator, no per-iteration aggregation; this is a "fire each item
  through a service" pattern. If you need to collect results, you'd add an
  Assign-into-local-list before the back-edge.
- **`ForEach.Target` semantics**: the Model API's `Target` property on a
  ForEach node may point to the "after-loop" target rather than the "loop body"
  target. The body entry uses a separate `CycleTarget` (or similar) property.
  When authoring via Model API, set BOTH — the body target AND the after-loop
  target. The dump above shows `Target (body): End` which is misleading;
  the actual body entry is reached through the back-edge. Test in Studio.

---

## Probe source — replay against any app

To re-run this introspection against any app, dispatch this Mentor prompt
(replace `{{ACTION_NAMES}}` with the comma-separated list and `{{APP_KEY}}`
with the target app's assetKey):

```csharp
// Imports: System, System.Linq, OutSystems.Model,
//          OutSystems.Model.Logic.Nodes, OutSystems.Model.Data

eSpace => {
    var targets = new[] { /* {{ACTION_NAMES}} */ };
    foreach (var name in targets) {
        var a = eSpace.ServerActions.FirstOrDefault(x => x.Name == name);
        if (a == null) { Console.WriteLine($"--- {name} NOT FOUND ---"); continue; }
        Console.WriteLine($"=== {name} ===");
        Console.WriteLine($"Inputs: "  + string.Join(", ", a.InputParameters .Select(p => p.Name + ":" + p.DataType)));
        Console.WriteLine($"Outputs: " + string.Join(", ", a.OutputParameters.Select(p => p.Name + ":" + p.DataType)));
        Console.WriteLine($"Locals: "  + string.Join(", ", a.LocalVariables  .Select(v => v.Name + ":" + v.DataType)));
        int i = 0;
        foreach (var n in a.Nodes) {
            i++;
            var t = n.GetType().Name;
            string lbl = "";
            try { lbl = (n.GetType().GetProperty("Label")?.GetValue(n) as string) ?? ""; } catch {}
            Console.WriteLine($"[{i}] {t} '{lbl}'");

            if (n is OutSystems.Model.Logic.Nodes.IIfNode if1) {
                Console.WriteLine($"    cond: {if1.Condition}");
                Console.WriteLine($"    True->{if1.TrueTarget?.GetType().Name}, False->{if1.FalseTarget?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.IAssignNode an1) {
                foreach (var asn in an1.Assignments)
                    Console.WriteLine($"    {asn.Variable} = {asn.Value}");
                Console.WriteLine($"    Target: {an1.Target?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.IExecuteServerActionNode ex1) {
                Console.WriteLine($"    Action: {ex1.Action?.Name}");
                foreach (var arg in ex1.Arguments)
                    Console.WriteLine($"    arg {arg.Parameter?.Name}: {arg.Value}");
                Console.WriteLine($"    Target: {ex1.Target?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.ISQLNode sql1) {
                var stmt = (sql1.Statement ?? "");
                if (stmt.Length > 500) stmt = stmt.Substring(0, 500) + "...";
                Console.WriteLine($"    SQL: {stmt}");
                foreach (var arg in sql1.Arguments)
                    Console.WriteLine($"    sql-arg {arg.Parameter?.Name}: {arg.Value}");
                Console.WriteLine($"    Target: {sql1.Target?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.IExceptionHandlerNode exh1) {
                Console.WriteLine($"    HandlerName: {exh1.Name}, ExceptionType: {exh1.Exception?.GetType().Name}, Abort: {exh1.AbortTransaction}");
                Console.WriteLine($"    Target: {exh1.Target?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.IForEachNode fe1) {
                try { Console.WriteLine($"    RecordList: {fe1.RecordList}"); } catch {}
                Console.WriteLine($"    Target (body): {fe1.Target?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.IStartNode st1) {
                Console.WriteLine($"    Target: {st1.Target?.GetType().Name}");
            }
            else if (n is OutSystems.Model.Logic.Nodes.IAggregateNode ag1) {
                try {
                    var d = ag1.AsDatabaseAggregate;
                    Console.WriteLine($"    Sources: " + string.Join(",", d.Sources.Select(s => s.Name + "(" + s.Source?.GetType().Name + ")")));
                    foreach (var fl in d.Filters)
                        Console.WriteLine($"    filter: {fl.Condition}");
                    foreach (var so in d.Sorts)
                        Console.WriteLine($"    sort: {so.Attribute} {so.SortDirection}");
                } catch (Exception ex) {
                    Console.WriteLine($"    <agg failed: {ex.Message}>");
                }
                Console.WriteLine($"    Target: {ag1.Target?.GetType().Name}");
            }
        }
        Console.WriteLine();
    }
}
```

## Sample 3 — `ValidateDocument` (Portal)

**Pattern**: AI-pipeline server action — aggregate to load context, external
LLM/validator call, regex strip on the raw response, JSON deserialize into a
typed Structure output.

### Signature

```
Action: ValidateDocument
ActionType: ServerAction
Public: false

Inputs (4, all mandatory):
  Binary           : Binary Data
  Filename         : Text
  HBDocumentTypeId : HBDocumentType Identifier
  LocaleId         : Locale2 Identifier

Outputs:
  DocumentValidationResponse : DocumentValidationResponse  (local Structure)
Locals: (none)
```

### Flow

```
Start
  ↓
Aggregate GetHBDocumentTypeById
  Sources: HBDocumentType
  Filter:  HBDocumentType.Id = HBDocumentTypeId
  ↓
ExecuteAction CallDocumentValidator
  args: AgentsConsumerApp = "HomeBanking",
        Binary    = Binary,
        LocaleId  = LocaleId,
        Filename  = Filename,
        UserMessage = (built from HBDocumentType.Label that was loaded in the aggregate)
  ↓
ExecuteAction Regex_Replace
  (strips everything outside the first [{…}] JSON-array bracket
   from the validator's text response)
  ↓
ExecuteAction JSONDeserialize
  Source: regex-stripped text from previous step
  Target Type: DocumentValidationResponse
  ↓
Assign "Set Output"
  DocumentValidationResponse = JSONDeserializeDocumentValidationResponse.Data
  ↓
End
```

### Recipe template implications

- **Aggregate-then-call pattern**: load enrichment context (HBDocumentType label
  here) via an aggregate, then thread that context into a downstream external
  call. The aggregate's output is referenced by `<AggregateName>.List.Current.<Entity>.<Attr>`.
- **External LLM call wiring**: `CallDocumentValidator` is a Service Action
  exposed by an agent module. Its signature accepts an `AgentsConsumerApp`
  Identifier (the literal "HomeBanking" here) plus the binary content + locale +
  filename + user message. This is the canonical "send to LLM with context"
  shape.
- **JSON deserialize through a regex-strip**: LLMs often wrap JSON output in
  Markdown code fences or prose. `Regex_Replace` is used to extract just the
  JSON payload before `JSONDeserialize` parses it into a typed Structure.
  Recipe note: the regex pattern is likely something like `^.*?(\[\{.*?\}\]).*$` —
  capture and replace with the first JSON-array literal.

---

## Sample 4 — `Get_Settings` (Portal)

**Pattern**: parameterless multi-output server action that hydrates UI config
from a mix of imported Service Action outputs + locally-generated values.

### Signature

```
Action: Get_Settings
ActionType: ServerAction
Public: false

Inputs : (none)
Outputs (6):
  Currency                  : Text
  GroupSeparator            : Text
  DecimalSeparator          : Text
  SessionId                 : Text
  GoogleAnalyticsTrackingID : Text
  IsDemoAccessCookieEnabled : Boolean
Locals : (none)
```

### Flow

```
Start
  ↓
ExecuteAction ServiceGetSettings   (Service Action from another app's settings core)
  outputs available: Currency, GroupSeparator, DecimalSeparator, AnalyticsTrackingID, IsDemoAccessCookieEnabled
  ↓
ExecuteAction GenerateGuid         (utility — produces a fresh UUID)
  output: Guid
  ↓
Assign "Set Outputs"
  Currency                  = ServiceGetSettings.Currency
  GroupSeparator            = ServiceGetSettings.GroupSeparator
  DecimalSeparator          = ServiceGetSettings.DecimalSeparator
  SessionId                 = GenerateGuid.Guid
  GoogleAnalyticsTrackingID = ServiceGetSettings.AnalyticsTrackingID  (note rename in target output)
  IsDemoAccessCookieEnabled = ServiceGetSettings.IsDemoAccessCookieEnabled
  ↓
End
```

### Recipe template implications

- **Multi-output projection**: a single Assign node sets every output. Each
  assignment is a single `<Output> = <expression>` line. The expressions
  reference the ExecuteAction node names directly (`ServiceGetSettings.X`,
  `GenerateGuid.Guid`) — these are the canonical Studio expression-language
  bindings.
- **Imported Service Action outputs as inputs**: `ServiceGetSettings` returns
  5 values; this action selects 4 of them and supplements with a freshly-
  generated GUID. The "fan-out to local + augment" shape is reusable for any
  "load config from elsewhere, add per-session values" action.
- **Output renaming**: `ServiceGetSettings.AnalyticsTrackingID` → output named
  `GoogleAnalyticsTrackingID`. Don't assume local output names match upstream
  names; the Assign block does the mapping.

---

## Sample 5 — `CheckAndGrantRole` (Portal)

**Pattern**: thin wrapper that delegates to a Service Action in another app.

### Signature

```
Action: CheckAndGrantRole
ActionType: ServerAction
Public: false

Inputs:
  UserId : User Identifier
Outputs: (none)
Locals : (none)
```

### Flow

```
Start
  ↓
ExecuteAction GrantHBPortalRole   (Service Action from a producer module)
  args: UserId = UserId
  ↓
End
```

### Recipe template implications

- **Thin-wrapper action**: a single ExecuteAction node calling a producer's
  Service Action with the same-named argument. This is the lightest possible
  action and the minimum viable example for testing the recipe template
  end-to-end on a fresh app — useful for a "smoke-test recipe" variant.

---

## Status

| Action | App | Captured | Pattern bucket |
|---|---|---|---|
| Sidebar_ChangeStatus | Backoffice | ✅ | Multi-step workflow w/ branch + aggregate-then-condition (recipe 06) |
| RequestAssignEmployeeBulk | Backoffice | ✅ | ForEach over list, per-item Service Action call (new recipe: foreach_list) |
| ValidateDocument | Portal | ✅ | AI pipeline: aggregate → external call → regex → deserialize → output (recipe 06 variant) |
| Get_Settings | Portal | ✅ | Multi-output config-load via Service Action + GUID (recipe 04 variant) |
| CheckAndGrantRole | Portal | ✅ | Thin wrapper (smoke-test recipe) |

## What this informs

With these 5 samples in hand, the following recipes can now be authored with
confidence:

- **`04_action_crud.md`** — minimal CRUD wrapper (CheckAndGrantRole shape) +
  multi-output projection (Get_Settings shape) for typical
  "read entity + project to outputs" patterns.
- **`05_action_sql_update.md`** — covered by PackageAndSubmitReport from the
  ComplianceOps build (memory `[[odc_mcp_sql_node_api]]`).
- **`06_action_workflow.md`** — covered by Sidebar_ChangeStatus + ValidateDocument
  (multi-step with branch, aggregate-then-condition, external-call pipeline).
- **`XX_action_foreach_list.md`** — new recipe, RequestAssignEmployeeBulk pattern.
