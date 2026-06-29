"""Tests for block_renderer.py (Recipe 22 — custom block authoring).

Two surfaces tested:
1. Synthetic BlockAST → rendered C# (the renderer)
2. Speculative `.block.tree.md` text → parsed BlockAST (the parser)

No live Mentor dispatch — that's deferred to T4 along with the live capture
of real block trees.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.banking_runner.block_renderer import (
    BlockAST,
    BlockEvent,
    BlockParam,
    parse_block_tree,
    render_block,
)
from harness.banking_runner.tree_parser import WidgetNode


# ─── Setup helpers ─────────────────────────────────────────────────────────────

def _hbicon_ast() -> BlockAST:
    """The smallest realistic custom block: HBIcon with one input + one Text widget."""
    return BlockAST(
        name="HBIcon",
        is_public=True,
        inputs=[BlockParam(name="IconName", data_type="Text", mandatory=True)],
        widgets=[
            WidgetNode(
                path="1",
                widget_type="Container",
                name="IconWrap",
                properties={"Style": "icon-wrap"},
                children=[
                    WidgetNode(
                        path="1.1",
                        widget_type="Text",
                        name=None,
                        properties={"Text": "IconName"},  # bound via expression at runtime
                    ),
                ],
            ),
        ],
        style_sheet=".icon-wrap { display: inline-flex; align-items: center; }",
    )


def _menu_ast() -> BlockAST:
    """A larger block: Menu with input + event + nested widgets."""
    return BlockAST(
        name="Menu",
        is_public=True,
        inputs=[
            BlockParam(name="ActiveItem", data_type="Text", mandatory=False),
            BlockParam(name="ActiveSubItem", data_type="Text", mandatory=False),
        ],
        events=[
            BlockEvent(
                name="OnNavigate",
                output_params=[BlockParam(name="TargetScreen", data_type="Text")],
            ),
        ],
        widgets=[
            WidgetNode(path="1", widget_type="Container", name="MenuRoot",
                       properties={"Style": "menu-root"}),
        ],
    )


# ─── Renderer ──────────────────────────────────────────────────────────────────

def test_render_block_basic():
    cs = render_block(_hbicon_ast())
    assert cs.startswith("eSpace => {")
    assert cs.endswith("}")
    # Flow lookup + block creation
    assert 'MobileFlows.FirstOrDefault(f => f.Name == "Common")' in cs
    assert 'flow.CreateBlock("HBIcon")' in cs
    # Public is forced false: IMobileBlock.Public = true compiles but triggers
    # OS-BLD-40409 at publish, so the renderer pins it false (is_public is
    # preserved on the AST for a future v2). See block_renderer._emit_block_setup.
    assert 'block.Public = false;' in cs
    # Self-healing idempotency: delete-then-author on re-dispatch (the old
    # "bail with ALREADY_EXISTS" guard was replaced — it short-circuited the
    # Public=false fix when a prior partial publish left the block at true).
    assert 'replaced existing block' in cs


def test_render_block_input_parameter():
    cs = render_block(_hbicon_ast())
    assert 'block.CreateInputParameter("IconName")' in cs
    assert 'ip.DataType = eSpace.TextType' in cs
    assert 'ip.IsMandatory = true' in cs


def test_render_block_widgets():
    cs = render_block(_hbicon_ast())
    # Container under block via CreateWidget<IContainer> (named from authored name)
    assert 'block.CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>("IconWrap")' in cs
    # Text child under the container var (c1)
    assert 'c1.CreateWidget<OutSystems.Model.UI.Mobile.Widgets.ITextWidget>(' in cs
    assert '"IconName"' in cs


def test_render_block_stylesheet():
    cs = render_block(_hbicon_ast())
    # Verbatim string for CSS
    assert 'block.StyleSheet = @"' in cs
    assert ".icon-wrap" in cs


def test_render_block_with_event():
    cs = render_block(_menu_ast())
    # Block events are DEFERRED to LOGIC phase (the Action-typed-input API does
    # not resolve on this compile context) — recorded as a comment, not emitted.
    assert 'EVENT OnNavigate(TargetScreen:Text)' in cs
    assert 'eSpace.ActionType' not in cs
    assert 'CreateOutputParameter' not in cs


def test_render_block_no_optional_blocks():
    """A bare-minimum block with no inputs/events/stylesheet still renders cleanly."""
    bare = BlockAST(name="Empty", widgets=[WidgetNode(path="1", widget_type="Container", name=None)])
    cs = render_block(bare)
    assert 'flow.CreateBlock("Empty")' in cs
    # No input/event/stylesheet sections
    assert 'CreateInputParameter' not in cs
    assert 'CreateOutputParameter' not in cs
    assert 'block.StyleSheet' not in cs


def test_render_block_diagnostic():
    cs = render_block(_hbicon_ast())
    assert 'Recipe 22: HBIcon' in cs


def test_render_block_default_value():
    ast = BlockAST(
        name="Spacer",
        inputs=[BlockParam(name="Size", data_type="Integer", mandatory=False, default="10")],
        widgets=[WidgetNode(path="1", widget_type="Container", name=None)],
    )
    cs = render_block(ast)
    assert 'CreateInputParameter("Size")' in cs
    assert 'SetDefaultValue("10")' in cs


def test_render_block_non_public():
    ast = BlockAST(
        name="Private",
        is_public=False,
        widgets=[WidgetNode(path="1", widget_type="Container", name=None)],
    )
    cs = render_block(ast)
    assert 'block.Public = false;' in cs


def test_render_block_custom_flow():
    ast = BlockAST(
        name="MainFlowBlock",
        flow_name="MainFlow",
        widgets=[WidgetNode(path="1", widget_type="Container", name=None)],
    )
    cs = render_block(ast)
    assert 'f.Name == "MainFlow"' in cs


# ─── Parser ────────────────────────────────────────────────────────────────────

def test_parse_block_tree_basic():
    text = """=== Block: HBIcon ===
Public: True
Inputs: IconName:Text (mandatory)
Events: (none)
Flow: Common
--- WIDGETS (hierarchical) ---
[1] Container 'IconWrap' Style="icon-wrap"
  [1.1] Text Text="IconName"
"""
    ast = parse_block_tree(text)
    assert ast.name == "HBIcon"
    assert ast.is_public is True
    assert ast.flow_name == "Common"
    assert len(ast.inputs) == 1
    assert ast.inputs[0].name == "IconName"
    assert ast.inputs[0].mandatory is True
    assert ast.events == []
    assert len(ast.widgets) == 1
    assert ast.widgets[0].widget_type == "Container"
    assert ast.widgets[0].name == "IconWrap"
    assert len(ast.widgets[0].children) == 1


def test_parse_block_tree_with_events():
    text = """=== Block: Menu ===
Public: True
Inputs: ActiveItem:Text
Events: OnNavigate (TargetScreen:Text), OnSelect (Id:Integer)
--- WIDGETS (hierarchical) ---
[1] Container 'MenuRoot'
"""
    ast = parse_block_tree(text)
    assert len(ast.events) == 2
    assert ast.events[0].name == "OnNavigate"
    assert len(ast.events[0].output_params) == 1
    assert ast.events[0].output_params[0].name == "TargetScreen"
    assert ast.events[1].name == "OnSelect"
    assert ast.events[1].output_params[0].data_type == "Integer"


def test_parse_block_tree_non_public():
    text = """=== Block: Private ===
Public: False
Inputs: (none)
Events: (none)
--- WIDGETS (hierarchical) ---
[1] Container (unnamed)
"""
    ast = parse_block_tree(text)
    assert ast.is_public is False


def test_parse_block_tree_with_stylesheet():
    text = """=== Block: Styled ===
Public: True
Inputs: (none)
Events: (none)
--- STYLESHEET ---
.my-class {
    color: red;
}
--- WIDGETS (hierarchical) ---
[1] Container (unnamed)
"""
    ast = parse_block_tree(text)
    assert ast.style_sheet is not None
    assert ".my-class" in ast.style_sheet
    assert "color: red" in ast.style_sheet


# ─── End-to-end ────────────────────────────────────────────────────────────────

def test_parse_then_render_round_trip():
    """A round-trip from parsed AST → rendered C# should produce a well-formed block."""
    text = """=== Block: HBIcon ===
Public: True
Inputs: IconName:Text (mandatory)
Events: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'IconWrap' Style="icon-wrap"
  [1.1] Text Text="IconName"
"""
    ast = parse_block_tree(text)
    cs = render_block(ast)
    # Balanced braces
    assert cs.count("{") == cs.count("}")
    # All HBIcon hallmarks present
    assert 'CreateBlock("HBIcon")' in cs
    assert 'CreateInputParameter("IconName")' in cs
    assert 'CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>("IconWrap")' in cs
    assert 'Recipe 22: HBIcon' in cs


def test_render_includes_chrome_stripped_marker_for_nested_custom_block():
    """Even inside a custom block, NESTED references to other custom blocks
    should get the chrome-stripped marker (e.g. a Header block whose body
    references HBIcon — HBIcon gets stripped here too)."""
    ast = BlockAST(
        name="Header",
        widgets=[
            WidgetNode(
                path="1", widget_type="Container", name="HeaderWrap",
                children=[
                    WidgetNode(
                        path="1.1",
                        widget_type="BlockInstance",
                        name=None,
                        source_block="HBIcon",
                    ),
                ],
            ),
        ],
    )
    cs = render_block(ast)
    # HBIcon is NOT in OS_UI_STANDARD_BLOCKS, so it gets stripped
    assert "CHROME-STRIPPED" in cs
    assert "HBIcon" in cs
