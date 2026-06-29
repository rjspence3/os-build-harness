"""Manual-gate UX — prompt the user to do a Portal/Studio gesture and wait.

The runner can't automate Portal app creation, Studio first-publish warmup, or
cross-app Manage Dependencies (per the corpus memories). When a gate is
reached, the orchestrator calls await_gate(...) to:

  1. Print a clear, copy-pasteable instruction
  2. Block stdin until the user types 'done' (or Ctrl+C to abort)
  3. Mark the gate as satisfied in StateDB

The UX is intentionally plain — terminal input.read_text() — to avoid TUI
dependencies. If we add a daemon mode later, gates would emit a desktop
notification + wait for a CLI ack instead.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass


_BANNER = "═" * 78
_THIN = "─" * 78


@dataclass
class Gate:
    """One manual gate. Kind identifies what kind of step (for state tracking);
    description is the human-readable instructions."""
    app: str
    kind: str          # e.g. 'portal_create' | 'studio_warmup' | 'manage_deps' | 'role_assign'
    title: str         # e.g. "Portal-create HomeBankingCore"
    instructions: str  # multi-line, paste-ready
    success_check: str  # human-readable test the user should run before typing 'done'


def await_gate(gate: Gate) -> bool:
    """Print the gate banner + block until the user types 'done'.
    Returns True on satisfied, False if user aborts (types 'abort')."""
    print()
    print(_BANNER)
    print(f"  ⏸  MANUAL GATE  [{gate.app}/{gate.kind}]")
    print(_BANNER)
    print()
    print(f"  {gate.title}")
    print()
    print(_THIN)
    print()
    for line in gate.instructions.strip().splitlines():
        print(f"  {line}")
    print()
    print(_THIN)
    print()
    print(f"  ✓ Success check: {gate.success_check}")
    print()
    print(_BANNER)
    while True:
        try:
            response = input("  Type 'done' when complete, or 'abort' to stop the runner: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Aborted by user.")
            return False
        if response == "done":
            print("  ✓ Gate satisfied. Resuming.\n")
            return True
        if response == "abort":
            print("  ✗ Aborted by user.")
            return False
        print(f"  (Unrecognized: {response!r}. Type 'done' or 'abort'.)")


# ─── Pre-built gates for the banking suite ─────────────────────────────────────

def gate_portal_create(app_name: str, app_display: str) -> Gate:
    return Gate(
        app=app_name,
        kind="portal_create",
        title=f"Portal-create the app: {app_display}",
        instructions=f"""
1. Open https://your-tenant.outsystems.dev/ in your browser.
2. Click "Apps" in the sidebar → "New App".
3. Choose template: "Web App" (Cross Device, Reactive Web).
4. Name: "{app_display}"
5. Click "Create App" and wait for Studio to open.
""",
        success_check=f"You can see '{app_display}' in the Portal Apps list AND Studio is open with the app loaded.",
    )


def gate_studio_warmup(app_name: str, app_display: str) -> Gate:
    return Gate(
        app=app_name,
        kind="studio_warmup",
        title=f"Studio first-publish for: {app_display}",
        instructions=f"""
Per [[odc_mcp_publish_studio_warmup]], a fresh Portal-created app needs ONE
Studio publish before MCP publish_start works.

1. In Studio (already open from previous gate), click the "1-Click Publish"
   button in the top right.
2. Wait for "Publish successful" toast.
3. Verify the app revision incremented to 1 (visible in Studio).
""",
        success_check=f"Studio shows 'Publish successful' and revision is 1 for {app_display}.",
    )


def gate_manage_dependencies(
    consumer_app: str,
    consumer_display: str,
    producer_module: str,
    elements: list[str],
) -> Gate:
    elements_lines = "\n".join(f"    - {e}" for e in elements)
    return Gate(
        app=consumer_app,
        kind=f"manage_deps_{producer_module}",
        title=f"Add {producer_module} dependencies to {consumer_display}",
        instructions=f"""
Consumer apps cannot reference Public elements from another module without
Studio's Manage Dependencies dialog (per [[odc_mcp_reference_add_studio_only]]).

1. Open {consumer_display} in Studio.
2. Press Cmd+Q (Manage Dependencies dialog opens).
3. In the search box, type "{producer_module}".
4. Expand {producer_module}.
5. Check the following elements:
{elements_lines}
6. Click "Apply".
7. Wait for the "Dependencies updated" toast.
8. Save the app (Cmd+S in Studio).
""",
        success_check=f"Manage Dependencies shows {producer_module} in the {consumer_display} app's references.",
    )


def gate_role_assignment(app_name: str, app_display: str, role_name: str, username: str) -> Gate:
    return Gate(
        app=app_name,
        kind="role_assign",
        title=f"Assign '{role_name}' role to {username} on {app_display}",
        instructions=f"""
For role-gated screens (per [[odc_endusers_vs_org_access]]), the End-user role
must be assigned in Portal AFTER the app is published.

1. Open https://your-tenant.outsystems.dev/apps in your browser.
2. Click on {app_display}.
3. Go to "End-user access" tab.
4. Click "Manage roles" (or "Add user" if user not yet present).
5. Find user '{username}' and assign role '{role_name}'.
6. Save.
""",
        success_check=f"User {username} has role {role_name} on {app_display}.",
    )
