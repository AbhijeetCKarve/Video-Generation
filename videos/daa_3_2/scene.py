"""Video 3.2 - 8-Queens & Graph Coloring. Rendered by build.py (needs SCHEDULE / ENVELOPE env vars)."""
import json
import os
import sys
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
SOL8 = [0, 4, 7, 5, 2, 6, 1, 3]
RGB = {1: "#EF4444", 2: "#22C55E", 3: "#3B82F6"}
CNAME = {1: "red", 2: "green", 3: "blue"}


def nq_trace(n, all_solutions=False):
    ev, x, sols = [], [], []

    def place(k, i):
        return all(x[j] != i and abs(x[j] - i) != abs(j - k) for j in range(k))

    def solve(k):
        if k == n:
            sols.append(list(x))
            return not all_solutions
        for i in range(n):
            if place(k, i):
                x.append(i)
                ev.append(("place", k, i))
                if solve(k + 1):
                    return True
                x.pop()
                ev.append(("back", k, i))
            else:
                ev.append(("kill", k, i))
        return False
    solve(0)
    return ev, sols


EV4, _ = nq_trace(4)
EV8, _ = nq_trace(8)
EV8_ALL, SOLS8 = nq_trace(8, all_solutions=True)
# graph coloring trace: (kind, vertex, color)
GC = [("place", 1, 1), ("kill", 2, 1), ("place", 2, 2), ("kill", 3, 1), ("kill", 3, 2), ("place", 3, 3),
      ("place", 4, 1), ("kill", 5, 1), ("kill", 5, 2), ("kill", 5, 3), ("back", 4, 1), ("place", 4, 2),
      ("place", 5, 1)]
GPOS = {1: (-1.7, 1.45), 2: (1.7, 1.45), 3: (0, 0.1), 4: (-1.7, -1.3), 5: (1.7, -1.3)}
GEDGES = [(1, 2), (1, 3), (2, 3), (2, 5), (3, 4), (3, 5), (4, 5)]
GNAMES = {1: "DAA", 2: "OS", 3: "CN", 4: "DBMS", 5: "TOC"}
# worked example 2: a square with one diagonal (contains the triangle 1-2-3)
EX2_EDGES = [(1, 2), (2, 3), (3, 4), (4, 1), (1, 3)]
EX2_M2 = [("place", 1, 1), ("kill", 2, 1), ("place", 2, 2), ("kill", 3, 1), ("kill", 3, 2), ("back", 2, 2),
          ("back", 1, 1), ("place", 1, 2), ("place", 2, 1), ("kill", 3, 1), ("kill", 3, 2), ("back", 2, 1),
          ("kill", 2, 2), ("back", 1, 2)]
EX2_M3 = [("place", 1, 1), ("kill", 2, 1), ("place", 2, 2), ("kill", 3, 1), ("kill", 3, 2), ("place", 3, 3),
          ("kill", 4, 1), ("place", 4, 2)]
SLOTS = {1: "9 AM", 2: "12 PM", 3: "3 PM"}


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
            self.mascot = FaceSpot(accent=UNIT_COLORS[S["unit"]]).move_to(MASCOT_POS)
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

    # ------------------------------------------------------------ hook
    def b_hook_board(self, b):
        self.board8 = Board(8, size=5.2, labels=False).move_to(STAGE + LEFT * 0.3)
        self.show(self.board8, anim=FadeIn, run_time=0.8, scale=0.9)
        self.at(b, 1)
        # a careless try: queens that attack each other
        cols = [0, 2, 2, 5, 1, 7, 4, 6]
        qs = []
        for r, c in enumerate(cols):
            anim, q = self.board8.place(r, c)
            qs.append(anim)
        self.stage.add(*self.board8.queens.values())
        self.go(LaggedStart(*qs, lag_ratio=0.15), run_time=1.6)
        self.sfx("pop")
        p = self.board8.pos
        lines = VGroup(Line(p(1, 2), p(2, 2), color=KILL, stroke_width=9),      # same column
                       Line(p(3, 5), p(5, 7), color=KILL, stroke_width=9))      # same diagonal
        x_marks = VGroup(*[label("\u00d7", 60, KILL, "BOLD").move_to(p(r, c)) for r, c in [(2, 2), (5, 7)]])
        self.stage.add(lines, x_marks)
        self.go(Create(lines), FadeIn(x_marks, scale=1.5), run_time=0.6)
        self.sfx("kill")

    def b_hook_count(self, b):
        self.board8.queens = {}
        self.clear(self.board8, run_time=0.4)          # fades the clashing queens and marks
        self.go(self.board8.animate.scale(0.62).move_to(np.array([-2.0, 0.3, 0])), run_time=0.7)
        tracker = ValueTracker(0)
        num = DecimalNumber(4426165368, num_decimal_places=0, group_with_commas=True, font_size=72, color=TEXT)
        num.scale_to_fit_width(min(num.width, 5.6))
        anchor = np.array([3.5, 1.2, 0])
        num.move_to(anchor)
        num.add_updater(lambda m: m.set_value(tracker.get_value()).move_to(anchor))
        cap = label("ways to place 8 queens", 30, MUTED).next_to(num, DOWN, buff=0.25)
        self.stage.add(num, cap)
        self.add(num)
        self.go(FadeIn(cap), tracker.animate.set_value(4426165368), run_time=2.2)
        num.clear_updaters()
        self.at(b, 1)
        good = label("92", 110, SAFE, "BOLD").move_to(np.array([2.6, -1.2, 0]))
        good_cap = label("of them work!", 30, SAFE).next_to(good, RIGHT, buff=0.3)
        anims = []
        for r, c in enumerate(SOL8):
            a, q = self.board8.place(r, c)
            anims.append(a)
        self.stage.add(*self.board8.queens.values(), good, good_cap)
        self.go(LaggedStart(*anims, lag_ratio=0.08), GrowFromCenter(good), FadeIn(good_cap), run_time=1.2)
        self.sfx("chime")

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
        unit = chip("UNIT III  ·  BACKTRACKING", UNIT_COLORS["III"], 34).move_to(STAGE + UP * 1.6)
        self.show(unit, anim=GrowFromCenter, run_time=0.5)
        self.at(b, 1)
        t1 = VGroup(chip("1", ACCENT, 30), label("The 8-Queens problem", 40, TEXT, "BOLD")).arrange(RIGHT, buff=0.3)
        t2 = VGroup(chip("2", ACCENT, 30), label("Graph coloring", 40, TEXT, "BOLD")).arrange(RIGHT, buff=0.3)
        g = VGroup(t1, t2).arrange(DOWN, aligned_edge=LEFT, buff=0.45).move_to(STAGE + DOWN * 0.3)
        self.stage.add(g)
        self.go(LaggedStart(FadeIn(t1, shift=RIGHT * 0.3), FadeIn(t2, shift=RIGHT * 0.3), lag_ratio=0.6), run_time=1.2)
        self.sfx("pop")

    def b_exam(self, b):
        star = chip("★  Exam favourite", GOLD, 28, "#0F172A").move_to(STAGE + DOWN * 2.1)
        self.show(star, anim=GrowFromCenter, run_time=0.5)
        self.sfx("pop")
        self.at(b, 1)
        self.say("Tips at the end!")

    # ------------------------------------------------------------ backtracking recap
    def recap_tree(self):
        top = STAGE + UP * 1.9
        lv1 = [STAGE + np.array([x, 0.65, 0]) for x in (-2.6, 0, 2.6)]
        lv2 = {0: [-3.4, -1.8], 1: [-0.8, 0.8], 2: [1.8, 3.4]}
        nodes, edges = {"r": top}, []
        for i, p in enumerate(lv1):
            nodes[f"a{i}"] = p
            edges.append(("r", f"a{i}"))
            for j, x in enumerate(lv2[i]):
                nodes[f"b{i}{j}"] = STAGE + np.array([x, -0.6, 0])
                edges.append((f"a{i}", f"b{i}{j}"))
                for k, dx in enumerate((-0.4, 0.4)):
                    nodes[f"c{i}{j}{k}"] = STAGE + np.array([x + dx, -1.8, 0])
                    edges.append((f"b{i}{j}", f"c{i}{j}{k}"))
        dots = {k: Dot(p, radius=0.13, color=PANEL_EDGE) for k, p in nodes.items()}
        lines = {(a, c): Line(nodes[a], nodes[c], color=PANEL_EDGE, stroke_width=3) for a, c in edges}
        return nodes, dots, lines

    def b_recap1(self, b):
        self.unsay()
        self.clear(run_time=0.4)
        self.rnodes, self.rdots, self.rlines = self.recap_tree()
        faint = VGroup(*self.rlines.values(), *self.rdots.values()).set_opacity(0.35)
        self.show(faint, run_time=0.6)
        self.at(b, 1)
        path = ["r", "a0", "b00", "c000"]
        for a, c in zip(path, path[1:]):
            self.go(self.rlines[(a, c)].animate.set_stroke(SAFE, opacity=1, width=5),
                    self.rdots[c].animate.set_color(SAFE).set_opacity(1), run_time=0.45)
            self.sfx("place", -0.4)
        self.go(self.rdots["r"].animate.set_color(SAFE).set_opacity(1), run_time=0.2)

    def b_recap2(self, b):
        bad = self.rdots["c000"]
        tag = chip("bound fails", KILL, 22).next_to(bad, DOWN, buff=0.15)
        cross = label("×", 54, KILL, "BOLD").move_to(bad)
        self.stage.add(tag, cross)
        self.go(bad.animate.set_color(KILL), FadeIn(cross, scale=1.6), FadeIn(tag), run_time=0.5)
        self.sfx("kill")
        self.at(b, 1)
        arrow = CurvedArrow(self.rnodes["c000"] + RIGHT * 0.25, self.rnodes["b00"] + RIGHT * 0.25,
                            angle=-1.2, color=BACK, stroke_width=5)
        self.stage.add(arrow)
        self.go(Create(arrow), run_time=0.6)
        self.sfx("back")
        self.go(self.rlines[("b00", "c001")].animate.set_stroke(SAFE, opacity=1, width=5),
                self.rdots["c001"].animate.set_color(SAFE).set_opacity(1), run_time=0.5)

    def b_recap3(self, b):
        cut = []
        for i in (1, 2):                                  # whole branches pruned early
            for key, ln in self.rlines.items():
                if key[1].startswith(("b%d" % i, "c%d" % i)) or key == ("r", f"a{i}"):
                    cut.append(ln.animate.set_stroke(KILL, opacity=0.25))
            cut.append(self.rdots[f"a{i}"].animate.set_color(KILL))
        self.go(*cut, run_time=0.8)
        scissors = VGroup(*[label("✂", 46, KILL).move_to((self.rnodes["r"] + self.rnodes[f"a{i}"]) / 2)
                            for i in (1, 2)])
        self.stage.add(scissors)
        self.go(FadeIn(scissors, scale=1.4), run_time=0.4)
        self.sfx("kill")
        self.at(b, 1)
        note = label("Whole branches cut away early", 30, GOLD, "BOLD").move_to(STAGE + RIGHT * 1.6 + DOWN * 2.55)
        self.show(note, run_time=0.5)

    # ------------------------------------------------------------ 8-queens model
    def b_q_rules(self, b):
        self.unsay()
        self.clear(run_time=0.4)
        self.qb = Board(8, size=4.6).move_to(STAGE + LEFT * 0.9)
        self.show(self.qb, run_time=0.6)
        self.at(b, 1)
        a, q = self.qb.place(3, 3)
        self.stage.add(q)
        self.go(a, run_time=0.5)
        self.sfx("place")
        tints = VGroup(*[self.qb.sq(r, c).copy().set_fill(KILL, 0.5) for r, c in self.qb.attack_cells(3, 3)])
        self.attack_tint = tints
        self.stage.add(tints)
        self.go(LaggedStart(*[FadeIn(t) for t in tints], lag_ratio=0.03), run_time=1.4)

    def b_q_explicit(self, b):
        q = self.qb.queens.pop(3)
        self.go(FadeOut(self.attack_tint), FadeOut(q), run_time=0.4)
        self.stage.remove(self.attack_tint, q)
        rows = VGroup(*[self.qb.sq(r, 0).copy().set_fill(ACCENT, 0.0).stretch_to_fit_width(self.qb.cell * 8)
                        .move_to(self.qb.pos(r, 3.5)) for r in range(8)])
        self.at(b, 1)
        anims = []
        for r, c in enumerate(SOL8):
            a, qq = self.qb.place(r, c)
            anims.append(a)
        self.stage.add(*self.qb.queens.values())
        self.go(LaggedStart(*anims, lag_ratio=0.25), run_time=2.0)
        self.sfx("place")
        hint = label("one queen per row", 26, ACCENT, "BOLD").next_to(self.qb, DOWN, buff=0.2)
        self.show(hint, run_time=0.4)
        self.hint = hint

    def b_q_vector(self, b):
        boxes = VGroup()
        for r in range(8):
            box = Square(self.qb.cell * 0.82, color=ACCENT, stroke_width=3).move_to(self.qb.pos(r, 7) + RIGHT * self.qb.cell * 1.6)
            boxes.add(box)
        title = MathTex("x[k]", color=ACCENT).scale(0.8).next_to(boxes, UP, buff=0.15)
        self.stage.add(boxes, title)
        self.go(FadeOut(self.hint), FadeIn(boxes, lag_ratio=0.1), FadeIn(title), run_time=0.7)
        self.stage.remove(self.hint)
        self.at(b, 1)
        nums = VGroup()
        anims = []
        for r, c in enumerate(SOL8):
            n = label(str(c + 1), 26, TEXT, "BOLD").move_to(boxes[r])
            nums.add(n)
            anims.append(TransformFromCopy(self.qb.col_labels[c], n))
        self.stage.add(nums)
        self.go(LaggedStart(*anims, lag_ratio=0.18), run_time=2.2)
        self.xboxes = VGroup(boxes, title, nums)

    def b_q_implicit(self, b):
        qs = list(self.qb.queens.values())
        self.qb.queens = {}
        self.go(*[FadeOut(q) for q in qs], FadeOut(self.xboxes), run_time=0.5)
        self.stage.remove(*qs, self.xboxes)
        self.at(b, 1)
        p = self.qb.pos
        pairs = [((1, 2), (5, 2), "same column"), ((2, 1), (5, 4), "same diagonal")]
        for (a, b2, why) in pairs:
            a1, q1 = self.qb.place(*a)
            a2, q2 = self.qb.place(*b2)
            ln = Line(p(*a), p(*b2), color=KILL, stroke_width=8)
            tag = chip(why, KILL, 22).next_to(self.qb, RIGHT, buff=0.3).shift(UP * (0.8 if why == "same column" else -0.4))
            self.stage.add(q1, q2, ln, tag)
            self.go(a1, a2, run_time=0.4)
            self.go(Create(ln), FadeIn(tag), run_time=0.5)
            self.sfx("kill")

    def b_q_diag(self, b):
        f = MathTex(r"|\,x_j - i\,|", r"=", r"|\,j - k\,|", color=TEXT).scale(1.1)
        card_ = card(f.width + 0.8, f.height + 0.7)
        g = VGroup(card_, f.move_to(card_))
        g.scale_to_fit_width(min(g.width, 3.9)).move_to(np.array([4.75, -1.25, 0]))
        self.stage.add(g)
        self.go(FadeIn(g, shift=UP * 0.2), run_time=0.5)
        f[0].set_color(GOLD)
        self.at(b, 1)
        f[2].set_color(GOLD)
        ex = MathTex(r"|1-4| = |2-5| = 3", color=KILL).scale(0.8).next_to(g, DOWN, buff=0.15)
        self.stage.add(ex)
        self.go(Indicate(f[2], color=GOLD), FadeIn(ex), run_time=0.8)

    def b_q_place(self, b):
        self.clear(run_time=0.4)
        code = CodePanel(["Algorithm Place(k, i)",
                          "  for j := 1 to k-1 do",
                          "    if (x[j] = i)                     // same column",
                          "       or (Abs(x[j]-i) = Abs(j-k))    // same diagonal",
                          "    then return false;",
                          "  return true;"], font_size=24).move_to(STAGE)
        self.code = code
        self.show(code, run_time=0.6)
        self.go(code.highlight(0))
        self.at(b, 1)
        self.go(code.highlight(2))
        self.go(code.highlight(3))
        self.go(code.highlight(5))

    # ------------------------------------------------------------ 4-queens trace
    def b_t_intro(self, b):
        self.clear(run_time=0.4)
        self.b4 = Board(4, size=2.8).move_to(np.array([-2.55, 0.15, 0]))
        self.tree = Tree(EV4, width=5.3, height=4.4, r=0.16, level_names=["x1", "x2", "x3", "x4"])
        self.tree.center_on(np.array([3.35, 0.1, 0]))
        self.show(self.b4, run_time=0.6)
        self.at(b, 1)
        self.show(self.tree, run_time=0.6)
        self.ev_i = 0

    def run4(self, b, phrase, n_events, per=0.55):
        self.at(b, phrase)
        span = self.phrase_len(b, phrase)
        step = max(0.3, min(per, span / max(n_events, 1)))
        for _ in range(n_events):
            kind, r, c = EV4[self.ev_i]
            if kind == "place":
                a, q = self.b4.place(r, c)
                self.stage.add(q)
                self.go(a, self.tree.grow(self.ev_i), run_time=step)
                self.sfx("place", -step)
            elif kind == "kill":
                self.go(self.b4.kill(r, c), self.tree.grow(self.ev_i), run_time=step)
                self.sfx("kill", -step)
            else:
                self.go(self.b4.remove(r), self.tree.mark_back(self.ev_i), run_time=step)
                self.sfx("back", -step)
            self.ev_i += 1

    def b_t_q1(self, b):
        self.run4(b, 0, 1)
        self.at(b, 1)
        self.go(Indicate(self.tree.mobs[self.tree.event_node[0]], color=GOLD, scale_factor=1.4), run_time=0.8)

    def b_t_q2(self, b):
        self.run4(b, 0, 2)
        self.run4(b, 1, 1)

    def b_t_dead(self, b):
        row = Rectangle(width=self.b4.cell * 4, height=self.b4.cell, color=GOLD, stroke_width=5).move_to(self.b4.pos(2, 1.5))
        self.stage.add(row)
        self.go(Create(row), run_time=0.5)
        self.run4(b, 1, 4, per=0.4)
        self.go(self.mascot.set_mood("surprised"), run_time=0.3)
        self.say("Dead end!")
        self.sfx("kill")
        self.dead_row = row

    def b_t_back(self, b):
        self.unsay()
        self.go(FadeOut(self.dead_row), self.mascot.set_mood("neutral"), run_time=0.3)
        self.stage.remove(self.dead_row)
        self.run4(b, 0, 1)
        self.run4(b, 1, 3)

    def b_t_dead2(self, b):
        self.run4(b, 0, 4, per=0.35)
        self.go(self.mascot.set_mood("surprised"), run_time=0.25)
        self.run4(b, 1, 5, per=0.42)

    def b_t_q1b(self, b):
        self.go(self.mascot.set_mood("neutral"), run_time=0.2)
        self.run4(b, 0, 1)
        self.run4(b, 1, 4, per=0.4)
        self.run4(b, 2, 1)

    def b_t_solved(self, b):
        self.run4(b, 0, 3, per=0.45)
        self.at(b, 1)
        sol = [1, 3, 0, 2]
        glow = VGroup(*[self.b4.sq(r, c).copy().set_fill(SAFE, 0.8) for r, c in enumerate(sol)])
        self.stage.add(glow)
        path = self.tree.path_to(len(EV4) - 1)
        answer = MathTex(r"x = (2,\,4,\,1,\,3)", color=SAFE).scale(0.9).next_to(self.b4, DOWN, buff=0.35)
        self.stage.add(answer)
        self.bring_to_front(*self.b4.queens.values())
        self.go(FadeIn(glow), *[self.tree.mobs[i][0].animate.set_fill(SAFE, 0.6) for i in path],
                Write(answer), self.mascot.set_mood("happy"), self.mascot.bounce(), run_time=1.0)
        self.add(*self.b4.queens.values())
        self.sfx("chime")

    def b_t_tree(self, b):
        self.at(b, 1)
        killed = [m for i, m in enumerate(self.tree.mobs) if m is not None and self.tree.nodes[i]["kind"] == "kill"]
        note = chip("killed by the bounding function", KILL, 22).next_to(self.tree, DOWN, buff=0.1)
        self.stage.add(note)
        self.go(LaggedStart(*[Indicate(k, color=KILL, scale_factor=1.5) for k in killed], lag_ratio=0.05),
                FadeIn(note), run_time=2.0)

    # ------------------------------------------------------------ 8-queens time-lapse
    def b_e_lapse(self, b):
        self.clear(run_time=0.5)
        board = Board(8, size=4.8).move_to(np.array([-0.6, 0.15, 0]))
        self.b8 = board
        qms = [board.queen(r, 0).set_opacity(0) for r in range(8)]
        probe = Square(board.cell, stroke_width=0, fill_color=SAFE, fill_opacity=0.6).move_to(board.pos(0, 0))
        placed = DecimalNumber(0, num_decimal_places=0, font_size=56, color=SAFE)
        backs = DecimalNumber(0, num_decimal_places=0, font_size=56, color=BACK)
        panel = VGroup(VGroup(label("placements", 26, MUTED), placed).arrange(DOWN, buff=0.1),
                       VGroup(label("backtracks", 26, MUTED), backs).arrange(DOWN, buff=0.1)).arrange(DOWN, buff=0.5)
        panel.move_to(np.array([4.4, 0.4, 0]))
        self.stage.add(board, probe, panel, *qms)
        self.go(FadeIn(board), FadeIn(panel), run_time=0.6)
        self.add(probe, *qms)
        # replay of all 981 steps: queen positions after each event
        states, q, np_, nb = [], {}, 0, 0
        for kind, r, c in EV8:
            if kind == "place":
                q[r] = c
                np_ += 1
            elif kind == "back":
                q.pop(r, None)
                nb += 1
            states.append((dict(q), kind, r, c, np_, nb))
        dur = b["end"] - self.now() - 0.4

        def update(_, alpha):
            st, kind, r, c, n1, n2 = states[min(int(alpha * len(states)), len(states) - 1)]
            for row in range(8):
                if row in st:
                    qms[row].set_opacity(1).move_to(board.pos(row, st[row]))
                else:
                    qms[row].set_opacity(0)
            probe.move_to(board.pos(r, c)).set_fill(SAFE if kind == "place" else (KILL if kind == "kill" else BACK), 0.6)
            placed.set_value(n1)
            backs.set_value(n2)
        holder = VGroup(probe, placed, backs, *qms)
        for t in np.linspace(0, dur - 0.5, 40):                  # steady ticking sound under the time-lapse
            self.sfx_events.append((round(self.now() + t, 3), "pop"))
        self.play(UpdateFromAlphaFunc(holder, update, rate_func=rate_functions.ease_in_out_sine), run_time=dur)
        self.qms8, self.probe8, self.panel8 = qms, probe, panel

    def b_e_result(self, b):
        self.go(FadeOut(self.probe8), run_time=0.3)
        self.stage.remove(self.probe8)
        glow = VGroup(*[self.b8.sq(r, c).copy().set_fill(SAFE, 0.8) for r, c in enumerate(SOL8)])
        self.stage.add(glow)
        self.add(glow, *self.qms8)
        self.go(FadeIn(glow), run_time=0.5)
        self.sfx("chime")
        self.at(b, 1)
        vec = MathTex(r"x = (1,5,8,6,3,7,2,4)", color=SAFE).scale(0.9).next_to(self.b8, DOWN, buff=0.25)
        self.stage.add(vec)
        self.go(Write(vec), run_time=1.6)

    def b_e_count(self, b):
        self.clear(run_time=0.5)
        grid = VGroup()
        size = 0.36
        for idx, sol in enumerate(SOLS8):
            sq = Square(size, stroke_color=PANEL_EDGE, stroke_width=1, fill_color=PANEL, fill_opacity=1)
            dots = VGroup(*[Dot(sq.get_corner(UL) + np.array([(c + 0.5) * size / 8, -(r + 0.5) * size / 8, 0]),
                                radius=0.017, color=SAFE) for r, c in enumerate(sol)])
            grid.add(VGroup(sq, dots))
        grid.arrange_in_grid(rows=8, cols=12, buff=0.06).move_to(np.array([-0.95, -0.15, 0]))
        title = label("all 92 solutions", 34, SAFE, "BOLD").next_to(grid, UP, buff=0.25)
        self.stage.add(grid, title)
        self.go(LaggedStart(*[FadeIn(g, scale=0.6) for g in grid], lag_ratio=0.02), FadeIn(title), run_time=2.6)
        self.at(b, 1)
        checked = sum(1 for e in EV8_ALL if e[0] != "back")
        cmp_ = VGroup(label(f"{checked:,} squares checked", 30, TEXT, "BOLD"),
                      label("instead of 4,426,165,368 boards", 26, MUTED)).arrange(DOWN, buff=0.12)
        cmp_.scale_to_fit_width(min(cmp_.width, 6.8 - grid.get_right()[0] - 0.35))
        cmp_.next_to(grid, RIGHT, buff=0.35)
        self.stage.add(cmp_)
        self.go(FadeIn(cmp_, shift=LEFT * 0.2), run_time=0.6)

    # ------------------------------------------------------------ algorithm
    def b_a_code(self, b):
        self.clear(run_time=0.4)
        self.ncode = CodePanel(["Algorithm NQueens(k, n)",
                                "  for i := 1 to n do",
                                "    if Place(k, i) then",
                                "    {",
                                "      x[k] := i;",
                                "      if (k = n) then write (x[1:n]);",
                                "      else NQueens(k+1, n);",
                                "    }"], font_size=23).move_to(STAGE + UP * 0.35)
        self.show(self.ncode, run_time=0.6)
        self.go(self.ncode.highlight(0))
        self.at(b, 1)
        self.go(self.ncode.highlight(1))

    def b_a_code2(self, b):
        self.go(self.ncode.highlight(2))
        self.go(self.ncode.highlight(4))
        self.at(b, 1)
        self.go(self.ncode.highlight(5))
        self.go(self.ncode.highlight(6))

    def b_a_complex(self, b):
        f = MathTex(r"T(n) = O(n!)", color=GOLD).scale(1.3)
        box = card(f.width + 1.0, f.height + 0.8)
        g = VGroup(box, f.move_to(box)).next_to(self.ncode, DOWN, buff=0.3)
        self.at(b, 1)
        self.show(g, anim=GrowFromCenter, run_time=0.6)

    # ------------------------------------------------------------ graph coloring
    def b_g_intro(self, b):
        self.clear(run_time=0.4)
        cards = VGroup(*[chip(GNAMES[k], PANEL_EDGE, 30) for k in range(1, 6)]).arrange(RIGHT, buff=0.3)
        cards.move_to(STAGE + UP * 1.4)
        slots = VGroup(*[chip(SLOTS[k], RGB[k], 28) for k in (1, 2, 3)]).arrange(RIGHT, buff=0.6)
        slots.move_to(STAGE + DOWN * 0.8)
        q = label("?", 90, GOLD, "BOLD").move_to(STAGE + UP * 0.3)
        self.show(cards, run_time=0.6, lag_ratio=0.2)
        self.at(b, 1)
        self.show(slots, q, run_time=0.6)
        self.gcards = cards

    def b_g_graph(self, b):
        self.clear(run_time=0.4)
        pos = {k: (x + 0.2, y) for k, (x, y) in GPOS.items()}
        self.graph = Graph(pos, GEDGES, names=GNAMES)
        verts = [self.graph.vert[k] for k in range(1, 6)]
        names = [m for m in self.graph if isinstance(m, Text)]
        self.stage.add(self.graph)
        self.go(*[GrowFromCenter(v) for v in verts], *[FadeIn(n) for n in names], run_time=0.8)
        self.at(b, 1)
        edges = [self.graph.edge_mobs[e] for e in GEDGES]
        for e in edges:
            e.set_opacity(0)
        self.go(LaggedStart(*[e.animate.set_opacity(1) for e in edges], lag_ratio=0.2), run_time=1.6)
        note = label("edge = common students", 24, GOLD).next_to(self.graph, RIGHT, buff=0.5).shift(UP * 1.3)
        self.show(note, run_time=0.4)
        self.gnote = note

    def b_g_def(self, b):
        self.go(FadeOut(self.gnote), run_time=0.3)
        self.stage.remove(self.gnote)
        t = VGroup(label("m-coloring", 32, TEXT, "BOLD"),
                   label("adjacent vertices", 24, MUTED), label("never share a color", 24, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        box = card(t.width + 0.6, t.height + 0.5)
        self.gdef = VGroup(box, t.move_to(box)).move_to(np.array([4.9, 1.6, 0]))
        self.show(self.gdef, run_time=0.5)
        self.at(b, 1)
        self.go(self.graph.flash_edges(3), run_time=0.8)

    def b_g_chromatic(self, b):
        f = MathTex(r"\chi(G) = 3", color=GOLD).scale(1.1).next_to(self.gdef, DOWN, buff=0.35)
        tri = VGroup(*[self.graph.edge_mobs[e] for e in [(1, 2), (1, 3), (2, 3)]])
        self.stage.add(f)
        self.go(Write(f), *[Indicate(e, color=GOLD, scale_factor=1) for e in tri], run_time=1.0)
        self.gchi = f

    def b_g_x(self, b):
        self.go(FadeOut(self.gdef), FadeOut(self.gchi), run_time=0.3)
        self.stage.remove(self.gdef, self.gchi)
        self.xb = VGroup(*[Square(0.62, color=ACCENT, stroke_width=3, fill_color=BG, fill_opacity=1) for _ in range(5)])
        self.xb.arrange(RIGHT, buff=0.08).move_to(np.array([4.9, 1.7, 0]))
        idx = VGroup(*[label(str(k + 1), 18, MUTED).next_to(self.xb[k], UP, buff=0.08) for k in range(5)])
        name = MathTex("x[k]", color=ACCENT).scale(0.8).next_to(self.xb, LEFT, buff=0.2)
        legend = VGroup(*[VGroup(Circle(0.14, fill_color=RGB[k], fill_opacity=1, stroke_width=0),
                                 label(f"{CNAME[k]} = {SLOTS[k]}", 22, MUTED)).arrange(RIGHT, buff=0.15)
                          for k in (1, 2, 3)]).arrange(DOWN, aligned_edge=LEFT, buff=0.15).move_to(np.array([4.9, 0.35, 0]))
        self.stage.add(self.xb, idx, name, legend)
        self.go(FadeIn(self.xb, lag_ratio=0.1), FadeIn(idx), FadeIn(name), run_time=0.7)
        self.at(b, 1)
        self.go(FadeIn(legend, shift=UP * 0.2), run_time=0.5)
        self.gc_i = 0
        self.xfill = {}

    def gc_events(self, b, phrase, n, per=0.6):
        self.at(b, phrase)
        span = self.phrase_len(b, phrase)
        step = max(0.35, min(per, span / max(n, 1)))
        for _ in range(n):
            kind, v, c = GC[self.gc_i]
            vert = self.graph.vert[v][0]
            box = self.xb[v - 1]
            if kind == "place":
                fill = Square(0.5, stroke_width=0, fill_color=RGB[c], fill_opacity=1).move_to(box)
                if v in self.xfill:
                    self.stage.remove(self.xfill[v])
                    self.remove(self.xfill[v])
                self.xfill[v] = fill
                self.stage.add(fill)
                self.go(self.graph.paint(v, RGB[c]), FadeIn(fill, scale=0.5), run_time=step)
                self.sfx("place", -step)
            elif kind == "kill":
                ring = Circle(self.graph.r + 0.12, color=RGB[c], stroke_width=8).move_to(vert)
                clash = [self.graph.edge_mobs[(v, j)] for j in self.graph.adj[v] if self.color_of(j) == c]
                self.go(FadeIn(ring, rate_func=there_and_back, remover=True),
                        *[Indicate(e, color=KILL, scale_factor=1) for e in clash], run_time=step)
                self.sfx("kill", -step)
            else:
                old = self.xfill.pop(v)
                self.stage.remove(old)
                self.go(self.graph.paint(v, PANEL), old.animate.set_fill(BACK), run_time=step)
                self.go(FadeOut(old), run_time=0.2)
                self.sfx("back", -step)
            self.gc_i += 1

    def color_of(self, v):
        col = None
        for kind, vv, c in GC[:self.gc_i]:
            if vv == v:
                col = c if kind == "place" else None
        return col

    def b_g_v1(self, b):
        self.gc_events(b, 1, 1)

    def b_g_v2(self, b):
        self.gc_events(b, 0, 1)
        self.gc_events(b, 1, 1)

    def b_g_v3(self, b):
        self.at(b, 0)
        self.go(self.graph.flash_edges(3), run_time=0.8)
        self.gc_events(b, 1, 3, per=0.5)

    def b_g_v4(self, b):
        self.go(self.graph.flash_edges(4), run_time=0.8)
        self.gc_events(b, 1, 1)

    def b_g_dead(self, b):
        self.gc_events(b, 0, 3, per=0.55)
        self.at(b, 1)
        self.go(self.mascot.set_mood("surprised"), run_time=0.3)
        self.say("No color left!")
        self.sfx("kill")

    def b_g_back(self, b):
        self.unsay()
        self.go(self.mascot.set_mood("neutral"), run_time=0.2)
        self.gc_events(b, 0, 1)
        self.gc_events(b, 1, 1)

    def b_g_done(self, b):
        self.gc_events(b, 0, 1)
        self.at(b, 1)
        sched = VGroup(*[VGroup(chip(SLOTS[k], RGB[k], 22),
                                label(", ".join(GNAMES[v] for v in range(1, 6) if self.color_of(v) == k), 24, TEXT))
                         .arrange(RIGHT, buff=0.25) for k in (1, 2, 3)]).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        sched.move_to(np.array([4.9, -1.85, 0]))
        self.stage.add(sched)
        self.go(FadeIn(sched, shift=UP * 0.2), self.mascot.set_mood("happy"), self.mascot.bounce(), run_time=0.8)
        self.sfx("chime")

    def b_g_code(self, b):
        self.clear(run_time=0.4)
        self.gcode = CodePanel(["Algorithm mColoring(k)",
                                "  repeat",
                                "    NextValue(k);        // next legal color for x[k]",
                                "    if (x[k] = 0) then return;   // none left: backtrack",
                                "    if (k = n) then write (x[1:n]);",
                                "    else mColoring(k+1);",
                                "  until (false);"], font_size=24).move_to(STAGE)
        self.show(self.gcode, run_time=0.6)
        self.go(self.gcode.highlight(2))
        self.at(b, 1)
        self.go(self.gcode.highlight(3))

    def b_g_complex(self, b):
        f = MathTex(r"O(n \cdot m^{n})", color=GOLD).scale(1.3)
        box = card(f.width + 1.0, f.height + 0.8)
        g = VGroup(box, f.move_to(box))
        self.go(self.gcode.animate.shift(UP * 1.1), run_time=0.4)
        g.next_to(self.gcode, DOWN, buff=0.3)
        parts = label("mⁿ colorings  ×  O(n) check each", 24, MUTED).next_to(g, DOWN, buff=0.2)
        self.at(b, 1)
        self.show(g, parts, run_time=0.6)

    # ------------------------------------------------------------ worked example 2: m = 2 vs m = 3
    def ex2_graph(self):
        pos = {1: (-2.9, 1.2), 2: (-0.5, 1.2), 3: (-0.5, -1.2), 4: (-2.9, -1.2)}
        return Graph(pos, EX2_EDGES, r=0.36)

    def ex2_tree(self, events, levels):
        t = Tree([(k, v - 1, c - 1) for k, v, c in events], width=4.4, height=3.7, r=0.19,
                 level_names=[f"v{i}" for i in range(1, levels + 1)])
        return t.center_on(np.array([3.55, 0.05, 0]))

    def run_ex2(self, b, phrase, events, n, per=0.55):
        self.at(b, phrase)
        span = self.phrase_len(b, phrase)
        step = max(0.3, min(per, span / max(n, 1)))
        for _ in range(n):
            kind, v, c = events[self.ex_i]
            if kind == "back":
                self.go(self.ex_tree.mark_back(self.ex_i), self.ex_g.paint(v, PANEL), run_time=step)
                self.sfx("back", -step)
            else:
                grow = self.ex_tree.grow(self.ex_i)
                node = self.ex_tree.mobs[self.ex_tree.event_node[self.ex_i]]
                if kind == "place":
                    node[0].set_fill(RGB[c], 0.9)
                    self.go(grow, self.ex_g.paint(v, RGB[c]), run_time=step)
                    self.sfx("place", -step)
                else:
                    ring = Circle(self.ex_g.r + 0.12, color=RGB[c], stroke_width=8).move_to(self.ex_g.vert[v])
                    self.go(grow, FadeIn(ring, rate_func=there_and_back, remover=True), run_time=step)
                    self.sfx("kill", -step)
            self.ex_i += 1

    def b_w_intro(self, b):
        self.clear(run_time=0.4)
        self.ex_g = self.ex2_graph()
        verts = [self.ex_g.vert[k] for k in range(1, 5)]
        edges = [self.ex_g.edge_mobs[e] for e in EX2_EDGES]
        self.stage.add(self.ex_g)
        self.go(*[GrowFromCenter(v) for v in verts], *[Create(e) for e in edges], run_time=0.9)
        self.at(b, 1)
        self.m_chip = chip("m = 2 ?", GOLD, 30, "#0F172A").next_to(self.ex_g, UP, buff=0.3)
        self.stage.add(self.m_chip)
        self.go(GrowFromCenter(self.m_chip), run_time=0.5)
        self.sfx("pop")

    def b_w_tree(self, b):
        self.ex_tree = self.ex2_tree(EX2_M2, 3)
        self.ex_i = 0
        self.show(self.ex_tree, run_time=0.5)
        self.run_ex2(b, 1, EX2_M2, 3)

    def b_w_dead(self, b):
        self.run_ex2(b, 0, EX2_M2, 2, per=0.6)
        self.go(self.mascot.set_mood("surprised"), run_time=0.3)
        self.run_ex2(b, 1, EX2_M2, 9, per=0.42)
        self.go(self.mascot.set_mood("neutral"), run_time=0.3)

    def b_w_fail(self, b):
        verdict = chip("\u00d7  2 colors are not enough", KILL, 26).next_to(self.ex_tree, DOWN, buff=0.15)
        self.stage.add(verdict)
        self.go(FadeIn(verdict, shift=UP * 0.2), self.m_chip.animate.set_opacity(0.4), run_time=0.5)
        self.sfx("kill")
        self.at(b, 1)
        tri = [self.ex_g.edge_mobs[e] for e in [(1, 2), (2, 3), (1, 3)]]
        tag = label("triangle", 26, GOLD, "BOLD").move_to(np.array([-1.3, 0.45, 0]))
        self.stage.add(tag)
        self.go(*[ln.animate.set_stroke(GOLD, width=8) for ln in tri], FadeIn(tag), run_time=0.8)
        self.ex_verdict, self.ex_tag, self.ex_tri = verdict, tag, tri

    def b_w_m3(self, b):
        old = [self.ex_tree, self.ex_verdict, self.m_chip, self.ex_tag]
        self.stage.remove(*old)
        m3 = chip("m = 3", SAFE, 30).move_to(self.m_chip)
        self.stage.add(m3)
        self.go(*[FadeOut(o) for o in old], GrowFromCenter(m3),
                *[ln.animate.set_stroke(MUTED, width=4) for ln in self.ex_tri],
                *[self.ex_g.paint(v, PANEL) for v in range(1, 5)], run_time=0.6)
        self.ex_tree = self.ex2_tree(EX2_M3, 4)
        self.ex_i = 0
        self.show(self.ex_tree, run_time=0.4)
        self.run_ex2(b, 0, EX2_M3, 6, per=0.4)
        self.run_ex2(b, 1, EX2_M3, 2, per=0.5)
        self.go(self.mascot.set_mood("happy"), self.mascot.bounce(), run_time=0.6)
        self.sfx("chime")

    def b_w_answer(self, b):
        chi = MathTex(r"\chi(G) = 3", color=GOLD).scale(1.1).next_to(self.ex_tree, DOWN, buff=0.2)
        self.stage.add(chi)
        self.go(Write(chi), run_time=0.8)
        self.at(b, 1)
        killed = [m for i, m in enumerate(self.ex_tree.mobs) if m is not None and self.ex_tree.nodes[i]["kind"] == "kill"]
        self.go(LaggedStart(*[Indicate(k, color=KILL, scale_factor=1.5) for k in killed], lag_ratio=0.15), run_time=1.5)

    # ------------------------------------------------------------ pattern, tips, recap
    def b_cmp(self, b):
        self.clear(run_time=0.4)
        left = VGroup(label("8-Queens", 30, TEXT, "BOLD"), MathTex(r"x[k] = \text{column}", color=MUTED).scale(0.7),
                      label("bound: Place(k, i)", 22, MUTED)).arrange(DOWN, buff=0.15)
        right = VGroup(label("Graph coloring", 30, TEXT, "BOLD"), MathTex(r"x[k] = \text{color}", color=MUTED).scale(0.7),
                       label("bound: NextValue(k)", 22, MUTED)).arrange(DOWN, buff=0.15)
        cards = VGroup(*[VGroup(card(4.0, 1.9), g) for g in (left, right)])
        for c_ in cards:
            c_[1].move_to(c_[0])
        cards.arrange(RIGHT, buff=0.5).move_to(STAGE + UP * 1.2)
        self.show(cards, run_time=0.6, lag_ratio=0.3)
        self.at(b, 1)
        steps = ["choose", "check bound", "go deeper", "backtrack"]
        chips_ = VGroup(*[chip(s, c, 24) for s, c in zip(steps, [ACCENT, GOLD, SAFE, BACK])]).arrange(RIGHT, buff=0.55)
        chips_.move_to(STAGE + DOWN * 1.2)
        arrows = VGroup(*[Arrow(chips_[i].get_right(), chips_[i + 1].get_left(), buff=0.08, color=MUTED,
                                stroke_width=4, max_tip_length_to_length_ratio=0.35) for i in range(3)])
        self.stage.add(chips_, arrows)
        self.go(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in chips_], lag_ratio=0.5), FadeIn(arrows), run_time=2.0)

    def tip(self, b, n, text, sub):
        if n == 1:
            self.clear(run_time=0.4)
            self.tips = VGroup()
        row = VGroup(chip(str(n), GOLD, 30, "#0F172A"),
                     VGroup(label(text, 30, TEXT, "BOLD"), label(sub, 22, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
                     ).arrange(RIGHT, buff=0.35)
        row.move_to(STAGE + UP * (1.7 - 1.35 * (n - 1))).align_to(STAGE + LEFT * 3.6, LEFT)
        self.stage.add(row)
        self.go(FadeIn(row, shift=RIGHT * 0.3), run_time=0.5)
        self.sfx("pop")

    def b_tip1(self, b):
        self.tip(b, 1, "Draw the 4-queens state space tree", "Mark the killed nodes clearly")

    def b_tip2(self, b):
        self.tip(b, 2, "Write Place(k, i)", "Explain the diagonal condition in words")

    def b_tip3(self, b):
        self.tip(b, 3, "Graph coloring: show x[ ] at every step", "Point out where you backtrack")

    def b_recap(self, b):
        self.clear(run_time=0.4)
        items = ["Build the solution one choice at a time",
                 "Check the bounding function after every choice",
                 "Kill a branch the moment it breaks a rule"]
        rows = VGroup(*[VGroup(label("✓", 34, SAFE, "BOLD"), label(t, 30, TEXT)).arrange(RIGHT, buff=0.3) for t in items])
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to(STAGE)
        self.stage.add(rows)
        for i, r in enumerate(rows):
            self.at(b, i)
            self.go(FadeIn(r, shift=RIGHT * 0.3), run_time=0.5)

    def b_next(self, b):
        self.clear(run_time=0.4)
        nxt = VGroup(label("NEXT VIDEO", 26, MUTED, "BOLD"), label("3.3  Sum of Subsets &", 44, TEXT, "BOLD"),
                     label("Hamiltonian Cycle", 44, TEXT, "BOLD")).arrange(DOWN, buff=0.15)
        box = card(nxt.width + 1.0, nxt.height + 0.8, edge=UNIT_COLORS["III"])
        g = VGroup(box, nxt.move_to(box)).move_to(STAGE)
        self.show(g, anim=FadeIn, run_time=0.6, shift=UP * 0.2)
        self.at(b, 1)
        self.go(self.mascot.wave(), self.mascot.set_mood("happy"), run_time=1.0)

    def end_card(self):
        self.unsay()
        self.clear(run_time=0.5)
        thanks = label("Thanks for watching", 56, TEXT, "BOLD")
        by = VGroup(label("CREATED BY", 24, MUTED, "BOLD"), label("Abhijeet Karve", 44, GOLD, "BOLD")).arrange(DOWN, buff=0.1)
        g = VGroup(thanks, by).arrange(DOWN, buff=0.5).move_to(STAGE)
        self.show(g, run_time=0.8, shift=UP * 0.2)
