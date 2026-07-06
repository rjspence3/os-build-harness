"""Tests for the Phase 3 pixel-fidelity gate (harness/capture.py) and the theme-token compiler
(harness/prompt_recipes.py).

Browser-free: the Playwright screenshotting (`_capture_screens_to_dir`/`run_pixel`) is proven live
against deployed apps. Here we exercise the DISCRIMINATING CORE — `_pixel_compare` — with generated
PIL images, so the gate's pass/fail behavior (identical => 100%/PASS, a restyle regression =>
below-threshold/FAIL, tolerance absorbs anti-alias noise, masking neutralizes an overlay) is pinned
deterministically. That is the Phase 3 exit criterion: emits a score vs a reference AND a restyle
regression fails the gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from harness import capture
from harness.prompt_recipes import _theme_css

GATE_THRESHOLD = 99.0  # harness-capture --pixel-threshold default


def _solid(path: Path, size, rgb) -> Path:
    Image.new("RGB", size, rgb).save(str(path))
    return path


def _split_color(path: Path, size, left_rgb, right_rgb) -> Path:
    """Left half one color, right half another — a coarse 'restyle' of half the screen."""
    img = Image.new("RGB", size, left_rgb)
    for x in range(size[0] // 2, size[0]):
        for y in range(size[1]):
            img.putpixel((x, y), right_rgb)
    img.save(str(path))
    return path


def test_pixel_compare_identical_is_100_and_passes(tmp_path):
    ref = _solid(tmp_path / "ref.png", (200, 120), (94, 106, 210))
    clone = _solid(tmp_path / "clone.png", (200, 120), (94, 106, 210))
    r = capture._pixel_compare(ref, clone, tol=16, mask_rects=[])
    assert r["match_pct"] == 100.0
    assert r["bbox"] is None          # nothing differs
    assert r["size_note"] is None
    assert r["match_pct"] >= GATE_THRESHOLD   # => MATCH


def test_pixel_compare_restyle_regression_drifts_and_fails(tmp_path):
    """A build that restyled half the screen must FALL BELOW threshold — the gate catches it."""
    ref = _solid(tmp_path / "ref.png", (200, 120), (255, 255, 255))
    clone = _split_color(tmp_path / "clone.png", (200, 120), (255, 255, 255), (10, 10, 10))
    r = capture._pixel_compare(ref, clone, tol=16, mask_rects=[])
    assert 45.0 < r["match_pct"] < 55.0       # ~half the pixels changed
    assert r["match_pct"] < GATE_THRESHOLD    # => DRIFT / gate FAIL
    assert r["bbox"] is not None              # heatmap has a region to show


def test_pixel_compare_tolerance_absorbs_small_noise(tmp_path):
    """A uniform per-channel delta <= tol (anti-alias / compression) still counts as a full match."""
    ref = _solid(tmp_path / "ref.png", (200, 120), (100, 100, 100))
    clone = _solid(tmp_path / "clone.png", (200, 120), (108, 108, 108))  # delta 8 <= tol 16
    r = capture._pixel_compare(ref, clone, tol=16, mask_rects=[])
    assert r["match_pct"] == 100.0
    assert r["mean_delta"] == 8.0             # measured, but under tolerance


def test_pixel_compare_delta_above_tolerance_counts_as_mismatch(tmp_path):
    ref = _solid(tmp_path / "ref.png", (200, 120), (100, 100, 100))
    clone = _solid(tmp_path / "clone.png", (200, 120), (140, 140, 140))  # delta 40 > tol 16
    r = capture._pixel_compare(ref, clone, tol=16, mask_rects=[])
    assert r["match_pct"] == 0.0
    assert r["match_pct"] < GATE_THRESHOLD


def test_pixel_compare_mask_neutralizes_differing_region(tmp_path):
    """Masking the drifting half restores a full match (ignore a browser-extension overlay etc.)."""
    ref = _solid(tmp_path / "ref.png", (200, 120), (255, 255, 255))
    clone = _split_color(tmp_path / "clone.png", (200, 120), (255, 255, 255), (10, 10, 10))
    masked = capture._pixel_compare(ref, clone, tol=16, mask_rects=[(100, 0, 200, 120)])
    assert masked["match_pct"] == 100.0


def test_pixel_compare_size_mismatch_reports_note(tmp_path):
    ref = _solid(tmp_path / "ref.png", (200, 120), (30, 30, 30))
    clone = _solid(tmp_path / "clone.png", (200, 90), (30, 30, 30))
    r = capture._pixel_compare(ref, clone, tol=16, mask_rects=[])
    assert r["size_note"] is not None
    assert "200, 120" in r["size_note"] and "200, 90" in r["size_note"]
    assert r["match_pct"] == 100.0            # common region is identical


def test_theme_css_compiles_palette_typography_and_spacing_deterministically():
    tokens = {
        "palette": {"primary": "#5E6AD2", "surface": "#FFFFFF"},
        "typography": {"family": "Inter, sans-serif", "size-base": "15px"},
        "spacing": {"sm": "8px", "lg": "24px"},
        "css": ".card { border-radius: 8px; }",
    }
    out = _theme_css(tokens)
    # palette stays UNPREFIXED so the runtime --<paletteKey> theme-applied check keeps working
    assert "--primary: #5E6AD2" in out and "--surface: #FFFFFF" in out
    # typography -> --font-*, spacing -> --space-*
    assert "--font-family: Inter, sans-serif" in out and "--font-size-base: 15px" in out
    assert "--space-sm: 8px" in out and "--space-lg: 24px" in out
    assert ".card { border-radius: 8px; }" in out
    assert _theme_css(tokens) == out          # deterministic across calls


def test_theme_css_empty_tokens_is_safe():
    assert _theme_css({}) == "/* theme */"
