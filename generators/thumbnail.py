#!/usr/bin/env python3
"""YouTube thumbnail (1280x720 PNG) for the N-Queens explainer.

    python3 generators/thumbnail.py --author "Abhijeet Karve" --out projects/nqueens/output/thumbnail.png

Big, high-contrast words that stay readable at phone size, the solved board
as the picture, and an author credit strip.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "generators"))
from nqueens import trace  # noqa: E402
from vedit import find_font  # noqa: E402

W, H = 1280, 720
BG_TOP, BG_BOTTOM = (11, 18, 34), (22, 36, 66)
WHITE, MUTED, YELLOW = "#FFFFFF", "#94A3B8", "#FACC15"
BLUE = "#3B82F6"
LIGHT, DARK = "#E2E8F0", "#94A3B8"


def font(name, size):
    return ImageFont.truetype(find_font(name), size)


def fit(draw, text, name, size, max_w):
    """Largest font size <= size at which text fits max_w."""
    while size > 20:
        f = font(name, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(name, size)


def board(n, size):
    """The solved board: one queen per row, highlighted green."""
    _, sol = trace(n)
    cell = size // n
    size = cell * n
    img = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(img)
    for r in range(n):
        for c in range(n):
            d.rectangle([c * cell, r * cell, (c + 1) * cell, (r + 1) * cell],
                        fill=LIGHT if (r + c) % 2 == 0 else DARK)
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    for r, c in enumerate(sol):
        od.rectangle([c * cell, r * cell, (c + 1) * cell, (r + 1) * cell], fill=(34, 197, 94, 190))
    img = Image.alpha_composite(img, over)
    d = ImageDraw.Draw(img)
    qf = font("DejaVu Sans", int(cell * 0.78))
    for r, c in enumerate(sol):
        d.text(((c + 0.5) * cell, (r + 0.5) * cell), "♛", font=qf, fill="#0B1220", anchor="mm",
               stroke_width=3, stroke_fill="#FFFFFF")
    return img


def make(n, author, out, tag="DAA  \u00b7  BACKTRACKING"):
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):                            # vertical gradient background
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))

    # board on the right, tilted slightly, with a soft blue glow behind it
    b = board(n, 470)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([730, 105, 730 + b.width + 50, 105 + b.height + 50],
                                           radius=30, fill=(59, 130, 246, 150))
    img.paste(glow.filter(ImageFilter.GaussianBlur(40)), (0, 0), glow.filter(ImageFilter.GaussianBlur(40)))
    frame = Image.new("RGBA", (b.width + 16, b.height + 16), "#FFFFFF")
    frame.paste(b, (8, 8), b)
    frame = frame.rotate(-4, resample=Image.BICUBIC, expand=True)
    img.paste(frame, (735, 95), frame)

    d = ImageDraw.Draw(img)
    x = 64
    # topic pill
    pf = font("Inter:extrabold", 30)
    label = tag
    w = d.textlength(label, font=pf)
    d.rounded_rectangle([x, 58, x + w + 44, 112], radius=27, fill=BLUE)
    d.text((x + 22, 85), label, font=pf, fill=WHITE, anchor="lm")

    # title: two huge lines
    t1 = fit(d, "N-QUEENS", "Inter Display:black", 170, 660)
    d.text((x - 4, 130), "N-QUEENS", font=t1, fill=WHITE, stroke_width=2, stroke_fill="#0B1220")
    t2 = fit(d, "PROBLEM", "Inter Display:black", 170, 660)
    d.text((x - 4, 300), "PROBLEM", font=t2, fill=YELLOW, stroke_width=2, stroke_fill="#0B1220")

    sub = font("Inter:semibold", 40)
    d.text((x, 485), "Solved step by step", font=sub, fill="#CBD5E1")

    # author strip
    d.rectangle([x, 580, x + 8, 662], fill=YELLOW)
    d.text((x + 28, 578), "PREPARED BY", font=font("Inter:bold", 26), fill=MUTED)
    d.text((x + 28, 608), author, font=fit(d, author, "Inter:extrabold", 50, 620), fill=WHITE)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--author", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="DAA  \u00b7  BACKTRACKING", help="text in the blue pill")
    args = ap.parse_args()
    out = make(args.n, args.author, args.out, args.tag)
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
