# Recipe 18 — Agent memory + app-specific state entities

## Purpose

Ensure the agent's conversation **Memory** entity is present (it is, on any
`template_Agent` clone) and add any **app-specific state entities** the agent's
tools need — WITHOUT touching the Memory entity.

## Critical rule (from the 24-agent survey)

**The Memory entity is SACRED.** Per `[[odc_agent_architectures]]`, all
template-clone agents share the same Memory entity (UUID `984d4abd-…`). Do NOT
extend it, rename it, or add attributes to it. For new agent state, create a
SEPARATE server entity (e.g. Banking Assistant's `TemporaryLoan`) — exactly the
Recipe 01 (server entity) pattern, scoped to the agent app.

## When to use

After Recipe 17 (app exists, Memory present), before tool wiring (Recipe 20) if
the tools read/write app-local state.

## Procedure

### Step A — verify Memory exists (read-only preflight)

```csharp
eSpace => {
    var mem = eSpace.Entities.FirstOrDefault(e => e.Name == "Memory");
    Console.WriteLine($"Recipe 18: Memory entity present={mem != null} | Status: {(mem != null ? "OK" : "MISSING")}");
}
```
If MISSING, the app was not cloned from `template_Agent` — fall back to Studio
or re-clone (Recipe 17).

### Step B — add app-specific state entities (Recipe 01 pattern)

For each state entity in the agent manifest, reuse **Recipe 01 (server entity)**
verbatim against the agent app's `app_key`: `eSpace.CreateServerEntity(name)`,
set `IdentifierAttribute` with `IsAutoNumber = AutoNumber.Yes` BEFORE other
attributes, FK `DeleteRule = Ignore`, etc. (All Recipe 01 rules apply — agent
apps are eSpaces like any other for entity authoring.)

## Diagnostic

```
Recipe 18: Memory present=True, state_entities_created=N | Status: OK
```

## Common failures

- **Tried to add an attribute to Memory** → don't. Add a separate entity.
- **PK change after publish** → `OS-RDBS-GEN-40003` (per `[[odc_db_upgrade_pk_change_blocked]]`).
  Set the identifier in the same call as CreateServerEntity, before first publish.

## Memory refs

- [[odc_agent_architectures]] — Memory entity is uniform + sacred
- 01_entity_server.md — the reused server-entity pattern
- [[odc_db_upgrade_pk_change_blocked]] — PK-after-publish wall

## Related recipes

- 17 (app create), 20 (tool wiring — tools read/write these state entities)
