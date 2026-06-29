"""Custom Block authoring renderer (R9b / Recipe 22).

Reads a captured `.block.tree.md` (same shape as `.tree.md` but for blocks) →
emits Mentor MCP applyModelApiCode that authors the block via
`IMobileFlow.CreateBlock(name)`.

Per `[[odc_mcp_block_creation_works]]`: non-layout blocks (cards, modals,
headers, icons) author cleanly via MCP. **Layout blocks** (those that own
the page chrome — top nav, side nav, header strip) have rendering walls
per `[[odc_mcp_layout_block_lifting_walls]]` and need Studio chat-pane.

Status: MVP — covers the common block shape: input parameters, widget tree
(reusing screen_renderer widget handlers), style sheet, block events. Live
capture path (Mentor probe → .block.tree.md) is deferred to T4 — for now
ASTs are constructed synthetically in tests OR parsed from a captured file
when one becomes available.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness.banking_runner.tree_parser import (
    WidgetNode,
    _PATH_RE,
    _parse_widget_header,
    _parent_path,
    _find_last_if,
)
from harness.banking_runner.screen_renderer import (
    RenderContext,
    _render_widget,
    _resolve_data_type,
    _format_default,
)


# ─── AST ───────────────────────────────────────────────────────────────────────

@dataclass
class BlockParam:
    name: str
    data_type: str
    mandatory: bool = False
    default: Optional[str] = None


@dataclass
class BlockEvent:
    """A block-output event (parent screens wire handlers via OnEvent:Name)."""
    name: str
    output_params: list[BlockParam] = field(default_factory=list)


@dataclass
class BlockAST:
    name: str                                           # block identifier
    is_public: bool = True                              # public by default — most custom blocks need to cross apps
    inputs: list[BlockParam] = field(default_factory=list)
    events: list[BlockEvent] = field(default_factory=list)
    widgets: list[WidgetNode] = field(default_factory=list)
    style_sheet: Optional[str] = None                   # block-scoped CSS
    flow_name: str = "Common"                           # blocks live on the Common flow by default


# ─── Parser (speculative — for future .block.tree.md captures) ─────────────────

def parse_block_tree_file(path: Path) -> BlockAST:
    """Parse a `.block.tree.md` file into a BlockAST. Format mirrors the screen
    capture format but uses `=== Block: <Name> ===` and adds `Public:`,
    `Events:`, and `StyleSheet:` header lines."""
    return parse_block_tree(path.read_text())


def parse_block_tree(text: str) -> BlockAST:
    """Parse the raw `.block.tree.md` content into a BlockAST."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    i = 0
    ast = BlockAST(name="<unknown>")

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("=== Block:"):
            m = re.search(r"=== Block:\s*(\S+)", line)
            if m:
                ast.name = m.group(1).rstrip(" =")
        elif line.startswith("Public:"):
            val = line[len("Public:"):].strip().lower()
            ast.is_public = val in ("true", "1", "yes")
        elif line.startswith("Inputs:"):
            ast.inputs = _parse_block_params(line[len("Inputs:"):].strip())
        elif line.startswith("Events:"):
            ast.events = _parse_block_events(line[len("Events:"):].strip())
        elif line.startswith("StyleSheet:"):
            # Marker only — actual CSS text follows in a fenced block below
            pass
        elif line.startswith("Flow:"):
            ast.flow_name = line[len("Flow:"):].strip()
        elif line.startswith("--- WIDGETS"):
            i += 1
            break
        elif line.startswith("--- STYLESHEET"):
            # Collect remaining lines until next "---" or EOF
            css_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("--- WIDGETS"):
                css_lines.append(lines[i])
                i += 1
            ast.style_sheet = "\n".join(css_lines).strip()
            continue
        i += 1

    # Widget tree — reuse the screen parser's logic
    path_to_node: dict[str, WidgetNode] = {}
    pending_branch_for: Optional[WidgetNode] = None
    pending_branch_type: Optional[str] = None

    for raw_line in lines[i:]:
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("PLACEHOLDER ") or stripped.startswith("[TRUE BRANCH") or stripped.startswith("[FALSE BRANCH"):
            if "TRUE BRANCH" in stripped:
                pending_branch_for = _find_last_if(path_to_node)
                pending_branch_type = "true"
            elif "FALSE BRANCH" in stripped:
                pending_branch_for = _find_last_if(path_to_node)
                pending_branch_type = "false"
            continue

        m = _PATH_RE.match(line)
        if not m:
            continue
        path, remainder = m.group(1), m.group(2)
        node = _parse_widget_header(path, remainder)
        if not node:
            continue

        if node.widget_type.lower() == "if":
            node.condition = node.properties.pop("Condition", None)

        parent_path = _parent_path(path)
        if parent_path and parent_path in path_to_node:
            parent = path_to_node[parent_path]
            node.parent = parent
            if parent.widget_type.lower() == "if":
                trailing = path[len(parent.path) + 1:]
                first_seg = trailing.split(".", 1)[0]
                if first_seg == "T":
                    parent.true_branch.append(node)
                elif first_seg == "F":
                    parent.false_branch.append(node)
                else:
                    parent.children.append(node)
            else:
                parent.children.append(node)
        else:
            ast.widgets.append(node)

        path_to_node[path] = node

    return ast


def _parse_block_params(line: str) -> list[BlockParam]:
    """Parse 'Inputs:' line — same grammar as screen inputs."""
    if line in ("(none)", "<none>", ""):
        return []
    items = _split_top_level(line, ",")
    params = []
    for item in items:
        item = item.strip()
        if not item or ":" not in item:
            continue
        name, rest = item.split(":", 1)
        name = name.strip()
        rest = rest.strip()
        mandatory = False
        default = None
        if "(mandatory)" in rest:
            mandatory = True
            rest = rest.replace("(mandatory)", "").strip()
        dm = re.search(r"\(default=([^)]*)\)", rest)
        if dm:
            default = dm.group(1)
            rest = re.sub(r"\s*\(default=[^)]*\)\s*", "", rest).strip()
        data_type = re.sub(r"\s*\(.*?\)\s*$", "", rest).strip()
        params.append(BlockParam(name=name, data_type=data_type, mandatory=mandatory, default=default))
    return params


def _parse_block_events(line: str) -> list[BlockEvent]:
    """Parse 'Events:' line — e.g. 'OnSelect (id:Integer), OnSubmit'."""
    if line in ("(none)", "<none>", ""):
        return []
    items = _split_top_level(line, ",", paren_aware=True)
    events = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        m = re.match(r"(\w+)\s*(?:\((.*)\))?\s*$", item)
        if not m:
            continue
        name = m.group(1)
        params = []
        if m.group(2):
            params = _parse_block_params(m.group(2))
        events.append(BlockEvent(name=name, output_params=params))
    return events


def _split_top_level(s: str, sep: str, paren_aware: bool = True) -> list[str]:
    if not paren_aware:
        return s.split(sep)
    out, depth, buf = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


# ─── Renderer ──────────────────────────────────────────────────────────────────

def render_block(ast: BlockAST) -> str:
    """Render the C# body for one block via `IMobileFlow.CreateBlock(name)`.

    Returns the bare `eSpace => { ... }` lambda — caller wraps in PROMPT_PREAMBLE.
    """
    # emit_real_placeholders: block definitions author Placeholder capture
    # lines as real CreateWidget<IPlaceholderWidget> calls (2026-06-11 probe).
    ctx = RenderContext(screen_var="block", emit_real_placeholders=True)

    _emit_block_setup(ast, ctx)
    _emit_block_inputs(ast, ctx)
    _emit_block_events(ast, ctx)
    _emit_block_widgets(ast, ctx)
    _emit_block_stylesheet(ast, ctx)
    _emit_block_diagnostic(ast, ctx)

    return "eSpace => {\n    " + "\n    ".join(ctx.lines) + "\n}"


def _emit_block_setup(ast: BlockAST, ctx: RenderContext):
    ctx.emit(f"// ─── Block: {ast.name} (Recipe 22) ─────────────")
    # Portal Phase C learning (2026-06-02): fresh apps only ship with MainFlow
    # + Common. Custom blocks live on a "Widgets" flow the source app authored
    # separately; mirror that on the rebuild by creating the target flow on
    # demand when it doesn't exist — same FirstOrDefault + create-if-null
    # resilience pattern baked into entity FK resolution. Per the MobileX
    # naming convention (CreateMobileTheme/CreateMobileFlow), the create API
    # is `eSpace.CreateMobileFlow(name)`.
    ctx.emit(f'var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{ast.flow_name}") ?? eSpace.CreateMobileFlow("{ast.flow_name}");')
    # Portal Phase C learning (2026-06-02): the previous idempotency guard
    # was "if existing → bail with ALREADY_EXISTS" which made the recipe
    # short-circuit when a prior failed publish had partially committed the
    # block at, e.g., Public=true. The renderer's Public=false fix never
    # applied because the guard skipped over the recreation. **Delete-then-
    # author is the self-healing pattern** — every re-dispatch refreshes
    # the block to the renderer's current intent. Per memory
    # [[odc_mcp_publish_lifecycle]] § "OS-BLD-40409 marker cleared by
    # deletion", removing the offending element drops the removed-feature
    # marker from the OML so the next publish accepts the new shape.
    ctx.emit(f'var existing = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileBlock>().FirstOrDefault(b => b.Name == "{ast.name}");')
    ctx.emit(f'if (existing != null) {{ existing.Delete(); Console.WriteLine($"Recipe 22: {ast.name} | replaced existing block"); }}')
    ctx.emit(f'var block = flow.CreateBlock("{ast.name}");')
    # Portal Phase C learning (2026-06-02): `IMobileBlock.Public = true` compiles
    # cleanly but triggers OS-BLD-40409 at publish (`ModelFeature_UIPublicProperty`
    # — a removed model feature, same author-clean/publish-fail pattern as
    # `IServerAction.Public = true` from Core LOGIC). Force false for v1; the
    # modern public-block API (likely `CreateServiceBlock` or library-level
    # exposure) is unprobed. Preserve `ast.is_public` on the AST for v2.
    _intended_public = ast.is_public  # noqa: F841 — preserved for v2
    is_public = "false"
    ctx.emit(f'block.Public = {is_public};')


def _emit_block_inputs(ast: BlockAST, ctx: RenderContext):
    if not ast.inputs:
        return
    ctx.emit("")
    ctx.emit("// ─── Input parameters ───────────────────────")
    for p in ast.inputs:
        cs_type = _resolve_data_type(p.data_type)
        mand = "true" if p.mandatory else "false"
        line = f'{{ var ip = block.CreateInputParameter("{p.name}"); ip.DataType = {cs_type}; ip.IsMandatory = {mand};'
        if p.default is not None:
            literal = _format_default(p.data_type, p.default)
            line += f' ip.SetDefaultValue("{literal}");'
        line += " }"
        ctx.emit(line)


def _emit_block_events(ast: BlockAST, ctx: RenderContext):
    """Block events (parent-facing) are DEFERRED to the LOGIC phase.

    The naive "Action-typed input parameter" model does not resolve on this
    compile context: `eSpace.ActionType` (CS1061 on IESpace) and
    `IInputParameter.CreateOutputParameter` (CS1061) both fail. The real block-
    event API is unresolved (reflection refused), so the STRUCTURE-phase block
    records its events as comments; event wiring happens in the LOGIC phase."""
    if not ast.events:
        return
    ctx.emit("")
    ctx.emit("// ─── Block events (DEFERRED to LOGIC phase — Action-typed API unresolved) ───")
    for ev in ast.events:
        args = ", ".join(f"{a.name}:{a.data_type}" for a in ev.output_params)
        ctx.emit(f'// EVENT {ev.name}({args}) — wire in LOGIC phase')


def _emit_block_widgets(ast: BlockAST, ctx: RenderContext):
    if not ast.widgets:
        ctx.emit("")
        ctx.emit("// (no widgets in block)")
        return
    ctx.emit("")
    ctx.emit("// ─── Widget tree ────────────────────────────")
    parent_var = "block"
    for w in ast.widgets:
        _render_widget(w, parent_var, ctx)


def _emit_block_stylesheet(ast: BlockAST, ctx: RenderContext):
    if not ast.style_sheet:
        return
    ctx.emit("")
    ctx.emit("// ─── Block style sheet ──────────────────────")
    # StyleSheet is a plain string property (direct assign) — NOT an object with
    # .SetText (CS1061). Same as IMobileScreen.StyleSheet. Escape for C# verbatim.
    css = ast.style_sheet.replace('"', '""')
    ctx.emit(f'block.StyleSheet = @"{css}";')


def _emit_block_diagnostic(ast: BlockAST, ctx: RenderContext):
    ctx.emit("")
    ctx.emit(f'Console.WriteLine($"Recipe 22: {ast.name} | ' +
             f'inputs={{block.InputParameters.Count()}}, ' +
             f'public={{block.Public}}, ' +
             f'stripped_chrome={ctx.stripped_count} | Status: OK");')
