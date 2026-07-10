"""Unit tests for the non-greedy build-cost diagnostic (harness.build_cost)."""
from harness import build_cost


def _spec():
    # data-model + 2 screens (a dashboard-count screen + a plain list) → structural-UI steps batch.
    return {
        "specVersion": "0.3", "app": {"name": "Demo"},
        "dataModel": {"entities": [{"name": "Case", "sampleData": [{"Title": "A"}], "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": True},
            {"name": "Title", "dataType": "Text"}]}]},
        "navigation": {"block": "SidebarNav", "items": [{"label": "Cases", "toScreen": "cases"}]},
        "screens": [{"id": "cases", "name": "Cases", "isDefault": True, "components": [
            {"id": "t", "type": "Table", "boundTo": "Case", "columns": [{"field": "Title", "kind": "text"}]}]}],
    }


def test_cost_counts_turns_publishes_and_sessions():
    c = build_cost.cost_of_spec(_spec())
    assert c.turns == c.steps > 0
    assert c.publishes_per_unit == c.steps          # current model: publish-per-unit
    assert c.sessions_reuse == 1                     # session-reuse → one cap slot
    assert c.sessions_greedy == c.steps             # no-reuse → one per step
    assert sum(c.by_recipe.values()) == c.steps     # recipe histogram sums to steps


def test_publish_batching_never_exceeds_per_unit_and_saves_on_structural_runs():
    c = build_cost.cost_of_spec(_spec())
    assert 1 <= c.publishes_batched <= c.publishes_per_unit
    # this spec has a contiguous run of structural-UI steps (screen/nav/place-nav/list-screen) →
    # batching collapses them to one publish, so there IS a saving.
    assert c.publish_savings >= 1


def test_batchable_run_collapses_to_one_publish():
    # a pure structural-UI run publishes ONCE when batched; a non-batchable step keeps its own publish.
    steps = [{"recipe": "data-model", "params": {}},      # own publish
             {"recipe": "screen", "params": {}},          # ┐
             {"recipe": "nav-block", "params": {}},       # ├ one batched publish
             {"recipe": "list-screen", "params": {}},     # ┘
             {"recipe": "seed-graph", "params": {}}]      # own publish
    c = build_cost.cost_of_plan("x", steps)
    assert c.publishes_per_unit == 5
    assert c.publishes_batched == 3                       # data-model + (screen|nav|list run) + seed
