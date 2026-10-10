"""Reusable Manim building blocks for the DAA series.

Mascot  - "Algo", the on-screen guide: lip-syncs to the narration, blinks,
          changes expression, points, shows speech bubbles.
Board   - n x n chessboard with queens, kills and attack lanes.
Tree    - state space tree laid out from a backtracking trace.
Graph   - vertices + edges that can be colored.
CodePanel / Header / chips - text furniture.
"""
import numpy as np
from manim import (DOWN, LEFT, ORIGIN, RIGHT, UP, UL, UR, Animation, AnimationGroup, Arc, Circle, Create,
                   Dot, Ellipse, FadeIn, FadeOut, Flash, GrowFromCenter, Indicate, Line, MathTex, Polygon,
                   Rectangle, Rotate, RoundedRectangle, Square, Succession, Text, Transform, VGroup, VMobject,
                   Wiggle, linear, rate_functions, there_and_back)

# ---------------------------------------------------------------- palette
BG = "#0F172A"
PANEL = "#1E293B"
PANEL_EDGE = "#334155"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
ACCENT = "#3B82F6"        # UI highlight (current row, cursor)
SAFE = "#22C55E"
KILL = "#EF4444"
BACK = "#F59E0B"
GOLD = "#FACC15"
LIGHT_SQ = "#E2E8F0"
DARK_SQ = "#94A3B8"
UNIT_COLORS = {"I": "#22C55E", "II": "#EAB308", "III": "#EF4444", "IV": "#A855F7", "V": "#3B82F6"}
FONT = "Inter"
MONO = "DejaVu Sans Mono"
QUEEN = "♛"


def label(text, size=28, color=TEXT, weight="NORMAL", font=FONT):
    return Text(text, font=font, font_size=size, color=color, weight=weight)


def chip(text, color=ACCENT, size=24, text_color=TEXT, pad=0.22):
    t = label(text, size, text_color, "BOLD")
    box = RoundedRectangle(width=t.width + 2 * pad + 0.1, height=t.height + 1.4 * pad, corner_radius=0.18,
                           fill_color=color, fill_opacity=1, stroke_width=0)
    return VGroup(box, t.move_to(box))


def card(width, height, color=PANEL, edge=PANEL_EDGE):
    return RoundedRectangle(width=width, height=height, corner_radius=0.2, fill_color=color, fill_opacity=1,
                            stroke_color=edge, stroke_width=2)


# ---------------------------------------------------------------- header
class Header(VGroup):
    """Top bar: section name on the left, series badge on the right."""

    def __init__(self, unit, code, **kw):
        super().__init__(**kw)
        self.badge = chip(f"DAA  ·  UNIT {unit}  ·  {code}", UNIT_COLORS[unit], 20).to_corner(UR, buff=0.35)
        self.section = label("", 24, MUTED, "BOLD").to_corner(UL, buff=0.4)
        self.add(self.badge, self.section)

    def set_section(self, text):
        new = label(text.upper(), 24, MUTED, "BOLD").to_corner(UL, buff=0.4)
        old = self.section
        self.remove(old)
        self.section = new
        self.add(new)
        return AnimationGroup(FadeOut(old, shift=UP * 0.2), FadeIn(new, shift=UP * 0.2))


# ---------------------------------------------------------------- mascot
class Mascot(VGroup):
    """Algo: a friendly robot teacher. Call attach(clock, envelope) once; after that
    the mouth follows the narration loudness and the eyes blink on their own."""

    def __init__(self, accent="#EF4444", height=2.0, **kw):
        super().__init__(**kw)
        head = RoundedRectangle(width=1.7, height=1.35, corner_radius=0.42, fill_color="#E0E7FF", fill_opacity=1,
                                stroke_color="#6366F1", stroke_width=4)
        screen = RoundedRectangle(width=1.34, height=0.86, corner_radius=0.28, fill_color="#1E1B4B",
                                  fill_opacity=1, stroke_width=0).move_to(head).shift(DOWN * 0.04)
        self.eye_l = RoundedRectangle(width=0.2, height=0.3, corner_radius=0.09, fill_color="#67E8F9",
                                      fill_opacity=1, stroke_width=0).move_to(screen).shift(LEFT * 0.3 + UP * 0.12)
        self.eye_r = self.eye_l.copy().shift(RIGHT * 0.6)
        self.mouth = RoundedRectangle(width=0.36, height=0.06, corner_radius=0.03, fill_color="#67E8F9",
                                      fill_opacity=1, stroke_width=0).move_to(screen).shift(DOWN * 0.22)
        self.cheeks = VGroup(*[Circle(0.07, fill_color="#F472B6", fill_opacity=0.55, stroke_width=0)
                               .move_to(screen).shift(d * 0.5 + DOWN * 0.13) for d in (LEFT, RIGHT)])
        # mortarboard cap with a tassel in the unit colour
        cap_top = Polygon([-0.95, 0.0, 0], [0, 0.32, 0], [0.95, 0.0, 0], [0, -0.32, 0], fill_color="#1E293B",
                          fill_opacity=1, stroke_color="#0B1220", stroke_width=2)
        cap_base = Rectangle(width=0.9, height=0.22, fill_color="#1E293B", fill_opacity=1, stroke_width=0)
        cap = VGroup(cap_base.shift(DOWN * 0.14), cap_top).next_to(head, UP, buff=-0.2)
        tassel = VGroup(Line(cap_top.get_center(), cap_top.get_center() + RIGHT * 0.62 + DOWN * 0.05,
                             color=accent, stroke_width=4),
                        Line(cap_top.get_center() + RIGHT * 0.62 + DOWN * 0.05,
                             cap_top.get_center() + RIGHT * 0.66 + DOWN * 0.42, color=accent, stroke_width=4),
                        Dot(cap_top.get_center() + RIGHT * 0.66 + DOWN * 0.46, radius=0.06, color=accent))
        body = RoundedRectangle(width=1.0, height=0.7, corner_radius=0.25, fill_color="#C7D2FE", fill_opacity=1,
                                stroke_color="#6366F1", stroke_width=4).next_to(head, DOWN, buff=-0.05)
        badge = Circle(0.11, fill_color=accent, fill_opacity=1, stroke_width=0).move_to(body)
        self.arm_l = Line(body.get_left() + UP * 0.1, body.get_left() + LEFT * 0.35 + DOWN * 0.25,
                          color="#6366F1", stroke_width=7)
        self.arm_r = Line(body.get_right() + UP * 0.1, body.get_right() + RIGHT * 0.35 + DOWN * 0.25,
                          color="#6366F1", stroke_width=7)
        self.face = VGroup(self.eye_l, self.eye_r, self.mouth, self.cheeks)
        self.add(self.arm_l, self.arm_r, body, badge, head, screen, self.face, cap, tassel)
        self.scale_to_fit_height(height)
        self._eye_h = self.eye_l.height
        self._mouth_h = self.mouth.height
        self.mood = "neutral"

    # -- automatic life: lip sync + blinking
    def attach(self, clock, envelope, fps=30):
        """clock() -> seconds since the scene started; envelope[i] = narration loudness 0..1 at frame i."""
        env = np.asarray(envelope)

        def mouth_updater(m):
            i = int(clock() * fps)
            level = env[i] if 0 <= i < len(env) else 0.0
            h = self._mouth_h * (1 + 4.5 * level)
            if self.mood == "surprised":
                h = max(h, self._mouth_h * 3.2)
            m.stretch_to_fit_height(max(h, 1e-3))

        def blink_updater(e):
            t = clock() % 4.1
            target = self._eye_h * (0.12 if t < 0.12 else (1.25 if self.mood == "surprised" else 1.0))
            e.stretch_to_fit_height(target)

        self.mouth.add_updater(mouth_updater)
        self.eye_l.add_updater(blink_updater)
        self.eye_r.add_updater(blink_updater)
        return self

    # -- gestures (each returns an Animation)
    def set_mood(self, mood):
        self.mood = mood
        color = {"happy": "#86EFAC", "surprised": "#FCA5A5", "thinking": "#FDE68A"}.get(mood, "#67E8F9")
        return AnimationGroup(*[e.animate(run_time=0.3).set_fill(color) for e in (self.eye_l, self.eye_r, self.mouth)])

    def bounce(self):
        return Indicate(self, scale_factor=1.08, color=None, run_time=0.6)

    def wave(self):
        return Succession(Rotate(self.arm_r, 0.7, about_point=self.arm_r.get_start(), run_time=0.25),
                          Rotate(self.arm_r, -1.0, about_point=self.arm_r.get_start(), run_time=0.25),
                          Rotate(self.arm_r, 1.0, about_point=self.arm_r.get_start(), run_time=0.25),
                          Rotate(self.arm_r, -0.7, about_point=self.arm_r.get_start(), run_time=0.25))

    def point(self):
        """Raise the right arm toward the stage, then lower it."""
        return Succession(Rotate(self.arm_r, 1.2, about_point=self.arm_r.get_start(), run_time=0.3),
                          Animation(self.arm_r, run_time=0.9),
                          Rotate(self.arm_r, -1.2, about_point=self.arm_r.get_start(), run_time=0.3))

    def tilt(self):
        return Rotate(self, 0.12, rate_func=there_and_back, run_time=0.9)

    def bubble(self, text, width=3.6):
        t = Text(text, font=FONT, font_size=22, color="#0F172A", weight="BOLD")
        if t.width > width:
            t.scale_to_fit_width(width)
        box = RoundedRectangle(width=t.width + 0.4, height=t.height + 0.34, corner_radius=0.18, fill_color=TEXT,
                               fill_opacity=1, stroke_width=0)
        tail = Polygon([0, 0, 0], [0.3, 0, 0], [0.02, -0.28, 0], fill_color=TEXT, fill_opacity=1, stroke_width=0)
        g = VGroup(box, t.move_to(box))
        g.next_to(self, UP, buff=0.18).align_to(self, LEFT).shift(RIGHT * 0.35)
        tail.next_to(box, DOWN, buff=-0.02).align_to(box, LEFT).shift(RIGHT * 0.35)
        return VGroup(g, tail)


class FaceSpot(VGroup):
    """Where your face-cam goes (the video itself is laid in at the final mix): an accent
    ring with the same calls as Mascot, which do nothing - your face does the reacting."""

    def __init__(self, accent="#EF4444", radius=1.11, **kw):
        super().__init__(**kw)
        self.ring = Circle(radius=radius + 0.05, stroke_color=accent, stroke_width=6)
        self.add(self.ring)

    def attach(self, clock, envelope, fps=30):
        return self

    def _still(self):
        return Animation(self.ring)

    def set_mood(self, mood):
        return self._still()

    bounce = wave = point = tilt = _still


class NoMascot(VGroup):
    """Stand-in for videos with no on-screen guide: every gesture is a harmless no-op."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.dot = Dot(radius=0.001, fill_opacity=0, stroke_width=0).move_to([0, -12, 0])
        self.add(self.dot)

    def attach(self, clock, envelope, fps=30):
        return self

    def _still(self):
        return Animation(self.dot)

    def set_mood(self, mood):
        return self._still()

    bounce = wave = point = tilt = _still


# ---------------------------------------------------------------- chessboard
class Board(VGroup):
    def __init__(self, n, size=3.4, labels=True, **kw):
        super().__init__(**kw)
        self.n, self.cell = n, size / n
        self.squares = VGroup(*[Square(self.cell, stroke_width=0, fill_opacity=1,
                                       fill_color=LIGHT_SQ if (r + c) % 2 == 0 else DARK_SQ)
                                .move_to(self.pos(r, c)) for r in range(n) for c in range(n)])
        self.add(self.squares)
        if labels:
            fs = 22 if n <= 5 else 16
            self.row_labels = VGroup(*[label(str(r + 1), fs, MUTED).move_to(self.pos(r, 0) + LEFT * self.cell * 0.85)
                                       for r in range(n)])
            self.col_labels = VGroup(*[label(str(c + 1), fs, MUTED).move_to(self.pos(0, c) + UP * self.cell * 0.85)
                                       for c in range(n)])
            self.add(self.row_labels, self.col_labels)
        self.queens = {}

    def pos(self, r, c):
        o = self.squares.get_center() if hasattr(self, "squares") else ORIGIN   # squares only, not labels
        half = (self.n - 1) / 2
        return o + np.array([(c - half) * self.cell, (half - r) * self.cell, 0])

    def sq(self, r, c):
        return self.squares[r * self.n + c]

    def queen(self, r, c, color="#0B1220"):
        q = Text(QUEEN, font="DejaVu Sans", font_size=72 * self.cell, color=color)
        q.scale_to_fit_height(self.cell * 0.72).move_to(self.pos(r, c))
        return q

    def place(self, r, c):
        q = self.queen(r, c)
        self.queens[r] = q
        flash = self.sq(r, c).copy().set_fill(SAFE, 0.85)
        return AnimationGroup(FadeIn(flash, rate_func=there_and_back, remover=True), GrowFromCenter(q),
                              run_time=0.45), q

    def kill(self, r, c):
        """A red ghost queen flashes on the attacked square, then fades."""
        ghost = self.queen(r, c, KILL)
        tint = self.sq(r, c).copy().set_fill(KILL, 0.55)
        return FadeIn(VGroup(tint, ghost), rate_func=there_and_back, remover=True, run_time=0.45)

    def remove(self, r):
        q = self.queens.pop(r)
        ghost = q.copy().set_color(BACK)
        return AnimationGroup(Transform(q, ghost, run_time=0.2), FadeOut(q, shift=UP * 0.3, run_time=0.4))

    def attack_cells(self, r, c):
        return [(rr, cc) for rr in range(self.n) for cc in range(self.n)
                if (rr, cc) != (r, c) and (rr == r or cc == c or abs(rr - r) == abs(cc - c))]


# ---------------------------------------------------------------- state space tree
class Tree(VGroup):
    """Lays out every node a backtracking trace will create, so the tree can grow without moving.

    events: [("place"|"kill"|"back", level, value)], levels/values 0-based."""

    def __init__(self, events, width=6.0, height=4.2, r=0.17, level_names=None, value_fmt=lambda v: str(v + 1),
                 kill_label=False, **kw):
        super().__init__(**kw)
        self.r = r
        self.kill_label = kill_label        # killed nodes show the struck-out value instead of a plain cross
        nodes, stack = [{"parent": None, "level": -1, "kind": "root", "children": []}], [0]
        self.event_node = []
        for kind, level, value in events:
            if kind == "back":
                self.event_node.append(stack.pop())
                continue
            nodes.append({"parent": stack[-1], "level": level, "value": value, "kind": kind, "children": []})
            nodes[stack[-1]]["children"].append(len(nodes) - 1)
            self.event_node.append(len(nodes) - 1)
            if kind == "place":
                stack.append(len(nodes) - 1)
        # leaves get consecutive x slots; parents sit above the middle of their children
        slot = [0]

        def lay(i):
            ch = nodes[i]["children"]
            if not ch:
                nodes[i]["x"] = slot[0]
                slot[0] += 1
            else:
                for c in ch:
                    lay(c)
                nodes[i]["x"] = (nodes[ch[0]]["x"] + nodes[ch[-1]]["x"]) / 2
        lay(0)
        depth = max(n["level"] for n in nodes) + 2
        sx = width / max(slot[0] - 1, 1)
        sy = height / max(depth - 1, 1)
        self.nodes = nodes
        self.node_pos = [np.array([n["x"] * sx - width / 2, height / 2 - (n["level"] + 1) * sy, 0]) for n in nodes]
        self.mobs = [None] * len(nodes)
        self.edges = [None] * len(nodes)
        self.root = Dot(self.node_pos[0], radius=r * 0.75, color=TEXT)
        self._root0 = self.node_pos[0].copy()
        self.mobs[0] = self.root
        self.add(self.root)
        if level_names:
            self.level_labels = VGroup(*[label(name, 18, MUTED).move_to(np.array([-width / 2 - 0.55,
                                                                                   height / 2 - (k + 1) * sy, 0]))
                                         for k, name in enumerate(level_names)])
            self.add(self.level_labels)
        self.value_fmt = value_fmt

    def center_on(self, point):
        """Place the tree so its complete final layout (all future nodes) is centred on point."""
        xs = [p[0] for p in self.node_pos]
        ys = [p[1] for p in self.node_pos]
        left = min(xs) - (0.8 if hasattr(self, "level_labels") else self.r)
        full = np.array([(left + max(xs) + self.r) / 2, (min(ys) + max(ys)) / 2, 0])
        off = self.root.get_center() - self._root0
        self.shift(np.asarray(point) - (full + off))
        return self

    def grow(self, event_index):
        """Animation that adds the node created by event `event_index` (place or kill)."""
        i = self.event_node[event_index]
        n = self.nodes[i]
        off = self.root.get_center() - self._root0          # follow the tree wherever it was moved
        p, q = self.node_pos[n["parent"]] + off, self.node_pos[i] + off
        if n["kind"] == "kill" and self.kill_label:
            rk = self.r * 0.85
            node = VGroup(Circle(rk, color=KILL, fill_color=BG, fill_opacity=1, stroke_width=3),
                          label(self.value_fmt(n["value"]), 16, KILL, "BOLD"),
                          Line(np.array([-rk, -rk, 0]) * 0.6, np.array([rk, rk, 0]) * 0.6, color=KILL,
                               stroke_width=3)).move_to(q)
            edge = Line(p, q, color=KILL, stroke_width=2, stroke_opacity=0.6)
        elif n["kind"] == "kill":
            node = VGroup(Circle(self.r * 0.75, color=KILL, fill_color=BG, fill_opacity=1, stroke_width=3),
                          label("×", 20, KILL, "BOLD")).move_to(q)
            edge = Line(p, q, color=KILL, stroke_width=2, stroke_opacity=0.6)
        else:
            node = VGroup(Circle(self.r, color=SAFE, fill_color=BG, fill_opacity=1, stroke_width=3),
                          label(self.value_fmt(n["value"]), 18, TEXT, "BOLD")).move_to(q)
            edge = Line(p, q, color=MUTED, stroke_width=2.5)
        edge.put_start_and_end_on(p + (q - p) / np.linalg.norm(q - p) * self.r * 0.8,
                                  q - (q - p) / np.linalg.norm(q - p) * self.r * 0.8)
        self.mobs[i], self.edges[i] = node, edge
        self.add(edge, node)
        return AnimationGroup(Create(edge), GrowFromCenter(node), run_time=0.35)

    def mark_back(self, event_index):
        i = self.event_node[event_index]
        return self.mobs[i][0].animate(run_time=0.3).set_stroke(BACK)

    def path_to(self, event_index):
        i, path = self.event_node[event_index], []
        while i:
            path.append(i)
            i = self.nodes[i]["parent"]
        return path


# ---------------------------------------------------------------- graph
class Graph(VGroup):
    def __init__(self, positions, edges, names=None, r=0.36, **kw):
        super().__init__(**kw)
        self.r = r
        self.pos = {k: np.array([x, y, 0]) for k, (x, y) in positions.items()}
        self.edge_mobs = {}
        for a, b in edges:
            ln = Line(self.pos[a], self.pos[b], color=MUTED, stroke_width=4)
            self.edge_mobs[(a, b)] = self.edge_mobs[(b, a)] = ln
            self.add(ln)
        self.vert = {}
        for k, p in self.pos.items():
            c = Circle(r, color=TEXT, fill_color=PANEL, fill_opacity=1, stroke_width=4).move_to(p)
            t = label(str(k), 26, TEXT, "BOLD").move_to(p)
            self.vert[k] = VGroup(c, t)
            self.add(self.vert[k])
            if names:
                nm = label(names[k], 18, MUTED).next_to(c, DOWN if p[1] <= 0 else UP, buff=0.1)
                self.add(nm)
        self.adj = {k: set() for k in positions}
        for a, b in edges:
            self.adj[a].add(b)
            self.adj[b].add(a)

    def paint(self, k, color):
        return self.vert[k][0].animate(run_time=0.4).set_fill(color, 1)

    def flash_edges(self, k, color=GOLD):
        lines = [self.edge_mobs[(k, j)] for j in self.adj[k]]
        return AnimationGroup(*[Indicate(ln, color=color, scale_factor=1.0) for ln in lines], run_time=0.7)


# ---------------------------------------------------------------- code panel
class CodePanel(VGroup):
    def __init__(self, lines, title=None, font_size=22, width=None, **kw):
        super().__init__(**kw)
        # Text drops leading spaces, so indentation is applied as a shift of whole character widths
        rows = VGroup(*[Text((ln.strip() or " ").replace(" ", "\u00a0"), font=MONO, font_size=font_size, color=TEXT)
                        for ln in lines])
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        char_w = Text("M" * 10, font=MONO, font_size=font_size).width / 10
        for row, ln in zip(rows, lines):
            row.shift(RIGHT * char_w * (len(ln) - len(ln.lstrip(" "))))
        w = width or rows.width + 0.7
        self.box = card(w, rows.height + (1.0 if title else 0.6))
        rows.move_to(self.box).align_to(self.box, LEFT).shift(RIGHT * 0.35)
        if title:
            rows.shift(DOWN * 0.2)
            t = label(title, 20, MUTED, "BOLD").next_to(self.box.get_top(), DOWN, buff=0.15).align_to(rows, LEFT)
            self.add(self.box, t)
        else:
            self.add(self.box)
        self.rows = rows
        self.add(rows)
        self.cursor = None

    def highlight(self, i, color=ACCENT):
        row = self.rows[i]
        bar = Rectangle(width=self.box.width - 0.3, height=row.height + 0.12, fill_color=color, fill_opacity=0.28,
                        stroke_width=0).move_to(row).align_to(self.box, LEFT).shift(RIGHT * 0.15)
        if self.cursor is None:
            self.cursor = bar
            self.add_to_back(bar)
            self.box.set_z_index(-1)
            return FadeIn(bar, run_time=0.3)
        return self.cursor.animate(run_time=0.3).move_to(bar)
