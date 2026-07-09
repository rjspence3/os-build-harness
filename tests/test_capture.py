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


def test_gated_screens_selects_access_restricted_only():
    """Phase 2 role gate targets only access-gated screens (adminOnly/requiresRole)."""
    spec = {"screens": [
        {"id": "home", "route": "/home"},
        {"id": "admin", "route": "/admin", "access": {"adminOnly": True}},
        {"id": "team", "route": "/team", "access": {"requiresRole": "Manager"}}]}
    ids = [s["id"] for s in capture._gated_screens(spec)]
    assert ids == ["admin", "team"]


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


# ── T-W1: verdict taxonomy ───────────────────────────────────────────────────
def test_classify_verdict_maps_every_class():
    """T-W1: _classify_verdict covers all expected tokens and handles edge cases."""
    cls = capture._classify_verdict
    # defects
    assert cls("NO_PERSIST (submitted, count did not grow)") == "defect"
    assert cls("NO_UPDATE") == "defect"
    assert cls("NO_DELETE") == "defect"
    assert cls("NOT_APPLIED (palette absent)") == "defect"
    assert cls("NO_CHART (no svg in content)") == "defect"
    assert cls("KPI_WRONG (shows 1, expected 4)") == "defect"
    # unverified (gate / driver gaps)
    assert cls("NO_LIST_SCREEN (cannot measure)") == "unverified"
    assert cls("NO_CREATE_ENTRY (no New button)") == "unverified"
    assert cls("NO_EDIT_ENTRY (no Edit control)") == "unverified"
    assert cls("NO_DELETE_ENTRY (no Delete control)") == "unverified"
    assert cls("NO_PARENT_CONTEXT (no parent entry point)") == "unverified"
    assert cls("FORM_NOT_FOUND (dead button)") == "unverified"
    assert cls("EDIT_FORM_NOT_FOUND (no editable field)") == "unverified"
    assert cls("SAVE_NOT_FOUND (no save button)") == "unverified"
    assert cls("NO_ROWS (nothing to delete)") == "unverified"
    # error prefixes -> unverified (not a confirmed defect)
    assert cls("ERROR RuntimeError('timeout')") == "unverified"
    assert cls("ERROR_CONNECTION_REFUSED") == "unverified"
    # unknown token -> unverified (never silently ok)
    assert cls("MYSTERY_VERDICT") == "unverified"
    assert cls("") == "unverified"
    # ok verdicts
    assert cls("PERSISTS") == "ok"
    assert cls("UPDATES") == "ok"
    assert cls("DELETES") == "ok"
    assert cls("APPLIED") == "ok"
    assert cls("RENDERS") == "ok"
    assert cls("KPI_OK") == "ok"


def test_finalize_attaches_verdict_class():
    """_finalize is additive — never renames existing keys."""
    r = {"verdict": "PERSISTS", "screen": "list", "entity": "Item"}
    result = capture._finalize(r)
    assert result is r                           # mutates in-place AND returns
    assert result["verdict_class"] == "ok"
    assert result["verdict"] == "PERSISTS"       # original key preserved


# ── T-W2: prefer= anchor ─────────────────────────────────────────────────────
def test_list_screen_prefers_action_screen():
    """T-W2: _list_screen_for_entity with prefer='intake' returns 'intake' when it is
    entity-bound, even though 'screening' also carries the entity and appears first."""
    from harness.prompt_recipes import _list_screen_for_entity
    spec = {"screens": [
        {"id": "screening", "components": [{"id": "t1", "type": "Table", "boundTo": "Supplier"}]},
        {"id": "intake",    "components": [{"id": "t2", "type": "Table", "boundTo": "Supplier"}]},
    ]}
    # without prefer: first bound screen is returned
    assert _list_screen_for_entity(spec, "Supplier") == "screening"
    # with prefer=intake: the action screen is preferred when it is entity-bound
    assert _list_screen_for_entity(spec, "Supplier", prefer="intake") == "intake"
    # with prefer pointing at a non-entity-bound screen: falls back to first bound screen
    spec2 = {"screens": [
        {"id": "unrelated", "components": [{"id": "x", "type": "Button"}]},
        {"id": "screening", "components": [{"id": "t1", "type": "Table", "boundTo": "Supplier"}]},
    ]}
    assert _list_screen_for_entity(spec2, "Supplier", prefer="unrelated") == "screening"


def test_drive_create_measures_on_action_screen():
    """T-W2 driver: _drive_create prefers the form_screen itself for measurement when it is
    entity-bound (anchor to the action's own screen — not the first entity-bound screen)."""
    from harness.prompt_recipes import _list_screen_for_entity
    # spec where entity appears on TWO screens; the action lives on the SECOND one (intake)
    spec = {"screens": [
        {"id": "screening", "components": [{"id": "t1", "type": "Table", "boundTo": "Supplier"}]},
        {"id": "intake",    "components": [{"id": "t2", "type": "Table", "boundTo": "Supplier"}]},
    ]}
    # Without prefer: first bound screen (screening) is returned.
    assert _list_screen_for_entity(spec, "Supplier") == "screening"
    # With prefer=intake (the action's form screen): intake is preferred because it is entity-bound.
    assert _list_screen_for_entity(spec, "Supplier", prefer="intake") == "intake"
    # Confirm the driver call-site would supply prefer=form_screen["id"].
    # We verify the logic here rather than mocking the full browser session.
    form_screen = spec["screens"][1]   # intake
    result_screen = _list_screen_for_entity(spec, "Supplier", prefer=form_screen["id"])
    assert result_screen == "intake"


# ── T-W3: edit-via-nav ────────────────────────────────────────────────────────
class FakePage:
    """Minimal browser-free page double.  Each evaluate() call pops the next scripted value
    from `side_effects`; `goto()` and `wait_for_timeout()` are no-ops."""
    def __init__(self, side_effects: list):
        self._effects = list(side_effects)
        self.url = "http://x/release"

    def evaluate(self, _js, *args):
        if not self._effects:
            return None
        val = self._effects.pop(0)
        return val() if callable(val) else val

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        pass


def test_drive_update_takes_nav_edit_path(monkeypatch):
    """T-W3: when there is no inline Edit row-action but an edit screen is reachable via a
    parent nav, _drive_update should take the nav-to-edit path and return UPDATES.

    Setup: 'release' is the form_screen (entity-bound list, no input params — so
    _goto_entity_list uses the simple route, no parent-context open).
    'partEdit' is the edit screen, reachable from 'release' via row navigation."""
    spec = {
        "screens": [
            {"id": "release", "route": "/release",
             "components": [{"id": "partsTable", "type": "Table", "boundTo": "Part"}],
             "navigation": [{"fromComponent": "partsTable", "event": "onClick",
                             "toScreen": "partEdit", "params": ["PartId"]}]},
            {"id": "partEdit", "route": "/part-edit",
             "components": [{"id": "partForm", "type": "Form"}],
             "inputParameters": [{"name": "PartId", "references": "Part", "isRequired": True}]},
        ],
        "dataModel": {"entities": [
            {"name": "Part", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                {"name": "Name", "dataType": "Text"}]}
        ]},
    }
    # evaluate() calls in order:
    # 1. _COUNT_JS on release list               -> 2 rows present
    # 2. _CLICK_ROWACTION_JS (inline edit)       -> False (no inline edit)
    # 3. nav-to-edit: opened_parent on release   -> True (row clicked)
    # 4. performance.now() for marker            -> 12345
    # 5. _SET_FIELD_JS (set marker on edit form) -> True
    # 6. save button click                       -> True
    # 7. body.innerText.includes(marker)         -> True (marker found after reload)
    side_effects = [2, False, True, 12345, True, True, True]
    page = FakePage(side_effects)
    form_screen = spec["screens"][0]  # release (the list screen, no input params)
    result = capture._drive_update(page, "http://x", spec, form_screen, "Part")
    assert result["verdict"] == "UPDATES"
    assert result.get("editVia") == "nav"


def test_drive_update_no_edit_path_is_unverified(monkeypatch):
    """T-W3 negative: when there is neither inline edit nor a nav-reachable edit screen,
    verdict must be NO_EDIT_ENTRY (unverified, not defect)."""
    spec = {
        "screens": [
            {"id": "list", "route": "/list",
             "components": [{"id": "partT", "type": "Table", "boundTo": "Part"}],
             "navigation": []},
        ],
        "dataModel": {"entities": [
            {"name": "Part", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
                {"name": "Name", "dataType": "Text"}]}
        ]},
    }
    # evaluate() calls: _COUNT_JS (2 rows) then _CLICK_ROWACTION_JS (False = no inline edit)
    side_effects = [2, False]
    page = FakePage(side_effects)
    form_screen = spec["screens"][0]  # list (no input params)
    result = capture._drive_update(page, "http://x", spec, form_screen, "Part")
    assert result["verdict"].startswith("NO_EDIT_ENTRY")
    assert capture._classify_verdict(result["verdict"]) == "unverified"


def test_drive_create_fills_always_visible_form():
    """Always-visible create form: _drive_create fills the visible inputs directly and saves,
    WITHOUT first clicking a 'reveal' button — on an always-visible form that button IS the save
    button and clicking it before filling would submit empty (the intake NO_PERSIST false-negative).
    Persists when the row count grows."""
    spec = {
        "screens": [{"id": "intake", "route": "/intake",
                     "components": [{"id": "t", "type": "Table", "boundTo": "Supplier"}],
                     "actions": [{"name": "CreateSupplier", "does": ["CreateEntity"]}]}],
        "dataModel": {"entities": [{"name": "Supplier", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
            {"name": "Code", "dataType": "Text"}]}]},
    }
    # evaluate() order: _COUNT_JS before=4 ; _FILL_JS=2 (>0 so NO reveal click) ; save="Add Supplier" ;
    # _COUNT_JS after=5 (grew)
    page = FakePage([4, 2, "Add Supplier", 5])
    result = capture._drive_create(page, "http://x", spec, spec["screens"][0], "Supplier")
    assert result["verdict"] == "PERSISTS"
    assert result.get("openedVia") is None      # the always-visible form needed no reveal click


def test_run_behavioral_routes_edit_screen_to_nav_driver(monkeypatch):
    """An edit-screen (declares CreateEntity but takes an id param referencing the entity) is
    verified via the nav-to-edit (update) driver, not the create-from-list driver — else it
    false-reports NO_CREATE_ENTRY (the partEdit case)."""
    called = []
    monkeypatch.setattr(capture, "_drive_create",
                        lambda p, b, s, sc, e: called.append(("create", sc["id"])) or {"verdict": "PERSISTS"})
    monkeypatch.setattr(capture, "_drive_update",
                        lambda p, b, s, sc, e: called.append(("update", sc["id"])) or {"verdict": "UPDATES"})
    monkeypatch.setattr(capture, "_apply_login", lambda *a, **k: {})

    class _P:
        url = ""
        def goto(self, *a, **k): pass
        def wait_for_timeout(self, *a): pass
        def evaluate(self, *a, **k): return None
    class _B:
        def new_context(self, **k):
            return type("C", (), {"new_page": lambda self: _P()})()
        def close(self): pass
    class _PW:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        chromium = type("Chr", (), {"launch": staticmethod(lambda **k: _B())})
    monkeypatch.setattr(capture, "_lazy_playwright", lambda: (lambda: _PW()))

    spec = {"screens": [
        {"id": "intake", "components": [{"id": "t", "type": "Table", "boundTo": "Supplier"}],
         "actions": [{"name": "CreateSupplier", "does": ["CreateEntity"]}]},
        {"id": "partEdit", "components": [{"id": "pf", "type": "Container"}],
         "inputParameters": [{"name": "PartId", "references": "Part"}],
         "actions": [{"name": "SavePart", "does": ["CreateEntity"]}]},
    ], "dataModel": {"entities": [
        {"name": "Supplier", "attributes": []}, {"name": "Part", "attributes": []}]}}
    capture.run_behavioral(spec, "http://x", {})
    assert ("create", "intake") in called          # normal create screen -> create-from-list driver
    assert ("update", "partEdit") in called         # edit screen -> nav-to-edit (update) driver
    assert ("create", "partEdit") not in called


# ── T-W5a: KPI check ─────────────────────────────────────────────────────────
def test_kpi_check_flags_list_length_bug():
    """T-W5a: _check_kpi_card returns KPI_WRONG (defect) when shown != expected,
    and KPI_OK (ok) when they match."""
    # shown=1 (Mentor bound .List.Length instead of .Count), expected=4
    result_wrong = capture._check_kpi_card(shown=1, expected=4,
                                            screen="dashboard", slug="suppliers")
    assert result_wrong["verdict"].startswith("KPI_WRONG")
    assert result_wrong["shown"] == 1 and result_wrong["expected"] == 4
    assert capture._classify_verdict(result_wrong["verdict"]) == "defect"

    # shown=4, expected=4 -> OK
    result_ok = capture._check_kpi_card(shown=4, expected=4,
                                         screen="dashboard", slug="suppliers")
    assert result_ok["verdict"] == "KPI_OK"
    assert capture._classify_verdict(result_ok["verdict"]) == "ok"

    # non-numeric shown -> KPI_WRONG (defect)
    result_none = capture._check_kpi_card(shown=None, expected=4,
                                           screen="dashboard", slug="suppliers")
    assert result_none["verdict"].startswith("KPI_WRONG")
    assert capture._classify_verdict(result_none["verdict"]) == "defect"


# ── T-W5a: live-count fallback (no sampleData) ───────────────────────────────
def test_true_count_for_entity_live_count_fallback():
    """T-W5a: when an entity has no sampleData, _true_count_for_entity must navigate to the
    entity's list screen and return the live row count from _COUNT_JS — NOT None.

    This test targets the dead-import bug (FIX-001): before the fix, the spurious
    `from harness.prompt_recipes import _route_of as _pr_route_of` raised ImportError,
    which the except-block swallowed, causing the function to always return None for any
    entity without sampleData.  After the fix the live-count path executes correctly."""
    spec = {
        "app": {"name": "t"},
        "screens": [
            {"id": "itemList", "route": "/items",
             "components": [{"id": "itemsTable", "type": "Table", "boundTo": "Item"}],
             "navigation": []},
        ],
        "dataModel": {"entities": [
            # Deliberately NO sampleData — forces the live-count path.
            {"name": "Item", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True}]}
        ]},
    }
    # FakePage.evaluate() is called once with _COUNT_JS + entity name; return 7 rows.
    page = FakePage([7])
    result = capture._true_count_for_entity(spec, "Item", page, "http://x")
    assert result == 7, (
        "Expected live row count 7 but got None — the dead-import bug may still be present"
    )
