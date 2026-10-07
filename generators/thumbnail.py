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


def graph_card(size=300):
    """Small 3-coloured graph (the graph-coloring example) on a white card."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=28, fill="#FFFFFF")
    s = size / 300
    pos = {1: (70, 80), 2: (230, 80), 3: (150, 150), 4: (70, 225), 5: (230, 225)}
    pos = {k: (x * s, y * s) for k, (x, y) in pos.items()}
    edges = [(1, 2), (1, 3), (2, 3), (2, 5), (3, 4), (3, 5), (4, 5)]
    colors = {1: "#EF4444", 2: "#22C55E", 3: "#3B82F6", 4: "#22C55E", 5: "#EF4444"}
    for a, b in edges:
        d.line([pos[a], pos[b]], fill="#334155", width=int(7 * s))
    r = 30 * s
    for k, (x, y) in pos.items():
        d.ellipse([x - r, y - r, x + r, y + r], fill=colors[k], outline="#0B1220", width=int(5 * s))
        d.text((x, y), str(k), font=font("Inter:extrabold", int(30 * s)), fill="#FFFFFF", anchor="mm")
    return img


def tree_card(w=490, h=470):
    """A state space tree on a white card: dead branches crossed out in red, the answer path in green."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=30, fill="#FFFFFF")
    ys = [70, 185, 300, 410]
    root = (w / 2, ys[0])
    lv1 = [(w * x, ys[1]) for x in (0.2, 0.56, 0.86)]
    nodes = [(root, None, "ok")] + [(p, root, k) for p, k in zip(lv1, ("path", "ok", "dead"))]
    a, b = lv1[0], lv1[1]
    lv2 = [((a[0] - 50, ys[2]), a, "dead"), ((a[0] + 50, ys[2]), a, "path"),
           ((b[0] - 32, ys[2]), b, "dead"), ((b[0] + 52, ys[2]), b, "ok")]
    lv3 = [((a[0] + 18, ys[3]), lv2[1][0], "dead"), ((a[0] + 82, ys[3]), lv2[1][0], "path"),
           ((b[0] + 52, ys[3]), lv2[3][0], "ok")]
    nodes += lv2 + lv3
    colors = {"ok": "#334155", "path": "#22C55E", "dead": "#EF4444"}
    for pos, parent, kind in nodes:
        if parent:
            d.line([parent, pos], fill=colors["path"] if kind == "path" else "#94A3B8", width=8 if kind == "path" else 5)
    for pos, parent, kind in nodes:
        r = 26 if kind != "dead" else 22
        x, y = pos
        if kind == "dead":
            d.ellipse([x - r, y - r, x + r, y + r], fill="#FFFFFF", outline=colors["dead"], width=6)
            d.line([x - 12, y - 12, x + 12, y + 12], fill=colors["dead"], width=6)
            d.line([x - 12, y + 12, x + 12, y - 12], fill=colors["dead"], width=6)
        else:
            d.ellipse([x - r, y - r, x + r, y + r], fill=colors[kind], outline="#0B1220", width=4)
    return img


def make(n, author, out, tag="DAA  \u00b7  BACKTRACKING", title=("N-QUEENS", "PROBLEM"),
         subtitle="Solved step by step", credit="PREPARED BY", tag_color=BLUE, visual="board"):
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):                            # vertical gradient background
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))

    # board (or state space tree) on the right, tilted slightly, with a soft glow behind it
    b = tree_card() if visual == "tree" else board(n, 470)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([730, 105, 730 + b.width + 50, 105 + b.height + 50],
                                           radius=30, fill=(59, 130, 246, 150))
    img.paste(glow.filter(ImageFilter.GaussianBlur(40)), (0, 0), glow.filter(ImageFilter.GaussianBlur(40)))
    frame = Image.new("RGBA", (b.width + 16, b.height + 16), "#FFFFFF")
    frame.paste(b, (8, 8), b)
    frame = frame.rotate(-4, resample=Image.BICUBIC, expand=True)
    img.paste(frame, (735, 95), frame)
    if "graph" in visual:                         # the second topic, overlapping the board's corner
        g = graph_card(250).rotate(5, resample=Image.BICUBIC, expand=True)
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([655, 420, 655 + 255, 420 + 255], radius=30, fill=(0, 0, 0, 140))
        img.paste(shadow.filter(ImageFilter.GaussianBlur(14)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(14)))
        img.paste(g, (640, 400), g)

    d = ImageDraw.Draw(img)
    x = 64
    # topic pill
    pf = font("Inter:extrabold", 30)
    w = d.textlength(tag, font=pf)
    d.rounded_rectangle([x, 58, x + w + 44, 112], radius=27, fill=tag_color)
    d.text((x + 22, 85), tag, font=pf, fill=WHITE, anchor="lm")

    # title: up to two huge lines (white, then yellow)
    max_w = 560 if "graph" in visual else 660
    y = 130
    for i, line in enumerate(title[:2]):
        f = fit(d, line, "Inter Display:black", 170 if len(title) == 2 else 190, max_w)
        d.text((x - 4, y), line, font=f, fill=WHITE if i == 0 else YELLOW, stroke_width=2, stroke_fill="#0B1220")
        y += int(f.size * 1.0) + 8
    if subtitle:
        d.text((x, max(y + 14, 470)), subtitle, font=font("Inter:semibold", 40), fill="#CBD5E1")

    # author strip
    d.rectangle([x, 580, x + 8, 662], fill=YELLOW)
    d.text((x + 28, 578), credit, font=font("Inter:bold", 26), fill=MUTED)
    d.text((x + 28, 608), author, font=fit(d, author, "Inter:extrabold", 50, 560), fill=WHITE)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--author", required=True)
    ap.add_argument("--n", type=int, default=6, help="board size of the picture")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="DAA  \u00b7  BACKTRACKING", help="text in the pill")
    ap.add_argument("--tag-color", default=BLUE, help="pill colour (e.g. the unit colour)")
    ap.add_argument("--title", default="N-QUEENS|PROBLEM", help="one or two title lines, split with |")
    ap.add_argument("--subtitle", default="Solved step by step")
    ap.add_argument("--credit", default="PREPARED BY", help="label above the author name")
    ap.add_argument("--visual", default="board", choices=["board", "board+graph", "tree"])
    args = ap.parse_args()
    out = make(args.n, args.author, args.out, args.tag, args.title.split("|"), args.subtitle, args.credit,
               args.tag_color, args.visual)
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
