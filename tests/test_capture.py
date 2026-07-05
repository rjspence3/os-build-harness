"""Tests for harness/capture.py — the runtime (rendered-DOM) verification channel.

Browser-free: exercises the pure composition seam `_assert_capture_channel`
(spec + a runtime screen-walk snapshot -> capture-channel pass/fail), which reuses
harness-verify's evaluators. The Playwright-driven sweep (`build_runtime_snapshot`)
is validated live against deployed apps, not in unit tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import capture


def _spec():
    """Minimal one-screen spec with the three capture-channel assertion kinds."""
    return {
        "specVersion": "0.2",
        "app": {"name": "t", "roles": ["User"]},
        "dataModel": {"entities": [{"name": "Item", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True}]}]},
        "screens": [
            {"id": "list", "name": "List", "route": "/list", "roles": ["User"],
             "components": [
                 {"id": "itemsTable", "type": "Table", "boundTo": "Item"},
                 {"id": "newBtn", "type": "Button", "label": "New"},
             ],
             "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "detail"}],
             "acceptance": {"assertions": [
                 {"kind": "componentPresent", "componentId": "itemsTable"},
                 {"kind": "binding", "componentId": "itemsTable", "boundTo": "Item"},
                 {"kind": "navigates", "fromComponent": "newBtn", "event": "onClick", "toScreen": "detail"},
             ]}},
            {"id": "detail", "name": "Detail", "route": "/detail", "roles": ["User"],
             "components": [], "navigation": [], "acceptance": {"assertions": []}},
        ],
    }


def test_all_pass_when_snapshot_confirms_everything():
    snapshot = {"screens": [
        {"id": "list",
         "components": [{"id": "itemsTable", "type": "Table", "boundTo": "Item"}],
         "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "detail"}]},
    ]}
    _results, n_pass, n_fail = capture._assert_capture_channel(_spec(), snapshot)
    assert (n_pass, n_fail) == (3, 0)


def test_binding_fails_when_component_present_but_unbound():
    # component resolved (present) but no boundTo emitted (e.g. data list rendered empty)
    snapshot = {"screens": [
        {"id": "list",
         "components": [{"id": "itemsTable", "type": "Table"}],  # no boundTo
         "navigation": [{"fromComponent": "newBtn", "event": "onClick", "toScreen": "detail"}]},
    ]}
    _results, n_pass, n_fail = capture._assert_capture_channel(_spec(), snapshot)
    # componentPresent + navigates pass; binding fails
    assert n_pass == 2 and n_fail == 1


def test_empty_snapshot_fails_all_capture_assertions():
    snapshot = {"screens": [{"id": "list", "components": [], "navigation": []}]}
    _results, n_pass, n_fail = capture._assert_capture_channel(_spec(), snapshot)
    assert n_pass == 0 and n_fail == 3


def test_navigates_fails_when_edge_absent():
    snapshot = {"screens": [
        {"id": "list",
         "components": [{"id": "itemsTable", "type": "Table", "boundTo": "Item"}],
         "navigation": []},  # nav edge not confirmed
    ]}
    _results, n_pass, n_fail = capture._assert_capture_channel(_spec(), snapshot)
    assert n_pass == 2 and n_fail == 1


def test_confirm_nav_href_matches_route_tail():
    assert capture._confirm_nav_href({"href": "/app/detail"}, "/detail") is True
    assert capture._confirm_nav_href({"href": "/app/other"}, "/detail") is False
    assert capture._confirm_nav_href({}, "/detail") is False


def test_parent_context_nav_resolves_route_and_label_for_child_create():
    """Seam 3c: the gate reaches a child create screen (tasks, needs ListId) by opening a
    parent record on the list screen. The helper must resolve the parent route + the click
    label from the parent's navigation entry."""
    spec = {"screens": [
        {"id": "lists", "route": "/lists",
         "components": [{"id": "openTasksBtn", "type": "Button", "label": "Open"}],
         "navigation": [{"fromComponent": "openTasksBtn", "event": "onClick",
                         "toScreen": "tasks", "params": ["ListId"]}]},
        {"id": "tasks", "route": "/tasks",
         "inputParameters": [{"name": "ListId", "references": "TaskList", "isRequired": True}]}]}
    assert capture._parent_context_nav(spec, spec["screens"][1]) == ("/lists", "Open")
    # a screen nobody navigates into with params -> None (drive it by its own route)
    assert capture._parent_context_nav(spec, spec["screens"][0]) is None
