"""Pixel-perfect gate: compare a clone screenshot against the original.

The "done" criterion for the V6 clone is pixel-match with the original at the same
viewport + same data/user. This computes a per-pixel difference, a match score,
and writes a diff heatmap so we can see exactly WHERE pixels differ (which drives
the next build iteration).

Usage:
  python scripts/pixel_diff.py <original.png> <clone.png> [diff_out.png] [--tol N]

--tol = per-channel tolerance (0-255, default 16): a pixel "matches" if every
channel differs by <= tol (kills anti-aliasing/compression noise). Reports:
  - match%  (pixels within tolerance)
  - mean per-pixel delta
  - bounding box of the differing region (where to focus the next iteration)
Exit 0 if match% >= threshold (default 99.5), else 1 — so the loop can gate on it.
"""
import sys
from PIL import Image, ImageChops


def load_rgb(path):
    return Image.open(path).convert("RGB")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a.split("=")[0]: (a.split("=", 1)[1] if "=" in a else True) for a in argv[1:] if a.startswith("--")}
    if len(args) < 2:
        print(__doc__)
        return 2
    tol = int(flags.get("--tol", 16))
    pass_threshold = float(flags.get("--threshold", 99.5))
    a = load_rgb(args[0])
    b = load_rgb(args[1])
    diff_out = args[2] if len(args) > 2 else "compare/pixel_diff.png"

    # --mask "x1,y1,x2,y2;..." zeroes rectangles in BOTH images before diffing
    # (used to ignore browser-extension overlays like the LastPass popup that
    # contaminate the same screen region on both captures).
    mask = flags.get("--mask")
    if isinstance(mask, str):
        from PIL import ImageDraw
        da, db = ImageDraw.Draw(a), ImageDraw.Draw(b)
        for rect in mask.split(";"):
            rect = rect.strip()
            if not rect:
                continue
            x1, y1, x2, y2 = (int(v) for v in rect.split(","))
            da.rectangle([x1, y1, x2, y2], fill=(0, 0, 0))
            db.rectangle([x1, y1, x2, y2], fill=(0, 0, 0))
        print(f"masked regions: {mask}")

    if a.size != b.size:
        # crop both to the common top-left region so a height/width diff doesn't
        # blow up the comparison — but REPORT it, since size mismatch matters.
        w, h = min(a.size[0], b.size[0]), min(a.size[1], b.size[1])
        print(f"SIZE MISMATCH original={a.size} clone={b.size} -> comparing common {w}x{h}")
        a = a.crop((0, 0, w, h))
        b = b.crop((0, 0, w, h))

    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()  # region where anything differs at all

    # per-pixel: matched if max channel delta <= tol
    px_a, px_b = a.load(), b.load()
    W, H = a.size
    total = W * H
    mismatched = 0
    sum_delta = 0
    # sample stride for speed on large images, then exact if small
    stride = 1 if total <= 1_600_000 else 2
    counted = 0
    for y in range(0, H, stride):
        for x in range(0, W, stride):
            ra, ga, ba = px_a[x, y]
            rb, gb, bb = px_b[x, y]
            d = max(abs(ra - rb), abs(ga - gb), abs(ba - bb))
            sum_delta += d
            counted += 1
            if d > tol:
                mismatched += 1
    match_pct = 100.0 * (1 - mismatched / counted)
    mean_delta = sum_delta / counted

    # heatmap: amplify the diff so differing regions are visible
    heat = diff.point(lambda v: min(255, v * 6))
    heat.save(diff_out)

    print(f"match%={match_pct:.2f}  mean_delta={mean_delta:.2f}  tol={tol}  stride={stride}")
    print(f"diff_bbox={bbox}  (None = identical region; else where pixels differ)")
    print(f"heatmap={diff_out}")
    ok = match_pct >= pass_threshold
    print(f"PIXEL GATE: {'PASS' if ok else 'FAIL'} (threshold {pass_threshold}%)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
