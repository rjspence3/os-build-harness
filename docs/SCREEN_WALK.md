# Producing the screen-walk snapshot (`harness-verify --phase live --screens`)

`harness-verify --phase live` checks the UI assertions (`componentPresent`, `binding`,
`navigates`) against a **screen-walk snapshot** — a JSON file the orchestrator fetches
from the *built* app via the MCP and passes with `--screens`. This is the producer for
that file. (The other snapshot, `--entities`, is simpler: just save a `context_entities`
MCP response — see [`examples/README.md`](../examples/README.md).)

Target shape — the contract in `harness/verify.py` (`load_screens_snapshot`), with a
worked example in [`examples/task_tracker/live_screens.json`](../examples/task_tracker/live_screens.json):

```json
{"screens": [{"id": "<screen>",
              "components": [{"id": "<widget>", "type": "<type>", "boundTo": "<entity-or-aggregate>"}],
              "navigation": [{"fromComponent": "<widget>", "event": "onClick", "toScreen": "<dest>"}]}]}
```

## How it works

A **read-only** `applyModelApiCode` walk of ONE screen enumerates its widgets and prints
the contract JSON to stdout between two markers. It only *reads* Model-API properties (no
`CreateX`/`SetX`, no publish) — it does not modify the app.

## The walk (ODC CrossDevice / Mobile screens)

Reflection-free (broad `System.Reflection` is blocked in the sandbox); compiles under the
Mentor sandbox validator. Parameterize `{{SCREEN_NAME}}`; set `{{FALLBACK_IDS}}` to `false`
(named + typed widgets only — recommended) or `true` (also emit unnamed widgets with a
deterministic positional id `type_<index>`).

```csharp
eSpace => {
    string target = "{{SCREEN_NAME}}";
    bool fallbackIds = {{FALLBACK_IDS}};
    OutSystems.Model.UI.Mobile.IMobileScreen screen = null;
    foreach (var flow in eSpace.MobileFlows) {
        var s = ((OutSystems.Model.IModelObject)flow)
            .GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>()
            .FirstOrDefault(x => x.Name == target);
        if (s != null) { screen = s; break; }
    }
    if (screen == null) { Console.WriteLine("SCREENWALK_JSON_BEGIN");
        Console.WriteLine("{\"screens\":[]}"); Console.WriteLine("SCREENWALK_JSON_END"); return; }
    var widgets = ((OutSystems.Model.IModelObject)screen)
        .GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.Widgets.IMobileWidgetSignature>().ToArray();
    string comps = ""; string navs = ""; int counter = 0;
    foreach (var w in widgets) {
        string ty = "Widget"; string rawName = null;
        if (w is ServiceStudio.Plugin.NRWidgets.IButton wb) { ty="Button"; rawName=wb.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.ILink wl) { ty="Link"; rawName=wl.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.IInput wi) { ty="Input"; rawName=wi.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.IList wli) { ty="List"; rawName=wli.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.IImage wim) { ty="Image"; rawName=wim.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.IIcon wic) { ty="Icon"; rawName=wic.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.IExpression we) { ty="Expression"; rawName=we.Name; }
        else if (w is ServiceStudio.Plugin.NRWidgets.IContainer wc) { ty="Container"; rawName=wc.Name; }
        else if (w is OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget wbi) { ty="BlockInstance"; rawName=wbi.Name; }
        bool named = !string.IsNullOrEmpty(rawName);
        if (!named && !fallbackIds) { counter++; continue; }
        if (ty == "Widget" && !fallbackIds) { counter++; continue; }
        string id = named ? rawName : (ty + "_" + counter); counter++;
        string eid = id.Replace("\\","\\\\").Replace("\"","\\\"");
        string boundTo = null;
        if (w is ServiceStudio.Plugin.NRWidgets.IList wlst && wlst.Source != null
            && !string.IsNullOrEmpty(wlst.Source.DisplayName))
            boundTo = wlst.Source.DisplayName.Replace("\\","\\\\").Replace("\"","\\\"");
        string comp = "{\"id\":\"" + eid + "\",\"type\":\"" + ty + "\"";
        if (boundTo != null) comp = comp + ",\"boundTo\":\"" + boundTo + "\"";
        comp = comp + "}";
        if (comps.Length > 0) comps = comps + ","; comps = comps + comp;
        OutSystems.Model.UI.Mobile.Events.IBuiltinEvent onClick = null;
        if (w is ServiceStudio.Plugin.NRWidgets.IButton wbtn) onClick = wbtn.OnClick;
        else if (w is ServiceStudio.Plugin.NRWidgets.ILink wlnk) onClick = wlnk.OnClick;
        if (onClick != null && onClick.Destination != null) {
            var dest = onClick.Destination as OutSystems.Model.UI.Mobile.IMobileScreen;
            if (dest != null) {
                string toScreen = dest.Name.Replace("\\","\\\\").Replace("\"","\\\"");
                string nav = "{\"fromComponent\":\"" + eid + "\",\"event\":\"onClick\",\"toScreen\":\"" + toScreen + "\"}";
                if (navs.Length > 0) navs = navs + ","; navs = navs + nav;
            }
        }
    }
    string sne = screen.Name.Replace("\\","\\\\").Replace("\"","\\\"");
    Console.WriteLine("SCREENWALK_JSON_BEGIN");
    Console.WriteLine("{\"screens\":[{\"id\":\"" + sne + "\",\"components\":[" + comps + "],\"navigation\":[" + navs + "]}]}");
    Console.WriteLine("SCREENWALK_JSON_END");
}
```

Imports: `System.Linq, OutSystems.Model, OutSystems.Model.UI.Mobile,
OutSystems.Model.UI.Mobile.Widgets, OutSystems.Model.UI.Mobile.Events,
ServiceStudio.Plugin.NRWidgets`.

## Running it via the Mentor MCP

The Mentor MCP **will not execute user-supplied code verbatim** — it authors and runs its
own read walk from your *intent*. This is capture, not authoring: it reads and prints, and
persists nothing (live-proven read-only — app revision unchanged after the walk). Instruct
it from intent, not C#:

> Run a **strictly read-only** `applyModelApiCode` walk of screen `<SCREEN>` — read the model
> and print JSON only, author nothing. Enumerate the screen's `IMobileWidgetSignature`
> descendants; type each via `is` checks (include `ITableRecords` for ODC Tables); read `Name`
> from the concrete cast (`IMobileWidgetSignature` has no `.Name`). For a data-bound widget set
> `boundTo` from the source aggregate's `DisplayName` (e.g. `GetTaskLists.List`) **and**
> `sourceEntity` = the entity that aggregate queries (e.g. `TaskList`); else both null. Capture
> navigation from `OnClick.Destination as IMobileScreen`. Emit named + typed widgets only.
> Inline code, string concatenation, no local functions, no `System.` prefix. Print ONE line of
> JSON between `SCREENWALK_JSON_BEGIN` and `SCREENWALK_JSON_END` in exactly this shape:
> `{"screens":[{"id":..,"components":[{"id","type","boundTo","sourceEntity"}],"navigation":[..]}]}`.

**Stdout fallback (observed live):** the Mentor sandbox's validation pipeline can swallow
`applyModelApiCode` stdout. Mentor then derives the same JSON from its authoritative
screen-detail read — identical read-only model data, so the result stays deterministic. Take
the JSON from between the markers wherever it appears (tool stdout or terminal `result.summary`).

Read the JSON from the `applyModelApiCode` `tool_end` event (`mentor_get_run details=true`
→ `mentor_get_event` on the id if truncated); `mentor_cancel` after `tool_end`. Save between
the markers to `screens.json` and pass `--screens screens.json`. (A non-guardrailed
`applyModelApiCode` actuator can run the C# above verbatim.)

## Validated

Proven live against a real 31-widget screen: the walk emitted the contract JSON,
`load_screens_snapshot` parsed it (31 components, 8 nav edges), and `componentPresent` /
`binding` / `navigates` assertions each evaluated to a real **pass** (correct spec) and
**fail** (wrong spec) — the same pipeline the shipped `examples/task_tracker/live_screens.json`
exercises offline.

## Coverage + limits (read these)

- **Widgets must be NAMED for reliable assertions.** Mentor-generated screens often leave
  widgets unnamed → they're skipped by default (or get synthetic `type_<index>` ids under
  `FALLBACK_IDS=true`, which only match spec assertions using that same scheme). **Name the
  widgets your spec asserts on** (`componentPresent`/`binding`).
- **ODC Table widgets are `ITableRecords` (live-proven 2026-07-02).** The base type cascade
  MISSES them — include an `ITableRecords` branch (type `"Table"`/`"ITableRecords"`, read
  `.Name`). `IList` binding is proven via `IList.Source.DisplayName`.
- **`boundTo` is the AGGREGATE; `sourceEntity` is the resolved entity (both emitted, proven).**
  A data widget's live source is an aggregate (`GetTaskLists.List`), not the bare entity
  (`TaskList`). The walk emits BOTH: `boundTo` = the aggregate `DisplayName`, and `sourceEntity`
  = the entity that aggregate queries, resolved in the walk. `verify._eval_binding` matches a
  spec `binding` against **either** form — so an entity-level assertion (`TaskList`) passes
  against an aggregate-bound widget with no fragile name heuristic. Live-proven end-to-end:
  task_tracker `harness-verify --phase live` scores **9/9, exit 0** (both table bindings match
  via `sourceEntity`). A wrong `sourceEntity` still fails — no false pass.
- **Navigation** captures `OnClick.Destination` that resolves to a screen (emit the target as
  the screen name or id — `harness-verify` normalizes both to the spec id). Navigation via a
  screen *action* (Destination null) is intentionally not captured.
- **One screen per call.** A full-screen walk can overflow MCP transport (~35–40K chars); the
  named + typed filter keeps output compact. Never batch screens into one call.
- Targets ODC **CrossDevice / Mobile** screens (the `MobileFlows` / `IMobileScreen` API).
