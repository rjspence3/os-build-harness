"""Living-corpus tests: INVARIANTS over a diverse, growing set of synthetic spec fixtures.

This is the anti-over-fit layer (see harness/corpus.py). Instead of memorizing one spec's output, it
asserts properties that must hold for ANY spec, across every fixture in tests/corpus/. Adding a
fixture (e.g. harvested from a build that exposed a new shape) extends coverage with zero new
assertions — the tests evolve as the builds progress.
"""
from pathlib import Path

import pytest

from harness import corpus

_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def _fixtures():
    return corpus.load_corpus(_CORPUS_DIR)


def test_corpus_is_diverse():
    """Guard the guard: the corpus must have MULTIPLE fixtures (one spec = over-index) from more than
    one domain. If it ever collapses to a single fixture, this fails loudly."""
    fx = _fixtures()
    assert len(fx) >= 2, "corpus must hold >=2 diverse specs (one spec over-indexes the engine)"


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.stem)
def test_fixture_satisfies_all_invariants(fixture):
    """Every corpus spec must ingest to a schema-valid app_spec that satisfies every universal
    invariant and yields a derivable plan — and re-ingest deterministically."""
    spec = corpus.ingest_fixture(fixture)
    problems = corpus.check_invariants(spec)
    assert not problems, f"{fixture.stem}: " + "; ".join(problems)


def test_run_corpus_is_all_green():
    """The whole-corpus runner (the same entry point the private lab uses over its real specs)."""
    results = corpus.run_corpus(_CORPUS_DIR)
    failing = {k: v for k, v in results.items() if v}
    assert not failing, f"corpus invariant failures: {failing}"


def test_invariants_actually_catch_a_bad_spec():
    """Negative control — the invariant set must REJECT a malformed spec (an FK to nothing, an entity
    with no identifier, an empty static entity). Proves the invariants have teeth, not vacuous passes."""
    bad = {"dataModel": {"entities": [
        {"name": "Thing", "attributes": [
            {"name": "Id", "dataType": "Identifier", "isIdentifier": False},   # no identifier
            {"name": "OwnerId", "dataType": "Identifier", "references": "Ghost"}]},  # dangling FK
        {"name": "S", "isStatic": True, "records": []}]}}                        # empty static
    problems = corpus.check_invariants(bad)
    kinds = {p.split("]")[0].strip("[") for p in problems}
    assert {"identifier_present", "fk_targets_declared", "static_records_nonempty"} <= kinds


def test_diverse_domains_share_no_entity_names():
    """A concrete over-fit tripwire: the two seed fixtures come from different domains, so they should
    NOT share entity names. If a future fixture is just a rename of another, this catches the laziness."""
    names_per = []
    for fx in _fixtures():
        spec = corpus.ingest_fixture(fx)
        names_per.append({e["name"] for e in spec.get("dataModel", {}).get("entities", [])})
    # no single entity name appears in ALL fixtures (would signal one spec cloned across the corpus)
    common = set.intersection(*names_per) if names_per else set()
    assert not common, f"entity names shared across all fixtures (over-fit smell): {common}"
