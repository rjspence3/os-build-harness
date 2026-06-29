# Recipe 21 — Agent multi-tenancy key (`AgentsConsumerApp Identifier`)

## Purpose

Wire the universal multi-tenancy key onto the agent's tools so one shared agent
serves multiple consumer apps (Home Banking, Supplier, eGov, MyInsurance…). Per
the 24-agent survey (`[[odc_agent_architectures]]`), **every production tool**
carries an `AgentsConsumerAppId : AgentsConsumerApp Identifier` parameter —
mandatory, system-filled, NOT LLM-filled.

## What `AgentsConsumerApp` is

A static entity in the **Agents Common Resources** library
(`0d6e0ed8-…`), records: `Supplier, eGov, HomeBanking, MyInsurance`. The agent
uses the consumer-app id to scope data/behavior per tenant. The reference must
be added to the agent app first (Recipe 17 step 3, Studio Manage Dependencies —
no clean MCP primitive per `[[odc_mcp_reference_add_studio_only]]`).

## When to use

Folded into Recipe 20 (it's the first tool parameter), or applied to existing
tools that lack the key.

## Resolving the Identifier type in applyModelApiCode

`AgentsConsumerApp` is a referenced static entity, so resolve its
`IdentifierType` via the references collection (it won't be a local entity):

```csharp
var consumerAppEntity = eSpace.References
    .SelectMany(r => r.Entities)
    .FirstOrDefault(e => e.Name == "AgentsConsumerApp");
if (consumerAppEntity == null) {
    Console.WriteLine("Recipe 21: FAILED — AgentsConsumerApp not referenced (add Agents Common Resources in Studio, Recipe 17 step 3)");
    return;
}
var consumerAppIdType = consumerAppEntity.IdentifierType;
```

## Apply to a tool's parameter (within Recipe 20)

```csharp
{ var p = act.CreateInputParameter("AgentsConsumerAppId");
  p.DataType = consumerAppIdType;
  p.IsMandatory = true; }
// ...and on the handler, it is SYSTEM-filled (never LLM):
handler.Arguments["AgentsConsumerAppId"].IsFilledByAI = false;
```

## Invariant (anti-drift)

- Type is ALWAYS `AgentsConsumerApp Identifier` (not Text, not Integer).
- `IsMandatory = true`, `IsFilledByAI = false` on EVERY tool. A tool missing this
  param, or marking it AI-filled, is a recipe bug.

## Diagnostic

```
Recipe 21: AgentsConsumerAppId on <ToolName> | type=AgentsConsumerApp Identifier, ai=false | Status: OK
```

## Memory refs

- [[odc_agent_architectures]] — universal multitenancy key on every production tool
- [[odc_mcp_reference_add_studio_only]] — add the Agents Common Resources reference in Studio
- [[odc_portal_core_agent_recipe]] — the multi-consumer constellation context

## Related recipes

- 17 (reference add), 20 (tool wiring — this is the first tool param)
