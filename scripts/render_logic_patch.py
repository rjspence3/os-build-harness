"""Recipe 26 — LOGIC patch-in-place for the Dashboard.

Re-runs the EXACT parts render that authored the published screen (same name
allocation), collects every stubbed/deferred expression site, filters to the
sites that are restorable now that the data infra exists (the only reason they
were stubbed was a _LOGIC_PHASE_TOKENS hit), rewrites Locale2→Locale (tenant
renamed the static entity, same globalKey), and emits one applyModelApiCode
recipe that SetValue/SetVisible-patches the live widgets by Name.

Patch-in-place instead of re-author: replacing the screen would destroy its
screen-scoped aggregates (upgraded by the INFRA pass, revs 30-32) and the
ChartCardsValue-typed local.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.banking_runner import screen_renderer as sr
from harness.banking_runner.tree_parser import parse_tree_file

CAPTURE = Path("data/MCP_RECIPES/apps/home_banking/_raw/portal-dashboard.tree.md")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/portal_v23/portal/26_logic_patch_dashboard.prompt.txt")

# The tenant renamed the Locale2 static to Locale (same globalKey) — INFRA
# pass referenced `Locale`. Original expressions say Locale2.
REWRITES = [("Entities.Locale2.", "Entities.Locale."), ("Locale2.", "Locale.")]


def _restorable(val: str) -> bool:
    """True when the ONLY reason the site was stubbed is the deny-list —
    i.e. it passes the full safety check once the deny tokens are ignored."""
    saved = sr._LOGIC_PHASE_TOKENS
    try:
        sr._LOGIC_PHASE_TOKENS = frozenset()
        return sr._expression_value_safe(val, set())
    finally:
        sr._LOGIC_PHASE_TOKENS = saved


def main() -> None:
    ast = parse_tree_file(CAPTURE)
    # Same call shape as scripts/build_banking.py uses for the Dashboard
    sr.render_screen_dechromed_parts(ast, role_name="HomeBankingPortal",
                                     flow_name="MainFlow")
    patches = getattr(sr.render_screen_dechromed_parts, "last_stub_patches", [])
    print(f"collected stub sites: {len(patches)}")

    lines: list[str] = []
    skipped = 0
    for kind, name, val in patches:
        for old, new in REWRITES:
            val = val.replace(old, new)
        if not _restorable(val):
            skipped += 1
            lines.append(f"// SKIP (still unrestorable): {name} = {val!r}")
            continue
        esc = val.replace("\\", "\\\\").replace('"', '\\"')
        if kind == "value":
            lines.append(
                f'{{ var w = screen.GetAllDescendantsOfType<ServiceStudio.Plugin.NRWidgets.IExpression>()'
                f'.FirstOrDefault(e => e.Name == "{name}"); '
                f'if (w == null) {{ Console.WriteLine($"MISS: {name}"); miss++; }} '
                f'else {{ w.SetValue("{esc}"); Console.WriteLine($"PATCHED value {name}"); patched++; }} }}'
            )
        else:  # visible
            lines.append(
                f'{{ var w = screen.GetAllDescendantsOfType<ServiceStudio.Plugin.NRWidgets.IContainer>()'
                f'.FirstOrDefault(c => c.Name == "{name}"); '
                f'if (w == null) {{ Console.WriteLine($"MISS: {name}"); miss++; }} '
                f'else {{ w.SetVisible("{esc}"); Console.WriteLine($"PATCHED visible {name}"); patched++; }} }}'
            )

    body = "\n    ".join(lines)
    recipe = f"""Execute this recipe EXACTLY as written. ONE applyModelApiCode call. Do not explore, do not improve the code. If it errors, STOP and report verbatim. Do not publish — the caller publishes separately.

```csharp
eSpace => {{
    // Recipe 26: LOGIC patch — restore stubbed Dashboard expressions now that
    // the data infra (aggregates/joins/structure/client action/Locale ref)
    // exists. Patch-in-place; the screen is NOT replaced.
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "MainFlow");
    if (flow == null) {{ Console.WriteLine($"FAILED: MainFlow not found"); return; }}
    var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>().FirstOrDefault(s => s.Name == "Dashboard");
    if (screen == null) {{ Console.WriteLine($"FAILED: Dashboard not found"); return; }}
    int patched = 0; int miss = 0;
    {body}
    Console.WriteLine($"Recipe 26: Dashboard | patched={{patched}}, missing={{miss}} | Status: {{(miss == 0 ? \\"OK\\" : \\"PARTIAL\\")}}");
}}
```

Required imports for the `imports` array on the applyModelApiCode call:
  - System.Linq
  - OutSystems.Model
  - OutSystems.Model.UI.Mobile
  - ServiceStudio.Plugin.NRWidgets
"""
    OUT.write_text(recipe)
    restored = len(patches) - skipped
    print(f"restorable: {restored}, still-skipped: {skipped}")
    print(f"wrote {OUT} ({len(recipe)} bytes)")


if __name__ == "__main__":
    main()
