"""Tests for chrome_wrap.py (Recipe 23 — chrome wrap of dechromed screens).

Two surfaces tested:
1. `extract_chrome_wrap_manifest(ast)` — pulls custom-block entries from a
   ScreenAST
2. `render_chrome_wrap(manifest)` — emits the wrapping C#

Plus a critical symmetry test: the marker Name that T2.2's screen renderer
sets on stripped Containers must EXACTLY equal the marker Name that T2.5's
chrome-wrap renderer looks up. They both call `strip_marker_name()`, so as
long as they agree on that function, the wrap can find every dechromed site.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.banking_runner.chrome_wrap import (
    ChromeWrapEntry,
    ChromeWrapManifest,
    extract_chrome_wrap_manifest,
    render_chrome_wrap,
)
from harness.banking_runner.screen_renderer import (
    render_screen_dechromed,
    strip_marker_name,
)
from harness.banking_runner.tree_parser import (
    ScreenAST,
    WidgetNode,
    parse_tree,
    parse_tree_file,
)


RAW_DIR = Path(__file__).resolve().parents[1] / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw"


# ─── Manifest extraction ───────────────────────────────────────────────────────

def _make_ast(*widgets: WidgetNode, name: str = "T") -> ScreenAST:
    return ScreenAST(name=name, widgets=list(widgets))


def test_extract_no_blocks():
    """Screen with no BlockInstances → manifest has zero entries."""
    ast = _make_ast(WidgetNode(path="1", widget_type="Container", name="Root"))
    m = extract_chrome_wrap_manifest(ast)
    assert m.entries == []


def test_extract_os_ui_block_skipped():
    """A BlockInstance pointing to an OS UI standard block is NOT a chrome
    site — manifest excludes it."""
    ast = _make_ast(WidgetNode(
        path="1", widget_type="BlockInstance", name="Layout",
        source_block="LayoutSideMenu",  # OS UI standard
    ))
    m = extract_chrome_wrap_manifest(ast)
    assert m.entries == []


def test_extract_custom_block():
    """A BlockInstance pointing to a custom block IS a chrome site."""
    ast = _make_ast(WidgetNode(
        path="1.2.3", widget_type="BlockInstance", name="MyMenu",
        source_block="Menu",
        properties={"ActiveItem": "Dashboard"},
    ))
    m = extract_chrome_wrap_manifest(ast)
    assert len(m.entries) == 1
    e = m.entries[0]
    assert e.path == "1.2.3"
    assert e.source_block == "Menu"
    assert e.widget_name == "MyMenu"
    assert e.parent_path == "1.2"
    assert e.parameters == {"ActiveItem": "Dashboard"}


def test_extract_walks_into_children():
    """Custom blocks nested deep in the tree are discovered."""
    inner = WidgetNode(path="1.1.1", widget_type="BlockInstance",
                       name="Inner", source_block="HBIcon")
    middle = WidgetNode(path="1.1", widget_type="Container", name="Middle",
                        children=[inner])
    outer = WidgetNode(path="1", widget_type="Container", name="Outer",
                       children=[middle])
    m = extract_chrome_wrap_manifest(_make_ast(outer))
    assert len(m.entries) == 1
    assert m.entries[0].path == "1.1.1"
    assert m.entries[0].source_block == "HBIcon"


def test_extract_walks_into_if_branches():
    """Custom blocks inside If true/false branches are discovered."""
    if_node = WidgetNode(path="1", widget_type="If", name=None, condition="x = 1")
    if_node.true_branch.append(WidgetNode(
        path="1.T.1", widget_type="BlockInstance", name=None,
        source_block="HBIcon",
    ))
    if_node.false_branch.append(WidgetNode(
        path="1.F.1", widget_type="BlockInstance", name=None,
        source_block="Header",
    ))
    m = extract_chrome_wrap_manifest(_make_ast(if_node))
    src_blocks = {e.source_block for e in m.entries}
    assert src_blocks == {"HBIcon", "Header"}


def test_extract_real_managesettings():
    """End-to-end against the real capture: every non-OS-UI BlockInstance
    becomes a manifest entry."""
    path = RAW_DIR / "backoffice-managesettings.tree.md"
    if not path.exists():
        pytest.skip("capture not present")
    ast = parse_tree_file(path)
    m = extract_chrome_wrap_manifest(ast)
    # ManageSettings is mostly LayoutSideMenu (OS UI) + inner Menu / HBIcon /
    # AlignCenter blocks. At least one custom block expected.
    assert len(m.entries) > 0
    # No OS UI standard blocks
    from harness.banking_runner.screen_renderer import OS_UI_STANDARD_BLOCKS
    for e in m.entries:
        assert e.source_block not in OS_UI_STANDARD_BLOCKS, \
            f"OS UI block {e.source_block} leaked into manifest"


# ─── Renderer ──────────────────────────────────────────────────────────────────

def _hbicon_chrome_site_manifest() -> ChromeWrapManifest:
    """Synthetic manifest: one HBIcon site at path 1.2."""
    return ChromeWrapManifest(
        screen_name="ManageSettings",
        flow_name="MainFlow",
        entries=[
            ChromeWrapEntry(
                path="1.2",
                source_block="HBIcon",
                widget_name="CheckMark",
                parent_path="1",
                parameters={"IconName": "check"},
            ),
        ],
    )


def test_render_wrap_basic_structure():
    cs = render_chrome_wrap(_hbicon_chrome_site_manifest())
    assert cs.startswith("eSpace => {")
    assert cs.endswith("}")
    # Flow + screen lookup
    assert 'MobileFlows.FirstOrDefault(f => f.Name == "MainFlow")' in cs
    assert 'Screen.Name == "ManageSettings"' in cs or 's.Name == "ManageSettings"' in cs
    # Wrap counter
    assert "int wrapped = 0, missing = 0" in cs


def test_render_wrap_finds_marker_by_strip_name():
    """The renderer must look up the marker Container using the EXACT name
    that T2.2 would have given it."""
    m = _hbicon_chrome_site_manifest()
    cs = render_chrome_wrap(m)
    expected_marker = strip_marker_name("HBIcon", "1.2")  # "_chrome_HBIcon_1_2"
    assert expected_marker in cs


def test_render_wrap_creates_block_instance():
    cs = render_chrome_wrap(_hbicon_chrome_site_manifest())
    # Block signature lookup (own flow OR references)
    assert 'b.Name == "HBIcon"' in cs
    assert 'eSpace.References.SelectMany(r => r.Blocks)' in cs
    # Block instance created INSIDE the marker via CreateWidget<IMobileBlockInstanceWidget>
    assert 'marker.CreateWidget<OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget>("CheckMark")' in cs
    # Source block set via reflection (SourceWebBlock not on the static interface)
    assert 'bi.GetType().GetProperty("SourceWebBlock").SetValue(bi, blockSig)' in cs


def test_render_wrap_binds_parameters():
    cs = render_chrome_wrap(_hbicon_chrome_site_manifest())
    # Block input params are DEFERRED to the LOGIC phase — recorded as a comment.
    assert "params (bind in LOGIC phase)" in cs
    assert "IconName" in cs


def test_render_wrap_no_removewidget_or_createblockinstance():
    """The old (live-disproven) API must not appear: marker stays as a wrapper
    (no RemoveWidget), and block instances use CreateWidget, not CreateBlockInstance."""
    cs = render_chrome_wrap(_hbicon_chrome_site_manifest())
    assert 'RemoveWidget' not in cs
    assert 'CreateBlockInstance' not in cs


def test_render_wrap_skips_layout_only_properties():
    """Width/Style/Visible are widget-layout props of the BlockInstance, NOT
    block input parameters — they must be excluded from the deferred-params comment."""
    m = ChromeWrapManifest(
        screen_name="T", flow_name="MainFlow",
        entries=[ChromeWrapEntry(
            path="1", source_block="HBIcon", widget_name=None,
            parent_path=None,
            parameters={"IconName": "check", "Width": "100", "Style": "icon"},
        )],
    )
    cs = render_chrome_wrap(m)
    # IconName IS a block parameter → appears in the deferred-params comment
    assert "'IconName'" in cs or "IconName" in cs
    # Width / Style must NOT be treated as block params
    assert "'Width'" not in cs
    assert "'Style'" not in cs


def test_render_wrap_diagnostic_includes_counts():
    m = _hbicon_chrome_site_manifest()
    cs = render_chrome_wrap(m)
    assert "Recipe 23: ManageSettings" in cs
    # Expected count is the number of entries
    assert "wrapped={wrapped}/1" in cs


def test_render_wrap_no_entries_still_valid():
    m = ChromeWrapManifest(screen_name="Empty", entries=[])
    cs = render_chrome_wrap(m)
    assert cs.startswith("eSpace => {")
    assert cs.endswith("}")
    assert "Recipe 23: Empty" in cs


# ─── Critical symmetry: T2.2 markers ↔ T2.5 lookups ────────────────────────

def test_marker_naming_is_deterministic():
    """Same source_block + path → same marker name. This is the contract
    that lets T2.5 find what T2.2 set."""
    assert strip_marker_name("HBIcon", "1.2.3") == strip_marker_name("HBIcon", "1.2.3")
    assert strip_marker_name("Menu", "1") == "_chrome_Menu_1"
    assert strip_marker_name("HBIcon", "1.2.3.T.1") == "_chrome_HBIcon_1_2_3_T_1"


def test_t22_marker_matches_t25_lookup():
    """End-to-end: T2.2 emits a marker name for a stripped Container, T2.5
    looks up the same name. If this test passes, every dechromed site can be
    re-wrapped without coordination state."""
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'Root'
  [1.1] BlockInstance 'Menu1' SourceBlock="Menu"
"""
    ast = parse_tree(sample)
    # T2.2 output: marker Name is the CreateWidget<IContainer>("<marker>") arg
    dechromed_cs = render_screen_dechromed(ast)
    expected_marker = strip_marker_name("Menu", "1.1")
    assert f'IContainer>("{expected_marker}")' in dechromed_cs

    # T2.5 output: lookup the same marker
    manifest = extract_chrome_wrap_manifest(ast)
    wrap_cs = render_chrome_wrap(manifest)
    assert f'c.Name == "{expected_marker}"' in wrap_cs


def test_t22_and_t25_handle_real_capture_symmetrically():
    """Cross-check against a real capture: every chrome marker T2.2 emits
    must appear as a T2.5 lookup."""
    path = RAW_DIR / "backoffice-managesettings.tree.md"
    if not path.exists():
        pytest.skip("capture not present")
    ast = parse_tree_file(path)
    dechromed_cs = render_screen_dechromed(ast)
    manifest = extract_chrome_wrap_manifest(ast)
    wrap_cs = render_chrome_wrap(manifest)

    # Every entry's marker name must appear in BOTH outputs
    for entry in manifest.entries:
        marker = strip_marker_name(entry.source_block, entry.path)
        assert f'IContainer>("{marker}")' in dechromed_cs, \
            f"T2.2 did not name marker {marker}"
        assert f'c.Name == "{marker}"' in wrap_cs, \
            f"T2.5 did not look up marker {marker}"


# ─── Round-trip: every real capture extracts cleanly ───────────────────────

@pytest.mark.parametrize("filename", [
    "portal-confirmation.tree.md",
    "portal-transfer.tree.md",
    "portal-personalloan.tree.md",
    "portal-requests.tree.md",
    "backoffice-dashboard.tree.md",
    "backoffice-requestdetail.tree.md",
    "backoffice-customers.tree.md",
    "backoffice-customerdetail.tree.md",
    "backoffice-managesettings.tree.md",
    "backoffice-personalloanofferletter.tree.md",
])
def test_every_capture_extracts_and_renders(filename):
    capture = RAW_DIR / filename
    if not capture.exists():
        pytest.skip(f"{filename} not present")
    ast = parse_tree_file(capture)
    m = extract_chrome_wrap_manifest(ast)
    cs = render_chrome_wrap(m)
    assert cs.startswith("eSpace => {")
    assert cs.endswith("}")
    assert cs.count("{") == cs.count("}")
