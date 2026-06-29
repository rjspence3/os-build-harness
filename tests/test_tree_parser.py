"""Tests for tree_parser.py.

Covers:
- Parsing all 10 captured `.tree.md` files in `_raw/`
- Per-screen sanity: name, input count, local count, aggregate count, top-level widget count
- Diff: identical trees produce zero differences; modified trees produce expected differences
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.banking_runner.tree_parser import (
    Aggregate,
    LocalVar,
    ScreenAST,
    ScreenParam,
    WidgetNode,
    diff_screens,
    parse_coverage,
    parse_tree,
    parse_tree_file,
)


RAW_DIR = Path(__file__).resolve().parents[1] / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw"

# Captures that parse cleanly (Dialect A: SourceBlock="X" + Placeholder paths;
# Dialect B: Source=X + IfWidget + letter-coded paths). Coverage ≥ 0.9.
CLEAN_CAPTURES = [
    "portal-confirmation.tree.md",
    "portal-transfer.tree.md",
    "portal-requests.tree.md",
    "backoffice-dashboard.tree.md",
    "backoffice-requestdetail.tree.md",
    "backoffice-customers.tree.md",
    "backoffice-customerdetail.tree.md",
    "backoffice-managesettings.tree.md",
    # Re-captured 2026-05-28 with the strict R8 prompt (was Dialect C, now 1.00).
    "backoffice-personalloanofferletter.tree.md",
]

# DESCOPED (2026-05-28): portal-personalloan (the loan wizard) is out of scope.
# Its getScreen reconstruction is ~372KB, which overruns Mentor's synthesis-LLM
# context window (the reformat hangs), and the deterministic widget-walker
# workaround is not executable via MCP — Mentor refuses to run arbitrary
# read-only applyModelApiCode (memory odc_mcp_mentor_wont_run_arbitrary_read_code).
# No MCP capture path exists for it. The 0.04-coverage _raw file is left in place
# but is not an in-scope target. Same class of gap as Mobile.
DIALECT_C_CAPTURES: list[str] = []


# ─── Smoke: every captured tree parses ──────────────────────────────────────

@pytest.mark.parametrize("filename,expected_screen_name", [
    ("portal-confirmation.tree.md", "Confirmation"),
    ("portal-transfer.tree.md", "Transfer"),
    ("portal-personalloan.tree.md", "PersonalLoan"),
    ("portal-requests.tree.md", "Requests"),
    ("backoffice-dashboard.tree.md", "Dashboard"),
    ("backoffice-requestdetail.tree.md", "RequestDetail"),
    ("backoffice-customers.tree.md", "Customers"),
    ("backoffice-customerdetail.tree.md", "CustomerDetail"),
    ("backoffice-managesettings.tree.md", "ManageSettings"),
    ("backoffice-personalloanofferletter.tree.md", "PersonalLoanOfferLetter"),
])
def test_every_capture_parses(filename, expected_screen_name):
    path = RAW_DIR / filename
    if not path.exists():
        pytest.skip(f"capture {filename} not present")
    ast = parse_tree_file(path)
    assert ast.name == expected_screen_name, f"name mismatch in {filename}"
    # Must have at least one widget at top level
    assert len(ast.widgets) > 0, f"{filename} parsed zero widgets"


# ─── Parse coverage — guards against silent under-parsing ───────────────────

@pytest.mark.parametrize("filename", CLEAN_CAPTURES)
def test_clean_captures_high_coverage(filename):
    """Dialects A + B must parse ≥ 90% of widget-ish lines. This is the
    regression guard for the bug where a dialect mismatch silently dropped all
    child widgets (only the root parsed). If a future capture or parser change
    regresses coverage, this fails loudly instead of producing an empty tree."""
    path = RAW_DIR / filename
    if not path.exists():
        pytest.skip(f"capture {filename} not present")
    cov = parse_coverage(path.read_text())
    assert cov["coverage"] >= 0.9, (
        f"{filename} coverage {cov['coverage']:.2f} "
        f"({cov['parsed_nodes']}/{cov['widget_lines']} widget lines) — "
        f"parser dropped widgets; check for a new capture dialect"
    )


# ─── ManageSettings — smallest, easiest to spot-check ───────────────────────

def test_managesettings_structure():
    """ManageSettings: 0 inputs, 1 local (IsBootstrapStarted), 2 aggregates, 1 root widget (LayoutSideMenu)."""
    path = RAW_DIR / "backoffice-managesettings.tree.md"
    if not path.exists():
        pytest.skip("capture not present")
    ast = parse_tree_file(path)
    assert len(ast.inputs) == 0
    # Local: IsBootstrapStarted Boolean default=False
    assert len(ast.locals) == 1
    assert ast.locals[0].name == "IsBootstrapStarted"
    assert ast.locals[0].data_type == "Boolean"
    assert ast.locals[0].default == "False"
    # Aggregates: GetDataSettings, GetRegions
    agg_names = {a.name for a in ast.aggregates}
    assert agg_names == {"GetDataSettings", "GetRegions"}
    assert next(a for a in ast.aggregates if a.name == "GetDataSettings").source == "DataSettings"
    # Top-level: 1 BlockInstance (LayoutSideMenu)
    assert len(ast.widgets) == 1
    root = ast.widgets[0]
    assert root.widget_type == "BlockInstance"
    assert root.name == "LayoutSideMenu"
    assert root.source_block == "LayoutSideMenu"


# ─── Confirmation — has If branches + BlockInstance placeholders ─────────────

def test_confirmation_has_if_branches():
    """Confirmation has an `If` widget — verify condition + branches present."""
    path = RAW_DIR / "portal-confirmation.tree.md"
    if not path.exists():
        pytest.skip("capture not present")
    ast = parse_tree_file(path)
    # Find the If widget anywhere in the tree
    if_widgets = _find_all(ast.widgets, lambda w: w.widget_type.lower() == "if")
    assert len(if_widgets) >= 1, "Confirmation should have at least one If widget"
    # The outer If has condition "TransactionId = NullIdentifier()"
    outer_if = if_widgets[0]
    assert outer_if.condition is not None
    assert "NullIdentifier" in outer_if.condition


# ─── Inputs parsing ─────────────────────────────────────────────────────────

def test_inputs_parsing():
    """Test the inputs line parser with mandatory + identifier types."""
    sample = """=== Screen: T ===
Inputs: AccountId:HBAccount Identifier (mandatory), Other:Text
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    assert len(ast.inputs) == 2
    assert ast.inputs[0].name == "AccountId"
    assert ast.inputs[0].data_type == "HBAccount Identifier"
    assert ast.inputs[0].mandatory is True
    assert ast.inputs[1].name == "Other"
    assert ast.inputs[1].data_type == "Text"
    assert ast.inputs[1].mandatory is False


def test_inputs_none_variants():
    """Both '(none)' and '<none>' should produce empty inputs."""
    for marker in ("(none)", "<none>"):
        sample = f"""=== Screen: T ===
Inputs: {marker}
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
        ast = parse_tree(sample)
        assert ast.inputs == []


# ─── Locals parsing ─────────────────────────────────────────────────────────

def test_locals_with_defaults():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: CountDownValue:Integer=10, Message:Text, IsActive:Boolean (default=False)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    assert len(ast.locals) == 3
    assert ast.locals[0].name == "CountDownValue"
    assert ast.locals[0].default == "10"
    assert ast.locals[1].default is None
    assert ast.locals[2].name == "IsActive"
    assert ast.locals[2].default == "False"


# ─── Aggregates parsing ────────────────────────────────────────────────────

def test_aggregates_parsing():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: GetX (source=Foo), GetY (source=Bar, sort=Bar.Name)
--- WIDGETS (hierarchical) ---
"""
    ast = parse_tree(sample)
    assert len(ast.aggregates) == 2
    assert ast.aggregates[0].name == "GetX"
    assert ast.aggregates[0].source == "Foo"
    assert ast.aggregates[1].source == "Bar"


# ─── Widget header parsing ──────────────────────────────────────────────────

def test_widget_header_with_properties():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'MyName' Style="card" Visible="True" Width="(fill parent)"
"""
    ast = parse_tree(sample)
    assert len(ast.widgets) == 1
    w = ast.widgets[0]
    assert w.widget_type == "Container"
    assert w.name == "MyName"
    assert w.properties == {"Style": "card", "Visible": "True", "Width": "(fill parent)"}


def test_widget_unnamed():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container (unnamed) Width="(fill parent)"
"""
    ast = parse_tree(sample)
    assert ast.widgets[0].name is None


def test_blockinstance_extracts_source_block():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'MenuInstance' SourceBlock="Menu" ActiveItem=null ActiveSubItem=null
"""
    ast = parse_tree(sample)
    w = ast.widgets[0]
    assert w.source_block == "Menu"
    assert "SourceBlock" not in w.properties  # lifted out


def test_widget_hierarchy_via_paths():
    """A child widget [1.1] should be a child of [1]."""
    sample = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'Root'
  [1.1] Container 'ChildA'
  [1.2] Container 'ChildB'
    [1.2.1] Text Text="hello"
"""
    ast = parse_tree(sample)
    assert len(ast.widgets) == 1
    root = ast.widgets[0]
    assert root.name == "Root"
    assert len(root.children) == 2
    assert root.children[0].name == "ChildA"
    assert root.children[1].name == "ChildB"
    assert len(root.children[1].children) == 1
    assert root.children[1].children[0].widget_type == "Text"


# ─── Diff ───────────────────────────────────────────────────────────────────

def test_diff_identical_tree():
    sample = """=== Screen: T ===
Inputs: (none)
Locals: X:Text
Aggregates: GetX (source=Foo)
--- WIDGETS (hierarchical) ---
[1] Container 'Root' Style="card"
  [1.1] Text Text="hello"
"""
    a = parse_tree(sample)
    b = parse_tree(sample)
    diffs = diff_screens(a, b)
    assert diffs == [], f"Expected no diffs, got {diffs}"


def test_diff_widget_type_change():
    sample_a = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'Root'
"""
    sample_b = sample_a.replace("Container", "Button")
    a = parse_tree(sample_a)
    b = parse_tree(sample_b)
    diffs = diff_screens(a, b)
    types_changed = [d for d in diffs if d.kind == "widget_type"]
    assert len(types_changed) == 1
    assert types_changed[0].expected == "Container"
    assert types_changed[0].actual == "Button"


def test_diff_property_change():
    sample_a = """=== Screen: T ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] Container 'Root' Style="card"
"""
    sample_b = sample_a.replace('Style="card"', 'Style="modal"')
    a = parse_tree(sample_a)
    b = parse_tree(sample_b)
    diffs = diff_screens(a, b)
    style_changes = [d for d in diffs if d.kind == "property" and "Style" in d.detail]
    assert len(style_changes) == 1


def test_diff_screen_name():
    a = parse_tree("=== Screen: A ===\nInputs: (none)\nLocals: (none)\nAggregates: (none)\n--- WIDGETS (hierarchical) ---\n")
    b = parse_tree("=== Screen: B ===\nInputs: (none)\nLocals: (none)\nAggregates: (none)\n--- WIDGETS (hierarchical) ---\n")
    diffs = diff_screens(a, b)
    name_diffs = [d for d in diffs if d.kind == "screen_name"]
    assert len(name_diffs) == 1


# ─── Helpers ────────────────────────────────────────────────────────────────

def _find_all(widgets, predicate):
    """Walk widget tree (including branch children of If) finding nodes that match."""
    out = []
    for w in widgets:
        if predicate(w):
            out.append(w)
        out.extend(_find_all(w.children, predicate))
        out.extend(_find_all(w.true_branch, predicate))
        out.extend(_find_all(w.false_branch, predicate))
    return out
