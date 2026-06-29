# Recipe 99 — Publish + verify (end of build)

## Purpose

Final step of every build sequence. Triggers `publish_start` via MCP, polls `publish_status` until terminal state, then runs a verification read-only `applyModelApiCode` call to assert the just-published OML matches expectations (entity count, screen count, action count, default screen presence).

Required after ANY mutation. Per `[[odc_mcp_publish_studio_warmup]]`, the FIRST publish on a fresh Portal-created app requires one prior Studio publish; this recipe assumes the warmup is done.

## When to use

- End of Phase 1 (after all static entities)
- End of Phase 2 (after all server entities)
- End of each Phase 3-7 step
- After every recipe call that mutates the app (safer to over-publish than to lose a session)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{APP_KEY}}` | Asset key UUID of the app being published | `fa7ab595-f8cd-4140-8826-2acc484727b6` |
| `{{EXPECTED_ENTITY_COUNT}}` | Entities expected after this phase | `35` |
| `{{EXPECTED_SCREEN_COUNT}}` | Screens expected (incl. Common flow auto-generated) | `10` |
| `{{EXPECTED_ACTION_COUNT}}` | Server+Client actions expected | `100` |
| `{{EXPECTED_DEFAULT_SCREEN}}` | Name of DefaultScreen if set, or null | `Dashboard` |

## Procedure (caller-side, NOT a single MCP call)

This recipe is **bookkeeping** — the actual MCP calls happen at the caller level:

```bash
# Step 1: publish_start
publish_start --app_key {{APP_KEY}}
# → returns publication_key (operation_key)

# Step 2: poll publish_status until terminal
# Per [[odc_mcp_publish_lifecycle]]:
#   - Running → Finished (~62s typical for medium app)
#   - 'Finished' is success, 'Failed' is failure
#   - Refreshed mentor_session_token appears ONLY at terminal-success

publish_status --key <publication_key>
# Poll until status != 'Running'

# Step 3: verify revision bumped
app_info --key {{APP_KEY}}
# → revision should be 1 higher than pre-publish snapshot
```

## Verification probe (run after publish completes)

```csharp
eSpace => {
    // Entities — direct collection on eSpace
    int entityCount       = eSpace.Entities.Count();
    int serverEntityCount = eSpace.Entities.Count(e => e.EntityKind == OutSystems.Model.Data.EntityKind.Server);
    int staticEntityCount = eSpace.Entities.Count(e => e.EntityKind == OutSystems.Model.Data.EntityKind.Static);

    // Actions — own actions live as descendants. Use IServerAction +
    // IClientAction (concrete types) rather than IActionSignature (which is
    // the read-only reference interface).
    int serverActionCount = eSpace.GetAllDescendantsOfType<OutSystems.Model.Logic.IServerAction>().Count();
    int clientActionCount = eSpace.GetAllDescendantsOfType<OutSystems.Model.Logic.IClientAction>().Count();
    int actionCount       = serverActionCount + clientActionCount;

    // Screens — MobileFlows (Mobile-prefixed API per [[odc_mcp_mobile_prefixed_api]])
    int screenCount = eSpace.MobileFlows.SelectMany(f =>
        f.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()).Count();

    int roleCount  = eSpace.Roles.Count();
    int themeCount = eSpace.MobileThemes.Count();  // Mobile-prefixed

    bool entityOK = entityCount == {{EXPECTED_ENTITY_COUNT}};
    bool screenOK = screenCount == {{EXPECTED_SCREEN_COUNT}};
    bool actionOK = actionCount == {{EXPECTED_ACTION_COUNT}};

    Console.WriteLine($"Recipe 99 — Post-publish verification:");
    Console.WriteLine($"  Entities: {entityCount} (server={serverEntityCount}, static={staticEntityCount}) — expected {{EXPECTED_ENTITY_COUNT}} — {(entityOK ? \"OK\" : \"MISMATCH\")}");
    Console.WriteLine($"  Screens:  {screenCount} — expected {{EXPECTED_SCREEN_COUNT}} — {(screenOK ? \"OK\" : \"MISMATCH\")}");
    Console.WriteLine($"  Actions:  {actionCount} (server={serverActionCount}, client={clientActionCount}) — expected {{EXPECTED_ACTION_COUNT}} — {(actionOK ? \"OK\" : \"MISMATCH\")}");
    Console.WriteLine($"  Roles:    {roleCount}");
    Console.WriteLine($"  Themes:   {themeCount}");
    Console.WriteLine($"Recipe 99: VerifyBuild | Status: {(entityOK && screenOK && actionOK ? \"OK\" : \"DRIFT\")}");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Logic
OutSystems.Model.UI.Mobile
```

## Expected stdout

```
Recipe 99 — Post-publish verification:
  Entities: 35 (server=21, static=14) — expected 35 — OK
  Screens:  10 — expected 10 — OK
  Actions:  100 — expected 100 — OK
  Roles:    3
  Themes:   2
  Default:  Dashboard — expected Dashboard — OK
Recipe 99: VerifyBuild | Status: OK
```

## Common failures

### ✗ `publish_start` returns HTTP 403

Cause: Portal-created app hasn't been opened in Studio yet. Per `[[odc_mcp_publish_studio_warmup]]`, the first publish on a fresh app must come from Studio (Cmd+1).
Fix: open the app in Studio, click "1-Click Publish", then retry the MCP `publish_start`.

### ✗ `publish_status` shows "Failed" with `OS-DPL-200xx`

Cause: deployment-step failure. Decode via `deploy_messages` per `[[odc_mcp_deploy_lifecycle]]`.
Fix: most common is `OS-DPL-20021` (DB script execution) — implies a schema change that the runtime can't apply. Roll back via `deploy_rollback`.

### ✗ Verification probe shows entity/screen drift

Cause: Mentor or a prior recipe call mutated more (or fewer) than expected. Most likely Mentor auto-fix went wrong per `[[odc_mcp_cascading_validation_auto_fix]]`.
Fix: read `context_entities` and `context_screens` for the actual list, compare against the manifest, identify the drift. Common drifts: missing FK attribute (Mentor "auto-fixed" by dropping it), extra side-effect screens (Mentor auto-created a list view).

### ✗ Verification shows correct counts but app doesn't load

Cause: counts match the manifest but runtime fails — usually a JS error in the bootstrap script (`OS-CLRT-00000` redirect loop or missing role).
Fix: check `[[odc_default_screen_redirect_loop]]`.

## Memory refs

- [[odc_mcp_publish_lifecycle]] — Running → Finished state machine
- [[odc_mcp_publish_studio_warmup]] — first publish needs Studio
- [[odc_mcp_deploy_lifecycle]] — for the deploy_status path after publish
- [[odc_mcp_cascading_validation_auto_fix]] — Mentor auto-corrections
- [[odc_default_screen_redirect_loop]] — runtime redirect-loop debug

## Related recipes

- Every other recipe — they all close with this one
