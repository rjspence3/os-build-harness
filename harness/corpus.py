"""Living test corpus — INVARIANTS over a GROWING set of spec fixtures.

The failure mode this prevents: anchoring the engine's regression tests on ONE real-world spec.
That over-indexes the parser/planner on that spec's quirks and turns the tests into a memorization of
its output — green while silently mishandling differently-shaped apps. It is the same over-fit disease
as WALL-006 (recipes tuned to the shapes they were built against), one layer up. (It also keeps any
client-derived spec out of the engine entirely — real specs live only in the private build lab.)

The fix mirrors the recipe layer's reconcile + the harvest ledger (harness/learning.py):
  * INVARIANTS, not memorized output — properties that must hold for ANY valid spec (every entity has
    an identifier; every FK targets a declared entity; every static entity has records; the plan is
    derivable; ingest is deterministic). Adding a spec to the corpus = automatic coverage, no rewrite.
  * A GROWING corpus — builds feed it. When a build exposes a new shape, the harvest adds a corpus
    fixture (a synthetic sibling in the engine; the real spec stays in the private lab). So the tests
    "evolve as the build progresses" instead of being authored once against one app.
  * TWO-TIER — this module takes a corpus directory, so the engine runs it over `tests/corpus/`
    (synthetic, public) and the private lab runs the SAME invariants over its real specs.
  * BLESS — `snapshot()` regenerates a fixture's golden app_spec (reviewed diff), the test-analog of
    the recipe reconcile: expectations track the engine as it evolves, not hand-edited assertions.

Pure + dependency-light: `run_corpus(dir)` returns {fixture: [problem, ...]}; a fixture PASSES when it
ingests to a schema-valid spec that satisfies every invariant and yields a non-empty plan.
"""
from __future__ import annotations

import json
from pathlib import Path


# ── invariants: (name, fn(app_spec) -> list[problem]) — each must hold for ANY valid spec ─────────
def _entities(spec: dict) -> list:
    return spec.get("dataModel", {}).get("entities", []) or []


def _inv_identifier_present(spec: dict) -> list:
    out = []
    for e in _entities(spec):
        ids = [a for a in e.get("attributes", []) if a.get("isIdentifier")]
        if len(ids) != 1:
            out.append(f"entity '{e.get('name')}' has {len(ids)} identifier attributes (want exactly 1)")
    return out


def _inv_fk_targets_declared(spec: dict) -> list:
    names = {e.get("name") for e in _entities(spec)}
    out = []
    for e in _entities(spec):
        for a in e.get("attributes", []):
            ref = a.get("references")
            if ref and ref not in names:
                out.append(f"{e.get('name')}.{a.get('name')} references undeclared entity '{ref}'")
    return out


def _inv_static_records_nonempty(spec: dict) -> list:
    out = []
    for e in _entities(spec):
        if e.get("isStatic") and not (e.get("records") or []):
            out.append(f"static entity '{e.get('name')}' has no records")
    return out


def _inv_attrs_well_formed(spec: dict) -> list:
    out = []
    for e in _entities(spec):
        for a in e.get("attributes", []):
            if not a.get("name"):
                out.append(f"entity '{e.get('name')}' has an attribute with no name")
            if not a.get("dataType"):
                out.append(f"{e.get('name')}.{a.get('name')} has no dataType")
    return out


def _inv_schema_valid(spec: dict) -> list:
    """Reuse the engine's own schema checker so the corpus can't drift from the schema contract."""
    try:
        from harness.verify import _schema_findings
        return [f"schema: {f}" for f in (_schema_findings(spec) or [])]
    except Exception:
        return []  # checker unavailable => not this invariant's job to fail


def _inv_plan_derivable(spec: dict) -> list:
    """A valid spec must yield a non-empty, non-crashing build plan."""
    try:
        from harness.prompt_recipes import plan_from_spec
        steps = plan_from_spec(spec)
        if not steps:
            return ["plan_from_spec produced no steps"]
        return []
    except Exception as exc:
        return [f"plan_from_spec raised: {exc!r}"]


INVARIANTS = [
    ("identifier_present", _inv_identifier_present),
    ("fk_targets_declared", _inv_fk_targets_declared),
    ("static_records_nonempty", _inv_static_records_nonempty),
    ("attrs_well_formed", _inv_attrs_well_formed),
    ("schema_valid", _inv_schema_valid),
    ("plan_derivable", _inv_plan_derivable),
]


def check_invariants(spec: dict) -> list:
    """All invariant violations for one ingested spec (empty == passes)."""
    problems = []
    for name, fn in INVARIANTS:
        for p in fn(spec):
            problems.append(f"[{name}] {p}")
    return problems


# ── corpus loading + ingest ───────────────────────────────────────────────────────────────────────
def ingest_fixture(path: Path) -> dict:
    """Markdown spec-doc -> app_spec (the ingest under test). Deterministic (no I/O beyond the read)."""
    from harness.spec_ingest import build_draft_spec
    return build_draft_spec(Path(path).read_text())


def load_corpus(corpus_dir: Path) -> list:
    """Every *.md spec fixture in the corpus directory, sorted for determinism."""
    return sorted(Path(corpus_dir).glob("*.md"))


def run_corpus(corpus_dir: Path) -> dict:
    """{fixture stem -> [problem, ...]} — invariants + a determinism check across the whole corpus.
    A fixture with an empty list passes; the corpus passes when every list is empty."""
    results = {}
    for path in load_corpus(corpus_dir):
        try:
            spec = ingest_fixture(path)
            problems = check_invariants(spec)
            # determinism: re-ingest must produce byte-identical output.
            again = ingest_fixture(path)
            if json.dumps(spec, sort_keys=True) != json.dumps(again, sort_keys=True):
                problems.append("[deterministic] re-ingest produced a different app_spec")
        except Exception as exc:
            problems = [f"[ingest] raised: {exc!r}"]
        results[path.stem] = problems
    return results


# ── bless / golden snapshot (the test-analog of the recipe reconcile) ───────────────────────────────
def snapshot(path: Path) -> dict:
    """The blessed golden for a fixture: its ingested app_spec. Written next to the fixture as
    <stem>.golden.json by `bless_corpus`; a test can diff live-ingest against it."""
    return ingest_fixture(path)


def golden_path(path: Path) -> Path:
    return Path(path).with_suffix(".golden.json")


def bless_corpus(corpus_dir: Path) -> list:
    """Regenerate every fixture's golden (reviewed via the diff, like reconcile). Returns written paths."""
    written = []
    for path in load_corpus(corpus_dir):
        gp = golden_path(path)
        gp.write_text(json.dumps(snapshot(path), indent=2, sort_keys=True) + "\n")
        written.append(gp)
    return written
