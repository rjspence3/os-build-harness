"""Tests for the app_spec -> natural-language SCREEN authoring bridge.

Mirrors the entity NL bridge tests (test_spec_adapter.py). Feeds
examples/task_tracker/app_spec.json through `render_spec_screens_nl` and asserts
the emitted NL names every widget by its exact spec `id`, resolves bindings and
navigation (id -> screen name), notes that screens are authored AFTER the data
model, renders non-navigation actions, honestly flags unmapped component types,
and contains no applyModelApiCode C#.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.banking_runner.spec_adapter import (
    collect_spec_screen_gaps,
    render_spec_screens_nl,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TASK_TRACKER_SPEC = REPO_ROOT / "examples" / "task_tracker" / "app_spec.json"


@pytest.fixture
def spec() -> dict:
    return json.loads(TASK_TRACKER_SPEC.read_text())


# ─── screens present + ordered ──────────────────────────────────────────────────

def test_both_screens_present(spec):
    nl = render_spec_screens_nl(spec)
    assert "Screen `Lists`" in nl
    assert "Screen `Tasks`" in nl


def test_lists_authored_before_tasks(spec):
    nl = render_spec_screens_nl(spec)
    assert nl.index("Screen `Lists`") < nl.index("Screen `Tasks`")


# ─── components named + bound ───────────────────────────────────────────────────

def test_lists_table_named_and_bound(spec):
    nl = render_spec_screens_nl(spec)
    assert "Table named `listsTable`" in nl          # exact id emitted as the name
    assert "showing `TaskList`" in nl                # boundTo -> showing records
    assert 'label "Your lists"' in nl                # label carried through


def test_tasks_table_named_and_bound(spec):
    nl = render_spec_screens_nl(spec)
    assert "Table named `tasksTable`" in nl
    # backtick-terminated so this does NOT accidentally match "showing `TaskList`"
    assert "showing `Task`" in nl


def test_open_button_navigates_to_tasks(spec):
    nl = render_spec_screens_nl(spec)
    assert "Button named `openTasksBtn`" in nl
    nav_line = next(line for line in nl.splitlines() if "openTasksBtn" in line)
    # navigation edge toScreen "tasks" (id) resolved to screen NAME "Tasks"
    assert "navigates to screen `Tasks`" in nav_line


# ─── header meta + input parameters ─────────────────────────────────────────────

def test_screen_header_carries_route_flow_role(spec):
    nl = render_spec_screens_nl(spec)
    assert "route /lists" in nl
    assert "flow MainFlow" in nl
    assert "role Member" in nl


def test_tasks_input_parameter_rendered(spec):
    nl = render_spec_screens_nl(spec)
    assert "input parameter `ListId`" in nl
    assert "referencing `TaskList`" in nl


# ─── functional actions (non-navigation) ────────────────────────────────────────

def test_create_task_action_rendered(spec):
    nl = render_spec_screens_nl(spec)
    assert "action `CreateTask`" in nl
    assert "CreateEntity" in nl


def test_pure_navigate_action_not_double_rendered(spec):
    # GoToTasks does ["Navigate"] only — already covered by the navigation edge,
    # so it must NOT appear as an explicit action line.
    nl = render_spec_screens_nl(spec)
    assert "action `GoToTasks`" not in nl


# ─── authoring-order note ───────────────────────────────────────────────────────

def test_preamble_notes_screens_after_data_model(spec):
    nl = render_spec_screens_nl(spec)
    lower = nl.lower()
    assert "data model" in lower
    assert "after" in lower
    assert "publish" in lower


# ─── NL, not C# ─────────────────────────────────────────────────────────────────

def test_no_csharp_in_screen_nl(spec):
    nl = render_spec_screens_nl(spec)
    assert "applyModelApiCode" not in nl
    assert "eSpace" not in nl
    assert "CreateWidget" not in nl


# ─── honesty: gaps ──────────────────────────────────────────────────────────────

def test_task_tracker_screens_have_no_gaps(spec):
    assert collect_spec_screen_gaps(spec) == []


def test_unrecognized_component_type_flagged():
    synthetic = {
        "app": {"name": "t", "roles": ["R"]},
        "dataModel": {
            "entities": [
                {
                    "name": "E",
                    "attributes": [
                        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}
                    ],
                }
            ]
        },
        "screens": [
            {
                "id": "s",
                "name": "S",
                "components": [{"id": "board1", "type": "Board"}],
                "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "board1"}]},
            }
        ],
    }
    gaps = collect_spec_screen_gaps(synthetic)
    assert any("Board" in g for g in gaps)
    # Best-effort: an unmapped type is still named (never silently dropped).
    nl = render_spec_screens_nl(synthetic)
    assert "Board named `board1`" in nl


def test_sidebar_nav_items_resolve_to_screen_names():
    synthetic = {
        "app": {"name": "t", "roles": ["R"]},
        "dataModel": {
            "entities": [
                {
                    "name": "E",
                    "attributes": [
                        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}
                    ],
                }
            ]
        },
        "screens": [
            {
                "id": "home",
                "name": "Home",
                "components": [
                    {
                        "id": "sidebar",
                        "type": "Sidebar",
                        "nav": [
                            {"label": "Home", "toScreen": "home"},
                            {"label": "Detail", "toScreen": "detail"},
                        ],
                    }
                ],
                "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "sidebar"}]},
            },
            {
                "id": "detail",
                "name": "Detail",
                "components": [{"id": "t", "type": "Text"}],
                "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "t"}]},
            },
        ],
    }
    nl = render_spec_screens_nl(synthetic)
    assert "navigates to screens `Home`, `Detail`" in nl


def test_non_onclick_event_is_mentioned():
    synthetic = {
        "app": {"name": "t", "roles": ["R"]},
        "dataModel": {
            "entities": [
                {
                    "name": "E",
                    "attributes": [
                        {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}
                    ],
                }
            ]
        },
        "screens": [
            {
                "id": "a",
                "name": "A",
                "components": [{"id": "form1", "type": "Form", "boundTo": "E"}],
                "navigation": [{"fromComponent": "form1", "event": "onSubmit", "toScreen": "b"}],
                "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "form1"}]},
            },
            {
                "id": "b",
                "name": "B",
                "components": [{"id": "t", "type": "Text"}],
                "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "t"}]},
            },
        ],
    }
    nl = render_spec_screens_nl(synthetic)
    assert "bound to `E`" in nl                       # Form binding phrasing
    assert "on onSubmit navigates to screen `B`" in nl


def test_missing_screens_raises():
    from harness.banking_runner.spec_adapter import SpecAdaptError

    with pytest.raises(SpecAdaptError):
        render_spec_screens_nl({"app": {"name": "t", "roles": ["R"]}, "dataModel": {"entities": []}})
