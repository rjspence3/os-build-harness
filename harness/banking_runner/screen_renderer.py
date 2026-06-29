"""Dechromed screen renderer (R9a).

Takes a parsed ScreenAST + manifest entry → emits Mentor MCP applyModelApiCode
that authors the screen using only standard OutSystemsUI components. Custom
blocks (Menu, Header, HBIcon, AlignCenter, etc.) are STRIPPED — they will be
wired later by Recipe 23 (chrome wrap).

The output is a STRUCTURE-phase recipe: the screen has correct data bindings,
correct widget hierarchy, working screen actions, but renders with OS UI
default look. The chrome pass replaces stripped placeholders + adds brand
blocks later.

Status: MVP — handles Container, Text, Button, Dropdown, Input, Image, If,
Placeholder/PLACEHOLDER, plus BlockInstance-to-OSUI-standard (Layout*, Wizard,
Carousel, Chart, etc.). Unknown widget types fall through with a TODO comment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from harness.banking_runner.tree_parser import ScreenAST, WidgetNode


# OS UI standard blocks — these are NOT considered custom chrome. Keep verbatim.
OS_UI_STANDARD_BLOCKS = {
    "LayoutTopMenu", "LayoutSideMenu", "LayoutBlank", "LayoutTop",
    "Wizard", "WizardItem",
    "Carousel", "StackedCarousel", "Tabs", "TabsHeader", "TabsContent",
    "Accordion", "AccordionItem", "Modal", "Notification",
    "ColumnChart", "PieChart", "LineChart", "AreaChart",
    "ChartXAxis", "ChartYAxis", "ChartSeriesStyling",
    "Pagination", "PaginationDropdown",
    "ColumnsMediumLeft", "ColumnsMediumRight", "Columns2",
    "Gallery", "ItemCard", "Card", "ListItem",
    "BlankSlate", "CheckMark", "Progress", "Loading",
    "Tooltip", "Popover", "Dropdown", "DateRangePicker",
}


# Widget types that map to Mentor MCP IWidget* concrete creators.
# Each handler takes (parent_var: str, node: WidgetNode, ctx: RenderContext) → list[str] of C# lines.
WIDGET_HANDLERS: dict[str, callable] = {}


# Canonical Model API widget interfaces (verified from prior-session ODC docs:
# `parent.CreateWidget<T>("Name")` is the real creation method — NOT
# screen.CreateContainer(), which does not exist on IMobileScreen).
_WIDGET_IFACE: dict[str, str] = {
    "container": "ServiceStudio.Plugin.NRWidgets.IContainer",
    "text": "OutSystems.Model.UI.Mobile.Widgets.ITextWidget",
    "button": "ServiceStudio.Plugin.NRWidgets.IButton",
    "if": "ServiceStudio.Plugin.NRWidgets.IIfWidget",
    "expression": "ServiceStudio.Plugin.NRWidgets.IExpression",
    "image": "ServiceStudio.Plugin.NRWidgets.IImage",
    "input": "OutSystems.Model.UI.Mobile.Widgets.IInput",
    "list": "ServiceStudio.Plugin.NRWidgets.IList",
    # Placeholder creation discovered 2026-06-11 (LayoutBlank probe): in-place
    # CreateWidget<IPlaceholderWidget> nests correctly — the old "placeholder
    # reparenting silently no-ops" wall only applies to MOVING placeholders.
    "placeholder": "OutSystems.Model.UI.Mobile.Widgets.IPlaceholderWidget",
}
_VAR_PREFIX: dict[str, str] = {
    "container": "c", "text": "t", "button": "btn", "if": "iff",
    "expression": "expr", "image": "img", "input": "inp", "list": "lst",
    "placeholder": "ph",
}


@dataclass
class RenderContext:
    """Mutable state during render. Tracks unique variable names + accumulated lines."""
    screen_var: str = "screen"
    lines: list[str] = None
    var_counter: int = 0
    # BLOCK-DEFINITION mode: render Placeholder capture lines as real
    # CreateWidget<IPlaceholderWidget> calls instead of descending past them.
    # Set by block_renderer.render_block; screens leave this False.
    emit_real_placeholders: bool = False
    # Name assigned by the most recent _create_widget call (the widget Name,
    # which may differ from the C# var) — consumed by the stub collector.
    last_widget_name: str = ""
    # LOGIC-patch collector: (kind, widget_name, original_expression) for every
    # site stubbed/deferred during render. kind ∈ {"value", "visible"}.
    # Consumed by render_screen_logic_patch to emit the post-infra restore
    # recipe (patch-in-place — re-authoring the screen would destroy its
    # screen-scoped aggregates and typed locals).
    stub_patches: list = None
    stripped_count: int = 0           # how many custom-chrome BlockInstances were stripped
    stripped_blocks: list[str] = None  # names of stripped custom blocks
    used_names: set = None             # widget Names already assigned (CreateWidget needs unique names)
    # Aggregate names whose Source= clause the R8 tree parser couldn't read.
    # We emit a `// TODO aggregate ...` comment for these instead of creating
    # a ScreenAggregate object. Expressions that reference these names by
    # token must be stubbed to "" by the expression validator (otherwise the
    # OML validator rejects publish: "Can't identify <name> element"). The
    # name set is populated by `_emit_aggregates` and consumed by
    # `_expression_value_safe` via `ctx`.
    unauthored_aggregates: set = None
    # Aggregate names that DID author successfully (source parsed, CreateSource
    # called). Used by `_expression_value_safe` to recognize safe `Get<X>.…`
    # path references vs unresolvable ones (e.g. `GetCounters.PendingRequests`
    # where GetCounters is neither an aggregate nor authored — could be a
    # getter ScreenAction the dechromed phase doesn't yet create).
    authored_aggregates: set = None
    # Local-variable names whose source AST data_type fell back to TextType
    # because `_resolve_data_type` had no Structure/Record mapping (e.g.
    # `NewTransfer:{Amount:Currency,...}`). Any widget property expression that
    # references `<localname>.Field` on these MUST be deferred — the AVS
    # publish validator rejects field-path access on a Text-typed local with
    # the closure-rule family error OS-APPS-40028 (second layer; first layer
    # was DefaultScreen rewire). Populated by `_emit_locals`, consumed by
    # `_apply_props`. Baked 2026-06-02 after the v5 dispatch caught
    # c49.SetVisible("NewTransfer.SelectedTransferDateOptionId=...") publishing
    # cleanly through applyModelApiCode but failing at AVS.
    unmapped_locals: set = None

    def __post_init__(self):
        if self.lines is None:
            self.lines = []
        if self.stripped_blocks is None:
            self.stripped_blocks = []
        if self.used_names is None:
            self.used_names = set()
        if self.unauthored_aggregates is None:
            self.unauthored_aggregates = set()
        if self.authored_aggregates is None:
            self.authored_aggregates = set()
        if self.unmapped_locals is None:
            self.unmapped_locals = set()

    def fresh_var(self, kind: str) -> str:
        """Generate a unique C# variable name for a widget."""
        self.var_counter += 1
        return f"{kind}{self.var_counter}"

    def emit(self, line: str):
        self.lines.append(line)


def _create_widget(ctx: "RenderContext", parent_var: str, kind: str,
                   node: Optional[WidgetNode] = None, *, name: Optional[str] = None) -> str:
    """Emit a `parent.CreateWidget<T>("Name")` line and return the new var.

    CreateWidget requires a non-empty, screen-unique Name. When `name` is given
    (e.g. a strip-marker), it is used verbatim. Otherwise the widget's authored
    name is used if it's a clean, not-yet-used identifier; else the var name."""
    var = ctx.fresh_var(_VAR_PREFIX[kind])
    iface = _WIDGET_IFACE[kind]
    if name is None:
        desired = (node.name if node and node.name else "") or ""
        candidate = re.sub(r"[^A-Za-z0-9_]", "", desired)
        if not candidate or not (candidate[0].isalpha() or candidate[0] == "_") or candidate in ctx.used_names:
            candidate = var
        name = candidate
    ctx.used_names.add(name)
    ctx.last_widget_name = name
    ctx.emit(f'var {var} = {parent_var}.CreateWidget<{iface}>("{name}");')
    return var


# ─── Entry point ──────────────────────────────────────────────────────────────

def render_screen_dechromed(
    ast: ScreenAST,
    role_name: Optional[str] = None,
    flow_name: str = "MainFlow",
    anonymous: bool = False,
) -> str:
    """Render the dechromed C# body for one screen.

    Returns the bare csharp block (no PROMPT_PREAMBLE wrapping). Caller wraps
    in the usual recipe envelope.

    anonymous=True: explicitly clear any role gate Mentor auto-applied AND set
    AnonymousAccess=true so unauthenticated users can reach the screen. This is
    REQUIRED for Login and InvalidPermissions; without it, the app has a
    lockout pattern (per memory `mentor_auto_applies_role_filter_to_new_screens`).
    Verified live 2026-06-09 on HomeBankingPortal3 — Mentor reapplies the role
    gate to every newly-authored screen by default; the renderer must override.
    """
    ctx = RenderContext()
    _emit_screen_setup(ast, ctx, role_name, flow_name, anonymous)
    _emit_inputs(ast, ctx)
    _emit_locals(ast, ctx)
    _emit_aggregates(ast, ctx)
    _emit_screen_actions_stubs(ast, ctx)
    _emit_widgets(ast, ctx)
    _emit_diagnostic(ast, ctx)
    return "eSpace => {\n    " + "\n    ".join(ctx.lines) + "\n}"


# ─── Screen setup ─────────────────────────────────────────────────────────────

def _emit_screen_setup(ast: ScreenAST, ctx: RenderContext, role_name: Optional[str], flow_name: str, anonymous: bool = False):
    ctx.emit(f"// ─── Screen: {ast.name} (dechromed) ─────────────")
    ctx.emit(f'var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{flow_name}");')
    # Self-healing: fresh MCP-created Web Apps (via `app_create`) ship WITHOUT
    # a MainFlow MobileFlow. The screen recipes assume it exists from
    # Portal-create's default OML template. Discovered live Portal Rebake1
    # 2026-06-02 (every screen batch hit `FAILED: MobileFlow MainFlow not
    # found`). Mirror the same on-demand-create pattern used in block_renderer.py
    # for blocks: if the flow doesn't exist, create it.
    ctx.emit(f'if (flow == null) {{ flow = eSpace.CreateMobileFlow("{flow_name}"); Console.WriteLine($"Created missing MobileFlow {flow_name}"); }}')
    # Self-healing: delete-then-author so re-dispatch on an existing screen
    # mutates cleanly instead of throwing ALREADY_EXISTS (mirrors the
    # block_renderer.py pattern). Required for re-validation after a renderer
    # fix: the existing screen at the prior rev is stale (e.g. dropped Form
    # subtree pre-2026-06-02-Form-fix); we want the fresh authoring to win.
    #
    # Portal Phase C VERIFY re-dispatch findings (2026-06-02): deleting a screen
    # that eSpace.DefaultScreen pointed to leaves DefaultScreen referring to a
    # dangling object — AVS rejects publish with OS-APPS-40028 closure-rule
    # violation. Capture DefaultScreen name BEFORE delete, then re-wire it to
    # the freshly-created screen if the name matches. (Capturing by name +
    # re-resolving avoids holding a stale reference.) Similar guards may be
    # needed for cross-screen NavigationSet / OnInitialize destinations as new
    # call sites surface — re-publish failures are the diagnostic.
    ctx.emit(f'var existing = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>().FirstOrDefault(s => s.Name == "{ast.name}");')
    ctx.emit(f'bool wasDefaultScreen = (existing != null && eSpace.DefaultScreen == existing);')
    ctx.emit(f'if (existing != null) {{ existing.Delete(); Console.WriteLine($"Recipe 07: {ast.name} | replaced existing screen (wasDefault={{wasDefaultScreen}})"); }}')
    ctx.emit(f'var screen = flow.CreateScreen("{ast.name}");')
    ctx.emit(f'if (wasDefaultScreen) {{ eSpace.DefaultScreen = screen; Console.WriteLine($"Recipe 07: {ast.name} | re-wired eSpace.DefaultScreen to fresh screen"); }}')
    if anonymous:
        # v3 bake (2026-06-09): explicitly clear any role gate Mentor auto-applied,
        # then set AnonymousAccess=true so unauthenticated visitors can reach this
        # screen. Required for Login + InvalidPermissions; without it the app has
        # a lockout (user has no role → can't reach Login → can't sign in →
        # _error.html). Per memory `mentor_auto_applies_role_filter_to_new_screens`
        # and bug-probe-confirmed live on HomeBankingPortal3 (rev 6 → 8 fix).
        ctx.emit(f'screen.Roles.Clear();  // override Mentor\'s auto-applied role gate')
        ctx.emit(f'screen.AnonymousAccess = true;  // allow unauthenticated visit')
    elif role_name:
        ctx.emit(f'screen.Roles.Clear();  // start clean — override Mentor\'s default')
        ctx.emit(f'var role = eSpace.Roles.FirstOrDefault(r => r.Name == "{role_name}") ' +
                 f'?? eSpace.References.SelectMany(r => r.Roles).FirstOrDefault(r => r.Name == "{role_name}");')
        ctx.emit(f'if (role != null) screen.Roles.Add(role);')


def _emit_inputs(ast: ScreenAST, ctx: RenderContext):
    if not ast.inputs:
        return
    ctx.emit("")
    ctx.emit("// ─── Inputs ─────────────────────────────────")
    for p in ast.inputs:
        cs_type = _resolve_data_type(p.data_type)
        mand = "true" if p.mandatory else "false"
        ctx.emit(f'{{ var ip = screen.CreateInputParameter("{p.name}"); ip.DataType = {cs_type}; ip.IsMandatory = {mand}; }}')


def _emit_locals(ast: ScreenAST, ctx: RenderContext):
    if not ast.locals:
        return
    ctx.emit("")
    ctx.emit("// ─── Local variables ────────────────────────")
    for v in ast.locals:
        cs_type = _resolve_data_type(v.data_type)
        # Track Structure/Record locals that fell back to TextType so SetVisible
        # expressions referencing `<localname>.Field` can be deferred.
        if "/* unmapped:" in cs_type:
            ctx.unmapped_locals.add(v.name)
        line = f'{{ var lv = screen.CreateLocalVariable("{v.name}"); lv.DataType = {cs_type};'
        if v.default is not None:
            # Default value is a literal expression — quote text, bool/numeric literal as-is
            literal = _format_default(v.data_type, v.default)
            line += f' lv.SetDefaultValue("{literal}");'
        line += " }"
        ctx.emit(line)


def _emit_aggregates(ast: ScreenAST, ctx: RenderContext):
    if not ast.aggregates:
        return
    ctx.emit("")
    ctx.emit("// ─── Screen aggregates ──────────────────────")
    for a in ast.aggregates:
        if not a.source:
            ctx.emit(f'// TODO aggregate {a.name} — source not parsed from "{a.raw_args}"')
            # Track so the expression validator can stub any expression that
            # references this aggregate by name (otherwise OS-APPS-40028 fires
            # at publish: "Can't identify <a.name> element in expression").
            ctx.unauthored_aggregates.add(a.name)
            continue
        # Source parsed → aggregate will be authored. Track the name so the
        # expression validator recognizes `<a.name>.X.Y` path references as
        # safe to emit verbatim.
        ctx.authored_aggregates.add(a.name)
        # Resolve the source entity — could be local or referenced
        ctx.emit(f'{{')
        ctx.emit(f'    var agg = screen.CreateScreenAggregate(false, "{a.name}");')
        ctx.emit(f'    agg.Fetch = OutSystems.Model.Enumerations.DataSourceFetch.AtStart;')
        ctx.emit(f'    agg.SetMaxRecords("50");')
        ctx.emit(f'    var srcEntity = eSpace.Entities.OfType<OutSystems.Model.Data.IServerEntitySignature>()')
        ctx.emit(f'        .FirstOrDefault(e => e.Name == "{a.source}")')
        ctx.emit(f'        ?? (OutSystems.Model.Data.IEntitySignature)eSpace.Entities.OfType<OutSystems.Model.Data.IStaticEntitySignature>()')
        ctx.emit(f'            .FirstOrDefault(e => e.Name == "{a.source}")')
        ctx.emit(f'        ?? eSpace.References.SelectMany(r => r.Entities).FirstOrDefault(e => e.Name == "{a.source}");')
        ctx.emit(f'    if (srcEntity != null) agg.AsDatabaseAggregate.CreateSource(srcEntity);')
        ctx.emit(f'    else Console.WriteLine($"WARN: aggregate {a.name} source entity {a.source} not found");')
        ctx.emit(f'}}')


def _emit_screen_actions_stubs(ast: ScreenAST, ctx: RenderContext):
    """For each unique OnClick/OnEvent destination referenced in the widget tree,
    create a stub screen action that the widgets can wire to.

    Scan-only — collects names; actual creation deferred to widget render time."""
    pass  # Implemented in _emit_widgets via OnClick handling


# ─── Widget tree ──────────────────────────────────────────────────────────────

def _emit_widgets(ast: ScreenAST, ctx: RenderContext):
    if not ast.widgets:
        ctx.emit("")
        ctx.emit("// (no top-level widgets)")
        return
    ctx.emit("")
    ctx.emit("// ─── Widget tree (dechromed — custom blocks stripped) ────────")

    # Pre-collect screen action names referenced via OnClick → SomeName (not Destination=...)
    actions = set()
    _collect_screen_actions(ast.widgets, actions)
    for action_name in sorted(actions):
        ctx.emit(f'{{ var sa = screen.CreateScreenAction("{action_name}");')
        ctx.emit(f'   var s = sa.CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>();')
        ctx.emit(f'   var e = sa.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>();')
        ctx.emit(f'   e.ConnectedBelow(s); }}  // stub action — body added later')

    # Render widgets. Top-level widgets attach to screen.MainContent placeholder
    # (or wherever the OS UI Layout has the slot). For simplicity we use the
    # default "screen" container — Mentor will route widgets into the canonical
    # placeholder based on the layout type.
    parent_var = "screen"
    for w in ast.widgets:
        _render_widget(w, parent_var, ctx)


def _collect_screen_actions(widgets: list[WidgetNode], out: set):
    for w in widgets:
        for event_name, target in w.events.items():
            # OnClick=Handler or OnClick→Destination=Dashboard or OnClick→Handler(args)
            if "Destination=" in target:
                continue  # navigation to another screen, not a screen action
            # Strip arg list
            handler = re.split(r"[\s(]", target, maxsplit=1)[0]
            if not handler or handler.startswith("("):
                continue
            # Skip non-identifier values that slip through from misparsed
            # Condition/Visible/etc. properties (e.g. `"True"`, `True`,
            # `False`, numeric literals). Action names must be valid C#
            # identifiers — first char alpha or _, rest alphanumeric or _.
            # Discovered Portal Phase C v3 dispatch 2026-06-02: an IfWidget's
            # Condition="True" leaked into events and emitted
            # CreateScreenAction(""True"") which is invalid C#.
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", handler):
                continue
            out.add(handler)
        _collect_screen_actions(w.children, out)
        _collect_screen_actions(w.true_branch, out)
        _collect_screen_actions(w.false_branch, out)


def _render_widget(node: WidgetNode, parent_var: str, ctx: RenderContext):
    """Emit C# to create the widget under `parent_var`. Dispatches to a
    type-specific handler; falls through to a generic comment for unknown types."""
    wtype = node.widget_type

    if wtype == "BlockInstance":
        _render_block_instance(node, parent_var, ctx)
        return

    if wtype in ("Container",):
        _render_container(node, parent_var, ctx)
        return

    if wtype == "Text":
        _render_text(node, parent_var, ctx)
        return

    if wtype == "Button":
        _render_button(node, parent_var, ctx)
        return

    if wtype == "If":
        _render_if(node, parent_var, ctx)
        return

    if wtype in ("Placeholder", "PLACEHOLDER"):
        # Anonymous / 'content' placeholders are the implicit containment slot
        # every Container materializes on its own (Container > content > child,
        # LayoutBlank probe 2026-06-11). Authoring them explicitly would
        # double-nest — descend transparently in BOTH modes.
        is_named = bool(node.name) and node.name.lower() != "content"
        if ctx.emit_real_placeholders and is_named:
            # BLOCK-DEFINITION mode (Recipe 22 / layout blocks): author a real
            # Placeholder widget in place. CreateWidget<IPlaceholderWidget>
            # nests correctly (LayoutBlank probe 2026-06-11) — the historical
            # wall only blocked MOVING placeholders after creation. Children
            # under a Placeholder in a BLOCK capture are the definition's
            # default content — author them inside the new placeholder.
            var = _create_widget(ctx, parent_var, "placeholder", node)
            _apply_props(var, node, ctx, kind="placeholder")
            for c in node.children:
                _render_widget(c, var, ctx)
            return
        # SCREEN mode: placeholder marker — the widget render simply descends
        # into children (the placeholder itself is part of the consumed layout
        # block, not a separate widget to create on the screen)
        for c in node.children:
            _render_widget(c, parent_var, ctx)
        return

    if wtype == "Dropdown":
        _render_dropdown(node, parent_var, ctx)
        return

    if wtype == "Input":
        _render_input(node, parent_var, ctx)
        return

    if wtype == "Form":
        # Forms are CONTAINERS, not leaves — they wrap form fields + nested
        # widgets. Lumping Form into _render_input (which doesn't descend)
        # silently drops the entire subtree. Discovered Portal Phase C VERIFY
        # 2026-06-02: Transfer.Form1 at path 1.S.2.1.2 contains 9 child
        # containers (one with a Button wrapping HBIcon, two siblings being
        # MaskText / MaskCurrency BlockInstances). All three failed to author
        # markers because the Form-handler bailout dropped them. Fix: render
        # Form as a plain Container — same dechromed semantics, descends into
        # children. Real Form widget (with Source/IsSubmitted/etc.) restored
        # in LOGIC phase.
        _render_container(node, parent_var, ctx)
        return

    if wtype == "Image":
        _render_image(node, parent_var, ctx)
        return

    if wtype == "Expression":
        _render_expression(node, parent_var, ctx)
        return

    # Fallback
    ctx.emit(f"// TODO widget type '{wtype}' at path {node.path} — handler not implemented; emitting Container shell")
    _render_container(node, parent_var, ctx)


def _render_block_instance(node: WidgetNode, parent_var: str, ctx: RenderContext):
    sb = node.source_block
    if not sb:
        ctx.emit(f"// BlockInstance at {node.path} has no SourceBlock — skipping")
        return

    if sb in OS_UI_STANDARD_BLOCKS:
        # Keep verbatim — create BlockInstance + descend into placeholder fillings.
        # The block-instance creation API needs the block signature in scope; for
        # the dechromed STRUCTURE phase we emit a named Container placeholder
        # (chrome wrap / a later pass swaps in the real OS UI BlockInstance).
        ctx.emit(f'// BlockInstance \'{node.name or "(unnamed)"}\' SourceBlock={sb} (OS UI standard — placeholder Container in dechromed phase)')
        var = _create_widget(ctx, parent_var, "container", node,
                             name=strip_marker_name(sb, node.path))
        for c in node.children:
            _render_widget(c, var, ctx)
        return

    # Custom block — strip and replace with marker Container.
    # The Container is NAMED with a stable, deterministic identifier so that
    # Recipe 23 (chrome wrap) can locate it later via Name lookup and replace
    # it with the real BlockInstance. The name uses the original BlockInstance
    # path so the same source_block referenced twice in one screen gets two
    # distinct markers (collision-free re-wrap).
    ctx.stripped_count += 1
    if sb not in ctx.stripped_blocks:
        ctx.stripped_blocks.append(sb)
    marker_name = strip_marker_name(sb, node.path)
    ctx.emit(f'// CHROME-STRIPPED: BlockInstance \'{node.name or "(unnamed)"}\' SourceBlock={sb} → named Container placeholder for Recipe 23 chrome wrap')
    var = _create_widget(ctx, parent_var, "container", node, name=marker_name)
    # Still descend into children — they may contain non-chrome widgets
    for c in node.children:
        _render_widget(c, var, ctx)


def strip_marker_name(source_block: str, path: str) -> str:
    """Return the stable Name that T2.2 assigns to a stripped placeholder
    Container. Recipe 23 looks up the Container by this Name to replace it.

    Format: `chrome_<source_block>_<path-with-dots-as-underscores>`.

    Portal Phase C VERIFY probe (rev 13, 2026-06-02): the OutSystems Model API
    SILENTLY STRIPS a leading underscore from widget `Name` during
    `CreateWidget("_chrome_...")` — the widget is persisted as
    `chrome_...`. (Likely because widget Names must round-trip as C#
    identifiers; a leading `_` followed by an alpha char is technically
    valid C# but the platform normalises it off anyway.) That means the
    OLD `_chrome_` prefix made the chrome_wrap lookup miss every marker
    (`wrapped=0/18` on Transfer at rev 13 — markers existed but under the
    stripped name). No leading underscore = renderer-emit and wrap-lookup
    strings finally agree. See memory [[odc_mcp_widget_name_strips_leading_underscore]].
    """
    return f"chrome_{source_block}_{path.replace('.', '_')}"


def _render_container(node: WidgetNode, parent_var: str, ctx: RenderContext):
    var = _create_widget(ctx, parent_var, "container", node)
    _apply_props(var, node, ctx)
    for c in node.children:
        _render_widget(c, var, ctx)


def _render_text(node: WidgetNode, parent_var: str, ctx: RenderContext):
    var = _create_widget(ctx, parent_var, "text", node)
    if "Text" in node.properties:
        # ITextWidget.Text is a literal (direct assign, no SetValue) — escape quotes.
        txt = node.properties["Text"].replace('\\', '\\\\').replace('"', '\\"').replace("\n", "\\n")
        ctx.emit(f'{var}.Text = "{txt}";')
    _apply_props(var, node, ctx, skip={"Text"}, kind="text")


def _render_button(node: WidgetNode, parent_var: str, ctx: RenderContext):
    # DECHROMED FIX (Portal Phase A): render Button as a Container placeholder.
    # OS UI Button widgets have a MANDATORY OnClick (Screen Action or Destination
    # reference); without a real handler the OML binary validator rejects
    # publish (OS-APPS-40028 "Input binary does not contain a valid OML" — the
    # dechromed manifest's `// var.OnClick → ...` comment is not a setter, so
    # OnClick stays unset). CHROME/LOGIC phase replaces this Container with a
    # real Button + wired OnClick once the target actions exist.
    onclick_note = ""
    if "OnClick" in node.events:
        target = node.events["OnClick"]
        if "Destination=" in target:
            dest = target.split("Destination=", 1)[1].strip()
            onclick_note = f" (original OnClick→Destination={dest})"
        else:
            handler = re.split(r"[\s(]", target, maxsplit=1)[0]
            onclick_note = f" (original OnClick→ScreenAction {handler})"
    ctx.emit(f"// DECHROMED Button '{node.name or '(unnamed)'}' → Container placeholder{onclick_note}")
    var = _create_widget(ctx, parent_var, "container", node)
    # Preserve the label as a child Text widget so the structure is still
    # visually distinguishable in dechromed-render previews.
    label = node.properties.get("Text")
    if label:
        label_e = label.replace('\\', '\\\\').replace('"', '\\"').replace("\n", "\\n")
        lbl = _create_widget(ctx, var, "text", None)
        ctx.emit(f'{lbl}.Text = "{label_e}";')
    _apply_props(var, node, ctx, skip={"Text"}, kind="container")
    for c in node.children:
        _render_widget(c, var, ctx)


def _render_if(node: WidgetNode, parent_var: str, ctx: RenderContext):
    # DECHROMED: render the If as a Container placeholder. The widget interface
    # for If (IIfWidget) is not resolvable on this app's compile context
    # (CS0234 in both ServiceStudio.Plugin.NRWidgets and
    # OutSystems.Model.UI.Mobile.Widgets); the conditional wrapper is restored
    # in the LOGIC phase. Branch children are flattened into the container so
    # all content widgets survive the STRUCTURE phase.
    var = _create_widget(ctx, parent_var, "container", node)
    cond = (node.condition or "").replace('\\', '\\\\').replace('"', '\\"')
    if cond:
        ctx.emit(f'// IF Condition="{cond}" — dechromed as Container; conditional restored in LOGIC phase')
    for c in node.true_branch:
        _render_widget(c, var, ctx)
    for c in node.false_branch:
        _render_widget(c, var, ctx)


def _render_dropdown(node: WidgetNode, parent_var: str, ctx: RenderContext):
    # No native IDropdown in the Model API surface. The OS UI dropdown is a
    # BlockInstance-style widget; in the dechromed STRUCTURE phase we emit a
    # named Container placeholder (PLAN_GAP: dropdown fidelity deferred to a
    # later pass). Bindings (List/Labels/Values/Variable) recorded as a comment.
    var = _create_widget(ctx, parent_var, "container", node)
    binds = {k: node.properties[k] for k in ("List", "Labels", "Values", "Variable") if k in node.properties}
    if binds:
        ctx.emit(f'// DROPDOWN placeholder — bindings: {binds}')
    _apply_props(var, node, ctx, skip={"List", "Labels", "Values", "Variable"})


def _render_input(node: WidgetNode, parent_var: str, ctx: RenderContext):
    # DECHROMED: render as a Container placeholder. IInput is not resolvable on
    # this app's compile context (CS0234 in OutSystems.Model.UI.Mobile.Widgets);
    # the real input widget + variable binding are restored in the LOGIC phase.
    var = _create_widget(ctx, parent_var, "container", node)
    if "Variable" in node.properties:
        ctx.emit(f'// INPUT Variable={node.properties["Variable"]} — dechromed as Container; real input in LOGIC phase')
    _apply_props(var, node, ctx, skip={"Variable"}, kind="container")


def _render_image(node: WidgetNode, parent_var: str, ctx: RenderContext):
    # DECHROMED FIX (Portal Phase A — revised): render Image as a Container
    # placeholder, mirroring the Button approach. Two reasons:
    #  1. `ServiceStudio.Plugin.NRWidgets.IImage` has NO `.Value` property
    #     (CS1061 — verified live 2026-06-02). The Image source/binding API
    #     uses a different setter (likely SetSource / SetUrl / a Resource
    #     reference) — UNPROBED at write-time.
    #  2. Without a source set, the OML binary validator rejects publish with
    #     OS-APPS-40028 ("Image.Value not set" in the validator's nomenclature).
    # Until the real Image-binding API is cracked, the safest validator-clean
    # path is a Container placeholder. CHROME phase promotes back to a real
    # Image once the source-API surface is verified.
    val = node.properties.get("Value")
    if val:
        ctx.emit(f"// DECHROMED Image '{node.name or '(unnamed)'}' Value={val!r} → Container placeholder (Image-source API unprobed; CHROME promotes)")
    else:
        ctx.emit(f"// DECHROMED Image '{node.name or '(unnamed)'}' → Container placeholder (no Value in capture)")
    var = _create_widget(ctx, parent_var, "container", node)
    _apply_props(var, node, ctx, kind="container")


def _render_expression(node: WidgetNode, parent_var: str, ctx: RenderContext):
    # DECHROMED FIX (Portal Phase A): validate Value is a parseable
    # OutSystems expression before emitting SetValue. Captured Values can
    # contain dechromed placeholder tokens that the OML validator rejects:
    #   1. Ellipsis `…CreatedOn` (unresolved field binding marker).
    #   2. Half-opened string literals (`'`, `'foo`).
    #   3. References to UNAUTHORED aggregates (e.g. `GetCounters.List[0]`
    #      where `GetCounters` is an aggregate whose source the parser couldn't
    #      read — see `_emit_aggregates`). The validator complains
    #      "Can't identify <name> element in expression".
    #   4. Bareword identifiers (`All`, `Pending`) that the validator wants as
    #      Text literals (`"All"`). When the captured Value matches only
    #      letters/digits/underscores and isn't a known unauthored aggregate,
    #      wrap it as a Text literal so the validator accepts it.
    var = _create_widget(ctx, parent_var, "expression", node)
    if "Value" in node.properties:
        val = node.properties["Value"]
        if _expression_value_safe_v2(val, ctx):
            emit_val = _wrap_bareword_as_text_literal(val)
            val_e = emit_val.replace('\\', '\\\\').replace('"', '\\"')
            ctx.emit(f'{var}.SetValue("{val_e}");')
        else:
            ctx.emit(f'// dechromed stub — original Expression.Value={val!r} (unparseable; LOGIC fills)')
            ctx.emit(f'{var}.SetValue("\\"\\"");')  # the literal "" expression
            if ctx.stub_patches is not None:
                ctx.stub_patches.append(("value", ctx.last_widget_name, val))
    else:
        ctx.emit(f'{var}.SetValue("\\"\\"");')  # empty-string-literal expression
    _apply_props(var, node, ctx, skip={"Value"}, kind="expression")


# A token boundary for finding identifier-style names inside an expression.
# Matches names like `GetCounters`, `Customer.Name`, `Entities.Status.Pending`.
_IDENT_TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
# A pure bareword is an identifier with no `.`, `(`, operators, etc.
_PURE_BAREWORD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# Tokens that resolve only after the LOGIC phase (joins, statics, structures).
# Hand-curated from publish-gate validation errors; LOGIC phase removes entries
# as it authors the backing elements.
_LOGIC_PHASE_TOKENS = {
    "TransactionType",      # join attr on GetLastTransactions (join not authored in STRUCTURE)
    "Locale2",              # static entity, not in the public-entity import set
    "ChartCardsValue",      # Structure-typed local fell back to TextType
    "BalancePercent", "IncomePercent", "ExpensesPercent", "Label",  # ChartCardsValue fields
    # v22 gate failure (12 errors): aggregate attr paths the STRUCTURE
    # aggregates don't expose (original aggregates had calculated/grouped
    # columns promoted to top level) + a client action unknown to the
    # expression scope. Amount over-stubs like Label — accepted.
    "GoalName", "TargetAmount", "AmountSum", "LabelLocale", "Amount",
    "FormatCurrencyCustom",
}


def _expression_value_safe(val: str, unauthored_aggregates: set) -> bool:
    """Return True if `val` looks like a parseable OutSystems expression we can
    safely emit via IExpression.SetValue at publish-time. False for dechromed
    placeholder tokens or references to unauthored aggregates.

    Heuristics (all conservative — favor emitting a stub over a bad value):
      * The Unicode horizontal ellipsis `…` is the dechromed placeholder marker.
      * A bare single quote `'` (and only `'`) is a half-opened string literal.
      * A string starting with `'` or `"` but not ending with the matching
        quote is an unterminated literal.
      * If any token in the expression matches an unauthored aggregate name
        from `ctx.unauthored_aggregates`, the validator can't resolve it.

    A pure bareword identifier (`All`, `Pending`) is NOT unsafe here — it gets
    wrapped as a Text literal by `_wrap_bareword_as_text_literal` before emit.
    """
    if not val:
        return False
    if "…" in val:
        return False
    # STRUCTURE-phase deny-list (Portal4 gate-1 failure 2026-06-11): tokens
    # whose backing elements only exist after the LOGIC phase — aggregate JOIN
    # attributes (TransactionType on GetLastTransactions), static entities not
    # in the public-entity import (Locale2), and Structure-typed record fields
    # on TextType-fallback locals (ChartCardsValue and its fields). Expressions
    # touching them validate as "Can't identify <token>" → one Error → AVS
    # rejects the publish (OS-APPS-40028). Stub now; LOGIC phase restores.
    for token in _IDENT_TOKEN_RE.findall(val):
        if token in _LOGIC_PHASE_TOKENS:
            return False
    stripped = val.strip()
    if stripped == "'" or stripped == '"':
        return False
    if stripped.startswith("'") and not stripped.endswith("'"):
        return False
    if stripped.startswith('"') and not stripped.endswith('"'):
        return False
    if unauthored_aggregates:
        for token in _IDENT_TOKEN_RE.findall(val):
            if token in unauthored_aggregates:
                return False
    return True


def _expression_value_safe_v2(val: str, ctx: RenderContext) -> bool:
    """Extended version of `_expression_value_safe` that also flags `Get<X>.…`
    path references where `<X>` is not in `ctx.authored_aggregates`. ODC's
    convention is `Get<Word>` for both screen aggregates and getter
    ScreenActions; in dechromed phase we author neither for sure, so any
    `Get<X>` we don't know is authored is conservatively stubbed.

    This is the v2 of the safety check called by `_render_expression`."""
    if not _expression_value_safe(val, ctx.unauthored_aggregates):
        return False
    # Any `Get[A-Z]…` token followed by a `.` path that ISN'T in our
    # known-authored aggregate set → likely unresolvable in dechromed.
    for token in _IDENT_TOKEN_RE.findall(val):
        if _GET_PATTERN_RE.match(token) and token not in ctx.authored_aggregates:
            # Allow Get tokens that aren't actually a path reference (no `.`
            # following the token), e.g. a bareword `GetSomething` used as
            # a plain identifier. We're conservative: stub if followed by `.`.
            if f"{token}." in val:
                return False
    return True


# Identifier matching `Get<Word>` — the convention for ODC screen aggregates
# and getter ScreenActions.
_GET_PATTERN_RE = re.compile(r"^Get[A-Z]\w*$")


# Match `<Identifier>.` field-access tokens in an expression.
_FIELD_ACCESS_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.")


def _expression_touches_unmapped_local(expr: str, unmapped_locals: set) -> bool:
    """Return True if the expression references `.Field` access on a local that
    fell back to TextType (`unmapped_locals` populated by `_emit_locals`).
    Caller should defer the SetVisible/SetCondition emit and let the LOGIC
    phase author the real Structure local + restore the expression.
    """
    if not unmapped_locals:
        return False
    for token in _FIELD_ACCESS_RE.findall(expr):
        if token in unmapped_locals:
            return True
    return False


# Match `=<PascalCase>` (or `<`, `>`, `<=`, `>=`, `!=`) RHS where the RHS token
# is unqualified (NOT preceded by `Entities.` or `.`) — typical pattern for an
# unqualified static-entity record reference (`= Regular1to2workingdays`,
# `= Schedule`, etc.). Pre-filter the obvious safe literals.
_EQ_RHS_PASCAL_RE = re.compile(r"[=<>!]+\s*([A-Z][A-Za-z0-9_]+)\b")
_SAFE_RHS_LITERALS = {"True", "False", "Null", "NullIdentifier"}


def _expression_has_unqualified_static_record(expr: str) -> bool:
    """Return True if the expression contains an equality whose RHS is a
    PascalCase bareword that looks like a static-entity record reference
    without the required `Entities.<Entity>.` qualifier. Studio renders
    these conveniently at edit-time but the AVS publish validator rejects
    them on dechromed screens where the LHS local's type is ambiguous.

    We only fire when the bareword is NOT a known safe literal (True / False
    / Null) AND is NOT immediately followed by `.` (which would mean it's the
    start of a qualified path like `Entities.Foo.Bar`). The check is RHS-only
    so identifiers used as expression heads (e.g. `Regular1to2workingdays`
    appearing on the LHS of a comparison) won't trip it.
    """
    for match in _EQ_RHS_PASCAL_RE.finditer(expr):
        token = match.group(1)
        if token in _SAFE_RHS_LITERALS:
            continue
        # Skip if the token is part of a qualified path (followed by `.`).
        end = match.end()
        if end < len(expr) and expr[end] == ".":
            continue
        # Skip if the token is preceded by `Entities.` (qualified head).
        start = match.start(1)
        if start >= 9 and expr[start - 9 : start] == "Entities.":
            continue
        return True
    return False


def _wrap_bareword_as_text_literal(val: str) -> str:
    """If `val` is a pure bareword identifier (just letters/digits/underscores),
    wrap it in C# escapes so the emitted SetValue sees an OutSystems Text
    literal `"<val>"` instead of an unresolved identifier. The validator
    rejects bare `All` with "Invalid Data Type — Text required instead of None"
    but accepts the Text literal `"All"`.

    Compound expressions (anything with `.`, `(`, operators, etc.) pass through
    unchanged so we don't quote-wrap a real expression like `Customer.Name`."""
    if _PURE_BAREWORD_RE.match(val):
        return f'"{val}"'
    return val


# ─── Property emission ─────────────────────────────────────────────────────────

# Widget kinds that expose SetStyle (CSS-class expression). ITextWidget /
# IExpression / IImage / IInput do NOT — verified live: ITextWidget.SetStyle is
# CS1061. For those, a Style class is recorded as a comment (dechromed phase);
# CustomStyle (inline) still applies to all widgets.
_SETSTYLE_KINDS = {"container", "button"}


def _static_style_classes(style_raw: str) -> str:
    """Extract the static CSS-class portion of a captured Style value.

    Plain class list (`main-content ThemeGrid_Container`) → returned whole.
    Compound expression (`layout layout-top" + If(HasFixedHeader, ...`) →
    leading literal segment up to the first quote/plus. Returns "" when no
    static prefix can be extracted."""
    candidate = style_raw.strip()
    # Strip a stray leading quote left by capture parsing
    if candidate.startswith('"'):
        candidate = candidate[1:]
    # Cut at the first quote or ` + ` — start of the expression tail
    for cut_marker in ('"', " + "):
        idx = candidate.find(cut_marker)
        if idx != -1:
            candidate = candidate[:idx]
    candidate = candidate.strip()
    if re.fullmatch(r"[A-Za-z0-9_\- ]+", candidate or ""):
        return candidate
    return ""


def _apply_props(var: str, node: WidgetNode, ctx: RenderContext,
                 skip: Optional[set] = None, kind: str = "container"):
    """Emit the canonical property setters:
      - Style (CSS class)  → SetStyle("<expr>") on container/button only
      - CustomStyle (inline CSS) → widget.CustomStyle = "<literal>"  (direct assign)
      - Visible (expr)     → SetVisible("<expr>")
      - Width: OS UI column descriptor (e.g. "2 col") maps to a layout class in
        Studio; no clean Model API setter — recorded as a comment, not emitted.
    """
    skip = skip or set()
    # CSS classes (Style) and inline CSS (CustomStyle) are CHROME-phase concerns:
    # the dechromed STRUCTURE phase records them as comments and the CHROME pass
    # (theme + chrome-wrap) applies them. This also avoids the SetStyle
    # quoted-expression escaping that fails model validation in this transport.
    if "Style" not in skip and node.properties.get("Style"):
        style_raw = node.properties["Style"]
        if kind in ("container", "button", "placeholder"):
            # Apply static CSS classes at author time — screens AND blocks.
            # The old screen-mode deferral ("applied in CHROME phase") left
            # every content widget classless, so the theme CSS had nothing to
            # target inside MainContent (proven live: rev 22 Dashboard rendered
            # a bare text column inside a correct layout grid). Block-mode
            # SetStyle published clean across revs 20/22, retiring the
            # escaping concern for static class lists. Compound expressions
            # (input-conditional toggles like If(HasFixedHeader, ...)) degrade
            # to their leading literal segment — conditionals are LOGIC phase.
            static_classes = _static_style_classes(style_raw)
            if static_classes:
                # IPlaceholderWidget exposes SetStyleClasses, not SetStyle
                # (CS1061 ×5, Recipe 22 dispatch 2026-06-11).
                style_method = "SetStyleClasses" if kind == "placeholder" else "SetStyle"
                ctx.emit(f'{var}.{style_method}("\\"{static_classes}\\"");')
                if static_classes != style_raw:
                    ctx.emit(f'// Style conditional suffix dropped (LOGIC phase) — was: {style_raw}')
            else:
                ctx.emit(f'// Style unparseable as classes — was: {style_raw}')
        else:
            ctx.emit(f'// Style="{style_raw}" (CSS class — applied in CHROME phase)')
    if "CustomStyle" not in skip and node.properties.get("CustomStyle"):
        ctx.emit(f'// CustomStyle="{node.properties["CustomStyle"]}" (inline CSS — applied in CHROME phase)')
    if "Visible" not in skip and node.properties.get("Visible"):
        vis_raw = node.properties["Visible"]
        # Defer SetVisible when the expression accesses a field path on a
        # Structure-typed local that fell back to TextType. AVS rejects the
        # publish with OS-APPS-40028 (closure rule, layer 2) because the
        # expression validator can't resolve `.Field` on a Text local. LOGIC
        # phase restores from manifest once Structures are authored.
        if _expression_touches_unmapped_local(vis_raw, ctx.unmapped_locals):
            ctx.emit(f'// SetVisible deferred (touches unmapped Structure local) — was: {vis_raw}')
        # Same LOGIC-phase deny-list as expression values (gate-1 failure
        # 2026-06-11: SetVisible("...Entities.Locale2...") = validation Error).
        elif any(t in _LOGIC_PHASE_TOKENS for t in _IDENT_TOKEN_RE.findall(vis_raw)):
            ctx.emit(f'// SetVisible deferred (LOGIC-phase token) — was: {vis_raw}')
            if ctx.stub_patches is not None:
                ctx.stub_patches.append(("visible", ctx.last_widget_name, vis_raw))
        # Defer SetVisible when the RHS of an equality references an
        # unqualified PascalCase token that looks like a static-entity
        # record (e.g. `=Regular1to2workingdays`). Studio Mentor auto-scopes
        # these to `Entities.<EntityName>.<Record>` at runtime, but the
        # AVS publish validator on the dechromed screen rejects them.
        elif _expression_has_unqualified_static_record(vis_raw):
            ctx.emit(f'// SetVisible deferred (unqualified static-entity record on RHS) — was: {vis_raw}')
        else:
            vis = vis_raw.replace('"', '\\"')
            ctx.emit(f'{var}.SetVisible("{vis}");')
    if "Width" not in skip and node.properties.get("Width"):
        ctx.emit(f'// Width="{node.properties["Width"]}" (OS UI column descriptor — layout class, set in CHROME phase)')


# ─── Diagnostic emission ───────────────────────────────────────────────────────

def _emit_diagnostic(ast: ScreenAST, ctx: RenderContext):
    # IMobileScreen exposes InputParameters + LocalVariables (countable live) but
    # NOT a `.Aggregates` property — bake the aggregate count from the AST instead.
    ctx.emit("")
    ctx.emit(f'Console.WriteLine($"Recipe 07-DECHROMED: {ast.name} | ' +
             f'inputs={{screen.InputParameters.Count()}}, locals={{screen.LocalVariables.Count()}}, ' +
             f'aggs={len(ast.aggregates)}, ' +
             f'stripped_chrome={ctx.stripped_count} ({", ".join(ctx.stripped_blocks)}) | ' +
             f'Status: OK");')


# ─── Helpers ───────────────────────────────────────────────────────────────────

_TYPE_MAP = {
    "Text": "eSpace.TextType",
    "Integer": "eSpace.IntegerType",
    "Long Integer": "eSpace.LongIntegerType",
    "Boolean": "eSpace.BooleanType",
    "Decimal": "eSpace.DecimalType",
    "Date Time": "eSpace.DateTimeType",
    "Date": "eSpace.DateType",
    "Email": "eSpace.EmailType",
    "Phone Number": "eSpace.PhoneNumberType",
    "Currency": "eSpace.CurrencyType",
    "Binary Data": "eSpace.BinaryDataType",
}


def _resolve_data_type(data_type: str) -> str:
    """Convert a manifest data_type string to a C# expression yielding the
    matching IDataType. Supports basic types + entity identifier types."""
    if data_type in _TYPE_MAP:
        return _TYPE_MAP[data_type]
    if data_type.endswith(" Identifier"):
        entity = data_type[: -len(" Identifier")]
        # Null-safe lookup across local server/static entities + references.
        # `.FirstOrDefault` everywhere (NEVER `.First`, which throws "Sequence
        # contains no matching element" when the entity is absent — e.g. on a
        # sandbox lacking the app's entities). Falls back to TextType so the
        # screen still authors for validation; on the real target app the
        # entity resolves and the correct Identifier type is used.
        if entity == "User":
            lookup = 'eSpace.References.SelectMany(r => r.Entities).FirstOrDefault(e => e.Name == "User")'
        else:
            lookup = (
                f'(eSpace.Entities.OfType<OutSystems.Model.Data.IServerEntitySignature>().FirstOrDefault(e => e.Name == "{entity}") '
                f'?? (OutSystems.Model.Data.IEntitySignature)eSpace.Entities.OfType<OutSystems.Model.Data.IStaticEntitySignature>().FirstOrDefault(e => e.Name == "{entity}") '
                f'?? eSpace.References.SelectMany(r => r.Entities).FirstOrDefault(e => e.Name == "{entity}"))'
            )
        return f'({lookup}?.IdentifierType ?? eSpace.TextType)'
    return f'eSpace.TextType /* unmapped: {data_type} */'


def _format_default(data_type: str, default: str) -> str:
    """Format a default value as a C# expression string."""
    if data_type == "Boolean":
        return "True" if default.lower() in ("true", "1") else "False"
    if data_type in ("Integer", "Long Integer", "Decimal", "Currency"):
        return default
    # Text-like: quote
    return f'\\"{default}\\"'


# ─── Large-screen split (v16, 2026-06-11) ─────────────────────────────────────
#
# Why: the rendered Dashboard recipe is 74KB (~37K tokens) — beyond every
# transport's single-emission cap (agent ≈16K output tokens, main loop ≈25K
# read cap). The fix mirrors the chrome-marker pattern: part 1 authors the
# full screen but renders oversized Container subtrees as NAMED EMPTY shells
# (`sect_N`, props applied, children skipped); parts 2+ look the shell up by
# name and fill its children. Only Container nodes are deferrable (If /
# BlockInstance can't host a lookup seam).
#
# Cross-part invariants carried via the part-1 ctx: used_names (CreateWidget
# names are screen-unique), authored/unauthored_aggregates + unmapped_locals
# (expression validation), var_counter (cosmetic but keeps vars unique in
# stitched review).

_SECTION_MIN_CHARS = 9_000     # don't defer subtrees smaller than this
_DEFAULT_PART_BUDGET = 42_000  # target max chars of C# body per part


def _measure_subtree(node: WidgetNode) -> int:
    """Rendered-size estimate (chars) of one subtree, in isolation."""
    scratch = RenderContext()
    _render_widget(node, "p", scratch)
    return sum(len(l) + 1 for l in scratch.lines)


def _collect_defer_candidates(widgets: list[WidgetNode], depth: int = 1,
                              out: list = None) -> list:
    """Container nodes at depth>=2 with children — the legal seam points."""
    if out is None:
        out = []
    for w in widgets:
        if depth >= 2 and w.widget_type == "Container" and w.children:
            out.append(w)
        _collect_defer_candidates(w.children, depth + 1, out)
        _collect_defer_candidates(w.true_branch, depth + 1, out)
        _collect_defer_candidates(w.false_branch, depth + 1, out)
    return out


def _is_ancestor(a: WidgetNode, b: WidgetNode) -> bool:
    n = b.parent
    while n is not None:
        if n is a:
            return True
        n = n.parent
    return False


def render_screen_dechromed_parts(
    ast: ScreenAST,
    role_name: Optional[str] = None,
    flow_name: str = "MainFlow",
    anonymous: bool = False,
    part_budget: int = _DEFAULT_PART_BUDGET,
) -> list[str]:
    """Render a screen as 1..N C# bodies, splitting when over part_budget.

    Returns [body] identical to render_screen_dechromed when it fits."""
    full = render_screen_dechromed(ast, role_name=role_name,
                                   flow_name=flow_name, anonymous=anonymous)
    if len(full) <= part_budget:
        return [full]

    # Greedy: defer the largest Container subtrees until part 1 fits.
    candidates = sorted(_collect_defer_candidates(ast.widgets),
                        key=_measure_subtree, reverse=True)
    deferred: list[WidgetNode] = []
    remaining = len(full)
    for cand in candidates:
        if remaining <= part_budget:
            break
        size = _measure_subtree(cand)
        if size < _SECTION_MIN_CHARS:
            break  # sorted desc — everything after is smaller
        if any(_is_ancestor(d, cand) or _is_ancestor(cand, d) for d in deferred):
            continue  # no nested deferrals
        deferred.append(cand)
        remaining -= size
    if not deferred:
        return [full]  # nothing deferrable — caller must handle oversize

    # Part 1: render with deferred nodes as named empty shells.
    stub_names = {}
    saved = {}
    for i, node in enumerate(deferred, 1):
        stub = f"sect_{i}"
        stub_names[id(node)] = stub
        saved[id(node)] = (node.name, node.children)
        node.name = stub
        node.children = []
    try:
        ctx1 = RenderContext()
        ctx1.stub_patches = []  # LOGIC-patch collector, shared across parts
        _emit_screen_setup(ast, ctx1, None if anonymous else role_name,
                           flow_name, anonymous)
        _emit_inputs(ast, ctx1)
        _emit_locals(ast, ctx1)
        _emit_aggregates(ast, ctx1)
        _emit_screen_actions_stubs(ast, ctx1)
        _emit_widgets(ast, ctx1)
        ctx1.emit("")
        ctx1.emit(f'Console.WriteLine($"Recipe 07 part1: {ast.name} | '
                  f'skeleton + {len(deferred)} deferred section shells | Status: PART-OK");')
        parts = ["eSpace => {\n    " + "\n    ".join(ctx1.lines) + "\n}"]
    finally:
        for node in deferred:
            node.name, node.children = saved[id(node)]

    # Parts 2+: one part per deferred subtree (greedy-mergeable later if small).
    for i, node in enumerate(deferred, 1):
        stub = stub_names[id(node)]
        ctxk = RenderContext()
        # carry cross-part invariants
        ctxk.used_names = set(ctx1.used_names)
        ctxk.authored_aggregates = set(ctx1.authored_aggregates)
        ctxk.unauthored_aggregates = set(ctx1.unauthored_aggregates)
        ctxk.unmapped_locals = set(ctx1.unmapped_locals)
        ctxk.stub_patches = ctx1.stub_patches  # shared collector
        ctxk.var_counter = ctx1.var_counter + i * 1000
        ctxk.emit(f"// ─── Screen part {i + 1}: fill section shell {stub} on {ast.name} ───")
        ctxk.emit(f'var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{flow_name}");')
        ctxk.emit(f'if (flow == null) {{ Console.WriteLine($"FAILED: MobileFlow {flow_name} not found"); return; }}')
        ctxk.emit(f'var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>().FirstOrDefault(s => s.Name == "{ast.name}");')
        ctxk.emit(f'if (screen == null) {{ Console.WriteLine($"FAILED: Screen {ast.name} not found — dispatch part 1 first"); return; }}')
        ctxk.emit(f'var sect = screen.GetAllDescendantsOfType<ServiceStudio.Plugin.NRWidgets.IContainer>().FirstOrDefault(c => c.Name == "{stub}");')
        ctxk.emit(f'if (sect == null) {{ Console.WriteLine($"FAILED: section shell {stub} not found — dispatch part 1 first"); return; }}')
        for child in node.children:
            _render_widget(child, "sect", ctxk)
        ctxk.emit("")
        ctxk.emit(f'Console.WriteLine($"Recipe 07 part{i + 1}: {ast.name} | '
                  f'section {stub} filled | Status: PART-OK");')
        parts.append("eSpace => {\n    " + "\n    ".join(ctxk.lines) + "\n}")
    # Expose the collected stub sites for render_screen_logic_patch (the
    # widget Names here match the published screen byte-for-byte because this
    # is the same allocation path that authored it).
    render_screen_dechromed_parts.last_stub_patches = list(ctx1.stub_patches)
    return parts
