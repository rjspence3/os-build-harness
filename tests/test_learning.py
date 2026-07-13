"""Tests for learning mode — the harvest ledger + its integrity guardrail."""
import json
from pathlib import Path

import pytest

from harness import learning
from harness.learning import HarvestEntry, add_entry, load_ledger, verify, render_markdown


def _entry(**kw):
    base = dict(id=1, slug="s1", trigger="t", evidence="e", root_cause="rc",
                harness_change="hc", pins=["test_theme_includes_outsystemsui_reset"],
                memory="some-memory", status="landed")
    base.update(kw)
    return HarvestEntry(**base)


def test_entry_round_trips_through_jsonl(tmp_path):
    p = tmp_path / "ledger.jsonl"
    add_entry(_entry(), path=p)
    loaded = load_ledger(p)
    assert len(loaded) == 1
    assert loaded[0].slug == "s1"
    assert loaded[0].pins == ["test_theme_includes_outsystemsui_reset"]
    # jsonl is one compact object per line
    assert len(p.read_text().splitlines()) == 1
    assert json.loads(p.read_text().splitlines()[0])["slug"] == "s1"


def test_duplicate_slug_rejected(tmp_path):
    p = tmp_path / "ledger.jsonl"
    add_entry(_entry(), path=p)
    with pytest.raises(ValueError):
        add_entry(_entry(id=2), path=p)  # same slug


def test_verify_clean_when_pin_exists(tmp_path):
    p = tmp_path / "ledger.jsonl"
    # pin references a real test in this repo's tests/ dir
    add_entry(_entry(pins=["test_theme_includes_outsystemsui_reset"]), path=p)
    assert verify(p) == []


def test_verify_fails_on_missing_pin(tmp_path):
    p = tmp_path / "ledger.jsonl"
    add_entry(_entry(pins=["test_this_pin_does_not_exist_anywhere_zzz"]), path=p)
    problems = verify(p)
    assert problems and "pinning test not found" in problems[0]


def test_verify_requires_a_pin_for_landed(tmp_path):
    p = tmp_path / "ledger.jsonl"
    add_entry(_entry(pins=[], status="landed"), path=p)
    problems = verify(p)
    assert problems and "no pinning test" in problems[0]


def test_proposed_entry_needs_no_pin(tmp_path):
    p = tmp_path / "ledger.jsonl"
    add_entry(_entry(pins=[], status="proposed"), path=p)
    assert verify(p) == []


def test_render_markdown_lists_entries(tmp_path):
    p = tmp_path / "ledger.jsonl"
    out = tmp_path / "L.md"
    add_entry(_entry(), path=p)
    md = render_markdown(p, out)
    assert "Harvest ledger" in md and "s1" in md
    assert out.exists()


# ── the REAL ledger in the repo must stay green (this is the guardrail in CI) ──
def test_repo_ledger_integrity():
    """The committed harvest ledger must pass verify(): every landed harvest cites an existing
    pinning test. This is what makes the learning loop self-enforcing."""
    if not learning.LEDGER_PATH.exists():
        pytest.skip("no ledger yet")
    problems = verify()
    assert problems == [], f"harvest ledger broken: {problems}"
