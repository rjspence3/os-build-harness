# Recipe 11 — Default Screen (entry-point routing)

## Purpose

Wire the app's DefaultScreen — the screen the platform routes to after successful login. Avoid the redirect-loop trap: setting DefaultScreen to Login causes infinite redirect because anonymous users are auto-redirected to Login, which is also the redirect target.

Canonical pattern: DefaultScreen = an authenticated-only screen (e.g., Dashboard, UserProfile) → platform routes anonymous users to Login → after login, routes back to DefaultScreen.

## When to use

- New app: setting DefaultScreen for the first time
- Existing app: switching DefaultScreen (e.g., from UserProfile → Dashboard after MainFlow screens exist)

For role-based routing (different DefaultScreens per role), use a Login-time client action that calls `RedirectTo` based on `CheckRole()` — that's a more complex pattern outside this recipe's scope.

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{DEFAULT_SCREEN_NAME}}` | Screen to set as default (must already exist) | `Dashboard` |
| `{{FLOW_NAME}}` | Flow containing the target screen | `MainFlow` |

## Mentor prompt (paste verbatim)

```csharp
eSpace => {
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{{FLOW_NAME}}")
        ?? throw new Exception("Flow '{{FLOW_NAME}}' not found");
    var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{DEFAULT_SCREEN_NAME}}");

    if (screen == null) {
        Console.WriteLine($"Recipe 11: {{DEFAULT_SCREEN_NAME}} | FAILED at screen lookup: not found in {{FLOW_NAME}}");
        return;
    }

    if (screen.Roles.Count() == 0 && !screen.AnonymousAccess) {
        Console.WriteLine($"Recipe 11: {{DEFAULT_SCREEN_NAME}} | FAILED at role guard: screen has neither AnonymousAccess nor any role — redirect loop on anonymous user");
        return;
    }

    eSpace.DefaultScreen = screen;
    Console.WriteLine($"Recipe 11: {{DEFAULT_SCREEN_NAME}} | Created: DefaultScreen set (roles={string.Join(\",\", screen.Roles.Select(r => r.Name))}, anonymous={screen.AnonymousAccess}) | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.UI.Mobile
```

## Expected stdout

```
Recipe 11: Dashboard | Created: DefaultScreen set (roles=HomeBankingPortal, anonymous=False) | Status: OK
```

## Common failures

### ✗ "Too many redirects" in browser

Symptom: hitting the app URL produces a browser-side `OS-CLRT-00000` redirect-loop error.
Cause: DefaultScreen is set to a screen that requires authentication BUT no Login screen exists OR Login screen is itself set as DefaultScreen.
Fix: ensure (a) a Login screen exists in Common flow (Mentor auto-creates this) and (b) DefaultScreen is set to an AUTH-required screen (not Login itself).

### ✗ User lands on UserProfile dead-end

Symptom: login succeeds, user lands on UserProfile with no nav, no buttons to anywhere.
Cause: DefaultScreen=UserProfile, but no MainFlow screens exist yet.
Fix: this is expected when the app is empty post-Phase-0. Once MainFlow screens are created (Phases 5+), update DefaultScreen.

### ✗ Anonymous users see "No permissions" instead of Login

Cause: DefaultScreen has roles assigned, but the platform isn't routing through Login first.
Fix: assign the End-user role to the user via ODC Portal → End-user access → Manage roles. The platform's "anonymous → Login → DefaultScreen" auto-routing only triggers when the user IS authenticated but lacks the screen's role.

## Example: set Portal/Dashboard as default

```yaml
DEFAULT_SCREEN_NAME: Dashboard
FLOW_NAME: MainFlow
```

After running, anonymous users hitting the app URL are redirected to Login. Authenticated users with `HomeBankingPortal` role land on Dashboard.

## Memory refs

- [[odc_default_screen_redirect_loop]] — Login-as-default is paradoxical
- [[odc_endusers_vs_org_access]] — End-user role mismatch causes "No permissions"

## Related recipes

- [03_role](./03_role.md) — the role gating the default screen
- [09_screen_dashboard](./09_screen_dashboard.md) — the typical DefaultScreen target
- [99_publish_verify](./99_publish_verify.md) — verify DefaultScreen routes correctly post-publish
