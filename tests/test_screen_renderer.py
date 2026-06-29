"""Tests for screen_renderer.py.

The renderer is pure (AST → C# string), so tests don't need a live Mentor
dispatch. They assert that the generated C# has the expected shape: screen
creation, input/local/aggregate setup, widget creation calls, custom-block
stripping, screen action stubs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.banking_runner.screen_renderer import render_screen_dechromed
from harness.banking_runner.tree_parser import parse_tree, parse_tree_file


RAW_DIR = Path(__file__).resolve().parents[1] / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw"


# ─── Smoke: every captured tree renders without crashing ────────────────────

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
def test_every_capture_renders(filename):
    path = RAW_DIR / filename
    if not path.exists():
        pytest.skip(f"capture {filename} not present")
    ast = parse_tree_file(path)
    cs = render_screen_dechromed(ast)
    assert cs.startswith("eSpace => {")
    assert cs.endswith("}")
    # Must reference flow + screen creation
    assert "MobileFlows.FirstOrDefault" in cs
    assert f'.CreateScreen("{ast.name}")' in cs
    # Must emit the diagnostic
    assert "Recipe 07-DECHROMED" in cs


# ─── Screen setup ───────────────────────────────────────────────────────────

def test_renders_screen_with_role():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast, role_name="HomeBankingBackoffice")
    assert 'screen.Roles.Add(role)' in cs
    assert 'eSpace.Roles.FirstOrDefault(r => r.Name == "HomeBankingBackoffice")' in cs


def test_no_role_when_none():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    assert 'screen.Roles.Add' not in cs


# ─── Inputs ─────────────────────────────────────────────────────────────────

def test_inputs_emitted():
    sample = """=== Screen: T ===
Inputs: AccountId:HBAccount Identifier (mandatory), Note:Text
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    assert 'CreateInputParameter("AccountId")' in cs
    assert 'CreateInputParameter("Note")' in cs
    # AccountId mandatory
    assert 'ip.IsMandatory = true;' in cs
    # AccountId identifier type resolution
    assert 'e.Name == "HBAccount"' in cs
    # Note → Text type
    assert 'eSpace.TextType' in cs


# ─── Locals ─────────────────────────────────────────────────────────────────

def test_locals_with_defaults_emitted():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: Count:Integer=10, Active:Boolean (default=True)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    assert 'CreateLocalVariable("Count")' in cs
    assert 'CreateLocalVariable("Active")' in cs
    assert 'SetDefaultValue("10")' in cs
    assert 'SetDefaultValue("True")' in cs


# ─── Aggregates ─────────────────────────────────────────────────────────────

def test_aggregates_emitted_with_source_lookup():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: GetCustomers (source=HBCustomer)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    assert 'CreateScreenAggregate(false, "GetCustomers")' in cs
    assert 'e.Name == "HBCustomer"' in cs


# ─── Widgets ────────────────────────────────────────────────────────────────

def test_container_with_children_emits_proper_parent_var():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'Root'
  [1.1] Text Text="Hello"
  [1.2] Button 'SaveBtn'
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    # Container creation under screen via CreateWidget<IContainer>
    assert 'screen.CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>(' in cs
    # Text under the container var (c1)
    assert 'c1.CreateWidget<OutSystems.Model.UI.Mobile.Widgets.ITextWidget>(' in cs
    # Button is DECHROMED to a Container placeholder — an OS UI Button has a
    # mandatory OnClick; without a real handler the OML validator rejects publish.
    # The real Button + wired OnClick is restored in the CHROME/LOGIC phase.
    assert "DECHROMED Button 'SaveBtn'" in cs
    assert 'c1.CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>("SaveBtn")' in cs
    # Text content
    assert '"Hello"' in cs


def test_text_with_quote_escapes():
    sample = '''=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Text Text="Say \\"hello\\" world"
'''
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    # Inner quotes escaped in emitted string
    assert 'Say \\"hello\\" world' in cs


# ─── Custom-block stripping ─────────────────────────────────────────────────

def test_custom_block_stripped():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'CustomChrome' SourceBlock="HBHeader"
  [1.1] Text Text="Inside chrome"
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    # Should mark the BlockInstance as stripped
    assert 'CHROME-STRIPPED' in cs
    assert 'SourceBlock=HBHeader' in cs
    # Should still create the inner Text widget
    assert '"Inside chrome"' in cs
    # The stripped block becomes a named placeholder Container for chrome wrap.
    # No leading underscore: the Model API silently strips it from widget Names,
    # so the marker persists as `chrome_<block>_<path>` (see strip_marker_name).
    assert 'CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>("chrome_HBHeader' in cs


def test_os_ui_standard_block_kept():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'TopLayout' SourceBlock="LayoutTopMenu"
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    # OS UI standard block — NOT stripped
    assert 'CHROME-STRIPPED' not in cs
    assert 'OS UI standard' in cs


# ─── Screen actions ─────────────────────────────────────────────────────────

def test_screen_action_stub_created_for_onclick_handler():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Button 'SaveBtn' OnClick=SaveSettingsOnClick
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    assert 'CreateScreenAction("SaveSettingsOnClick")' in cs
    # Action body: Start → End stub
    assert 'CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>()' in cs
    assert 'CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>()' in cs


def test_destination_navigation_not_treated_as_action():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Button 'NavBtn' OnClick→Destination=Dashboard
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    # Dashboard is a screen, not a screen action — must NOT be wrapped in CreateScreenAction
    assert 'CreateScreenAction("Dashboard")' not in cs
    # But it should be noted as destination wiring
    assert 'Destination=Dashboard' in cs


# ─── If widget ──────────────────────────────────────────────────────────────

def test_if_widget_emits_condition_and_branches():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] If (unnamed) Condition="x = 1"
"""
    ast = parse_tree(sample)
    cs = render_screen_dechromed(ast)
    # Dechromed: If renders as a Container placeholder; the condition is recorded
    # as a comment for LOGIC-phase restoration (IIfWidget is unresolvable on the
    # app compile context).
    assert 'CreateWidget<ServiceStudio.Plugin.NRWidgets.IContainer>(' in cs
    assert 'IF Condition="x = 1"' in cs


# ─── ManageSettings end-to-end ──────────────────────────────────────────────

def test_managesettings_full_dechromed_render():
    """End-to-end: parse ManageSettings, render, verify expected hallmarks."""
    path = RAW_DIR / "backoffice-managesettings.tree.md"
    if not path.exists():
        pytest.skip("capture not present")
    ast = parse_tree_file(path)
    cs = render_screen_dechromed(ast, role_name="HomeBankingBackoffice", flow_name="MainFlow")

    # Screen + role
    assert 'CreateScreen("ManageSettings")' in cs
    assert 'HomeBankingBackoffice' in cs

    # Local variable
    assert 'CreateLocalVariable("IsBootstrapStarted")' in cs
    assert 'SetDefaultValue("False")' in cs

    # Both aggregates
    assert 'CreateScreenAggregate(false, "GetDataSettings")' in cs
    assert 'CreateScreenAggregate(false, "GetRegions")' in cs

    # The root LayoutSideMenu is OS UI standard — kept
    assert 'LayoutSideMenu' in cs

    # Save action stub
    assert 'CreateScreenAction("SaveSettingsOnClick")' in cs

    # Diagnostic at end
    assert 'Recipe 07-DECHROMED' in cs
    assert 'ManageSettings' in cs


def test_render_output_is_valid_csharp_block():
    """The output must be a well-formed eSpace => { ... } expression."""
    path = RAW_DIR / "backoffice-managesettings.tree.md"
    if not path.exists():
        pytest.skip("capture not present")
    ast = parse_tree_file(path)
    cs = render_screen_dechromed(ast)
    # Balanced braces
    assert cs.count("{") == cs.count("}")
    # No null-byte / unicode-escape disasters
    assert "\x00" not in cs
