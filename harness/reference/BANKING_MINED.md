<!-- Mined from the home_banking clone build (the benchmark ODC build) — builds/home_banking/MCP_RECIPES/.
     Feeds CAPABILITY_MATRIX.md (coverage) + SEAMS.md (thrash-free notes). Each row cites its source recipe. -->

# Banking-clone build intelligence (coverage + thrash)

## Coverage — ODC constructs authored, with the working Model-API approach
| Construct | Working approach (Model-API/Mentor) | Contract/gotcha | Source |
|---|---|---|---|
| Server entity + Long PK | `CreateServerEntity`; `CreateAttribute("Id")` LongInteger IsAutoNumber; set `IdentifierAttribute` FIRST | can't change published PK (OS-RDBS-GEN-40003) | 01_entity_server |
| Typed attributes | `CreateAttribute`+`DataType=eSpace.{Text/Bool/Integer/Decimal/DateTime/Currency/BinaryData/Email}Type` | large text OK (Text 50000000) | 01_entity_server |
| FK attribute | `DataType=References...Named("User").IdentifierType`; `DeleteRule=Ignore` | null-guard identType or OS-APPS-40028; User under References not Entities | 01_entity_server |
| Static entity + records | `CreateStaticEntity`; Public=true; `CreateRecord(label)`+`SetAttributeValue`; MANUAL Long PK + explicit Ids | CreateRecord throws if exists; auto-number unsupported for static | 02_entity_static |
| Structures | reference from `eSpace.Structures`/`References`; use in action/agent signatures; nesting supported | — | BACKEND_CLONE_SPEC §a |
| Role + anonymous | `CreateRole`; `screen.Roles.Add`; anon = `AnonymousAccess=true` + clear Roles | role-gated + no Login → _error.html; Mentor auto-adds role filter — clear it | 03_role, 30_remaining_screens |
| Screen aggregate + filter/sort/join/calc/groupby/agg | `CreateScreenAggregate(false,"GetX")`; ns `OutSystems.Model.Logic.Aggregates` `CreateFilter/Sort/Join/CalculatedAttribute/GroupByAttribute/AggregatedAttribute`; `AggregationType.Sum` | wrong ns=CS0234; quote literals; source entity must be Public+fully-imported | 08/29 dashboard |
| SQL node | `CreateNode<ISQLNode>`; `Statement=@"...{Entity}...[Attr]...@P"`; `CreateInputParameter`+bind | `{Entity}` braces `[Attr]` brackets `@X` declare+bind; LongIntegerToIdentifier cast | 05_action_sql_update |
| Server action | `CreateServerAction`; In/Out params; `IExecuteServerActionNode.Action`; create `IStartNode`+`IEndNode`, wire `.Target`/`ConnectedBelow` | Server Actions can't be Public in Apps (OS-BLD-40409) | 04_action_crud |
| Service action (public API) | `CreateServiceAction`; `.Public=true` | compiles+cross-app callable (the 96-action Core contract) | GAPS, BACKEND_CLONE_SPEC §b |
| Action body nodes | `CreateNode<IAssign/IExecuteAction/IIf/IForEach/IEnd>().ConnectedBelow`; If `ConnectedToTheTrueBranchOf`; ForEach `loop.CycleTarget=body` | Assign iteration ≠ flow order (id by var name); CycleTarget not Target; LLM node ServerRequestTimeout=60 | 05a, 16 |
| Table / detail / dashboard / wizard / modal / master-detail screens | `CreateScreen`+Title+Roles; aggregate + ITableRecords `GetX.List.Current.Entity.Attr`; detail `CreateInputParameter(parent.IdentifierType)`+MaxRecords1; wizard StepNo+per-step `Visible="StepNo=N"`; modal `CreatePopup`+Bool `Visible`; sidebar `Visible=IsOpen`+`Agg.Refresh()` | Mentor Web refuses >1 Dashboard/app; too many widgets → screen-scope session wall (stage across turns) | 07/08/09/12/13/15 |
| Widgets | `parent.CreateWidget<IContainer/IExpression/IButton/IInput>`; button text via IExpression in `.Content`; nav `OnClick.DestinationScreen`+`SetArgumentValue` | no IButton.SetLabel / no SetDestination; IInput REQUIRES bound Variable; block-instance can't nest children | 28 W-A..D |
| Chart (Column/Pie) | `addReferenceToElements` OutSystemsCharts→ReferenceWebBlock in MobileFlows["Charts"]; `CreateWidget<IMobileBlockInstanceWidget>`+`SourceBlock=Charts\ColumnChart`; bind DataPointList | CHART WALL RETIRED — native works; only DATA wiring is grammar friction (2-series via 2 DataPoint lists) | 28, 29 |
| Web block | `flow.CreateBlock`; `CreateInputParameter`; events=ActionType inputs; widgets same API | NEVER Public=true on layout/UI block (OS-BLD-40409) | 22_block_create |
| Layout/menu (author into placeholders) | `inst.PlaceholdersContent.First(p=>p.Placeholder.Name=="MainContent").CreateWidget<T>()` | layout-block reparent silently no-ops; build into right placeholder from start | 28 |
| Theme / CSS | `MobileThemes.First ?? CreateMobileTheme`; `theme.StyleSheet=@"css"`; ACTIVATE via `DefaultMobileTheme`/`MainFlow.Theme` | fresh theme inert until activated; @import stripped at publish (use @font-face); Style=class vs CustomStyle=inline; verify at RUNTIME | 10/27 |
| Theme anchoring | `w.SetStyle("\"class\"")` / `SetStyleClasses`; conditional class verbatim | class names are string literals (escape \"); bare ident=variable; IsDesktop() rejected in Web Style | 27 |
| Custom fonts/icons | `@font-face hb-icons`+Sora in theme; icon = font+`.hb-icon` class ligature; re-host binaries as Resources | original URLs UUID-unstable per deploy; block-import a red herring for icons | V6_BUILD_SPEC §7 |
| Exposed REST | `CreateIntegration<IRestService>`+`CreateAction`+HTTPMethod/URLPath/params; Authentication=None; auto Start node | live-verified 200; used for temp triggers | HANDOFF, MEMORY rest_endpoint |
| Consumed REST / external producers | reference via `addReferenceToElements` (Firebase/UltimatePDF/Lottie/Markdown/InputMasks) | reference-add is the friction | walls Wall03 |
| Business Process / BPT | `CreateBusinessProcess`; `CreateNode<IStart/IAutomaticActivity/IHumanActivity/IDecision/IEnd>`; `Start.StartProcessOn=event`+`TriggerMode=Event`; auto-activity `ActionToTrigger=publicServiceAction` | auto-activity can ONLY call a PUBLIC Service Action; publishing 0-process Workflow app corrupts verify cache | HANDOFF |
| Human activity gate | `IHumanActivityNode`; `DestinationScreen` via addReferenceToElements(screenKey,appKey); `CreateCloseOnCondition(...)` correlate event.RequestId=Start.RequestId | else gate never closes; DestinationScreen param type must match (Long vs Identifier) | HANDOFF |
| Decision / global event | `IDecisionNode` `IOutcome.Target`+`.Value`; `CreateGlobalEvent` in NON-Workflow app; raise `ITriggerGlobalNode` | CreateGlobalEvent THROWS in BusinessProcess-kind app | HANDOFF |
| AI Agent structure | `CreateAgent`; `EnableActionCalling=true`; `app_create kind=AIAgent` = BARE shell | template_Agent clone arrives with 6 SAs + Memory + connection | 17 |
| AI Agent tool wiring | `handler=agent.CreateActionHandler()` (PARAMETERLESS); `handler.Action=sa`; per-arg `SetArgumentValue`+`IsFilledByAI=false`; `CreateNode<ICallAgentNode>().Agent=agent` | CRACKED 2026-06-12; tool = Server Action, no special Tool type | 20/21 |
| AI Agent system prompt | literal in BuildMessages SA `SystemMessageContent.ContentText`, switched on AgentsConsumerAppId | NOT on AgentTask; inline [{Role}] literal rejected; edit via applyModelApiCode not NL synthesis | 19, MEMORY |
| **AI Model binding** | **WALL LIFTED 2026-07-05** — bind agent AIModel slot to a **Trial** AIModelConnection (`TrialClaudeHaiku4_5`) in the authoring turn; MCP-only | **Publishes clean (rev 1→2, NO OS-APPS-40028). Portal-only at banking-build time; NO LONGER required.** Use a Trial model. | 17, MEMORY ai_model_binding_portal_only (CORRECTED) |
| Sample data/bootstrap | native SampleData/ + LoadSampleData orchestrator + JSON resources + IsInDevStage gate | runs once on first publish (DELETE-then-INSERT + remove guard to re-seed) | MEMORY native_sample_data |
| Multi-app references | `AddDependency(ParseGlobalKey("<producerKey>*<elementKey>"))`+RefreshDependencies; or addReferenceToElements | referenced elements under References.Named("X").Entities; import STATIC too; hidden Id-only stub → OS-APPS-40028 | 28/29 |
| NOT exercised in banking | external .NET libraries; timers; explicit index authoring | — | — |

## Thrash / walls — symptom → first-try resolution (the 0%-thrash notes)
| Symptom | Resolution | Source |
|---|---|---|
| Bulk addReferenceToElements (55-86 elems) hangs >10-22min | cap ~15 elems/call, split per producer app | GAPS V6/V15 |
| Each fresh turn burns 3-5min on get_app_summary | WARM-SESSION: pay it once, resume via session_id+token (3× speedup) | WARM_SESSION_DISPATCH |
| Aggregate/expr on referenced entity → OS-APPS-40028, 0 in-session errors | fully element-import EVERY touched entity (incl static) TryParseGlobalKey→AddDependency→RefreshDependencies; isolate imports in own turn | 29, MEMORY hidden_stub |
| ListAppend onto client-action node throws + rolls back turn's imports | use a data AGGREGATE for chart data; isolate entity-imports in own committing turn | 29 |
| Fresh theme CSS inert at runtime | ACTIVATE theme (DefaultMobileTheme/MainFlow.Theme); verify at RUNTIME not in-model | GAPS V26, walls Wall03 |
| Icons render as name-texts, 0 glyphs | add @font-face hb-icons + .hb-icon class to theme + apply class; block-import not needed | GAPS V22 |
| List/Structure locals silently become Text → publish rejects List ops | renderer must resolve "<X> List"/Structure to real IDataType (harvest a verified List-typed call first) | GAPS V19 |
| Server/UI-block Public=true → OS-BLD-40409 | cross-app actions = ServiceAction Public=true; UI blocks Public=false | GAPS A1/V23 |
| Human gate never closes | add CloseOnCondition correlating event.RequestId=Start.RequestId | HANDOFF, walls Wall01 |
| Publishing 0-process Workflow app locks all writes ("invalid verify caches") | author refs+process+publish in ONE turn; recover via SkipESpaceValidation+SkipDependencyValidation atop mutating block, or Studio reload | HANDOFF |
| Tool-wiring CreateActionHandler(action) CS1061 ("was verified") | parameterless CreateActionHandler() then .Action=sa; read tool_end EVENTS not chat summary (phantom) | 20, MEMORY phantom_authoring |
| AIAgent action invocation via exec_in_app → 404 | temp anonymous REST trigger → AgentFlow (RequestId=0), publish, same-origin fetch, remove | INTAKE_AGENT proof |
| Session reports success but rev won't move (phantom) | fresh mentor_start per committing edit; trust rev-increment; cancel only read-only turns (never a mutation) | 29, MEMORY session_wedge |
| Publish succeeded + no_changes_detected → nothing deployed | don't report as landed; verify deployed inventory | 99_verify_phase |
| dechrome→chrome-wrap wrong slot / OS-APPS-40028 "not valid OML" | abandon dechrome→wrap; build ON active theme layout, author INTO named placeholders | 28, GAPS V14 |
| `[id*=...]` needed to style widgets | CSS substring selectors publish clean; target b{N}-{WidgetName} classes not domain ids | GAPS V18 |
| MCP transport truncates AgentTask/prompt at ~35,877 chars | getServerAction returns C# incl literal; or "describe+quote fixed phrases"; byte-exact needs Studio | BACKEND_CLONE_SPEC |
| Embedding base64 binary in applyModelApiCode HANGS | binary enters at RUNTIME (REST body/screen input), never in the authoring call | HANDOFF |

**Two big strategic walls (design-level, HITL):** runtime role-gated screens 401 without a real customer login (needs end-user login or anonymous-backoffice demo path); and built-from-scratch screens can't match originals — adopt an existing pixel-faithful clone and reference-swap the data layer rather than restyle from scratch.
