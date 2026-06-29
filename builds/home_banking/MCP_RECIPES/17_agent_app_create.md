# Recipe 17 — Agent app create (GATE, not an applyModelApiCode recipe)

## Purpose

Stand up a new AIAgent app so the internals recipes (18–21) can author against
it. **App creation is NOT possible via MCP** (`mentor_start` requires an
`app_key`; per `[[odc_mcp_no_app_creation]]` there is no MCP path to create a
WebApp/Agent app). So this recipe is a **manual gate** — like the Studio-warmup
gate — that the orchestrator pauses on.

## When to use

First step of any agent-app build, before recipes 18–21.

## Procedure (manual / Portal)

1. **Portal-create the agent app** OR **clone `template_Agent`**
   (`4917e928-cb9f-40bb-a3dc-fe9ebacc8b2f`, a system module). 18/24 production
   agents are template clones. A clone arrives with the canonical shape already
   in place (per `[[odc_agent_architectures]]`):
   - 6 baseline Server Actions (BuildMessages, etc.)
   - the **Memory entity** (UUID `984d4abd-…` — uniform across clones; SACRED,
     do not extend — add separate entities for new state)
   - 1 model connection
   - 0 custom tools
2. **Studio warmup**: open the new app in Service Studio once and 1-Click
   Publish (per `[[odc_mcp_publish_studio_warmup]]` — the first MCP publish on a
   fresh Portal-created app returns HTTP 403 until a Studio publish has run).
3. **Add the Agents Common Resources reference** (Manage Dependencies, Studio):
   the `AgentsConsumerApp` static entity + shared structures live in
   `Agents Common Resources` (`0d6e0ed8-…`). Required for the multitenancy key
   (Recipe 21). Per `[[odc_mcp_reference_add_studio_only]]`, cross-app reference
   add has no clean MCP primitive — Studio Cmd+Q.
4. **Capture the app_key** (via `app_list --search <name>`) and hand it to the
   orchestrator for recipes 18–21.

## Gate outputs

| Output | Used by |
|---|---|
| `app_key` of the new agent app | Recipes 18–21, publish_start |
| Confirmed Memory entity present | Recipe 18 (verify, don't recreate) |
| Agents Common Resources referenced | Recipe 21 (AgentsConsumerApp Identifier) |

## Notes

- AI Model Connection management (provider, keys) is Portal-only — not scriptable.
- Tool IMPORT / MCP-server config is Portal-only (per `[[odc_mcp_tool_import_flow]]`).
  Recipe 20 wires LOCAL Server Actions as tools (which IS scriptable) — not
  imported MCP tools.

## Memory refs

- [[odc_mcp_no_app_creation]] — no MCP app-create path
- [[odc_agent_architectures]] — clone shape, Memory entity UUID, clusters
- [[odc_mcp_publish_studio_warmup]] — first-publish 403
- [[odc_portal_core_agent_recipe]] — the Portal+Core+agents constellation
- [[odc_mcp_reference_add_studio_only]] — cross-app reference add

## Related recipes

- 18 (memory/state entity), 19 (system prompt), 20 (tool wiring), 21 (multitenancy)

## CORRECTION (2026-06-12): app_create DOES mint AIAgent apps
The "App creation NOT possible via MCP" claim is STALE/WRONG. `app_create({name, kind:"AIAgent"})`
mints an AIAgent shell (verified: HBIntakeAgentClone 279d96b4, rev 1). BUT the shell is BARE —
no MainFlow, no Memory entity, no Agent element, no template_Agent scaffold. Not a template clone;
the whole agent is hand-authored. Agent element: `eSpace.CreateAgent(name)`; set `EnableActionCalling=true`.
**AIModel wall:** the Agent's `AIModel` property must bind an **AI Model Connection** asset, which is
**Portal-only** (provider+keys, secrets) and not scriptable/bindable via MCP. Without it, publish fails
`OS-APPS-40028` / `(Error) Required Property Value … AIModel must be set`. So MCP authors the entire agent
STRUCTURE but cannot make it run without a Portal-created AI Model Connection in the tenant.
