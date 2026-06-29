# Recipe 22 — Custom Block create (CHROME phase)

## Purpose

Author a custom Web/Mobile Block via `IMobileFlow.CreateBlock(name)`. Custom
blocks carry the brand chrome that gets stripped during the dechromed-screen
pass (Recipe 07) — so this recipe runs BEFORE the chrome-wrap pass (Recipe 23)
that wires those screens to use the blocks.

Per `[[odc_mcp_block_creation_works]]`: non-layout blocks (cards, modals,
headers, icons) author cleanly via MCP. **Layout blocks** that own page
chrome (top nav, side nav, layout shells) have rendering walls per
`[[odc_mcp_layout_block_lifting_walls]]` and need Studio chat-pane authoring.

## When to use

After the structural-phase recipes (entities, server actions) are
published, but before any chrome-wrap of dechromed screens.

Order:
1. Recipe 01 (static entities)
2. Recipe 02 (server entities)
3. Recipe 03-04 (server + client actions — stubs)
4. **Recipe 22 (this — custom blocks)**
5. Recipe 07 (dechromed screens — Mentor strips block references)
6. Recipe 23 (chrome wrap — re-wires screens to use the blocks from this recipe)
7. Recipe 99 (publish + verify)

## Inputs

| Placeholder | Meaning | Example |
|---|---|---|
| `{{BLOCK_NAME}}` | Block identifier | `HBIcon` |
| `{{FLOW_NAME}}` | MobileFlow that owns the block | `Common` |
| `{{IS_PUBLIC}}` | Whether the block can be referenced from other apps | `true` |
| `{{INPUTS_BLOCK}}` | Input-parameter creation block | see below |
| `{{EVENTS_BLOCK}}` | Block-event input-parameter block | see below |
| `{{WIDGETS_BLOCK}}` | Widget tree creation block | see below |
| `{{STYLESHEET_BLOCK}}` | Block-scoped CSS (optional) | see below |

## Single-call template

```csharp
eSpace => {
    var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{{FLOW_NAME}}");
    if (flow == null) { Console.WriteLine($"FAILED: MobileFlow {{FLOW_NAME}} not found"); return; }

    // Idempotent: skip if block already exists (re-runs after publish failures land cleanly)
    var existing = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileBlock>()
        .FirstOrDefault(b => b.Name == "{{BLOCK_NAME}}");
    if (existing != null) { Console.WriteLine($"Recipe 22: {{BLOCK_NAME}} | Status: ALREADY_EXISTS"); return; }

    var block = flow.CreateBlock("{{BLOCK_NAME}}");
    block.IsPublic = {{IS_PUBLIC}};

    {{INPUTS_BLOCK}}
    {{EVENTS_BLOCK}}
    {{WIDGETS_BLOCK}}
    {{STYLESHEET_BLOCK}}

    Console.WriteLine($"Recipe 22: {{BLOCK_NAME}} | Status: OK");
}
```

## Sub-blocks

### `{{INPUTS_BLOCK}}` — Block input parameters

```csharp
{ var ip = block.CreateInputParameter("IconName");
  ip.DataType = eSpace.TextType;
  ip.IsMandatory = true; }
```

### `{{EVENTS_BLOCK}}` — Block events (Action-typed input parameters)

ODC convention: block events are exposed to parent screens as input
parameters typed `Action`. The parent passes an event-handler reference;
the block fires it via `TriggerEvent`.

```csharp
{ var ip = block.CreateInputParameter("OnSelect");
  ip.DataType = eSpace.ActionType;
  ip.IsMandatory = false;
  { var op = ip.CreateOutputParameter("SelectedId"); op.DataType = eSpace.IntegerType; }
}
```

### `{{WIDGETS_BLOCK}}` — Widget tree

Same widget API as screens — `block.CreateContainer()`, `c.CreateText()`,
`c.CreateButton()`, etc. See Recipe 07 for the widget vocabulary.

```csharp
var c1 = block.CreateContainer();
c1.Name = "IconWrap";
c1.Style.SetValue("icon-wrap");
{
    var t = c1.CreateText();
    t.Text = "IconName";  // Bound via expression in real render
}
```

### `{{STYLESHEET_BLOCK}}` — Block-scoped CSS

```csharp
block.StyleSheet.SetText(@".icon-wrap { display: inline-flex; ... }");
```

## Expected stdout

```
Recipe 22: HBIcon | inputs=1, public=True, stripped_chrome=0 | Status: OK
```

## Common failures

### ✗ `Block with name X already exists`

Cause: prior recipe call landed and we're re-running.
Fix: the `existing != null` guard at the top makes this idempotent. If you
want to forcibly recreate, use `flow.RemoveWidget(existing)` first (but be
sure no published screen references the block, or the publish will fail).

### ✗ Layout block authored but doesn't render correctly

Cause: per `[[odc_mcp_layout_block_lifting_walls]]`, layout-shell blocks
need 9 specific OS UI CSS classes (`layout`, `layout-top`, `main`,
`header-top`, `header-content`, `content`, `main-content`, `hero`,
`hero-content`) on nested wrappers. MCP authoring succeeds but runtime
rendering breaks. Use Studio chat-pane for layout blocks.

### ✗ Block event handler not callable from parent

Cause: forgot to type the input parameter as `eSpace.ActionType`.
Fix: confirm `DataType = eSpace.ActionType` for every event input. ODC has
no special "event" type — events ARE Action-typed inputs.

### ✗ Block visible in Studio but stylesheet has no effect

Cause: same as the screen variant — block CSS rules with `@import` get
stripped at publish per `[[odc_publish_strips_css_import]]`. Inline the
rules or use JS-injection via OnReady.

## Pre-flight checklist

- [ ] Flow exists (default `Common` for shared blocks; `MainFlow` for app-private)
- [ ] Block name unique within the flow
- [ ] If event params present: all use `eSpace.ActionType` for the input
- [ ] If layout block: prefer Studio chat-pane (this recipe will land but render breaks)

## Memory refs

- [[odc_mcp_block_creation_works]] — IMobileFlow.CreateBlock(name) confirmed
- [[odc_mcp_layout_block_lifting_walls]] — layout-shell block rendering issues
- [[odc_publish_strips_css_import]] — CSS @import stripping at publish
- [[odc_mcp_style_vs_customstyle]] — Style vs CustomStyle semantic distinction

## Related recipes

- Recipe 07 — dechromed screen authoring (strips block references that this recipe authors)
- Recipe 23 — chrome wrap (wires dechromed screens to use the blocks from this recipe)
- Recipe 99 — publish + verify
