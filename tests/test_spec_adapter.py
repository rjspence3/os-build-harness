"""Tests for the app_spec -> renderer-dataclass adapter (entity layer, increment 1).

Feeds examples/task_tracker/app_spec.json through `spec_adapter` + the existing
recipe.py renderers and asserts the mapping is faithful and the rendered batch is
non-empty valid authoring text.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.banking_runner.recipe import (
    render_attribute_line,
    render_server_entity,
    topologically_order_server_entities,
)
from harness.banking_runner.spec_adapter import (
    SPEC_TO_ODC_DATATYPE,
    collect_spec_gaps,
    render_spec_entities,
    spec_to_entities,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TASK_TRACKER_SPEC = REPO_ROOT / "examples" / "task_tracker" / "app_spec.json"


@pytest.fixture
def spec() -> dict:
    return json.loads(TASK_TRACKER_SPEC.read_text())


# ─── structural mapping ─────────────────────────────────────────────────────────

def test_both_entities_present(spec):
    manifest = spec_to_entities(spec)
    names = {e.name for e in manifest.server_entities}
    assert names == {"TaskList", "Task"}
    # Neither is static.
    assert manifest.static_entities == []


def test_tasklist_title_is_text(spec):
    manifest = spec_to_entities(spec)
    task_list = next(e for e in manifest.server_entities if e.name == "TaskList")
    title = next(a for a in task_list.attributes if a.name == "Title")
    assert title.data_type == "Text"
    assert title.length == 100
    assert title.is_mandatory is True


def test_task_isdone_is_boolean(spec):
    manifest = spec_to_entities(spec)
    task = next(e for e in manifest.server_entities if e.name == "Task")
    is_done = next(a for a in task.attributes if a.name == "IsDone")
    assert is_done.data_type == "Boolean"
    assert is_done.is_mandatory is True


def test_pk_identifier_consumed_not_a_column(spec):
    manifest = spec_to_entities(spec)
    task = next(e for e in manifest.server_entities if e.name == "Task")
    # The isIdentifier "Id" attribute becomes the PK, not a rendered column.
    assert task.pk_name == "Id"
    assert task.pk_data_type == "Long Integer"
    assert task.pk_is_auto_number is True
    assert "Id" not in {a.name for a in task.attributes}


def test_reference_becomes_fk_identifier_attribute(spec):
    manifest = spec_to_entities(spec)
    task = next(e for e in manifest.server_entities if e.name == "Task")
    list_id = next(a for a in task.attributes if a.name == "ListId")
    # app_spec references="TaskList" -> ODC space-form FK dataType.
    assert list_id.data_type == "TaskList Identifier"
    assert list_id.is_mandatory is True


# ─── topological ordering ───────────────────────────────────────────────────────

def test_server_entities_fk_topologically_ordered(spec):
    manifest = spec_to_entities(spec)
    ordered = topologically_order_server_entities(manifest.server_entities)
    names = [e.name for e in ordered]
    # Task references TaskList -> referenced entity authored first.
    assert names.index("TaskList") < names.index("Task")


# ─── rendered batch text ────────────────────────────────────────────────────────

def test_fk_attribute_renders_as_identfk_line(spec):
    manifest = spec_to_entities(spec)
    task = next(e for e in manifest.server_entities if e.name == "Task")
    list_id = next(a for a in task.attributes if a.name == "ListId")
    # taskListEntity = _camel("TaskList") + "Entity"
    line = render_attribute_line(list_id, {"TaskList": "taskListEntity"})
    assert line == 'AddIdentFk(e, "ListId", taskListEntity?.IdentifierType, true);'


def test_render_spec_entities_nonempty_valid_batch(spec):
    batch = render_spec_entities(spec)
    assert batch.strip()
    # Valid authoring batch text: contains a csharp fence and the Model API root.
    assert "```csharp" in batch
    assert "eSpace" in batch


def test_rendered_task_entity_contains_mapped_attributes(spec):
    manifest = spec_to_entities(spec)
    local_server = {e.name for e in manifest.server_entities}
    task = next(e for e in manifest.server_entities if e.name == "Task")
    prompt = render_server_entity(task, local_server, set())
    assert 'AddText(e, "Title", 200, true);' in prompt
    # IsDone is mandatory:true in the spec — Boolean/Integer/Binary now propagate
    # mandatory (was dropped; caught by live harness-verify on the built app).
    assert 'AddBool(e, "IsDone", true);' in prompt
    assert 'AddIdentFk(e, "ListId", taskListEntity?.IdentifierType, true);' in prompt
    # FK target is a local server entity -> resolved via IServerEntity lookup.
    assert 'Named("TaskList")' in prompt


def test_rendered_tasklist_entity_title_length(spec):
    manifest = spec_to_entities(spec)
    local_server = {e.name for e in manifest.server_entities}
    task_list = next(e for e in manifest.server_entities if e.name == "TaskList")
    prompt = render_server_entity(task_list, local_server, set())
    assert 'AddText(e, "Title", 100, true);' in prompt


# ─── gaps (honesty) ─────────────────────────────────────────────────────────────

def test_task_tracker_has_no_mapping_gaps(spec):
    assert collect_spec_gaps(spec) == []


def test_datatype_map_covers_enum_minus_special_cases():
    # Identifier + Time are the two enum members with no direct column mapping.
    assert "Identifier" not in SPEC_TO_ODC_DATATYPE
    assert "Time" not in SPEC_TO_ODC_DATATYPE
    assert SPEC_TO_ODC_DATATYPE["LongInteger"] == "Long Integer"
    assert SPEC_TO_ODC_DATATYPE["DateTime"] == "Date Time"
    assert SPEC_TO_ODC_DATATYPE["PhoneNumber"] == "Phone Number"


def test_time_datatype_flagged_as_gap():
    synthetic = {
        "app": {"name": "t", "roles": ["R"]},
        "dataModel": {
            "entities": [
                {
                    "name": "Event",
                    "attributes": [
                        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                        {"name": "StartsAt", "dataType": "Time", "mandatory": True},
                    ],
                }
            ]
        },
    }
    gaps = collect_spec_gaps(synthetic)
    assert any("Time" in g for g in gaps)


def test_static_entity_maps_with_records():
    synthetic = {
        "app": {"name": "t", "roles": ["R"]},
        "dataModel": {
            "entities": [
                {
                    "name": "Priority",
                    "isStatic": True,
                    "attributes": [
                        {"name": "Id", "dataType": "Integer", "isIdentifier": True, "mandatory": True},
                        {"name": "Label", "dataType": "Text", "mandatory": True},
                    ],
                    "records": [
                        {"Label": "Low"},
                        {"Label": "High"},
                    ],
                }
            ]
        },
    }
    manifest = spec_to_entities(synthetic)
    assert len(manifest.static_entities) == 1
    priority = manifest.static_entities[0]
    assert priority.pk_name == "Id"
    assert priority.pk_data_type == "Integer"
    assert priority.records == ["Low", "High"]


def test_manytoone_relationship_synthesizes_fk():
    synthetic = {
        "app": {"name": "t", "roles": ["R"]},
        "dataModel": {
            "entities": [
                {
                    "name": "Author",
                    "attributes": [
                        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    ],
                },
                {
                    "name": "Book",
                    "attributes": [
                        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                    ],
                    "relationships": [{"to": "Author", "kind": "manyToOne", "mandatory": True}],
                },
            ]
        },
    }
    manifest = spec_to_entities(synthetic)
    book = next(e for e in manifest.server_entities if e.name == "Book")
    fk = next(a for a in book.attributes if a.data_type == "Author Identifier")
    assert fk.name == "AuthorId"
    assert fk.is_mandatory is True
