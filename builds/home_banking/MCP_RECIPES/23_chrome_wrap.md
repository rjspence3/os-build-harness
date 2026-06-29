# Recipe 23 — Chrome Wrap (CHROME phase)

## Purpose

Wires a dechromed screen (output of Recipe 07 / T2.2) to the custom blocks it
*originally* referenced (output of Recipe 22 / T2.3). Mutates an existing
published screen in place — does not recreate from scratch.

The dechromed screen has placeholder Containers where the original
BlockInstances used to live. Each placeholder Container carries a stable
marker Name from `strip_marker_name(source_block, path)`:

```
_chrome_HBIcon_1_2_1_1_T_1_1_I_1
└──────┬─────┘└─────────┬─────────┘
   source_block    path in original AST (dots → underscores)
```

Recipe 23 walks the manifest of stripped sites, looks up each marker
Container by Name, creates a `BlockInstance` in the same parent, binds the
input parameters, then removes the marker Container.

## When to use

```
Order:
1. Recipe 01-04 (entities + actions)
2. Recipe 22 (custom blocks — Recipe 22 must complete + publish first)
3. Recipe 07 (dechromed screens — emits stripped placeholders)
4. **Recipe 23 (this — chrome wrap)**
5. Recipe 10 (theme replace)
6. Recipe 11 (default screen)
7. Recipe 99 (publish + verify)
```

Recipe 22's blocks MUST be published before Recipe 23 runs — the
BlockInstance creation looks up the block signature via
`eSpace.MobileFlows.SelectMany(f => f.GetAllDescendantsOfType<IMobileBlock>())`
or `eSpace.References.SelectMany(r => r.Blocks)` — both require the block to
have landed.

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{SCREEN_NAME}}` | Screen being wrapped | `ManageSettings` |
| `{{FLOW_NAME}}` | MobileFlow that owns the screen | `MainFlow` |
| `{{ENTRIES_BLOCK}}` | One block per chrome site | see below |

## Single-call template

```csharp
eSpace => {
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{{FLOW_NAME}}");
    if (flow == null) { Console.WriteLine($"FAILED: MobileFlow {{FLOW_NAME}} not found"); return; }
    var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
        .FirstOrDefault(s => s.Name == "{{SCREEN_NAME}}");
    if (screen == null) { Console.WriteLine($"FAILED: Screen {{SCREEN_NAME}} not found"); return; }
    int wrapped = 0, missing = 0;

    {{ENTRIES_BLOCK}}

    Console.WriteLine($"Recipe 23: {{SCREEN_NAME}} | wrapped={wrapped}/{expected}, missing={missing} | Status: {(...)}");
}
```

## Sub-block — `{{ENTRIES_BLOCK}}` — one per chrome site

```csharp
{
    var marker = screen.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileContainer>()
        .FirstOrDefault(c => c.Name == "_chrome_HBIcon_1_2_1_1_T_1_1_I_1");
    if (marker == null) { Console.WriteLine($"WARN: chrome marker not found — skipping"); missing++; }
    else {
        var blockSig = eSpace.MobileFlows
            .SelectMany(f => f.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileBlock>())
            .FirstOrDefault(b => b.Name == "HBIcon")
            ?? eSpace.References.SelectMany(r => r.Blocks).FirstOrDefault(b => b.Name == "HBIcon");
        if (blockSig == null) { Console.WriteLine($"WARN: block HBIcon not found"); missing++; }
        else {
            var parent = marker.Parent;
            var bi = parent.CreateBlockInstance(blockSig);
            bi.Name = "CheckMark";  // original BlockInstance name from .tree.md
            { var p = bi.Parameters.FirstOrDefault(pp => pp.Name == "IconName"); if (p != null) p.SetValue("check"); }
            parent.RemoveWidget(marker);
            wrapped++;
        }
    }
}
```

## Expected stdout

```
Recipe 23: ManageSettings | wrapped=4/4, missing=0 | Status: OK
```

If `wrapped < expected` or `missing > 0`, status is `PARTIAL` — investigate
which markers didn't resolve.

## Common failures

### ✗ Marker Container not found

Cause: the dechromed screen never landed (Recipe 07 failed), or T2.2 didn't
name the strip site stably.
Fix: verify the marker name follows `_chrome_<source_block>_<path>` exactly.
Re-run Recipe 07 if needed.

### ✗ BlockSig is null (custom block not found)

Cause: Recipe 22 didn't run, OR ran but the block lives in a different app
that hasn't been imported.
Fix: confirm Recipe 22 completed and published. If cross-app, ensure the
producer app's reference is added (Studio Cmd+Q Manage Dependencies — see
`[[odc_mcp_reference_add_studio_only]]`).

### ✗ Parameter binding silently ignored

Cause: parameter name doesn't match a block input. The `FirstOrDefault`
guard returns null and we skip silently.
Fix: dump `bi.Parameters.Select(p => p.Name)` to confirm what's available.
Common: block was created with a different input-parameter name than the
caller expects.

### ✗ Visible drift after wrap

Cause: marker Container had non-chrome children that get removed along with
the marker. Per PLAN_GAP CW-A below, child widget preservation is not yet
wired.

## PLAN_GAP register

- **CW-A**: Children of stripped Containers are DISCARDED at wrap time
  rather than moved into the BlockInstance placeholders. For the Banking
  recreate this is OK — children were synthetic widgets the dechromed pass
  emitted only to keep the screen renderable, and the real BlockInstance
  carries its own internals. For screens where the stripped block had
  user-visible content inside its placeholders (e.g. a Card block whose
  caller passed text/icons via placeholder fillings), CW-A means content
  loss. Track placeholder fillings explicitly in v2.
- **CW-B**: Block input parameter values that contain runtime expressions
  (e.g. `Aggregate.Current.Field`) are passed as literal strings to
  `SetValue`. Whether OS UI evaluates them depends on the parameter type;
  Text-typed inputs work, Action-typed don't. Validate per-block.
- **CW-C**: `Parameters.FirstOrDefault(pp => pp.Name == X)` is the only
  guard. If the block input changes name between Recipe 22 author and
  Recipe 23 wrap, the wrap silently drops the binding. Recipe 22's
  diagnostic should declare its inputs; consider adding a cross-check.

## Memory refs

- [[odc_mcp_block_creation_works]] — IMobileFlow.CreateBlock works
- [[odc_mcp_layout_block_lifting_walls]] — layout-block rendering walls
- [[odc_mcp_reference_add_studio_only]] — cross-app reference walls

## Related recipes

- Recipe 07 — dechromed screen authoring (PAIRED with this recipe)
- Recipe 22 — custom block create (PREREQ for this recipe)
- Recipe 99 — publish + verify


## ⚠️ DEPRECATED (2026-06-13) — WRONG ORDER
Dechrome-then-chrome-wrap is the wrong build order (proven). It never fills the
layout placeholders, so content lands in the wrong slot. Use **Recipe 28**
(build screen ON the layout, fill MainContent/SideContent placeholders). Kept for
history only.
