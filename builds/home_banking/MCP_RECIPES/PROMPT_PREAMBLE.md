# MCP Recipe — Prompt Preamble

Prepend this preamble to every Mentor turn that uses a recipe from this library. It primes Mentor to act like a deterministic compiler, not an exploratory agent.

## What this preamble does

- Tells Mentor the API surface is known — no probing, no `get_app_summary` waste.
- References the corpus memories so Mentor doesn't repeat solved problems.
- Locks Mentor to a single `applyModelApiCode` call per turn.
- Sets a strict failure protocol: stop, report verbatim, do not iterate.
- Defines the diagnostic-output shape so the caller can verify.

## Paste verbatim, prefixed to the recipe body

```
You are executing a Mentor MCP recipe from a debugged library. The library is
a defined methodology — recipes compose in phase order (STRUCTURE → LOGIC →
CHROME → VERIFY) and each recipe defines as much as possible explicitly. The
API surface and patterns are pre-resolved — do NOT explore, probe, reflect,
or call get_app_summary.

CONSTRAINTS (non-negotiable):

1. ONE applyModelApiCode call per recipe. No reflection, no exploratory reads.
2. Use the EXACT code provided. Do not "improve" it.
3. If the call throws compile or runtime error: STOP and report the error
   verbatim. Do NOT iterate, do NOT regenerate, do NOT attempt a fix.
4. Print only the diagnostic output the recipe specifies. No extra summarization.
5. Do NOT publish from inside the recipe. The caller runs publish_start
   separately.
6. The recipe's PHASE annotation determines what the call may touch:
   - STRUCTURE: entities, statics, roles, dechromed screens, default screen.
     Uses ONLY standard OutSystemsUI widgets + the manifest's own custom
     types. Custom blocks (Menu, Header, brand icons) are NOT yet authored —
     do not reference them.
   - LOGIC: server/service/client actions; expressions referencing the
     STRUCTURE phase's entities. No widget/screen mutations.
   - CHROME: custom blocks, theme CSS, chrome-wrap (replacing dechromed
     widget shells with custom-block instances). Assumes STRUCTURE + LOGIC
     phases published successfully.
   - VERIFY: read-only context_* / applyModelApiCode probes that compare
     published state vs manifest expectations.
   A phase-violating call (e.g. a STRUCTURE recipe trying to wrap a screen
   in HBIcon) is a recipe-library bug — STOP and report.

API SURFACE PRE-RESOLVED (do not rediscover):

- Server entity creation: eSpace.CreateServerEntity(name)
- PK setup: entity.IdentifierAttribute = idAttr (assign AFTER attr created, BEFORE
  any other attribute). idAttr.IsAutoNumber = OutSystems.Model.Enumerations.AutoNumber.Yes;
  idAttr.IsMandatory = true; idAttr.DataType = eSpace.LongIntegerType.
  (IsAutoNumber is an enum, NOT bool. Values: No | Yes | YesIfEmpty)
- FK attributes: a.DataType = <staticEntity>.IdentifierType or
  userIdentType (resolved via eSpace.References)
- FK DeleteRule: ALWAYS set to OutSystems.Model.Enumerations.DeleteRule.Ignore
  (Protect is deprecated and causes OS-BLD-40409 at publish time)
- Static entity creation: eSpace.CreateStaticEntity(name)
- Role creation: eSpace.CreateRole(name); role.Public = false
- Server action: eSpace.CreateServerAction(name); action.Public = bool
- SQL node: action.CreateNode<ISQLNode>("name"); sqlNode.Statement = "SQL";
  sqlNode.CreateInputParameter(name); sqlNode.SetArgumentValue(param, "expr")
- Screen creation: BLOCKED on some apps by a platform bug — recipe must declare
  if it touches CreateScreen and the caller will route accordingly
- DefaultScreen: eSpace.DefaultScreen = some IScreen reference
- Publish: external to recipes; caller runs publish_start then publish_status

CORPUS REFERENCES (relevant memories, already encoded into recipes):

- odc_mcp_entity_auto_actions_incomplete — PK required before publish
- odc_db_upgrade_pk_change_blocked — never alter PK post-publish; delete+recreate
- odc_mcp_sql_node_api — ISQLNode surface
- odc_mcp_publish_terminal_success_gate — never cancel a session you intend to publish
- odc_mcp_screen_creation_broken_complianceops — known per-app CreateScreen bug
- odc_mcp_record_literal_via_typed_local — Server Action record creation pattern
- odc_long_integer_to_identifier_cast — LongIntegerToIdentifier for ID arguments
- odc_mcp_assign_node_iteration_not_flow_order — identify Assign nodes by Variable name

REQUIRED IMPORTS (always include these in the imports array):

System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Logic
OutSystems.Model.Logic.Nodes
OutSystems.Model.Enumerations
OutSystems.Model.Types

DIAGNOSTIC OUTPUT FORMAT:

End the C# block with ONE Console.WriteLine that prints, on a single line:
"Recipe <NN>: <Name> | Created: <comma list> | Status: OK"

If any intermediate step asserts a non-null pre-condition that fails, print:
"Recipe <NN>: <Name> | FAILED at <step name>: <what was unexpected>"
and return from the lambda. The caller treats this as a fatal stop.

API ANTI-HALLUCINATION TABLE (251 CS1061 compile errors across two production
builds trace to these — the member you remember does NOT exist; use the right column):

| You will want to write | It does not exist — write this instead |
|---|---|
| `ITypeSignature.Name` | reflect `.DisplayName` via GetProperty |
| `IMobileWidget` | `OutSystems.Model.UI.Mobile.Widgets.IMobileWidgetSignature` |
| `idAttr.AutoNumber = ...` | `idAttr.IsAutoNumber = OutSystems.Model.Enumerations.AutoNumber.Yes` |
| `eSpace.Actions` | `eSpace.ServerActions` / `eSpace.ServiceActions` (separate collections) |
| `Reference.MobileBlocks` | `reference.GetAllDescendantsOfType<IMobileBlockSignature>()` |
| `list.Append(x)` | `ListAppend` node / `RecordLiteral` patterns |
| `Services.ModelServices.TryParseKey(s, ref k)` | `TryParseKey(s, out k)` — `out`, not `ref` |
| `ExpressionDefinition.FromString(s)` | `CreateAssignment(name, expr)` two-arg overload, or implicit string |
| `eSpace.Themes` / `CreateTheme` / `Flows` | `MobileThemes` / `CreateMobileTheme` / `MobileFlows` (Mobile-prefixed) |
| `IServerAction.StartNode` / `.EndNode` | `CreateNode<IStartNode>()` + `endNode.ConnectedBelow(startNode)` |
| `screen.CreateContainer()` | `parent.CreateWidget<IContainer>("Name")` |
| `IPlaceholderWidget.SetStyle(...)` | `IPlaceholderWidget.SetStyleClasses(...)` (placeholders only; containers/buttons keep `SetStyle`) |
| `widget.GetType().GetProperty("Parent")` | `GetProperties().FirstOrDefault(p => p.Name == "Parent")` — single-name GetProperty throws AmbiguousMatch on widget types |
| `ITextWidget.GetStyleClasses()` / `SetStyleClasses("cls")` | read `w.StyleClasses.Text`; write `w.SetStyleClasses(ExpressionDefinition.Parse("\"cls\""))` — no getter; setter takes an ExpressionDefinition (a quoted-string literal), not a bare string |
| `IMobileFlow.DefaultScreen = s` | `eSpace.DefaultScreen = s` (eSpace-level only) |
| `IButton.SetLabel("X")` / `ILink.SetLabel` | text via an `IExpression` inside `btn.Content` (SetLabel does not exist) — W-A |
| `IBuiltinEvent.SetDestination(screen)` | `btn.OnClick.Destination = screen` (it's a property, no setter) — W-B |
| `IInput` with no Variable | `screen.CreateLocalVariable(n)` + `input.SetVariable(n)` — "Variable must be set" else — W-C |
| Button with no OnClick | every Button needs `OnClick.Destination` (self-nav OK) — "On Click must be set" else — W-D |
| `block.Public = true` on a layout/UI block | keep `Public = false` — `OS-BLD-40409` deprecated-feature publish crash (V23) |
| `eSpace.Entities` for referenced entities | `eSpace.References.Named("X").Entities` (local-only collection else) — V25 |
| `If(IsDesktop(),...)` in a Web Style expression | static desktop-equivalent classes — `IsDesktop/IsTablet/IsPhone` rejected in Web Style (V24) |
| set `theme.StyleSheet` and expect styling | also ACTIVATE the theme: `eSpace.DefaultMobileTheme` / `MainFlow.Theme` / `Layouts.Theme` (V26) |
| dechrome screen → chrome-wrap after (Recipe 23) | build screen ON the layout, fill MainContent/SideContent placeholders (Recipe 28) — wrap-after is the wrong order |

ANTI-PATTERNS — DO NOT (verified failures from production builds):

1. DO NOT skip a phase or batch because you think it's "not needed for visual
   parity" or "doesn't fit in budget." Phase order is dependency order. If a
   phase has been planned, dispatch it. If you can't, HALT and report — never
   skip ahead.

2. DO NOT replace the provided C# with your own "simpler" version. The recipe
   library encodes hard-won workarounds for OML serialization, AVS validation,
   sandbox import allowlist, and Mentor session quirks. "Improving" the code
   reliably breaks the build.

3. DO NOT use System.Collections.Generic, System.Collections.IEnumerable, or
   any System namespace outside System and System.Linq. They are sandbox-walled
   (use .ToArray() + typed array iteration).

4. DO NOT trust your own narrative "Status: OK" without verifying state.
   Mentor reports successful BlockInstance wraps that OML rejects at publish.
   The published OML is the source of truth — verify via context_search,
   app_refs, or follow-up applyModelApiCode probe before claiming success.

5. DO NOT set IServerAction.Public = true. Removed feature in ODC
   (OS-BLD-40409). Use IServiceAction.Public = true for cross-app exposure.

6. Chrome-wrap source binding is TYPE-DEPENDENT (Portal4 bisection 2026-06-11):
   LOCAL IMobileBlock blocks → reflection on SourceWebBlock (proven published,
   Rebake1 rev 23). REFERENCED IMobileBlockSignature → typed
   bi.SourceBlock = signature (proven published, Counter probe rev 28).
   Assigning a local block OBJECT via the typed setter corrupts the OML
   (OS-APPS-40028 at publish, zero in-session errors). The recipe encodes the
   correct branch per type — do not alter it.

7. DO NOT use getScreen on complex screens — returns 277K-char dumps that
   crash Mentor synthesis. Walk via applyModelApiCode + IMobileScreen +
   IMobileWidgetSignature.

8. DO NOT improvise widget content for a screen instead of executing the
   recipe. The captured widget tree IS the design; deviation produces a
   different app, not a clone.

Now execute the following recipe:
```

Below this preamble, paste the body of the chosen recipe file (everything after
its `## Mentor prompt (paste verbatim)` section).
