# Test Fixtures

Static fixtures for the offline unit/integration suite (`domain_*.json`, `system_*.json`,
entity snapshots). No client-derived material lives here.

## Spec-ingest fixtures → `tests/corpus/`

The markdown spec-document fixtures that drive `harness/spec_ingest.py`'s end-to-end tests are the
**synthetic corpus** under `tests/corpus/` — several independently-authored specs from *different*
domains and structures. They are deliberately diverse so the parser/planner is validated against
variety + invariants (see `harness/corpus.py` and `tests/test_corpus.py`), never over-indexed on one
spec's quirks. Adding a fixture there extends coverage with no new hand-written assertions.

The corpus is client-agnostic by construction: real build specs (which name real tenants/apps) live
only in the private build lab, run through the *same* invariant framework — they never enter this repo.
