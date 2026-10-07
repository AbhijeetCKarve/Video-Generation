"""Video 3.1 - Backtracking Strategy Fundamentals. Rendered by build.py (needs SCHEDULE / ENVELOPE env vars)."""
import json
import os
import sys
from itertools import product
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from manim import *  # noqa: E402,F401,F403
from kit import *    # noqa: E402,F401,F403

S = json.loads(Path(os.environ["SCHEDULE"]).read_text())
ENV = np.load(os.environ["ENVELOPE"])
SFX_LOG = os.environ.get("SFX_LOG")
config.background_color = BG

STAGE = np.array([0.9, 0.15, 0])
MASCOT_POS = np.array([-5.75, -1.05, 0])
VARIANT = os.environ.get("VARIANT", "")
FACE = VARIANT == "face"          # your camera in a circle where the mascot stands
FACE_POS = np.array([-6.07, -1.05, 0])

STUDENTS = "ABC"
NAMES = {"A": "Aman", "B": "Bhavna", "C": "Chirag"}
SCOL = {"A": "#3B82F6", "B": "#EC4899", "C": "#A855F7"}


def bt_trace(values, n, ok):
    """Backtracking over x[0..n-1] with every value tried at every level: [("place"|"kill"|"back", level, index)]."""
    ev, x = [], []

    def solve(k):
        for i, v in enumerate(values):
            if ok(x + [v]):
                x.append(v)
                ev.append(("place", k, i))
                if k < n - 1:
                    solve(k + 1)
                x.pop()
                ev.append(("back", k, i))
            else:
                ev.append(("kill", k, i))
    solve(0)
    return ev


def seat_ok(t):
    return len(set(t)) == len(t) and all({a, b} != {"A", "B"} for a, b in zip(t, t[1:]))


def binary_ok(t):
    return all(not (a == "1" and b == "1") for a, b in zip(t, t[1:]))


SEAT_EV = bt_trace(STUDENTS, 3, seat_ok)
BIN_EV = bt_trace("01", 3, binary_ok)


def token(s, r=0.42):
    return VGroup(Circle(r, fill_color=SCOL[s], fill_opacity=1, stroke_color=TEXT, stroke_width=3),
                  label(s, int(r * 80), TEXT, "BOLD"))


def seat(k):
    box = RoundedRectangle(width=1.6, height=1.1, corner_radius=0.2, fill_color=PANEL, fill_opacity=1,
                           stroke_color=PANEL_EDGE, stroke_width=3)
    return VGroup(box, label(f"seat {k}", 22, MUTED).next_to(box, DOWN, buff=0.12))


def struck(text, size=26):
    t = label(text, size, KILL, "BOLD", font=MONO)
    return VGroup(t, Line(t.get_left() + LEFT * 0.08, t.get_right() + RIGHT * 0.08, color=KILL, stroke_width=4))


class Video(Scene):
    # ------------------------------------------------------------ timing helpers
    def now(self):
        return self.renderer.time

    def until(self, t):
        dt = t - self.now()
        if dt > 1 / 30:
            self.wait(dt)

    def at(self, b, i):
        self.until(b["phrases"][min(i, len(b["phrases"]) - 1)]["start"])

    def phrase_len(self, b, i):
        ph = b["phrases"][min(i, len(b["phrases"]) - 1)]
        return ph["end"] - ph["start"]

    def sfx(self, kind, delay=0.0):
        self.sfx_events.append((round(self.now() + delay, 3), kind))

    def go(self, *anims, run_time=None):
        anims = [a for a in anims if a is not None] + self.pending
        self.pending = []
        if anims:
            if run_time:
                self.play(*anims, run_time=run_time)
            else:
                self.play(*anims)

    def clear(self, *keep, run_time=0.5):
        gone = [m for m in self.stage if m not in keep]
        self.stage = VGroup(*keep)
        if gone:
            self.go(*[FadeOut(m) for m in gone], run_time=run_time)

    def show(self, *mobs, anim=FadeIn, run_time=0.6, **kw):
        for m in mobs:
            self.stage.add(m)
        self.go(*[anim(m, **kw) for m in mobs], run_time=run_time)

    def drop(self, *mobs, run_time=0.4):
        """Fade out a few stage objects, keep the rest."""
        for m in mobs:
            self.stage.remove(m)
        self.go(*[FadeOut(m) for m in mobs], run_time=run_time)

    def react(self, mood):
        m = self.mascot
        if not self.mascot_on:
            return
        if mood == "excited":
            self.pending += [m.set_mood("happy"), m.bounce()]
        elif mood == "warm":
            self.pending += [m.set_mood("happy")]
        elif mood == "curious":
            self.pending += [m.set_mood("thinking"), m.tilt()]
        elif mood == "emphatic":
            self.pending += [m.set_mood("neutral"), m.point()]
        else:
            self.pending += [m.set_mood("neutral")]

    def say(self, text, hold=None):
        """Speech bubble from the mascot; removed at the next bubble or explicitly."""
        self.unsay()
        if FACE:                         # you say it yourself on camera
            return
        self.bubble_mob = self.mascot.bubble(text)
        self.go(FadeIn(self.bubble_mob, shift=UP * 0.15), run_time=0.3)

    def unsay(self):
        if getattr(self, "bubble_mob", None) is not None:
            self.go(FadeOut(self.bubble_mob), run_time=0.25)
            self.bubble_mob = None

    # ------------------------------------------------------------ main loop
    def construct(self):
        self.sfx_events, self.pending, self.stage = [], [], VGroup()
        self.mascot_on = False
        thumb = ImageMobject(str(Path(os.environ["SCHEDULE"]).parents[1] / "output" / "thumbnail.png"))
        thumb.scale_to_fit_width(config.frame_width)
        self.add(thumb)
        self.until(S["intro"] - 0.5)
        self.play(FadeOut(thumb), run_time=0.5)
        self.header = Header(S["unit"], S["code"])
        self.header_on = False
        if FACE:
            self.mascot = FaceSpot(accent=UNIT_COLORS[S["unit"]], radius=0.926).move_to(FACE_POS)
        else:
            self.mascot = Mascot(accent=UNIT_COLORS[S["unit"]], height=1.9).move_to(MASCOT_POS + LEFT * 4)
            self.mascot.attach(self.now, ENV)
            self.add(self.mascot)
        for b in S["beats"]:
            self.until(b["start"])
            if b["section"] and self.header_on:
                self.pending.append(self.header.set_section(b["section"]))
            self.react(b["mood"])
            getattr(self, "b_" + b["key"])(b)
            self.go()
            if self.now() > b["end"] + 0.2:
                print(f"OVERRUN {b['key']}: ended {self.now():.2f}s, window closed {b['end']:.2f}s")
        self.until(S["end_card"])
        self.end_card()
        self.until(S["total"])
        if SFX_LOG:
            Path(SFX_LOG).write_text(json.dumps(self.sfx_events))

    # ------------------------------------------------------------ hook: the maze
    def b_hook_maze(self, b):
        o = STAGE + DOWN * 0.1
        pts = {"S": (-4.2, -1.0), "J1": (-2.0, -1.0), "D1": (-2.0, 1.7), "J2": (0.9, -1.0), "K": (0.9, 1.0),
               "D2": (3.3, 1.0), "E": (4.4, -1.0)}
        P = {k: o + np.array([x, y, 0]) for k, (x, y) in pts.items()}
        corridors = [("S", "J1"), ("J1", "D1"), ("J1", "J2"), ("J2", "K"), ("K", "D2"), ("J2", "E")]
        maze = VGroup(*[Line(P[a], P[c], color=PANEL_EDGE, stroke_width=30) for a, c in corridors],
                      *[Dot(p, radius=0.15, color=PANEL_EDGE) for p in P.values()])
        start = label("START", 22, MUTED, "BOLD").next_to(P["S"], DOWN, buff=0.3)
        exit_ = chip("EXIT", SAFE, 22).next_to(P["E"], RIGHT, buff=0.15)
        walker = Dot(P["S"], radius=0.13, color=GOLD).set_z_index(5)
        self.show(maze, start, exit_, run_time=0.7)
        self.add(walker)
        self.stage.add(walker)
        self.maze = VGroup(maze, start, exit_)
        self.at(b, 1)
        moves = [("S", "J1", GOLD), ("J1", "D1", GOLD), ("D1", None, None), ("D1", "J1", BACK), ("J1", "J2", GOLD),
                 ("J2", "K", GOLD), ("K", "D2", GOLD), ("D2", None, None), ("D2", "K", BACK), ("K", "J2", BACK),
                 ("J2", "E", SAFE)]
        step = max(0.3, min(0.6, self.phrase_len(b, 1) / 12))
        trails = VGroup()
        for a, c, col in moves:
            if c is None:                                   # dead end
                x = label("×", 54, KILL, "BOLD").move_to(P[a])
                trails.add(x)
                self.go(FadeIn(x, scale=1.6), run_time=step)
                self.sfx("kill", -step)
                continue
            tr = Line(P[a], P[c], color=col, stroke_width=8)
            trails.add(tr)
            self.go(Create(tr), walker.animate.move_to(P[c]), run_time=step)
            if col == BACK:
                self.sfx("back", -step)
        self.stage.add(trails)
        self.maze.add(trails, walker)
        self.go(Flash(P["E"], color=SAFE, line_length=0.3), run_time=0.5)
        self.sfx("chime")

    def b_hook_name(self, b):
        self.go(self.maze.animate.set_opacity(0.18).scale(0.8).move_to(STAGE + DOWN * 0.6), run_time=0.6)
        fwd = chip("go forward  →", SAFE, 26)
        back = chip("←  step back when stuck", BACK, 26, "#0F172A")
        g = VGroup(fwd, back).arrange(RIGHT, buff=0.5).move_to(STAGE + DOWN * 1.8)
        self.stage.add(g)
        self.go(LaggedStart(FadeIn(fwd, shift=RIGHT * 0.3), FadeIn(back, shift=LEFT * 0.3), lag_ratio=0.6), run_time=1.2)
        self.at(b, 1)
        title = label("BACKTRACKING", 84, GOLD, "BOLD").move_to(STAGE + UP * 0.9)
        self.show(title, anim=GrowFromCenter, run_time=0.7)
        self.sfx("whoosh")

    def b_hook_mascot(self, b):
        self.clear(run_time=0.5)
        self.mascot_on = True
        if FACE:                         # the face-cam fades in inside this ring at the mix
            self.go(GrowFromCenter(self.mascot), run_time=0.6)
        else:
            self.go(self.mascot.animate.move_to(MASCOT_POS), run_time=0.8)
        self.sfx("whoosh")
        self.go(self.mascot.wave(), run_time=1.0)
        series = label("DAA SERIES", 34, MUTED, "BOLD")
        by = label("by Abhijeet Karve", 54, TEXT, "BOLD")
        g = VGroup(series, by).arrange(DOWN, buff=0.25).move_to(STAGE + UP * 0.4)
        self.show(g, anim=FadeIn, run_time=0.6, shift=UP * 0.2)
        self.at(b, 1)
        # with the real voice you introduce yourself, so Algo just greets the students
        self.say("Hi, students!" if VARIANT == "real" else "Hi! I'm Algo")
        guide = label("your guide, step by step", 30, ACCENT).next_to(g, DOWN, buff=0.4)
        self.show(guide, run_time=0.5)

    def b_syllabus(self, b):
        self.unsay()
        self.clear(run_time=0.4)
        self.header_on = True
        self.header.set_section("Today's plan")
        self.add(self.header)
        self.go(FadeIn(self.header, shift=DOWN * 0.2), run_time=0.5)
        unit = chip("UNIT III  ·  BACKTRACKING", UNIT_COLORS["III"], 34).move_to(STAGE + UP * 2.0)
        self.show(unit, anim=GrowFromCenter, run_time=0.5)
        self.unit_chip = unit
        self.at(b, 1)
        topics = ["State space tree", "Explicit & implicit constraints", "Depth-first search", "Control abstraction"]
        rows = VGroup(*[VGroup(chip(str(i + 1), ACCENT, 28), label(t, 36, TEXT, "BOLD")).arrange(RIGHT, buff=0.3)
                        for i, t in enumerate(topics)])
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.32).move_to(STAGE + DOWN * 0.45)
        self.stage.add(rows)
        self.go(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in rows], lag_ratio=0.5), run_time=2.2)
        self.sfx("pop")

    def b_exam(self, b):
        star = chip("★  Exam favourite", GOLD, 26, "#0F172A").next_to(self.unit_chip, RIGHT, buff=0.3)
        self.show(star, anim=GrowFromCenter, run_time=0.5)
        self.sfx("pop")
        self.at(b, 1)
        self.say("Tips at the end!")

    # ------------------------------------------------------------ brute force vs backtracking
    def seats_and_students(self):
        seats = VGroup(*[seat(k + 1).move_to(STAGE + np.array([x, -0.55, 0])) for k, x in enumerate((-2.2, 0, 2.2))])
        tokens = {s: token(s).move_to(STAGE + np.array([x, 1.75, 0])) for s, x in zip(STUDENTS, (-2.2, 0, 2.2))}
        names = VGroup(*[label(NAMES[s], 22, MUTED).next_to(tokens[s], DOWN, buff=0.1) for s in STUDENTS])
        return seats, tokens, names

    def b_bf_problem(self, b):
        self.unsay()
        self.clear(run_time=0.4)
        self.seats, self.tokens, self.names = self.seats_and_students()
        self.show(self.seats, run_time=0.6)
        self.at(b, 1)
        self.stage.add(*self.tokens.values(), self.names)
        self.go(LaggedStart(*[GrowFromCenter(self.tokens[s]) for s in STUDENTS], lag_ratio=0.4),
                FadeIn(self.names), run_time=1.4)
        self.sfx("pop")

    def b_bf_rule(self, b):
        a, bb = self.tokens["A"], self.tokens["B"]
        chat = chip("chat chat!", PANEL_EDGE, 20).move_to((a.get_center() + bb.get_center()) / 2 + UP * 0.75)
        self.show(chat, anim=GrowFromCenter, run_time=0.4)
        self.go(Wiggle(a), Wiggle(bb), run_time=1.0)
        self.at(b, 1)
        rule = VGroup(card(6.4, 0.85, edge=KILL), label("Rule:  A and B must not sit side by side", 26, TEXT, "BOLD"))
        rule[1].move_to(rule[0])
        rule.move_to(STAGE + DOWN * 2.2)
        self.show(rule, run_time=0.5, shift=UP * 0.2)
        self.sfx("pop")
        self.chat = chat

    def b_bf_brute(self, b):
        self.clear(run_time=0.4)
        tuples = ["".join(t) for t in product(STUDENTS, repeat=3)]
        grid = VGroup(*[Text(" ".join(t), font=MONO, font_size=26, color=TEXT,
                             t2c={s: SCOL[s] for s in STUDENTS}) for t in tuples])
        grid.arrange_in_grid(rows=3, cols=9, buff=(0.38, 0.4)).move_to(STAGE + UP * 0.2)
        self.grid, self.tuples = grid, tuples
        self.stage.add(grid)
        self.go(LaggedStart(*[FadeIn(t, scale=0.8) for t in grid], lag_ratio=0.06), run_time=2.2)
        self.at(b, 1)
        marks = [t.animate.set_opacity(1 if seat_ok(list(s)) else 0.25) for t, s in zip(grid, tuples)]
        self.go(LaggedStart(*marks, lag_ratio=0.05), run_time=2.0)

    def b_bf_count(self, b):
        f = MathTex(r"3 \times 3 \times 3 = 27", color=TEXT).scale(1.3).move_to(STAGE + UP * 2.2)
        self.show(f, anim=Write, run_time=1.2)
        self.at(b, 1)
        c = chip("27 complete arrangements to build and test", KILL, 26).move_to(STAGE + DOWN * 1.9)
        self.show(c, anim=GrowFromCenter, run_time=0.5)
        self.sfx("pop")

    def b_bf_idea(self, b):
        self.clear(run_time=0.4)
        self.seats, self.tokens, self.names = self.seats_and_students()
        self.show(self.seats, *self.tokens.values(), self.names, run_time=0.6)
        self.at(b, 1)
        a = self.tokens["A"]
        self.go(a.animate.move_to(self.seats[0][0]), run_time=0.6)
        self.sfx("place", -0.2)
        ok = label("✓", 40, SAFE, "BOLD").next_to(self.seats[0][0], UP, buff=0.15)
        self.show(ok, run_time=0.3)
        self.ok_mark = ok

    def b_bf_kill(self, b):
        bb = self.tokens["B"]
        home = bb.get_center()
        self.go(bb.animate.move_to(self.seats[1][0]), run_time=0.6)
        self.sfx("place", -0.2)
        bad = label("A next to B  ×", 26, KILL, "BOLD").next_to(self.seats[1][0], UP, buff=0.15)
        self.show(bad, run_time=0.3)
        self.go(Indicate(self.seats[1][0], color=KILL, scale_factor=1.1), run_time=0.5)
        self.sfx("kill", -0.4)
        self.go(bb.animate.move_to(home), run_time=0.5)
        self.at(b, 1)
        gone = VGroup(*[struck(t) for t in ("A B A", "A B B", "A B C")]).arrange(RIGHT, buff=0.6)
        note = label("never built", 24, MUTED)
        row = VGroup(gone, note).arrange(RIGHT, buff=0.5).move_to(STAGE + DOWN * 2.15)
        self.stage.add(row)
        self.go(LaggedStart(*[FadeIn(g, shift=DOWN * 0.2) for g in gone], lag_ratio=0.3), FadeIn(note), run_time=1.2)
        self.sfx("kill")

    # ------------------------------------------------------------ tuple + constraints
    def b_tuple(self, b):
        self.clear(run_time=0.4)
        t = label("A solution is a tuple", 34, MUTED, "BOLD").move_to(STAGE + UP * 1.5)
        self.show(t, run_time=0.5)
        self.at(b, 1)
        f = MathTex(r"x = (x_1,\ x_2,\ \dots,\ x_n)", color=TEXT).scale(1.5).move_to(STAGE + UP * 0.2)
        self.show(f, anim=Write, run_time=1.2)
        self.tuple_tex, self.tuple_title = f, t

    def b_tuple_ex(self, b):
        self.drop(self.tuple_title)
        self.go(self.tuple_tex.animate.scale(0.6).move_to(STAGE + UP * 2.3), run_time=0.5)
        seats = VGroup(*[seat(k + 1).move_to(STAGE + np.array([x, -0.1, 0])) for k, x in enumerate((-2.2, 0, 2.2))])
        xs = VGroup(*[MathTex(f"x_{k + 1}", color=ACCENT).scale(0.9).next_to(seats[k][0], UP, buff=0.2)
                      for k in range(3)])
        self.show(seats, xs, run_time=0.6)
        self.at(b, 1)
        toks = [token(s).move_to(seats[k][0]) for k, s in enumerate("ACB")]
        self.stage.add(*toks)
        self.go(LaggedStart(*[FadeIn(t, shift=DOWN * 0.4) for t in toks], lag_ratio=0.4), run_time=1.2)
        self.sfx("place", -0.6)
        ans = MathTex(r"(A,\ C,\ B)", color=TEXT).scale(1.0).move_to(STAGE + DOWN * 1.9)
        names = label("Aman,  Chirag,  Bhavna", 24, MUTED).next_to(ans, RIGHT, buff=0.5)
        self.show(ans, names, run_time=0.5)

    def b_c_intro(self, b):
        self.clear(run_time=0.4)
        self.ccards = {}
        for side, title, col, tc in ((-1, "EXPLICIT", ACCENT, TEXT), (1, "IMPLICIT", GOLD, "#0F172A")):
            box = card(4.5, 3.7).move_to(STAGE + np.array([side * 2.4, 0.35, 0]))
            head = chip(title, col, 28, tc).next_to(box.get_top(), DOWN, buff=0.25)
            self.ccards[title] = (box, head)
        self.at(b, 1)
        self.show(*[VGroup(*v) for v in self.ccards.values()], run_time=0.8, shift=UP * 0.2)

    def card_line(self, title, mob, row):
        box, head = self.ccards[title]
        return mob.move_to(box.get_top() + DOWN * (1.15 + 0.62 * row))

    def b_c_explicit(self, b):
        l1 = self.card_line("EXPLICIT", label("each variable on its own", 26, TEXT, "BOLD"), 0)
        self.show(l1, run_time=0.5)
        self.at(b, 1)
        f = self.card_line("EXPLICIT", MathTex(r"x_i \in \{A,\ B,\ C\}", color=ACCENT).scale(1.0), 1)
        self.show(f, anim=Write, run_time=0.8)

    def b_c_space(self, b):
        l1 = self.card_line("EXPLICIT", label("solution space", 24, MUTED), 2.2)
        self.show(l1, run_time=0.4)
        self.at(b, 1)
        f = self.card_line("EXPLICIT", MathTex(r"3^3 = 27 \text{ tuples}", color=TEXT).scale(0.9), 3.0)
        self.show(f, anim=Write, run_time=0.7)

    def b_c_implicit(self, b):
        l1 = self.card_line("IMPLICIT", label("variables related to each other", 26, TEXT, "BOLD"), 0)
        self.show(l1, run_time=0.5)
        self.at(b, 1)
        l2 = self.card_line("IMPLICIT", label("which tuples are answers", 24, MUTED), 0.8)
        self.show(l2, run_time=0.4)

    def b_c_implicit_ex(self, b):
        self.at(b, 1)
        r1 = VGroup(MathTex(r"x_i \neq x_j", color=GOLD).scale(0.9), label("nobody seated twice", 22, MUTED)
                    ).arrange(RIGHT, buff=0.25)
        r2 = label("A and B not neighbours", 24, GOLD, "BOLD")
        self.show(self.card_line("IMPLICIT", r1, 2.0), run_time=0.5)
        self.sfx("pop", -0.3)
        self.show(self.card_line("IMPLICIT", r2, 2.9), run_time=0.5)
        self.sfx("pop", -0.3)

    def b_c_trick(self, b):
        left = chip("ONE variable", ACCENT, 24).next_to(self.ccards["EXPLICIT"][0], DOWN, buff=0.3)
        self.show(left, anim=GrowFromCenter, run_time=0.4)
        self.at(b, 1)
        right = chip("RELATION between variables", GOLD, 24, "#0F172A").next_to(self.ccards["IMPLICIT"][0], DOWN, buff=0.3)
        self.show(right, anim=GrowFromCenter, run_time=0.4)

    # ------------------------------------------------------------ the state space tree
    def b_t_intro(self, b):
        self.clear(run_time=0.4)
        self.tree = Tree(SEAT_EV, width=8.0, height=3.8, r=0.2, level_names=["seat 1", "seat 2", "seat 3"],
                         value_fmt=lambda v: STUDENTS[v], kill_label=True)
        self.tree.center_on(STAGE + RIGHT * 0.35 + UP * 0.3)
        self.tree.level_labels.set_opacity(0)
        self.show(self.tree, run_time=0.5)
        self.ev_i = 0
        self.at(b, 1)
        empty = label("empty", 20, MUTED).next_to(self.tree.root, RIGHT, buff=0.2)
        self.show(empty, run_time=0.4)
        self.go(Indicate(self.tree.root, color=GOLD, scale_factor=1.8), run_time=0.7)
        self.empty_tag = empty

    def b_t_levels(self, b):
        self.go(LaggedStart(*[l.animate.set_opacity(1) for l in self.tree.level_labels], lag_ratio=0.4), run_time=1.4)
        self.at(b, 1)
        c = chip("edge = one choice", PANEL_EDGE, 22).move_to(STAGE + np.array([3.6, 2.3, 0]))
        self.show(c, run_time=0.4)
        self.edge_chip = c

    def run(self, b, phrase, n, per=0.5):
        self.at(b, phrase)
        span = self.phrase_len(b, phrase)
        step = max(0.28, min(per, span / max(n, 1)))
        for _ in range(n):
            kind = SEAT_EV[self.ev_i][0]
            if kind == "back":
                self.go(self.tree.mark_back(self.ev_i), run_time=step)
                self.sfx("back", -step)
            else:
                self.go(self.tree.grow(self.ev_i), run_time=step)
                self.sfx("place" if kind == "place" else "kill", -step)
            self.ev_i += 1

    def node_of(self, ev):
        return self.tree.mobs[self.tree.event_node[ev]]

    def mark_answer(self, ev, text):
        path = self.tree.path_to(ev)
        tag = chip(text + "  ✓", SAFE, 22).next_to(self.node_of(ev), DOWN, buff=0.18)
        self.stage.add(tag)
        self.answer_tags = getattr(self, "answer_tags", []) + [tag]
        self.go(*[self.tree.mobs[i][0].animate.set_fill(SAFE, 0.6) for i in path], GrowFromCenter(tag),
                self.mascot.set_mood("happy"), self.mascot.bounce(), run_time=0.8)
        self.sfx("chime")

    def b_t_a(self, b):
        self.drop(self.empty_tag, self.edge_chip)
        self.run(b, 0, 1)                                  # A on seat 1
        self.at(b, 1)
        self.go(Indicate(self.node_of(0), color=GOLD, scale_factor=1.4), run_time=0.7)

    def b_t_a2(self, b):
        self.run(b, 0, 1)                                  # A A: seated twice
        self.run(b, 1, 1)                                  # A B: neighbours
        self.run(b, 2, 1)                                  # A C

    def b_t_acb(self, b):
        self.run(b, 0, 2, per=0.6)                         # A C A dies, A C B lives
        self.at(b, 1)
        self.mark_answer(5, "A C B")

    def b_t_back(self, b):
        self.run(b, 0, 4, per=0.4)                         # back, A C C dies, back, back
        self.run(b, 1, 1)                                  # B on seat 1

    def b_t_bca(self, b):
        self.run(b, 0, 4, per=0.45)                        # B A, B B die, B C, B C A
        self.at(b, 1)
        self.mark_answer(14, "B C A")

    def b_t_c(self, b):
        self.run(b, 0, 6, per=0.3)                         # finish B, then C on seat 1
        self.run(b, 1, 12, per=0.36)                       # everything under C dies

    def b_t_result(self, b):
        self.at(b, 1)
        res = VGroup(chip("24 nodes generated", SAFE, 24), label("vs", 24, MUTED),
                     chip("39 in the full tree", PANEL_EDGE, 24)).arrange(RIGHT, buff=0.3)
        res.move_to(STAGE + DOWN * 2.45)
        self.drop(*self.answer_tags)
        self.show(res, run_time=0.5, shift=UP * 0.2)
        self.sfx("pop")
        self.bottom = res

    # ------------------------------------------------------------ terminology
    def bottom_note(self, *mobs):
        if getattr(self, "bottom", None) is not None:
            self.drop(self.bottom, run_time=0.3)
        g = VGroup(*mobs).arrange(RIGHT, buff=0.35).move_to(STAGE + DOWN * 2.45)
        self.bottom = g
        self.show(g, run_time=0.4, shift=UP * 0.15)
        return g

    def ring(self, i, color, width=5):
        return Circle(self.tree.r * 1.35, color=color, stroke_width=width).move_to(self.tree.mobs[i])

    def b_n_states(self, b):
        self.at(b, 1)
        nodes = [m for m in self.tree.mobs if m is not None]
        self.bottom_note(chip("every node = a problem state", ACCENT, 24))
        self.go(LaggedStart(*[Indicate(m, color=ACCENT, scale_factor=1.3) for m in nodes], lag_ratio=0.03), run_time=1.6)

    def b_n_solution(self, b):
        leaves = [i for i, n in enumerate(self.tree.nodes) if n.get("level") == 2]
        rings = VGroup(*[self.ring(i, ACCENT, 4) for i in leaves])
        self.bottom_note(chip("complete tuple = solution state", ACCENT, 24))
        self.stage.add(rings)
        self.go(LaggedStart(*[Create(r) for r in rings], lag_ratio=0.05), run_time=1.0)
        self.at(b, 1)
        gold = VGroup(*[self.ring(self.tree.event_node[e], GOLD, 6) for e in (5, 14)])
        self.stage.add(gold)
        self.go(FadeOut(rings), *[Create(r) for r in gold], run_time=0.7)
        self.stage.remove(rings)
        self.bottom_note(chip("satisfies every constraint = answer state", GOLD, 24, "#0F172A"))
        self.sfx("chime", -0.3)
        self.answer_rings = gold

    def b_n_live(self, b):
        self.drop(self.answer_rings)
        self.at(b, 1)
        r = self.ring(0, ACCENT, 6)
        self.live_ring = r
        self.stage.add(r)
        self.go(Create(r), run_time=0.5)
        self.bottom_note(chip("live", ACCENT, 24), label("generated, children not all generated yet", 24, MUTED))

    def b_n_enode(self, b):
        e = self.ring(self.tree.event_node[0], GOLD, 6)
        self.stage.add(e)
        self.go(Create(e), Indicate(self.node_of(0), color=GOLD), run_time=0.6)
        self.bottom_note(chip("E-node", GOLD, 24, "#0F172A"), label("being expanded right now", 24, MUTED))
        self.at(b, 1)
        dead = [m for i, m in enumerate(self.tree.mobs) if m is not None and self.tree.nodes[i]["kind"] == "kill"]
        self.go(LaggedStart(*[Indicate(m, color=KILL, scale_factor=1.4) for m in dead], lag_ratio=0.04), run_time=1.4)
        self.bottom_note(chip("dead", KILL, 24), label("never expanded again", 24, MUTED))
        self.state_rings = VGroup(self.live_ring, e)

    def b_n_bound(self, b):
        self.drop(self.state_rings)
        self.bottom_note(chip("bounding function", KILL, 24), MathTex(r"B_k(x_1, \dots, x_k)", color=TEXT).scale(0.8))
        self.at(b, 1)
        f = MathTex(r"B_k = \text{false} \ \Rightarrow \ \text{kill the node}", color=KILL).scale(0.8)
        self.bottom_note(f)

    # ------------------------------------------------------------ depth-first search
    def b_d_order(self, b):
        self.drop(self.bottom)
        self.bottom = None
        made = [i for i, ev in enumerate(SEAT_EV) if ev[0] != "back"]
        nums = VGroup(*[label(str(k + 1), 16, GOLD, "BOLD").next_to(self.node_of(e), UR, buff=0.0)
                        for k, e in enumerate(made)])
        self.stage.add(nums)
        self.go(LaggedStart(*[FadeIn(n, scale=1.5) for n in nums], lag_ratio=0.15), run_time=3.2)
        self.sfx("pop")
        self.order_nums = nums

    def b_d_dfs(self, b):
        path = [self.tree.event_node[e] for e in (0, 3, 5)]
        self.go(LaggedStart(*[Indicate(self.tree.mobs[i], color=GOLD, scale_factor=1.6) for i in path],
                            lag_ratio=0.5), run_time=1.4)
        self.at(b, 1)
        self.bottom_note(chip("DEPTH-FIRST", GOLD, 24, "#0F172A"), label("go deep first, back up when stuck", 24, MUTED))

    def mini_tree(self, order, title, sub, col):
        pos = [(0, 1.0), (-1.1, 0), (1.1, 0), (-1.6, -1.0), (-0.6, -1.0), (0.6, -1.0), (1.6, -1.0)]
        pts = [np.array([x, y, 0]) for x, y in pos]
        edges = VGroup(*[Line(pts[p], pts[c], color=PANEL_EDGE, stroke_width=3)
                         for p, c in ((0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6))])
        dots = VGroup(*[Circle(0.24, color=MUTED, fill_color=BG, fill_opacity=1, stroke_width=3).move_to(p) for p in pts])
        nums = VGroup(*[label(str(order[i]), 22, col, "BOLD").move_to(pts[i]) for i in range(7)])
        head = VGroup(label(title, 28, TEXT, "BOLD"), label(sub, 20, MUTED)).arrange(DOWN, buff=0.08)
        head.next_to(dots, UP, buff=0.35)
        return VGroup(head, edges, dots), nums, sorted(range(7), key=lambda i: order[i])

    def b_d_bfs(self, b):
        self.clear(run_time=0.4)
        self.bottom = None
        left, lnums, lorder = self.mini_tree([1, 2, 5, 3, 4, 6, 7], "Depth-first", "backtracking", GOLD)
        right, rnums, rorder = self.mini_tree([1, 2, 3, 4, 5, 6, 7], "Breadth-first", "branch & bound  ·  video 3.4", ACCENT)
        VGroup(VGroup(left, lnums), VGroup(right, rnums)).arrange(RIGHT, buff=1.4).move_to(STAGE + DOWN * 0.1)
        self.show(left, run_time=0.5)
        self.stage.add(lnums)
        self.go(LaggedStart(*[FadeIn(lnums[i], scale=1.5) for i in lorder], lag_ratio=0.35), run_time=1.6)
        self.at(b, 1)
        self.show(right, run_time=0.5)
        self.stage.add(rnums)
        self.go(LaggedStart(*[FadeIn(rnums[i], scale=1.5) for i in rorder], lag_ratio=0.35), run_time=1.6)

    # ------------------------------------------------------------ control abstraction
    def side_note(self, title, lines, col, y):
        g = VGroup(label(title, 26, col, "BOLD"), *[label(t, 22, TEXT) for t in lines]).arrange(DOWN, buff=0.08)
        box = card(3.0, g.height + 0.4)
        return VGroup(box, g.move_to(box)).move_to(np.array([5.45, y, 0]))

    def b_a_code(self, b):
        self.clear(run_time=0.4)
        code = CodePanel(["Algorithm Backtrack(k)",
                          "for (each x[k] in T(x[1..k-1])) do",
                          "{",
                          "  if (Bk(x[1..k]) = true) then",
                          "  {",
                          "    if (x[1..k] is an answer)",
                          "      then write x[1..k];",
                          "    if (k < n) then Backtrack(k+1);",
                          "  }",
                          "}"], font_size=21)
        code.move_to(np.array([-0.5, 0.25, 0]))
        self.code = code
        self.show(code, run_time=0.6)
        self.go(code.highlight(0))
        self.at(b, 1)
        given = label("x[1..k-1] already chosen", 22, MUTED).next_to(code, DOWN, buff=0.15).align_to(code, LEFT)
        self.show(given, run_time=0.4)
        self.given = given

    def b_a_for(self, b):
        self.drop(self.given)
        self.go(self.code.highlight(1))
        self.at(b, 1)
        n = self.side_note("T( )", ["all values", "for x[k]", "= explicit"], ACCENT, 1.4)
        self.show(n, run_time=0.5)
        self.note_t = n

    def b_a_bound(self, b):
        self.go(self.code.highlight(3))
        n = self.side_note("Bk( )", ["bounding", "function", "= implicit"], GOLD, -0.8)
        self.show(n, run_time=0.5)
        self.note_b = n

    def b_a_answer(self, b):
        self.go(self.code.highlight(5))
        self.at(b, 1)
        self.go(self.code.highlight(7))

    def b_a_map(self, b):
        self.drop(self.note_t, self.note_b)
        g = VGroup(label("Seating", 26, SAFE, "BOLD"), MathTex(r"T = \{A, B, C\}", color=TEXT).scale(0.75),
                   label("Bk: nobody twice,", 22, TEXT), label("A not next to B", 22, TEXT)).arrange(DOWN, buff=0.12)
        box = card(3.0, g.height + 0.45, edge=SAFE)
        note = VGroup(box, g.move_to(box)).move_to(np.array([5.45, 0.3, 0]))
        self.show(note, run_time=0.5)

    def b_a_eff(self, b):
        self.clear(run_time=0.4)
        title = label("Efficiency depends on", 30, MUTED, "BOLD").move_to(STAGE + UP * 2.2)
        self.show(title, run_time=0.4)
        items = ["Time to generate the next x[k]", "How many x[k] satisfy the explicit constraints",
                 "Time to compute the bounding function", "How many x[k] pass the bounding function"]
        rows = VGroup(*[VGroup(chip(str(i + 1), ACCENT, 26), label(t, 28, TEXT)).arrange(RIGHT, buff=0.3)
                        for i, t in enumerate(items)])
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.32).move_to(STAGE + UP * 0.25)
        self.stage.add(rows)
        for ph, idx in ((1, (0, 1)), (2, (2, 3))):
            self.at(b, ph)
            for i in idx:
                self.go(FadeIn(rows[i], shift=RIGHT * 0.3), run_time=0.45)
                self.sfx("pop", -0.3)

    def b_a_worst(self, b):
        worst = chip("Worst case: exponential", KILL, 24)
        good = chip("Good bounding function  →  fast in practice", SAFE, 24)
        g = VGroup(worst, good).arrange(RIGHT, buff=0.4).move_to(STAGE + DOWN * 2.0)
        self.show(worst, anim=GrowFromCenter, run_time=0.4)
        self.at(b, 1)
        self.show(good, anim=GrowFromCenter, run_time=0.4)
        self.sfx("chime", -0.2)

    # ------------------------------------------------------------ practice
    def b_p_intro(self, b):
        self.clear(run_time=0.4)
        head = label("YOUR TURN", 34, GOLD, "BOLD").move_to(STAGE + UP * 1.7)
        self.show(head, anim=GrowFromCenter, run_time=0.4)
        self.sfx("pop")
        self.at(b, 1)
        q = VGroup(label("All binary strings of length 3", 40, TEXT, "BOLD"),
                   label("with no two 1s next to each other", 40, TEXT, "BOLD")).arrange(DOWN, buff=0.2)
        box = card(q.width + 0.9, q.height + 0.7, edge=GOLD)
        self.question = VGroup(box, q.move_to(box)).move_to(STAGE + DOWN * 0.1)
        self.show(self.question, run_time=0.6, shift=UP * 0.2)

    def b_p_pause(self, b):
        bars = VGroup(*[RoundedRectangle(width=0.35, height=1.1, corner_radius=0.1, fill_color=TEXT, fill_opacity=1,
                                         stroke_width=0) for _ in range(2)]).arrange(RIGHT, buff=0.3)
        pause = VGroup(Circle(0.95, color=TEXT, stroke_width=6), bars).move_to(STAGE + DOWN * 0.9 + LEFT * 2.5)
        txt = label("Pause and draw the tree", 30, TEXT, "BOLD").next_to(pause, RIGHT, buff=0.4)
        self.go(self.question.animate.scale(0.75).move_to(STAGE + UP * 1.3), run_time=0.4)
        self.show(pause, txt, run_time=0.5)
        self.say("Your turn!")
        self.at(b, 1)
        self.say("I'll wait!")

    def b_p_tree(self, b):
        self.unsay()
        self.clear(run_time=0.4)
        self.btree = Tree(BIN_EV, width=5.6, height=3.6, r=0.2, level_names=["x1", "x2", "x3"],
                          value_fmt=str, kill_label=True)
        self.btree.center_on(STAGE + LEFT * 0.9 + UP * 0.2)
        self.show(self.btree, run_time=0.4)
        made = [i for i, ev in enumerate(BIN_EV) if ev[0] != "back"]
        half = len(made) // 2
        for ph, chunk in ((0, made[:half]), (1, made[half:])):
            self.at(b, ph)
            step = max(0.25, min(0.45, self.phrase_len(b, ph) / max(len(chunk), 1)))
            for e in chunk:
                self.go(self.btree.grow(e), run_time=step)
                self.sfx("kill" if BIN_EV[e][0] == "kill" else "place", -step)

    def b_p_answer(self, b):
        self.at(b, 1)
        leaves = [e for e, ev in enumerate(BIN_EV) if ev[0] == "place" and ev[1] == 2]
        answers = VGroup(*[chip(s, SAFE, 26) for s in ("000", "001", "010", "100", "101")])
        answers.arrange(DOWN, buff=0.18).move_to(np.array([5.4, 0.3, 0]))
        self.stage.add(answers)
        step = max(0.3, min(0.6, self.phrase_len(b, 1) / 5))
        for chip_, e in zip(answers, leaves):
            node = self.btree.mobs[self.btree.event_node[e]]
            self.go(FadeIn(chip_, shift=LEFT * 0.2), node[0].animate.set_fill(SAFE, 0.6), run_time=step)
            self.sfx("pop", -step)

    # ------------------------------------------------------------ tips, recap
    def tip(self, b, n, text, sub):
        if n == 1:
            self.clear(run_time=0.4)
        row = VGroup(chip(str(n), GOLD, 30, "#0F172A"),
                     VGroup(label(text, 30, TEXT, "BOLD"), label(sub, 22, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
                     ).arrange(RIGHT, buff=0.35)
        row.move_to(STAGE + UP * (1.7 - 1.35 * (n - 1))).align_to(STAGE + LEFT * 3.6, LEFT)
        self.stage.add(row)
        self.go(FadeIn(row, shift=RIGHT * 0.3), run_time=0.5)
        self.sfx("pop")

    def b_tip1(self, b):
        self.tip(b, 1, "Define explicit & implicit constraints", "Give an example, like the seating problem")

    def b_tip2(self, b):
        self.tip(b, 2, "Draw the state space tree", "Number nodes in order, cross out the dead ones")

    def b_tip3(self, b):
        self.tip(b, 3, "Write the control abstraction", "One line each for T( ) and the bounding function")

    def b_recap(self, b):
        self.clear(run_time=0.4)
        items = ["Build a tuple one choice at a time",
                 "Search the state space tree depth-first",
                 "Kill a node when it fails the bounding function"]
        rows = VGroup(*[VGroup(label("✓", 34, SAFE, "BOLD"), label(t, 30, TEXT)).arrange(RIGHT, buff=0.3) for t in items])
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to(STAGE)
        self.stage.add(rows)
        for i, r in enumerate(rows):
            self.at(b, i + 1)
            self.go(FadeIn(r, shift=RIGHT * 0.3), run_time=0.5)

    def b_next(self, b):
        self.clear(run_time=0.4)
        nxt = VGroup(label("NEXT VIDEO", 26, MUTED, "BOLD"), label("3.2  8-Queens &", 44, TEXT, "BOLD"),
                     label("Graph Coloring", 44, TEXT, "BOLD")).arrange(DOWN, buff=0.15)
        box = card(nxt.width + 1.0, nxt.height + 0.8, edge=UNIT_COLORS["III"])
        g = VGroup(box, nxt.move_to(box)).move_to(STAGE)
        self.show(g, anim=FadeIn, run_time=0.6, shift=UP * 0.2)
        self.at(b, 1)
        self.go(self.mascot.wave(), self.mascot.set_mood("happy"), run_time=1.0)

    def end_card(self):
        """Upper part only: the lower half stays free for YouTube's end-screen boxes."""
        self.unsay()
        self.clear(run_time=0.5)
        thanks = label("Thanks for watching", 56, TEXT, "BOLD")
        by = VGroup(label("CREATED BY", 24, MUTED, "BOLD"), label("Abhijeet Karve", 44, GOLD, "BOLD")).arrange(DOWN, buff=0.1)
        g = VGroup(thanks, by).arrange(DOWN, buff=0.4).move_to(STAGE + UP * 1.7)
        self.show(g, run_time=0.8, shift=UP * 0.2)
