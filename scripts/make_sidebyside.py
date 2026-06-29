"""Build a labeled side-by-side composite: original (left) vs V6 (right)."""
import sys

from PIL import Image, ImageDraw, ImageFont


def load_font(size):
    for path in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def main(argv):
    left_path = argv[1] if len(argv) > 1 else "compare/orig_final.png"
    right_path = argv[2] if len(argv) > 2 else "compare/v6_final.png"
    out = argv[3] if len(argv) > 3 else "compare/v6_final_sidebyside.png"

    a = Image.open(left_path).convert("RGB")
    b = Image.open(right_path).convert("RGB")
    h = max(a.height, b.height)
    label_h = 48
    gap = 16
    canvas = Image.new("RGB", (a.width + gap + b.width, h + label_h), (18, 18, 28))
    canvas.paste(a, (0, label_h))
    canvas.paste(b, (a.width + gap, label_h))

    d = ImageDraw.Draw(canvas)
    f = load_font(28)
    d.text((16, 10), "ORIGINAL — HomeBankingPortal / Andrea", fill=(255, 255, 255), font=f)
    d.text((a.width + gap + 16, 10), "V6 — HomeBankingPortal6 / Andrea (rev 47)", fill=(120, 230, 160), font=f)
    canvas.save(out)
    print("wrote", out, canvas.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
