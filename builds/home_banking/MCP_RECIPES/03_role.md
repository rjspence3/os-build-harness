# Recipe 03 — Role (security primitive)

## Purpose

Create ONE role on the current app. Roles gate screen access (`screen.Roles.Add(role)`) and feature gates (`CheckRole()` in expressions). A role is `Public` if it must be referenced from consumer apps via Manage Dependencies; otherwise private to this app.

A role belongs to ONE producer app. Consumer apps reference roles via Manage Dependencies in Studio — there's no MCP path to add the cross-app reference (per `[[odc_mcp_reference_add_studio_only]]`).

## When to use

- Authoring a new app's security model from a `roles.yaml` manifest
- Adding a role to an existing app (idempotent: caller should pre-check; this recipe will throw on duplicate name)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ROLE_NAME}}` | PascalCase role name | `HomeBankingPortal` |
| `{{ROLE_DESCRIPTION}}` | One-sentence description | `Customer-facing role for the Home Banking Portal app` |
| `{{IS_PUBLIC}}` | `true` if consumed cross-app, `false` if internal | `true` |

## Mentor prompt (paste verbatim, with {{}} substituted)

```csharp
eSpace => {
    var r = eSpace.CreateRole("{{ROLE_NAME}}");
    r.Description = "{{ROLE_DESCRIPTION}}";
    r.Public = {{IS_PUBLIC}};
    Console.WriteLine($"Recipe 03: {{ROLE_NAME}} | Created: role (Public={r.Public}) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
```

## Expected stdout

```
Recipe 03: HomeBankingPortal | Created: role (Public=True) | Status: OK
```

## Common failures

### ✗ `Role 'X' already exists`

Cause: role name collision. Roles are name-unique within an app.
Fix: caller should query `app_info` for existing roles and skip if present, OR rename. ODC does NOT auto-suffix role names like it does for Service Actions.

### ✗ `Public flag mismatch after publish`

Symptom: you set `Public = true` but the role appears as private to consumer apps.
Cause: changing `Public` on an existing role doesn't propagate until the producer app is republished AND every consumer's Manage Dependencies is refreshed.
Fix: republish the producer, then in each consumer Studio: Cmd+Q → Refresh dependency.

## Example: 3 Home Banking roles

```yaml
# Core owns all 3
- name: HomeBankingCore
  description: Internal role used by HomeBankingCore for backend service-action access
  is_public: false
- name: HomeBankingPortal
  description: Customer-facing role for the Home Banking Portal app
  is_public: true
- name: HomeBankingBackoffice
  description: Admin/underwriter role for the Home Banking Backoffice app
  is_public: true
```

Each entry runs as a separate recipe call (one Mentor turn per role). Producer app: HomeBankingCore. Consumers (Portal, Backoffice) reference the two Public roles via Studio after producer publishes.

## Memory refs

- [[odc_mcp_reference_add_studio_only]] — cross-app role references require Studio Cmd+Q
- [[odc_mcp_role_cross_app_propagation]] — Public flag propagation rules

## Related recipes

- [11_default_screen](./11_default_screen.md) — DefaultScreen often gates on a role
- [99_publish_verify](./99_publish_verify.md) — publish producer before consumers can see Public roles
