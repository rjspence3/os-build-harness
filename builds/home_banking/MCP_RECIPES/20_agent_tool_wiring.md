# Recipe 20 — Agent tool wiring (Server Action → agent tool)

## Purpose

Give an agent a tool: author a local **Server Action** (the tool body) and wire
it onto the agent's Call element via `CreateActionHandler`, marking which
arguments the LLM fills (`IsFilledByAI`) vs which the system fills. Per
`[[odc_agent_tools_are_server_actions]]`, there is NO special "Tool" type — an
agent tool IS a Server Action referenced by an ActionHandler on the
`Call<ModelName>` element inside the AgentFlow.

## API status (live re-test 2026-05-28)

- ✅ **Tool BODY**: `eSpace.CreateServerAction(name)` + `CreateInputParameter` +
  `CreateNode<IStart/IEnd>()` + flow — COMPILES (confirmed against MCP_TEST_AGENT).
- ⚠️ **Tool WIRING — UNVALIDATED / KNOWN-WRONG**: `agentNode.CreateActionHandler(act)`
  throws **CS1061** (`ICallAgentNode` has no `CreateActionHandler`). The type
  `OutSystems.Model.Logic.Nodes.ICallAgentNode` resolves, but the wiring method
  below is wrong — the prior "B5 verified" was phantom-authoring (chat summary,
  not a compile). The real attach-as-tool + per-arg `IsFilledByAI` API is UNKNOWN.
  Re-crack by guess-and-check against a fresh `template_Agent` clone that has a
  live `ICallAgentNode` (MCP_TEST_AGENT has none, so it can't be the test bed).
  The `CreateActionHandler(...)` / `handler.Arguments[...].IsFilledByAI` lines in
  the template below are PLACEHOLDERS pending that re-cracking.

## When to use

CHROME/LOGIC-phase, after the agent app + its state entities exist (17, 18).

## Standard tool parameter conventions (every production tool)

Per `[[odc_agent_architectures]]`, every production tool follows this signature:

| Parameter | Type | Filled by | IsFilledByAI |
|---|---|---|---|
| `AgentsConsumerAppId` | `AgentsConsumerApp Identifier` | system (multitenancy — Recipe 21) | **false** |
| `RequestId` | `Long Integer` | system | **false** |
| `SessionId` | `Text(50)` | system | **false** |
| `LocaleId` | `Text` (optional) | system | **false** |
| *(domain inputs)* | per tool | the LLM | **true** |

Output convention (3 agents converge): `AIAgentResponse` struct
`{Recommendation, Title, Description, DataSummary}` (all Text).

## Single-call template

```csharp
eSpace => {
    // 1. The tool body (Server Action). Reuse Recipe 04/06 to build the flow.
    var act = eSpace.CreateServerAction("{{TOOL_NAME}}");
    act.Public = false;
    // system-filled params (NOT AI):
    { var p = act.CreateInputParameter("AgentsConsumerAppId"); p.DataType = /* AgentsConsumerApp Identifier, Recipe 21 */; p.IsMandatory = true; }
    { var p = act.CreateInputParameter("RequestId"); p.DataType = eSpace.LongIntegerType; p.IsMandatory = true; }
    { var p = act.CreateInputParameter("SessionId"); p.DataType = eSpace.TextType; p.IsMandatory = true; }
    // LLM-filled domain inputs:
    { var p = act.CreateInputParameter("{{AI_PARAM}}"); p.DataType = eSpace.TextType; }
    // (build the flow: Start -> work -> End; set outputs per AIAgentResponse)
    var start = act.CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>();
    var end = act.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>();
    end.ConnectedBelow(start);

    // 2. Wire it as a tool on the agent's Call element.
    var agent = /* the IAgent / Call<Model> element — locate per template */;
    var handler = agent.CreateActionHandler(act);

    // 3. Mark which args the LLM controls.
    handler.Arguments["{{AI_PARAM}}"].IsFilledByAI = true;
    handler.Arguments["AgentsConsumerAppId"].IsFilledByAI = false;
    handler.Arguments["RequestId"].IsFilledByAI = false;
    handler.Arguments["SessionId"].IsFilledByAI = false;

    Console.WriteLine($"Recipe 20: {{TOOL_NAME}} wired | ai_args=1, system_args=3 | Status: OK");
}
```

> PLAN_GAP A20: the locator for the agent Call element (`agent.CreateActionHandler`)
> varies (AgentFlow vs AgentTask name drift per `[[odc_agent_architectures]]` —
> resolve by key UUID, not name). Pin it per architecture via one `getAgent`/
> `get_app_summary` inspection and record in the manifest.

## Critical: persist with publish_start

Per `[[odc_mcp_agent_app_authoring_wall]]`, Mentor writes are session-scoped.
After the tool-wiring turn, call `publish_start` with the terminal-event
`mentor_session_token` or the work vanishes. Read events (tool_end stdout), NOT
the chat summary (which may refuse despite success).

## Diagnostic

```
Recipe 20: <ToolName> wired | ai_args=N, system_args=M | Status: OK
```

## Memory refs

- [[odc_agent_tools_are_server_actions]] — tool == Server Action on Call element
- [[odc_mcp_agent_app_authoring_wall]] — CreateActionHandler + IsFilledByAI verified (B5); read events; publish to persist
- [[odc_agent_architectures]] — param conventions, AgentFlow/AgentTask drift
- [[odc_service_action_collision_rename]] — name-collision rename gotcha for actions

## Related recipes

- 04/06 (action body), 21 (the AgentsConsumerAppId multitenancy param), 99 (publish/verify)

## CRACKED (2026-06-12): the real tool-wiring API (was UNKNOWN/CS1061)
Verified live (model read-back) on HBIntakeAgentClone:
- Agent: `var agent = eSpace.CreateAgent("LoanIntakeAgent"); agent.EnableActionCalling = true;`
- Tool wiring: `var handler = agent.CreateActionHandler();` (PARAMETERLESS — not CreateActionHandler(action)),
  then `handler.Action = <serverAction>;`
- Per-arg system-fill: `handler.Arguments.SetArgumentValue(param, "0"); arg.IsFilledByAI = false;`
  (IsFilledByAI=false = caller supplies it, e.g. LoanRequestId; true = the LLM fills it).
- Call node in an entry action: `var n = action.CreateNode<ICallAgentNode>(); n.Agent = agent; n.SetArgumentValue(...);`
- System prompt: the inline `[{Role:...}]` message-list LITERAL is REJECTED by the expression parser
  (`mismatched input '['`). Working pattern = a BuildMessages server action that builds the AIMessage list
  via record-field Assigns + ListAppend (recipe 19 inline pattern), assigned to a System-role AIMessage.ContentText.
