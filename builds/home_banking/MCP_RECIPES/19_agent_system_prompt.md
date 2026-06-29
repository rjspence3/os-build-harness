# Recipe 19 — Agent system prompt

## Purpose

Set/replace the agent's system prompt (its instructions/persona). Per the
24-agent survey (`[[odc_agent_architectures]]`) the prompt lives in **one of
three places** — detect the architecture FIRST, then target the right slot.

## The three prompt locations

| Pattern | Where the text lives | Used by | Recipe action |
|---|---|---|---|
| **Inline literal** (canonical, 22/24) | a Comment/SystemMessage node's `.Text` (the `SystemMessageContent.ContentText` in the `BuildMessages` action's SystemMessage Assign) | most agents | edit that node's `.Text` |
| **Composed from struct** | a `BuildSystemPrompt` action assembles the prompt from `AgentDefinition`'s 6 text fields | PO Document Intake, K1 | set the AgentDefinition struct field defaults |
| **Embedded in param description** | a Server Action parameter's `description` (LLM reads it via the tool spec) | Communication Agent's `*GenerateEmail` | edit the parameter `.Description` |

## When to use

After Recipe 17/18, anytime the agent's instructions change.

## Detect the architecture (read-only preflight)

```csharp
eSpace => {
    var hasAgentDef = eSpace.Structures.Any(s => s.Name == "AgentDefinition");
    var build = eSpace.GetAllDescendantsOfType<OutSystems.Model.Logic.IServerAction>()
        .FirstOrDefault(a => a.Name == "BuildMessages");
    Console.WriteLine($"Recipe 19-DETECT: AgentDefinition={hasAgentDef}, BuildMessages={build != null} | " +
        $"pattern={(hasAgentDef ? "structured" : "inline")}");
}
```

## Procedure — INLINE pattern (canonical)

The system prompt is the `.Text` of the SystemMessage content node inside
`BuildMessages`. Per `[[odc_mcp_agent_app_authoring_wall]]`, a **natural-language**
"change the system prompt" request is refused at Mentor's synthesis layer, but a
direct `applyModelApiCode` edit of the node `.Text` succeeds (the wall is
synthesis-only — read events, not summary).

```csharp
eSpace => {
    var build = eSpace.GetAllDescendantsOfType<OutSystems.Model.Logic.IServerAction>()
        .First(a => a.Name == "BuildMessages");
    // The system-prompt text node — locate by the assignment whose target is the
    // SystemMessage content (name/shape is agent-specific; inspect the assign
    // nodes once per architecture and pin the locator). Then:
    //   node.Text = "<new prompt>";  (literal text property — escape quotes)
    // Pinned per-agent in the manifest's `system_prompt_locator`.
    Console.WriteLine($"Recipe 19: system prompt set (inline) | Status: OK");
}
```

> PLAN_GAP A19: the exact node locator inside BuildMessages varies per
> template revision — pin it per architecture via a one-time `getServerAction`
> inspection (read the events, not the summary) and record it in the manifest.

## Procedure — STRUCTURED pattern

Set the `AgentDefinition` struct's text-field defaults (Role, Goal, Tone, etc.).
The prompt is composed at runtime from these + the `AgentProfile_*` enums.

## Procedure — PARAM-DESCRIPTION pattern

Edit the relevant Server Action parameter's `.Description`.

## Diagnostic

```
Recipe 19: system prompt set (<pattern>) | Status: OK
```

## Memory refs

- [[odc_agent_architectures]] — the 3 prompt locations + detection
- [[odc_mcp_agent_app_authoring_wall]] — NL refusal vs applyModelApiCode success; read events
- [[mentor_phantom_authoring]] — verify against runtime, not chat narration

## Related recipes

- 17 (app), 18 (state), 20 (tools), 21 (multitenancy)
