"""harness-ingest — two-stage spec-document ingestion subsystem.

Stage A (deterministic): parse a markdown prose spec into a schema-valid
``app_spec.json`` draft (specVersion 0.2). Every extractor is crash-proof —
malformed or missing sections are skipped and noted in a ``ParseReport``, never
raised.

Stage B (semantic gap surfacing): run ``plan_gaps_from_spec`` on the draft to
build a worklist of unresolved semantic wiring (``boundTo``, ``action.does``,
``auth.provider``, nav edges). Emit a fill-prompt an orchestrator session
completes. The ingester never calls an LLM — Python structures, checks, and
surfaces; the CC session actuates.

CLI: harness-ingest <spec.md> --out <p> [--fidelity demo|production]
     [--emit-prompt] [--report] [--json]
Exit: 0 success; 1 production AND blocking gaps; 2 file missing or bad fidelity.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Preamble mirrored from prompt_recipes._PREAMBLE style ────────────────────
_INGEST_PREAMBLE = (
    "You are completing a DRAFT app_spec.json produced by harness-ingest from a prose "
    "spec document. The draft passes JSON-Schema validation but is missing semantic wiring "
    "(boundTo, action.does, auth.provider, nav edges). Fill in EXACTLY the gaps listed "
    "below — do NOT restructure or rename anything else. Emit the completed app_spec.json; "
    "re-run harness-verify --phase spec until clean."
)


# ── §3.1 Markdown primitives ─────────────────────────────────────────────────

@dataclass
class MarkdownTable:
    headers: list[str]
    rows: list[list[str]]  # each row padded/truncated to len(headers)

    def column(self, name: str) -> list[str]:
        """Return all values in the column whose header matches name (case-insensitive).
        Raises KeyError if the column is absent."""
        lower = name.lower()
        for i, h in enumerate(self.headers):
            if h.lower() == lower:
                return [r[i] for r in self.rows]
        raise KeyError(f"column {name!r} not in table headers {self.headers}")

    def has_columns(self, *names: str) -> bool:
        """Return True when all requested columns are present (case-insensitive)."""
        header_lower = {h.lower() for h in self.headers}
        return all(n.lower() in header_lower for n in names)


@dataclass
class Section:
    level: int          # count of leading '#'
    title: str
    lines: list[str]    # lines until the next heading of ANY level (flat)
    tables: list[MarkdownTable]


def parse_markdown_tables(text: str) -> list[MarkdownTable]:
    """Parse GFM pipe-tables from text. Never raises on malformed input."""
    tables: list[MarkdownTable] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # A table header row must contain at least one pipe and be non-empty.
        if "|" not in line:
            i += 1
            continue
        # The next line must be the separator row (cells of dashes/colons).
        if i + 1 >= len(lines):
            i += 1
            continue
        sep = lines[i + 1]
        if not re.match(r"^\s*\|?[\s\-:]+(\|[\s\-:]+)*\|?\s*$", sep):
            i += 1
            continue
        # Parse header cells.
        headers = _split_table_row(line)
        if not headers:
            i += 1
            continue
        # Collect body rows.
        rows: list[list[str]] = []
        j = i + 2
        while j < len(lines) and "|" in lines[j] and not re.match(
            r"^\s*\|?[\s\-:]+(\|[\s\-:]+)*\|?\s*$", lines[j]
        ):
            raw_row = _split_table_row(lines[j])
            # Pad short rows; truncate long rows.
            padded = (raw_row + [""] * len(headers))[: len(headers)]
            rows.append(padded)
            j += 1
        tables.append(MarkdownTable(headers=headers, rows=rows))
        i = j
    return tables


def _split_table_row(line: str) -> list[str]:
    """Split a pipe-table row into trimmed cell strings, preserving escaped pipes."""
    # Replace escaped pipes temporarily to avoid splitting on them.
    placeholder = "\x00PIPE\x00"
    line = line.replace(r"\|", placeholder)
    # Strip optional leading/trailing pipes.
    stripped = line.strip().lstrip("|").rstrip("|")
    cells = [c.replace(placeholder, "|").strip() for c in stripped.split("|")]
    return [c for c in cells if cells] if cells != [""] else []


def parse_sections(text: str) -> list[Section]:
    """Parse markdown ATX headings into a flat list of Section objects. Never raises."""
    if not text:
        return []
    sections: list[Section] = []
    current_level: int | None = None
    current_title: str = ""
    current_lines: list[str] = []

    heading_re = re.compile(r"^(#{1,6})\s+(.*)")

    def _flush() -> None:
        if current_level is None:
            return
        block = "\n".join(current_lines)
        sections.append(Section(
            level=current_level,
            title=current_title,
            lines=current_lines[:],
            tables=parse_markdown_tables(block),
        ))

    for line in text.splitlines():
        m = heading_re.match(line)
        if m:
            _flush()
            current_level = len(m.group(1))
            current_title = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    _flush()
    return sections


# ── §3.2 Type mapping ─────────────────────────────────────────────────────────

# FK regex — matches '<EntityName> Id' where name starts with an alpha character.
_FK_RE = re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9_ ]*?)\s+Id$")

# Literal type mapping table (case-insensitive keys).
_LITERAL_TYPE_MAP: dict[str, str] = {
    "text": "Text",
    "date time": "DateTime",
    "datetime": "DateTime",
    "date": "Date",
    "time": "Time",
    "boolean": "Boolean",
    "integer": "Integer",
    "long integer": "LongInteger",
    "longinteger": "LongInteger",
    "decimal": "Decimal",
    "currency": "Currency",
    "email": "Email",
    "phone number": "PhoneNumber",
    "phonenumber": "PhoneNumber",
}


def map_attribute_type(raw_type: str) -> tuple[str, str | None, bool]:
    """Map a raw spec type string to (odcDataType, references, isIdentifier).

    Resolution order (first match wins):
      1. Auto Number → Identifier, None, True
      2. Exact 'User Id' literal → Text, None, False (NOT an FK)
      3. FK '<Name> Id' pattern → Identifier, <Name>, False
      4. 'Text (unlimited)' / 'Text (N)' → Text, None, False
      5. Remaining literals in the mapping table → (mapped, None, False)
      6. Unmapped → Text (fallback), None, False
    """
    stripped = raw_type.strip()
    lower = stripped.lower()

    # 1. Auto Number
    if lower == "auto number":
        return ("Identifier", None, True)

    # 2. Exact 'User Id' literal
    if lower == "user id":
        return ("Text", None, False)

    # 3. FK pattern: '<Name> Id'
    fk_match = _FK_RE.fullmatch(stripped)
    if fk_match:
        return ("Identifier", fk_match.group("name").strip(), False)

    # 4. Text with length qualifier
    if lower.startswith("text ("):
        return ("Text", None, False)

    # 5. Literal table
    if lower in _LITERAL_TYPE_MAP:
        return (_LITERAL_TYPE_MAP[lower], None, False)

    # 6. Fallback
    return ("Text", None, False)


def parse_text_length(raw_type: str) -> int | None:
    """Extract the numeric length from 'Text (N)'. Returns None for 'unlimited' or non-Text."""
    m = re.match(r"text\s*\(\s*(\d+)\s*\)", raw_type.strip(), re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


# ── §3.4 ParseReport ─────────────────────────────────────────────────────────

@dataclass
class ParseReport:
    sections_seen: list[str] = field(default_factory=list)
    extracted: dict[str, int] = field(default_factory=dict)  # {kind: count}
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = ["=== ParseReport ==="]
        lines.append(f"Sections seen: {', '.join(self.sections_seen) or '(none)'}")
        lines.append(f"Extracted: " + (
            ", ".join(f"{k}={v}" for k, v in sorted(self.extracted.items())) or "(none)"))
        if self.skipped:
            lines.append("Skipped:")
            for s in self.skipped:
                lines.append(f"  - {s}")
        if self.notes:
            lines.append("Notes:")
            for n in self.notes:
                lines.append(f"  - {n}")
        return "\n".join(lines)


# ── §3.4 Stage A extractors ───────────────────────────────────────────────────

def _strip_emphasis(text: str) -> str:
    """Remove markdown bold/italic markers from a string."""
    return re.sub(r"\*+([^*]+)\*+", r"\1", text).strip()


def _truthy_cell(cell: str) -> bool:
    """Return True when a permissions-matrix cell represents a 'yes' value."""
    return cell.strip().lower() in {"yes", "y", "yes (own)", "x", "✓", "✔", "true"}


def extract_entities(sections: list[Section], report: ParseReport) -> list[dict]:
    """Extract DATABASE entities from sections under an 'Entities' heading.

    Each sub-section under 'Entities' with a table containing Attribute/Type
    columns becomes one entity. Rows missing Attribute or Type are skipped.
    Entities with zero valid attributes are dropped.
    """
    entities: list[dict] = []
    in_entities = False

    for sec in sections:
        title_lower = sec.title.lower()

        # Enter the Entities block on an 'Entities' heading (level ≤ 4).
        if title_lower == "entities" and sec.level <= 4:
            in_entities = True
            report.sections_seen.append(sec.title)
            continue

        # Stop on a sibling heading that is NOT a child of the Entities block.
        if in_entities and sec.level <= 4 and title_lower != "entities":
            # If we hit 'static entities' or another peer, stop entity extraction.
            if title_lower in {"static entities", "roles", "screens", "screen navigation",
                               "external integrations", "business rules", "workflows"}:
                break

        if not in_entities:
            continue

        # Each child section (level ≥ 4) under Entities is one entity.
        if sec.level >= 4 and sec.tables:
            entity_name = sec.title.strip()
            report.sections_seen.append(entity_name)

            # Find a table with Attribute and Type columns.
            attr_table: MarkdownTable | None = None
            for t in sec.tables:
                if t.has_columns("Attribute", "Type"):
                    attr_table = t
                    break

            if attr_table is None:
                report.skipped.append(f"entity '{entity_name}': no Attribute/Type table found")
                continue

            attributes: list[dict] = []
            for row in attr_table.rows:
                try:
                    attr_name_col = _col_index(attr_table, "Attribute")
                    type_col = _col_index(attr_table, "Type")
                    req_col = _col_index_optional(attr_table, "Required")
                    desc_col = _col_index_optional(attr_table, "Description")
                except KeyError:
                    report.notes.append(f"entity '{entity_name}': header lookup failed")
                    continue

                attr_name = row[attr_name_col].strip() if attr_name_col < len(row) else ""
                raw_type = row[type_col].strip() if type_col < len(row) else ""

                if not attr_name:
                    report.notes.append(f"entity '{entity_name}': row missing Attribute name — skipped")
                    continue
                if not raw_type:
                    report.notes.append(f"entity '{entity_name}': attr '{attr_name}' missing Type — skipped")
                    continue

                data_type, references, is_identifier = map_attribute_type(raw_type)
                if data_type == "Text" and not references and not is_identifier:
                    # Check for unmapped type (non-Text raw types that fell through).
                    if raw_type.lower() not in {
                        "text", "auto number", "user id", "boolean", "integer",
                        "long integer", "longinteger", "decimal", "currency",
                        "email", "phone number", "phonenumber", "date", "date time",
                        "datetime", "time",
                    } and not raw_type.lower().startswith("text ("):
                        fk_test = _FK_RE.fullmatch(raw_type.strip())
                        if not fk_test:
                            report.notes.append(
                                f"entity '{entity_name}': attr '{attr_name}' raw type {raw_type!r} "
                                f"unmapped — defaulted to Text"
                            )

                mandatory_raw = row[req_col].strip() if req_col is not None and req_col < len(row) else ""
                mandatory = mandatory_raw.lower() in {"yes", "y", "true"}

                attr: dict = {"name": attr_name, "dataType": data_type, "mandatory": mandatory}
                if is_identifier:
                    attr["isIdentifier"] = True
                if references:
                    attr["references"] = references
                if data_type == "Text":
                    length = parse_text_length(raw_type)
                    if length is not None:
                        attr["length"] = length
                if desc_col is not None and desc_col < len(row):
                    desc = row[desc_col].strip()
                    if desc:
                        attr["description"] = desc

                attributes.append(attr)

            if not attributes:
                report.skipped.append(
                    f"entity '{entity_name}': 0 valid attributes — entity dropped (minItems 1 required)"
                )
                continue

            entities.append({"name": entity_name, "attributes": attributes})
            report.extracted["entities"] = report.extracted.get("entities", 0) + 1

    return entities


def _col_index(table: MarkdownTable, name: str) -> int:
    lower = name.lower()
    for i, h in enumerate(table.headers):
        if h.lower() == lower:
            return i
    raise KeyError(name)


def _col_index_optional(table: MarkdownTable, name: str) -> int | None:
    lower = name.lower()
    for i, h in enumerate(table.headers):
        if h.lower() == lower:
            return i
    return None


def extract_static_entities(sections: list[Section], report: ParseReport) -> list[dict]:
    """Extract STATIC entities from sections under a 'Static Entities' heading.

    Each sub-section under 'Static Entities' with a Record/Label table becomes a
    static entity. Rows with blank Record are skipped. The synthesized attributes
    are: Id (Identifier, PK), Label (Text), and Order (Integer) when that column
    is present.
    """
    static_entities: list[dict] = []
    in_static = False

    for sec in sections:
        title_lower = sec.title.lower()

        if title_lower == "static entities" and sec.level <= 4:
            in_static = True
            report.sections_seen.append(sec.title)
            continue

        if in_static and sec.level <= 4 and title_lower not in {"static entities"}:
            if title_lower in {"roles", "screens", "screen navigation",
                               "external integrations", "business rules", "workflows",
                               "entities"}:
                break

        if not in_static:
            continue

        if sec.level >= 4 and sec.tables:
            entity_name = sec.title.strip()
            report.sections_seen.append(entity_name)

            record_table: MarkdownTable | None = None
            for t in sec.tables:
                if t.has_columns("Record", "Label"):
                    record_table = t
                    break

            if record_table is None:
                report.skipped.append(f"static entity '{entity_name}': no Record/Label table")
                continue

            has_order = record_table.has_columns("Order")
            record_col = _col_index(record_table, "Record")
            label_col = _col_index(record_table, "Label")
            order_col = _col_index_optional(record_table, "Order") if has_order else None
            desc_col = _col_index_optional(record_table, "Description")

            # Synthesize standard attributes for the static entity.
            attributes: list[dict] = [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "Label", "dataType": "Text", "mandatory": True},
            ]
            if has_order:
                attributes.append({"name": "Order", "dataType": "Integer"})

            records: list[dict] = []
            for row in record_table.rows:
                record_val = row[record_col].strip() if record_col < len(row) else ""
                if not record_val:
                    report.notes.append(f"static entity '{entity_name}': blank Record — row skipped")
                    continue

                label_val = row[label_col].strip() if label_col < len(row) else ""
                record_obj: dict = {"Record": record_val, "Label": label_val}

                if order_col is not None and order_col < len(row):
                    raw_order = row[order_col].strip()
                    if raw_order:
                        try:
                            record_obj["Order"] = int(raw_order)
                        except ValueError:
                            record_obj["Order"] = raw_order  # keep raw + note
                            report.notes.append(
                                f"static entity '{entity_name}': Order {raw_order!r} not an integer — kept raw"
                            )

                if desc_col is not None and desc_col < len(row):
                    desc = row[desc_col].strip()
                    if desc:
                        record_obj["Description"] = desc

                records.append(record_obj)

            entity: dict = {
                "name": entity_name,
                "isStatic": True,
                "attributes": attributes,
                "records": records,
            }
            static_entities.append(entity)
            report.extracted["static_entities"] = report.extracted.get("static_entities", 0) + 1

    return static_entities


def extract_roles(
    sections: list[Section], report: ParseReport
) -> tuple[list[str], list[dict]]:
    """Extract roles from 'Role Definitions' and 'Permissions Matrix' sections.

    Returns (roles_list, permissions_list). Bold markers are stripped from role
    names. permissions_list contains {action, roles:[...]} entries. Returns
    ([], []) when no tables are found.
    """
    roles: list[str] = []
    permissions: list[dict] = []
    found_role_table = False

    for sec in sections:
        title_lower = sec.title.lower()

        if title_lower in {"role definitions", "roles"} and sec.tables:
            for t in sec.tables:
                if t.has_columns("Role"):
                    try:
                        role_col = _col_index(t, "Role")
                    except KeyError:
                        continue
                    for row in t.rows:
                        raw = row[role_col].strip() if role_col < len(row) else ""
                        cleaned = _strip_emphasis(raw)
                        if cleaned and cleaned not in roles:
                            roles.append(cleaned)
                    found_role_table = True
                    report.sections_seen.append(sec.title)

        elif title_lower == "permissions matrix" and sec.tables:
            for t in sec.tables:
                if not t.headers or len(t.headers) < 2:
                    continue
                # First column = action; remaining columns = roles.
                role_headers = [_strip_emphasis(h) for h in t.headers[1:]]
                action_col = 0
                try:
                    action_col = _col_index(t, "Action")
                except KeyError:
                    pass  # use column 0 as fallback

                for row in t.rows:
                    action_name = row[action_col].strip() if action_col < len(row) else ""
                    if not action_name:
                        continue
                    truthy_roles = []
                    for i, rh in enumerate(role_headers, start=1):
                        cell = row[i].strip() if i < len(row) else ""
                        if _truthy_cell(cell):
                            truthy_roles.append(rh)
                    permissions.append({"action": action_name, "roles": truthy_roles})

                report.sections_seen.append(sec.title)
                found_role_table = True

    if not found_role_table:
        report.notes.append("No role definition table found; app.roles will default to ['User']")

    return roles, permissions


def infer_component_type(input_type_cell: str) -> str:
    """Infer an ODC component type from the 'Input Type' cell of a Data Table row.

    Case-insensitive substring matching, first match wins. The precedence order
    is load-bearing: 'date' is checked before 'picker' so 'Date picker' maps
    to DatePicker rather than Dropdown.
    """
    lower = input_type_cell.lower()
    # Date-related inputs before generic 'picker' (which maps to Dropdown).
    if "date" in lower:
        return "DatePicker"
    if any(k in lower for k in ("dropdown", "radio")):
        return "Dropdown"
    # 'picker' without 'date' (e.g. 'User picker') -> Dropdown.
    if "picker" in lower:
        return "Dropdown"
    if any(k in lower for k in ("checkbox", "boolean")):
        return "Checkbox"
    if any(k in lower for k in ("read-only", "badge", "label")):
        return "Label"
    if "button" in lower:
        return "Button"
    return "Input"


def synthesize_acceptance(components: list[dict], bound_entity: str | None = None) -> dict:
    """Synthesize a minimal acceptance block that satisfies minItems 1.

    When bound_entity is supplied, emits an entityExists assertion. Otherwise
    emits a componentPresent assertion on the first component (or a placeholder).
    """
    if bound_entity:
        return {"assertions": [{"kind": "entityExists", "entity": bound_entity}]}
    if components:
        return {"assertions": [{"kind": "componentPresent", "componentId": components[0]["id"]}]}
    return {"assertions": [{"kind": "componentPresent", "componentId": "placeholder"}]}


def _slug_id(title: str) -> str:
    """Convert a section title into a camelCase-ish stable screen id.

    Keeps the first token as CamelCase; joining words are lowercased then rejoined.
    For simple titles this produces the CamelCase-preserving id the plan expects.
    """
    # Remove non-alphanumeric characters and split.
    tokens = re.sub(r"[^A-Za-z0-9 ]", "", title).split()
    if not tokens:
        return "screen"
    # Join preserving original casing but stripping spaces.
    return "".join(tokens)


def extract_screens(sections: list[Section], report: ParseReport) -> list[dict]:
    """Extract screen definitions from sections whose children contain 'Data Table'/'Actions'.

    Because ``parse_sections`` produces a flat list, a screen section (e.g. level 4)
    may have no direct tables — its sub-sections (level 5 'Data Table', 'Actions')
    carry the tables. This extractor handles both cases:
      - A section that directly owns a Field+InputType table.
      - A section (candidate) whose immediately-following deeper sections are named
        'Data Table' or 'Actions' (a common prose-spec pattern).

    The 'Input Type' cell drives ``infer_component_type``. The ``does`` field is
    intentionally OMITTED from actions — Stage B flags the write-path gap.
    A minimal ``acceptance`` block is synthesized so the draft passes schema
    validation (minItems 1).
    """
    screens: list[dict] = []

    # Non-screen section titles to skip even if they have tables.
    _NON_SCREEN = {
        "data model", "entities", "static entities", "roles", "role definitions",
        "permissions matrix", "screen navigation", "external integrations",
        "business rules", "workflows", "non-functional requirements",
        "transition rules", "data table", "actions", "display elements",
        "navigation", "screen design", "action visibility table",
        "edit access rules", "notification details",
    }

    n = len(sections)
    i = 0
    while i < n:
        sec = sections[i]
        title = sec.title.strip()
        title_lower = title.lower()

        # Skip sections that are clearly not screens.
        if title_lower in _NON_SCREEN or sec.level < 3:
            i += 1
            continue

        # Strategy 1: The section directly owns a Data Table (Field + Input Type).
        data_table: MarkdownTable | None = None
        actions_table: MarkdownTable | None = None
        for t in sec.tables:
            if data_table is None and t.has_columns("Field", "Input Type"):
                data_table = t
            elif actions_table is None and t.has_columns("Action"):
                actions_table = t

        # Strategy 2: Scan immediately-following deeper sections for 'Data Table'/'Actions'.
        # These child sections must be at a deeper level than the candidate screen section.
        child_idx = i + 1
        while child_idx < n and sections[child_idx].level > sec.level:
            child = sections[child_idx]
            child_title_lower = child.title.strip().lower()
            if child_title_lower == "data table" and data_table is None:
                for t in child.tables:
                    if t.has_columns("Field", "Input Type") or t.has_columns("Field", "Label"):
                        data_table = t
                        break
            elif child_title_lower == "actions" and actions_table is None:
                for t in child.tables:
                    if t.has_columns("Action"):
                        actions_table = t
                        break
            child_idx += 1

        if data_table is None and actions_table is None:
            i += 1
            continue

        screen_id = _slug_id(title)
        components: list[dict] = []

        if data_table is not None:
            try:
                field_col = _col_index(data_table, "Field")
            except KeyError:
                field_col = 0

            input_type_col = _col_index_optional(data_table, "Input Type")

            for row in data_table.rows:
                field_name = row[field_col].strip() if field_col < len(row) else ""
                if not field_name:
                    continue
                raw_input_type = ""
                if input_type_col is not None and input_type_col < len(row):
                    raw_input_type = row[input_type_col].strip()
                comp_type = infer_component_type(raw_input_type) if raw_input_type else "Input"
                components.append({"id": field_name, "type": comp_type})

        if not components:
            # No data table fields — synthesize a placeholder Container.
            components = [{"id": "placeholder", "type": "Container"}]
            report.notes.append(f"screen '{title}': no Data Table found — placeholder Container added")

        actions: list[dict] = []
        if actions_table is not None:
            action_col = _col_index_optional(actions_table, "Action")
            if action_col is None:
                action_col = 0
            first_comp_id = components[0]["id"] if components else "primaryBtn"
            for row in actions_table.rows:
                action_name = row[action_col].strip() if action_col < len(row) else ""
                if not action_name:
                    continue
                # 'does' is intentionally omitted — Stage B flags the write-path gap.
                actions.append({
                    "name": action_name,
                    "trigger": {
                        "onComponent": first_comp_id,
                        "event": "onClick",
                    },
                })

        screen: dict = {
            "id": screen_id,
            "name": title,
            "route": f"/{screen_id}",
            "components": components,
            "acceptance": synthesize_acceptance(components),
        }
        if actions:
            screen["actions"] = actions

        screens.append(screen)
        report.extracted["screens"] = report.extracted.get("screens", 0) + 1
        report.sections_seen.append(title)

        # Skip over the child sections we already consumed.
        i = child_idx

    return screens


def extract_integrations(
    sections: list[Section], report: ParseReport
) -> tuple[list[dict], list[dict]]:
    """Extract integration and logic units from prose sections.

    Scans the 'External Integrations' section and any 'Business Rules' / appendix
    sections for SAP/REST/API keywords (-> RestApi consume) and Excel/batch/import
    keywords (-> excelImport logic unit). This extractor is inherently lower-fidelity
    than table-based extraction — many specs express these in prose.
    """
    integrations: list[dict] = []
    logic_units: list[dict] = []

    # Keywords that signal a REST/SAP integration.
    rest_keywords = {"sap", "rest", "api", "soap", "odbc", "web service", "endpoint"}
    # Keywords that signal an Excel/batch import logic unit.
    excel_keywords = {"excel", "csv", "spreadsheet", "batch import", "file import", "bulk import"}

    # Integration names already added (deduplicate).
    seen_integration_names: set[str] = set()
    seen_logic_names: set[str] = set()

    for sec in sections:
        title_lower = sec.title.lower()
        # Scan relevant sections.
        if not any(k in title_lower for k in {
            "integration", "business rule", "appendix", "external", "import",
            "agent", "file", "batch",
        }):
            continue

        body = "\n".join(sec.lines).lower()

        for keyword in rest_keywords:
            if keyword in body:
                # Derive a name from the keyword or section title.
                name = sec.title.replace(" ", "").title() + "Integration"
                if name in seen_integration_names:
                    continue
                integrations.append({
                    "name": name,
                    "kind": "RestApi",
                    "direction": "consume",
                    "description": f"Integration detected from section '{sec.title}' (keyword: {keyword})",
                })
                seen_integration_names.add(name)
                report.notes.append(f"integration '{name}' inferred from keyword '{keyword}' in '{sec.title}'")
                break  # one integration per section

        for keyword in excel_keywords:
            if keyword in body:
                name = "ImportRows"
                if name in seen_logic_names:
                    continue
                # Try to infer a target entity from the prose.
                logic_units.append({
                    "kind": "excelImport",
                    "name": name,
                    "description": f"Bulk import logic detected from section '{sec.title}' (keyword: {keyword})",
                })
                seen_logic_names.add(name)
                report.notes.append(f"excelImport '{name}' inferred from keyword '{keyword}' in '{sec.title}'")
                break

    if not integrations and not logic_units:
        report.notes.append("No integration or import keywords found in spec sections")

    report.extracted["integrations"] = len(integrations)
    report.extracted["logic_units"] = len(logic_units)
    return integrations, logic_units


def extract_workflow_note(sections: list[Section], report: ParseReport) -> str | None:
    """Extract a workflow summary note from a 'Transition rules' table or 'Workflows' heading.

    Returns a one-line summary string, or None when absent. Crucially, this does
    NOT synthesize a BPT process — workflow becomes a report note only.
    """
    for sec in sections:
        title_lower = sec.title.lower()

        if "workflow" in title_lower:
            note = f"Workflow section '{sec.title}' detected — review manually for BPT authoring."
            report.notes.append(note)
            return note

        # Scan for 'Transition rules' tables in any section.
        for t in sec.tables:
            if t.has_columns("From", "To"):
                transitions = len(t.rows)
                note = (
                    f"State-transition table found in '{sec.title}' "
                    f"({transitions} transition(s)); no BPT process synthesized — "
                    f"review 'Workflows' heading for business process requirements."
                )
                report.notes.append(note)
                return note

    return None


# ── §3.5 Stage A assembly ─────────────────────────────────────────────────────

def _extract_app_name(sections: list[Section], raw_text: str) -> str:
    """Extract the application name from a **Application**: line or H1 heading.

    The **Application**: line (if present) gives a cleaner name than the H1
    which may include subtitles.
    """
    # Prefer the **Application**: pattern first (cleaner than H1 subtitles).
    m = re.search(r"\*\*Application\*\*\s*:\s*(.+)", raw_text)
    if m:
        return m.group(1).strip()

    # Fallback: use the H1 heading.
    for sec in sections:
        if sec.level == 1:
            return sec.title.strip()

    return "IngestedApp"


def build_draft_spec(markdown: str, report: ParseReport | None = None) -> dict:
    """Stage A: parse markdown spec into a schema-valid draft (specVersion 0.2).

    Never raises on bad markdown — malformed sections are skipped and noted in
    the report. The returned dict always passes ``harness.verify._schema_findings``.
    """
    if report is None:
        report = ParseReport()

    if not markdown or not markdown.strip():
        # Minimal valid skeleton for empty input.
        report.notes.append("Empty markdown input — returning minimal skeleton")
        return {
            "specVersion": "0.2",
            "app": {"name": "IngestedApp", "roles": ["User"]},
            "dataModel": {"entities": []},
            "screens": [],
        }

    sections = parse_sections(markdown)

    app_name = _extract_app_name(sections, markdown)
    roles, permissions = extract_roles(sections, report)
    if not roles:
        roles = ["User"]
        report.notes.append("No roles extracted; defaulting to ['User']")

    entities = extract_entities(sections, report)
    static_entities = extract_static_entities(sections, report)
    screens = extract_screens(sections, report)
    integrations, logic_units = extract_integrations(sections, report)
    workflow_note = extract_workflow_note(sections, report)

    if workflow_note:
        report.notes.append(f"Workflow: {workflow_note}")

    # Permissions are recorded as a note — no schema field.
    if permissions:
        report.notes.append(
            f"Permissions matrix: {len(permissions)} action(s) extracted "
            f"(no schema field; carry into Stage B wiring)."
        )

    draft: dict = {
        "specVersion": "0.2",
        "app": {
            "name": app_name,
            "roles": roles,
        },
        "dataModel": {
            "entities": entities + static_entities,
        },
        "screens": screens,
    }

    # Optional blocks: omit when empty (keeps the draft minimal).
    if integrations:
        draft["integrations"] = integrations
    if logic_units:
        draft["logic"] = logic_units

    return draft


# ── §3.6 Stage B — gaps + fill-prompt ────────────────────────────────────────

_INTEGRATION_DETAIL_RE = re.compile(r"integration '([^']+)'")


def _integration_name_from_detail(detail: str) -> str | None:
    """Extract the integration name from a rest-consume gap's detail field
    (shape: "integration '<name>'"). Returns None when no name is present."""
    match = _INTEGRATION_DETAIL_RE.search(detail or "")
    return match.group(1) if match else None


def plan_gaps_with_fidelity(spec: dict, fidelity: str = "demo") -> list[dict]:
    """Call plan_gaps_from_spec unmodified and annotate each gap with blocking:bool.

    In 'demo' mode all gaps are blocking=False. In 'production' mode two gap
    classes flip to blocking=True:
      1. capability=='auth:app-local'
      2. capability=='rest-consume' AND the matching integration has no auth set
         (None, empty, or 'None' — unhardened).

    Raises ValueError for an unrecognized fidelity string.
    """
    if fidelity not in {"demo", "production"}:
        raise ValueError(f"fidelity must be 'demo' or 'production', got {fidelity!r}")

    # Import here to keep Stage A import-free from harness.prompt_recipes.
    from harness.prompt_recipes import plan_gaps_from_spec  # noqa: PLC0415

    raw_gaps = plan_gaps_from_spec(spec)
    result: list[dict] = []

    # Build a quick lookup of integration auth values for the rest-consume check.
    integration_auth: dict[str, str | None] = {}
    for integ in spec.get("integrations", []) or []:
        name = integ.get("name", "")
        integration_auth[name] = integ.get("auth") or None

    for gap in raw_gaps:
        annotated = copy.deepcopy(gap)

        if fidelity == "production":
            capability = gap.get("capability", "")
            if capability == "auth:app-local":
                annotated["blocking"] = True
            elif capability == "rest-consume":
                # Correlate THIS gap to its own integration (the gap detail is
                # "integration '<name>'") and block only when that integration is
                # unhardened — a hardened sibling must not be flagged. When no name
                # resolves, default to unhardened (fail closed).
                name = _integration_name_from_detail(gap.get("detail", ""))
                if name is not None and name in integration_auth:
                    annotated["blocking"] = integration_auth[name] in (None, "", "None")
                else:
                    annotated["blocking"] = True
            else:
                annotated["blocking"] = False
        else:
            annotated["blocking"] = False

        result.append(annotated)

    return result


def blocking_gaps(gaps: list[dict]) -> list[dict]:
    """Return only the gaps where blocking is True."""
    return [g for g in gaps if g.get("blocking") is True]


def render_fill_prompt(spec: dict, gaps: list[dict], report: ParseReport) -> str:
    """Render a fill-prompt the orchestrator feeds to a CC session to complete the draft.

    Pure string; no MCP/LLM calls. Mirrors _INGEST_PREAMBLE style.
    """
    app_name = spec.get("app", {}).get("name", "?")
    entity_count = len(spec.get("dataModel", {}).get("entities", []))
    screen_count = len(spec.get("screens", []))
    gap_count = len(gaps)
    blocking_count = len(blocking_gaps(gaps))

    header = (
        f"{_INGEST_PREAMBLE}\n\n"
        f"SPEC: {app_name}, {entity_count} entities, {screen_count} screens, "
        f"{gap_count} gap(s), {blocking_count} blocking.\n"
    )

    # Group gaps: blocking first, then by kind.
    sorted_gaps = sorted(gaps, key=lambda g: (0 if g.get("blocking") else 1, g.get("kind", "")))

    gap_lines = ["\n=== GAP WORKLIST ==="]
    for g in sorted_gaps:
        blocking_marker = " [BLOCKING]" if g.get("blocking") else ""
        gap_lines.append(
            f"• [{g.get('capability', '?')}]{blocking_marker} {g.get('detail', '')}\n"
            f"  at {g.get('where', '?')}  →  {g.get('resolution', '')}"
        )

    # Include any workflow note from the report.
    workflow_notes = [n for n in report.notes if n.lower().startswith("workflow")]
    if workflow_notes:
        gap_lines.append("\n=== WORKFLOW NOTE ===")
        for note in workflow_notes:
            gap_lines.append(f"  {note}")

    gap_lines.append(
        "\n=== NEXT STEP ===\n"
        "Fill the gaps above. Emit the completed app_spec.json; "
        "re-run harness-verify --phase spec until clean."
    )

    return header + "\n".join(gap_lines)


@dataclass
class IngestResult:
    spec: dict
    report: ParseReport
    gaps: list[dict]
    fill_prompt: str
    fidelity: str

    def blocking(self) -> list[dict]:
        """Return the subset of gaps that are blocking."""
        return blocking_gaps(self.gaps)


def ingest(markdown: str, fidelity: str = "demo") -> IngestResult:
    """Run Stage A then Stage B and return an IngestResult.

    Never raises on bad markdown (returns a minimal-skeleton result). Raises
    ValueError only on a bad fidelity string.
    """
    report = ParseReport()
    draft = build_draft_spec(markdown, report)
    gaps = plan_gaps_with_fidelity(draft, fidelity)
    prompt = render_fill_prompt(draft, gaps, report)
    return IngestResult(
        spec=draft,
        report=report,
        gaps=gaps,
        fill_prompt=prompt,
        fidelity=fidelity,
    )


# ── §3.7 CLI ─────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """Entry point for harness-ingest."""
    ap = argparse.ArgumentParser(
        prog="harness-ingest",
        description="Ingest a markdown app spec into a schema-valid app_spec.json draft.",
    )
    ap.add_argument("spec", type=Path, help="Path to the spec markdown file.")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write the draft JSON to this path (dry-preview when omitted).")
    ap.add_argument("--fidelity", choices=["demo", "production"], default="demo",
                    help="Gap fidelity mode (default: demo; production flags blocking gaps).")
    ap.add_argument("--emit-prompt", action="store_true",
                    help="Also print the fill-prompt for the orchestrator.")
    ap.add_argument("--report", action="store_true",
                    help="Also print the gap worklist and ParseReport.")
    ap.add_argument("--json", action="store_true",
                    help="Print {spec,report,gaps,fill_prompt,fidelity} as JSON.")
    args = ap.parse_args(argv)

    try:
        markdown = args.spec.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as e:
        print(f"harness-ingest: cannot read spec: {e}", file=sys.stderr)
        return 2

    try:
        result = ingest(markdown, fidelity=args.fidelity)
    except ValueError as e:
        print(f"harness-ingest: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "spec": result.spec,
            "report": {
                "sections_seen": result.report.sections_seen,
                "extracted": result.report.extracted,
                "skipped": result.report.skipped,
                "notes": result.report.notes,
            },
            "gaps": result.gaps,
            "fill_prompt": result.fill_prompt,
            "fidelity": result.fidelity,
        }, indent=2))
        return 1 if (args.fidelity == "production" and result.blocking()) else 0

    # Write the draft.
    if args.out is not None:
        args.out.write_text(json.dumps(result.spec, indent=2) + "\n", encoding="utf-8")

    # Summary line.
    app_name = result.spec.get("app", {}).get("name", "?")
    entity_count = len(result.spec.get("dataModel", {}).get("entities", []))
    screen_count = len(result.spec.get("screens", []))
    gap_count = len(result.gaps)
    block_count = len(result.blocking())
    print(
        f"harness-ingest: {app_name!r} — {entity_count} entities, {screen_count} screens, "
        f"{gap_count} gap(s), {block_count} blocking [{args.fidelity}]"
    )

    if args.report:
        print("\n=== GAP WORKLIST ===")
        for g in result.gaps:
            blocking_marker = " [BLOCKING]" if g.get("blocking") else ""
            print(f"  [{g.get('capability')}]{blocking_marker} {g.get('detail')}")
            print(f"    at {g.get('where')}  →  {g.get('resolution')}")
        print()
        print(result.report.render())

    if args.emit_prompt:
        print()
        print(result.fill_prompt)

    if args.fidelity == "production" and result.blocking():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
