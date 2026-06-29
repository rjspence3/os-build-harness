"""Parser for `.tree.md` files captured by R8 (Mentor synthesis output).

Reads Mentor's indented widget-tree summary and produces a typed AST. Used by:
- Screen recipe renderer (R9): AST → applyModelApiCode that recreates the screen
- Structural diff (T4.3): two ASTs → list of significant differences

Format observed in `_raw/*.tree.md`:

    === Screen: <Name> ===
    Inputs: <name:type, ...>
    Locals: <name:type, ...>
    Aggregates: <name (source=..., filter=...), ...>
    --- WIDGETS (hierarchical) ---
    [1] WidgetType 'Name' Property="Value" Property=null ...
      [1.1] ChildType ...
        [1.1.1] ...

Variants the parser must tolerate:
- 2-space OR 4-space indentation (use path notation as truth)
- `PLACEHOLDER 'Name'` (marker line, no path) AND `Placeholder 'Name'` (widget with path)
- `If` widgets with `[TRUE BRANCH ...]` / `[FALSE BRANCH ...]` marker lines
- Path segments like `T`, `F`, `I`, `L` (branch / placeholder shorthand)
- "(unnamed)" → name=None
- Properties can contain escaped quotes: `Style="\"my-class\""`
- OnClick destinations: `OnClick→Destination=Dashboard` or `OnClick=SaveSettingsOnClick`
- Events: `OnEvent:ReturnBinary→Handler(arg=expr)`

The parser is pragmatic — best-effort line-by-line extraction. Lines it can't
parse get logged but don't halt the parse.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─── AST types ─────────────────────────────────────────────────────────────────

@dataclass
class ScreenParam:
    name: str
    data_type: str
    mandatory: bool = False
    default: Optional[str] = None


@dataclass
class LocalVar:
    name: str
    data_type: str
    default: Optional[str] = None


@dataclass
class Aggregate:
    name: str
    source: Optional[str] = None      # e.g. "DataSettings"
    raw_args: str = ""                # e.g. "source=DataSettings, sort=Region.Region"


@dataclass
class WidgetNode:
    """One widget in the tree. Children reachable via `.children` (or branch
    fields for If). Parent reachable via `.parent` (set during parse)."""
    path: str                         # "1.2.3" or "1.2.1.1.T.1" (T/F for If branches)
    widget_type: str                  # "Container" | "Text" | "BlockInstance" | "If" | "Placeholder" | ...
    name: Optional[str]               # author-set name, or None for unnamed
    properties: dict[str, str] = field(default_factory=dict)
    children: list["WidgetNode"] = field(default_factory=list)
    parent: Optional["WidgetNode"] = field(default=None, repr=False)

    # BlockInstance specifics
    source_block: Optional[str] = None
    # block input parameter bindings (the non-SourceBlock properties on the BlockInstance line)
    # are stored in `properties` for uniformity

    # If specifics
    condition: Optional[str] = None
    true_branch: list["WidgetNode"] = field(default_factory=list)
    false_branch: list["WidgetNode"] = field(default_factory=list)

    # Event handlers — e.g. "OnClick" → "Destination=Dashboard"
    events: dict[str, str] = field(default_factory=dict)


@dataclass
class ScreenAST:
    name: str
    inputs: list[ScreenParam] = field(default_factory=list)
    locals: list[LocalVar] = field(default_factory=list)
    aggregates: list[Aggregate] = field(default_factory=list)
    widgets: list[WidgetNode] = field(default_factory=list)


# ─── Parser ────────────────────────────────────────────────────────────────────

# Path: [1] or [1.2.3] or [1.2.1.1.T.1] (Dialect B letter branches) or
# [1.Header] / [1.BannerContent.1] (Dialect C word segments).
#
# Distinguishing rule: a PATH always starts with a digit (the root is always
# numeric, e.g. `1`), and contains only word chars + dots — no spaces. A
# bracketed MARKER (`[Icon]`, `[True]`, `[WizardItem 1]`, `[Placeholder 'X']`)
# starts with a letter or contains a space, so it fails this regex and is
# routed to marker handling instead. This one rule covers all three dialects.
_PATH_RE = re.compile(r"^\s*\[(\d[\w.]*)\]\s*(.*?)\s*$")

# Bracketed placeholder marker (Dialect B): `[Placeholder 'Content']` — no
# numeric path. Treated like the bare `PLACEHOLDER` marker in Dialect A.
_BRACKET_PLACEHOLDER_RE = re.compile(r"^\s*\[Placeholder\b")

# Widget-type dialect normalization. Dialect B uses "IfWidget" where Dialect A
# uses "If". Normalizing here keeps branch attribution + diff + chrome_wrap
# (all of which key on widget_type == "If") dialect-agnostic.
_WIDGET_TYPE_ALIASES = {
    "IfWidget": "If",
}

# Widget header: WidgetType 'Name' or WidgetType (unnamed)
# Followed by space-separated key=value or key="quoted value" properties
_WIDGET_HEADER_RE = re.compile(
    r"^(\w+)\s+(?:'([^']*)'|\(([^)]+)\)|)\s*(.*)$"
)

# Property: key="value" or key=value (no quotes for bare tokens like null/True/numbers)
_PROP_RE = re.compile(
    r"""
    (\w+)                       # key
    =
    (?:
        "((?:[^"\\]|\\.)*)"     # quoted value (escaped quotes)
        |
        ([^\s"]+)               # bare token (null, True, identifier, etc.)
    )
    """,
    re.VERBOSE,
)

# Event: OnClick→Destination=Dashboard or OnClick→Handler or OnClick=Handler
# or OnEvent:Name→Handler(args)
_EVENT_RE = re.compile(
    r"(On\w+(?::\w+)?)\s*(?:→|=)\s*(.*)"
)

# Widget-type tokens used by the coverage heuristic. A line that, after leading
# whitespace, begins with one of these is "widget-ish" — it should have been
# parsed into a node. Used by parse_coverage() to detect under-parsing (e.g.
# Dialect C's unbracketed indent-based widget lines that the path-based parser
# cannot see).
_WIDGET_TOKENS = (
    "Container", "Text", "Button", "Expression", "Image", "If", "IfWidget",
    "BlockInstance", "Input", "Link", "List", "Table", "Form", "Dropdown",
    "Checkbox", "RadioButton", "Counter", "Chart", "Icon",
)
_WIDGET_LINE_RE = re.compile(
    r"^\s*(?:\[\d[\w.]*\]\s*)?(" + "|".join(_WIDGET_TOKENS) + r")\b"
)


def parse_coverage(text: str) -> dict:
    """Estimate how completely parse_tree() captured a `.tree.md`.

    Returns {'widget_lines', 'parsed_nodes', 'coverage'}. A widget_line is any
    line whose content (after optional [path] prefix) begins with a known
    widget token. `coverage = parsed_nodes / widget_lines` (clamped ≤ 1.0).

    Low coverage (< ~0.9) flags a capture in a dialect the parser handles
    poorly — currently the narrative Dialect C with unbracketed widget lines.
    This guards against the silent under-parse bug where only the root widget
    was captured (the regression that motivated this helper)."""
    ast = parse_tree(text)

    def _count(widgets) -> int:
        n = 0
        for w in widgets:
            n += 1
            n += _count(w.children)
            n += _count(w.true_branch)
            n += _count(w.false_branch)
        return n

    parsed_nodes = _count(ast.widgets)

    # Count widget-ish lines, but only inside the WIDGETS section.
    lines = text.splitlines()
    in_widgets = False
    widget_lines = 0
    for line in lines:
        if line.strip().startswith("--- WIDGETS"):
            in_widgets = True
            continue
        if not in_widgets:
            continue
        if _WIDGET_LINE_RE.match(line):
            widget_lines += 1

    coverage = 1.0 if widget_lines == 0 else min(1.0, parsed_nodes / widget_lines)
    return {"widget_lines": widget_lines, "parsed_nodes": parsed_nodes, "coverage": coverage}


def parse_tree_file(path: Path) -> ScreenAST:
    """Parse a `.tree.md` file into a ScreenAST. Raises ValueError if the file
    doesn't have the expected header structure."""
    text = path.read_text()
    return parse_tree(text)


def parse_tree(text: str) -> ScreenAST:
    """Parse the raw `.tree.md` content into a ScreenAST."""
    # Strip outer ``` fences if present
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    # Header parse
    i = 0
    ast = ScreenAST(name="<unknown>")

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("=== Screen:"):
            m = re.search(r"=== Screen:\s*(\S+)", line)
            if m:
                ast.name = m.group(1).rstrip(" =")
        elif line.startswith("Inputs:"):
            ast.inputs = _parse_params(line[len("Inputs:"):].strip())
        elif line.startswith("Locals:"):
            ast.locals = _parse_locals(line[len("Locals:"):].strip())
        elif line.startswith("Aggregates:"):
            ast.aggregates = _parse_aggregates(line[len("Aggregates:"):].strip())
        elif line.startswith("--- WIDGETS"):
            i += 1
            break  # widget tree begins on next line
        else:
            # Unknown header line — skip
            pass
        i += 1

    # Parse widgets — path-based hierarchy
    # Maintain a path → WidgetNode map; parent path is path[:last-dot]
    path_to_node: dict[str, WidgetNode] = {}
    pending_branch_for: Optional[WidgetNode] = None   # If we just saw [TRUE BRANCH ...], the next widgets go into true_branch
    pending_branch_type: Optional[str] = None         # "true" or "false"

    for raw_line in lines[i:]:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # Skip placeholder marker lines — Dialect A `PLACEHOLDER 'Header'`
        # (bare, no path) AND Dialect B `[Placeholder 'Content']` (bracketed,
        # no numeric path). Both are structural markers; the real child widgets
        # arrive with their own paths that carry placeholder shorthand segments
        # (H/M/S/C/I/L). Also detect explicit [TRUE/FALSE BRANCH] markers.
        stripped = line.strip()
        if (stripped.startswith("PLACEHOLDER ")
                or _BRACKET_PLACEHOLDER_RE.match(line)
                or stripped.startswith("[TRUE BRANCH")
                or stripped.startswith("[FALSE BRANCH")):
            continue

        m = _PATH_RE.match(line)
        if not m:
            continue  # unrecognized line — skip

        path, remainder = m.group(1), m.group(2)
        node = _parse_widget_header(path, remainder)
        if not node:
            continue

        # If pattern: lift the Condition. Normalized type is "If" (Dialect B
        # emits "IfWidget"; _parse_widget_header already normalizes it).
        if node.widget_type == "If":
            node.condition = node.properties.pop("Condition", None)

        # Attach to parent via nearest-ancestor lookup. Dialect B collapses
        # single-child containers, so the exact parent path (path minus last
        # segment) may not exist as a node — walk up until an ancestor is found.
        parent = _find_nearest_ancestor(path, path_to_node)
        if parent is not None:
            node.parent = parent
            if parent.widget_type == "If":
                # The segment immediately AFTER the If's own path decides the
                # branch: T → true_branch, F → false_branch, anything else →
                # children (shouldn't happen for a well-formed If).
                trailing = path[len(parent.path) + 1:] if path.startswith(parent.path + ".") else ""
                first_seg = trailing.split(".", 1)[0] if trailing else ""
                if first_seg == "T":
                    parent.true_branch.append(node)
                elif first_seg == "F":
                    parent.false_branch.append(node)
                else:
                    parent.children.append(node)
            else:
                parent.children.append(node)
        else:
            # Top-level widget
            ast.widgets.append(node)

        path_to_node[path] = node

    return ast


def _find_nearest_ancestor(
    path: str, path_to_node: dict[str, WidgetNode]
) -> Optional[WidgetNode]:
    """Walk up the dotted path, dropping trailing segments, until an existing
    node is found. Returns None if the path is top-level or no ancestor exists.

    Dialect B captures collapse single-child wrappers, leaving gaps in the
    path hierarchy (e.g. a node at `1.M.1.2.1` whose nominal parent `1.M.1.2`
    was never emitted). Nearest-ancestor attachment keeps such nodes in the
    tree under the closest real ancestor instead of orphaning them to the
    top level."""
    segments = path.split(".")
    for cut in range(len(segments) - 1, 0, -1):
        candidate = ".".join(segments[:cut])
        if candidate in path_to_node:
            return path_to_node[candidate]
    return None


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _parse_widget_header(path: str, remainder: str) -> Optional[WidgetNode]:
    """Parse the part after `[path]` — widget type, name, properties, events."""
    if not remainder.strip():
        return None
    m = _WIDGET_HEADER_RE.match(remainder)
    if not m:
        return None
    widget_type, name_quoted, name_unnamed, rest = m.groups()
    name = name_quoted if name_quoted else None  # (unnamed) → None

    # Normalize widget-type dialect variants. Dialect B writes "IfWidget";
    # downstream code (branch attribution, diff, chrome_wrap) keys on "If".
    widget_type = _WIDGET_TYPE_ALIASES.get(widget_type, widget_type)

    node = WidgetNode(path=path, widget_type=widget_type, name=name)

    # Properties
    for pm in _PROP_RE.finditer(rest):
        key, quoted_val, bare_val = pm.groups()
        val = quoted_val if quoted_val is not None else bare_val
        # Unescape simple escapes
        val = val.replace('\\"', '"')
        # Treat null/None/empty as missing
        if val in ("null", "None", ""):
            continue
        node.properties[key] = val

    # BlockInstance: lift the source-block reference to its own field.
    #   Dialect A: `SourceBlock="X"`   Dialect B: `Source=X` (bare)
    #   Dialect C: `'Name' (SourceName)` — source in parens right after the name
    if widget_type == "BlockInstance":
        if "SourceBlock" in node.properties:
            node.source_block = node.properties.pop("SourceBlock")
        elif "Source" in node.properties:
            node.source_block = node.properties.pop("Source")
        elif name_unnamed and name_unnamed.strip() != "unnamed":
            # `BlockInstance (WizardItem)` — unnamed form, source is the parens group
            node.source_block = name_unnamed.strip()
        else:
            # `BlockInstance 'Name' (SourceName) ...` — parens group leads `rest`
            paren_m = re.match(r"\(([\w]+)\)", rest)
            if paren_m:
                node.source_block = paren_m.group(1)

    # Events: scan rest for OnXxx→ or OnXxx= patterns
    for em in _EVENT_RE.finditer(rest):
        event_name, target = em.groups()
        node.events[event_name] = target.strip()

    return node


def _parent_path(path: str) -> Optional[str]:
    """For path '1.2.3' return '1.2'; for '1' return None."""
    if "." not in path:
        return None
    return path.rsplit(".", 1)[0]


def _find_last_if(path_to_node: dict[str, WidgetNode]) -> Optional[WidgetNode]:
    """Find the most-recently-added If widget. Used to attribute branch markers."""
    for node in reversed(list(path_to_node.values())):
        if node.widget_type.lower() == "if":
            return node
    return None


def _parse_params(line: str) -> list[ScreenParam]:
    """Parse 'Inputs:' line like 'TransactionId:Transaction Identifier (mandatory), RequestId:LoanRequest Identifier'."""
    if line in ("(none)", "<none>", ""):
        return []
    # Split on comma but respect parentheses (since type names like "User Identifier (mandatory)" contain spaces)
    items = _split_top_level(line, ",")
    params = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        # Pattern: Name:DataType [optional (mandatory)] [optional (extra info)]
        # First split on first colon
        if ":" not in item:
            continue
        name, rest = item.split(":", 1)
        name = name.strip()
        rest = rest.strip()
        # Detect (mandatory) suffix
        mandatory = False
        if "(mandatory)" in rest:
            mandatory = True
            rest = rest.replace("(mandatory)", "").strip()
        # Strip any trailing (...) annotations
        data_type = re.sub(r"\s*\(.*?\)\s*$", "", rest).strip()
        params.append(ScreenParam(name=name, data_type=data_type, mandatory=mandatory))
    return params


def _parse_locals(line: str) -> list[LocalVar]:
    """Parse 'Locals:' line like 'IsBootstrapStarted:Boolean (default=False), Other:Text'."""
    if line in ("(none)", "<none>", ""):
        return []
    items = _split_top_level(line, ",")
    locals_ = []
    for item in items:
        item = item.strip()
        if not item or ":" not in item:
            continue
        name, rest = item.split(":", 1)
        name = name.strip()
        rest = rest.strip()
        # Detect (default=...)
        default = None
        m = re.search(r"\(default=([^)]*)\)", rest)
        if m:
            default = m.group(1)
            rest = re.sub(r"\s*\(default=[^)]*\)\s*", "", rest).strip()
        # Detect =value syntax (e.g. "Integer=10")
        if "=" in rest and not default:
            type_str, default = rest.rsplit("=", 1)
            rest = type_str.strip()
            default = default.strip()
        data_type = re.sub(r"\s*\(.*?\)\s*$", "", rest).strip()
        locals_.append(LocalVar(name=name, data_type=data_type, default=default))
    return locals_


def _parse_aggregates(line: str) -> list[Aggregate]:
    """Parse 'Aggregates:' line like 'GetDataSettings (source=DataSettings), GetRegions (source=Region, sort=...)'."""
    if line in ("(none)", "<none>", ""):
        return []
    # Split on top-level commas only (parens inside count as nested)
    items = _split_top_level(line, ",", paren_aware=True)
    aggs = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        # Name + optional (args)
        m = re.match(r"(\w+)\s*(?:\((.*)\))?\s*$", item)
        if not m:
            continue
        name, args = m.group(1), (m.group(2) or "").strip()
        source = None
        sm = re.search(r"source=([^,)]+)", args)
        if sm:
            source = sm.group(1).strip()
        aggs.append(Aggregate(name=name, source=source, raw_args=args))
    return aggs


def _split_top_level(s: str, sep: str, paren_aware: bool = True) -> list[str]:
    """Split s on sep, respecting parentheses nesting if paren_aware."""
    if not paren_aware:
        return s.split(sep)
    out = []
    depth = 0
    buf = []
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


# ─── Diff (for T4.3 structural verification) ───────────────────────────────────

@dataclass
class Difference:
    """One author-visible difference between two ASTs."""
    path: str           # widget path where difference found, or "" for top-level
    kind: str           # "widget_type" | "name" | "property" | "source_block" | "child_count" | "condition" | "event"
    detail: str         # human-readable
    expected: str
    actual: str


# Properties that matter for structural identity. Other props (e.g. internal
# bookkeeping) are ignored for the diff.
SIGNIFICANT_PROPERTIES = {
    "Text", "Value", "Style", "CustomStyle", "Source", "Condition",
    "Visible", "Width", "List", "Labels", "Values", "Variable", "Image",
    "Type", "Enabled", "Mandatory",
}


def diff_screens(expected: ScreenAST, actual: ScreenAST) -> list[Difference]:
    """Compare two parsed screens. Returns the list of author-visible differences."""
    diffs: list[Difference] = []

    if expected.name != actual.name:
        diffs.append(Difference("", "screen_name", "Screen name", expected.name, actual.name))

    _diff_param_list(diffs, "inputs", expected.inputs, actual.inputs)
    _diff_local_list(diffs, "locals", expected.locals, actual.locals)
    _diff_aggregate_list(diffs, "aggregates", expected.aggregates, actual.aggregates)

    _diff_widget_lists(diffs, "", expected.widgets, actual.widgets)
    return diffs


def _diff_widget_lists(diffs, parent_path: str, expected: list[WidgetNode], actual: list[WidgetNode]):
    if len(expected) != len(actual):
        diffs.append(Difference(
            parent_path or "/", "child_count",
            f"child widget count differs at {parent_path or 'root'}",
            str(len(expected)), str(len(actual)),
        ))
    # Compare position-by-position (widget order matters for layout)
    for i, (e, a) in enumerate(zip(expected, actual)):
        _diff_widget(diffs, e, a)


def _diff_widget(diffs, e: WidgetNode, a: WidgetNode):
    path = e.path
    if e.widget_type != a.widget_type:
        diffs.append(Difference(path, "widget_type", "widget type", e.widget_type, a.widget_type))
        return  # different types — children comparison meaningless
    if e.name != a.name:
        diffs.append(Difference(path, "name", "widget name", e.name or "", a.name or ""))
    if e.source_block != a.source_block:
        diffs.append(Difference(path, "source_block", "BlockInstance source", e.source_block or "", a.source_block or ""))
    if e.condition != a.condition:
        diffs.append(Difference(path, "condition", "If condition", e.condition or "", a.condition or ""))

    # Properties — only the significant ones
    e_props = {k: v for k, v in e.properties.items() if k in SIGNIFICANT_PROPERTIES}
    a_props = {k: v for k, v in a.properties.items() if k in SIGNIFICANT_PROPERTIES}
    for k in set(e_props) | set(a_props):
        ev, av = e_props.get(k), a_props.get(k)
        if ev != av:
            diffs.append(Difference(path, "property", f"property {k}", ev or "(missing)", av or "(missing)"))

    # Events
    for k in set(e.events) | set(a.events):
        ev, av = e.events.get(k), a.events.get(k)
        if ev != av:
            diffs.append(Difference(path, "event", f"event {k}", ev or "(missing)", av or "(missing)"))

    # Children + branches
    _diff_widget_lists(diffs, path, e.children, a.children)
    if e.widget_type.lower() == "if":
        _diff_widget_lists(diffs, f"{path}.T", e.true_branch, a.true_branch)
        _diff_widget_lists(diffs, f"{path}.F", e.false_branch, a.false_branch)


def _diff_param_list(diffs, kind: str, e_list: list[ScreenParam], a_list: list[ScreenParam]):
    e_map = {p.name: p for p in e_list}
    a_map = {p.name: p for p in a_list}
    for name in set(e_map) | set(a_map):
        e_p, a_p = e_map.get(name), a_map.get(name)
        if not e_p:
            diffs.append(Difference(name, kind, f"{kind[:-1]} not in expected", "(missing)", repr(a_p)))
        elif not a_p:
            diffs.append(Difference(name, kind, f"{kind[:-1]} not in actual", repr(e_p), "(missing)"))
        elif e_p != a_p:
            diffs.append(Difference(name, kind, f"{kind[:-1]} {name} differs", repr(e_p), repr(a_p)))


def _diff_local_list(diffs, kind: str, e_list: list[LocalVar], a_list: list[LocalVar]):
    e_map = {p.name: p for p in e_list}
    a_map = {p.name: p for p in a_list}
    for name in set(e_map) | set(a_map):
        e_p, a_p = e_map.get(name), a_map.get(name)
        if not e_p:
            diffs.append(Difference(name, kind, f"{kind[:-1]} not in expected", "(missing)", repr(a_p)))
        elif not a_p:
            diffs.append(Difference(name, kind, f"{kind[:-1]} not in actual", repr(e_p), "(missing)"))
        elif e_p != a_p:
            diffs.append(Difference(name, kind, f"{kind[:-1]} {name} differs", repr(e_p), repr(a_p)))


def _diff_aggregate_list(diffs, kind: str, e_list: list[Aggregate], a_list: list[Aggregate]):
    e_map = {p.name: p for p in e_list}
    a_map = {p.name: p for p in a_list}
    for name in set(e_map) | set(a_map):
        e_p, a_p = e_map.get(name), a_map.get(name)
        if not e_p:
            diffs.append(Difference(name, kind, f"aggregate not in expected", "(missing)", repr(a_p)))
        elif not a_p:
            diffs.append(Difference(name, kind, f"aggregate not in actual", repr(e_p), "(missing)"))
        elif e_p.source != a_p.source:
            diffs.append(Difference(name, kind, f"aggregate {name} source", e_p.source or "", a_p.source or ""))
