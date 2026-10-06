#!/usr/bin/env python3
"""Animated explainer for the N-Queens problem (backtracking).

Produces an MP4, an .srt of captions and a .script.txt narration script,
ready to be used as a clip in a vedit project. With --voice, your recorded
lines are placed on the timeline and frames are held so nothing overlaps:

    python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --script-only
    python3 scripts/record_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice
    python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --voice projects/nqueens/voice
    python3 vedit.py build projects/nqueens/project.json
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vedit import find_font, load_theme, probe_duration  # noqa: E402

W, H = 1920, 1080
LIGHT, DARK = "#E2E8F0", "#94A3B8"
RED, GREEN, ORANGE = "#EF4444", "#22C55E", "#F59E0B"
QUEEN = "♛"
# number of solutions for N = 1..12 (OEIS A000170)
SOLUTION_COUNTS = [1, 0, 0, 2, 10, 4, 40, 92, 352, 724, 2680, 14200]


# ---------------------------------------------------------------- algorithm

def attackers(queens, row, col):
    """Queens already placed (one per row, queens[r] = column) that attack (row, col)."""
    out = []
    for r, c in enumerate(queens):
        if c == col:
            out.append((r, c, "same column"))
        elif abs(c - col) == row - r:
            out.append((r, c, "same diagonal"))
    return out


def trace(n):
    """Run backtracking until the first solution, recording every step."""
    events, queens = [], []

    def solve(row):
        if row == n:
            return True
        for col in range(n):
            att = attackers(queens, row, col)
            if att:
                events.append({"kind": "conflict", "row": row, "col": col,
                               "queens": list(queens), "att": att})
                continue
            queens.append(col)
            events.append({"kind": "place", "row": row, "col": col, "queens": list(queens)})
            if solve(row + 1):
                return True
            queens.pop()
            events.append({"kind": "backtrack", "row": row, "col": col, "queens": list(queens)})
        return False

    solved = solve(0)
    return events, (list(queens) if solved else None)


# ---------------------------------------------------------------- drawing

class Painter:
    def __init__(self, n, theme):
        self.n, self.t = n, theme
        self.board = 640
        self.cell = self.board // n
        self.board = self.cell * n
        self.x0, self.y0 = 170, 70 + (640 - self.board) // 2
        text_font = find_font(theme["font"])
        self.f = {s: ImageFont.truetype(text_font, s) for s in (26, 30, 36, 44, 60)}
        self.queen_font = ImageFont.truetype(find_font("DejaVu Sans"), int(self.cell * 0.72))

    def center(self, r, c):
        return self.x0 + c * self.cell + self.cell // 2, self.y0 + r * self.cell + self.cell // 2

    def cell_box(self, r, c):
        x, y = self.x0 + c * self.cell, self.y0 + r * self.cell
        return [x, y, x + self.cell, y + self.cell]

    def frame(self, queens=(), tint=None, ghost=None, lines=(), label="", message="",
              current_row=None, stats=None, panel=None):
        """tint: {(r, c): color}, ghost: (r, c, color), lines: [((r,c),(r,c),color)]."""
        img = Image.new("RGB", (W, H), self.t["background"])
        d = ImageDraw.Draw(img)
        n, cell = self.n, self.cell

        for r in range(n):
            for c in range(n):
                d.rectangle(self.cell_box(r, c), fill=LIGHT if (r + c) % 2 == 0 else DARK)
            d.text((self.x0 - 30, self.y0 + r * cell + cell // 2), str(r + 1),
                   font=self.f[26], fill=self.t["muted"], anchor="mm")
        for c in range(n):
            d.text((self.x0 + c * cell + cell // 2, self.y0 - 26), str(c + 1),
                   font=self.f[26], fill=self.t["muted"], anchor="mm")

        if tint:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            for (r, c), color in tint.items():
                od.rectangle(self.cell_box(r, c), fill=color + "99")
            img.paste(overlay, (0, 0), overlay)
            d = ImageDraw.Draw(img)

        if current_row is not None and current_row < n:
            y = self.y0 + current_row * cell
            d.rectangle([self.x0 - 4, y - 4, self.x0 + self.board + 4, y + cell + 4],
                        outline=self.t["accent"], width=5)

        for (r1, c1), (r2, c2), color in lines:
            d.line([self.center(r1, c1), self.center(r2, c2)], fill=color, width=7)

        for r, c in enumerate(queens):
            d.text(self.center(r, c), QUEEN, font=self.queen_font, fill="#111827",
                   anchor="mm", stroke_width=2, stroke_fill="#FFFFFF")
        if ghost:
            r, c, color = ghost
            d.text(self.center(r, c), QUEEN, font=self.queen_font, fill=color,
                   anchor="mm", stroke_width=2, stroke_fill="#111827")

        self.draw_panel(d, label, message, queens, current_row, stats, panel)
        return img

    def wrap(self, d, text, font, width):
        lines = []
        for para in text.split("\n"):
            line = ""
            for word in para.split():
                trial = (line + " " + word).strip()
                if d.textlength(trial, font=font) <= width:
                    line = trial
                else:
                    lines.append(line)
                    line = word
            lines.append(line)
        return lines

    def draw_panel(self, d, label, message, queens, current_row, stats, panel):
        x, width, t = 920, 880, self.t
        d.text((x, 60), f"N-Queens  ·  N = {self.n}", font=self.f[60], fill=t["text"])
        d.text((x, 150), label.upper(), font=self.f[30], fill=t["accent"])
        y = 195
        for line in self.wrap(d, message, self.f[36], width)[:4]:
            d.text((x, y), line, font=self.f[36], fill=t["text"])
            y += 48

        if panel == "summary":
            self.draw_summary(d, x)
            return
        if panel == "intro":
            return

        y = 410
        d.text((x, y), "queens[row] = column", font=self.f[26], fill=t["muted"])
        box = min(70, (width - 10 * (self.n - 1)) // self.n)
        for r in range(self.n):
            bx, by = x + r * (box + 10), y + 45
            active = r == current_row
            d.rectangle([bx, by, bx + box, by + box], outline=t["accent"] if active else t["muted"],
                        width=4 if active else 2)
            val = str(queens[r] + 1) if r < len(queens) else "·"
            d.text((bx + box / 2, by + box / 2), val, font=self.f[36], fill=t["text"], anchor="mm")

        if stats:
            d.text((x, 560), f"Placed: {stats['place']}    Conflicts: {stats['conflict']}"
                             f"    Backtracks: {stats['backtrack']}", font=self.f[30], fill=t["text"])
        lx = x
        for color, name in ((GREEN, "safe → place queen"), (RED, "attacked → skip"),
                            (ORANGE, "dead end → backtrack")):
            d.rectangle([lx, 625, lx + 24, 649], fill=color)
            d.text((lx + 34, 622), name, font=self.f[26], fill=t["muted"])
            lx += 46 + d.textlength(name, font=self.f[26])

    def draw_summary(self, d, x):
        t = self.t
        d.text((x, 440), "N", font=self.f[30], fill=t["muted"])
        d.text((x, 490), "solutions", font=self.f[30], fill=t["muted"])
        for i, count in enumerate(SOLUTION_COUNTS[:10]):
            cx = x + 190 + i * 62
            hi = i + 1 == self.n
            d.text((cx, 455), str(i + 1), font=self.f[30], fill=t["accent"] if hi else t["text"], anchor="mm")
            d.text((cx, 505), str(count), font=self.f[26], fill=t["accent"] if hi else t["text"], anchor="mm")


# ---------------------------------------------------------------- script

def attack_zone(n, r, c):
    return {(rr, cc): RED for rr in range(n) for cc in range(n)
            if (rr, cc) != (r, c) and (rr == r or cc == c or abs(rr - r) == abs(cc - c))}


def build_scenes(n, p, speed, frame_dir):
    """Draw every frame to frame_dir. Returns scenes [[png, seconds]] and the
    narration [(scene_index, text)]: each line starts when its scene appears."""
    scenes, narration = [], []

    def add(img, secs, line=None):
        path = frame_dir / f"f{len(scenes):05d}.png"
        if img is not None:
            img.save(path)
        if line:
            narration.append((len(scenes), line))
        scenes.append([path, secs])

    mid = n // 2
    add(p.frame(label="The puzzle", panel="intro",
                message=f"Place {n} queens on a {n}\u00d7{n} chessboard so that no two queens attack each other."),
        5 / speed, f"The N-Queens puzzle: place {n} queens so none can attack another.")
    add(p.frame(queens=[], ghost=(mid, mid, "#111827"), tint=attack_zone(n, mid, mid), label="The rules",
                panel="intro", message="A queen attacks every square in its row, its column and both diagonals."),
        5 / speed, "A queen attacks along its row, its column and both diagonals.")
    add(p.frame(label="The strategy: backtracking", panel="intro",
                message="Go row by row. Try each column left to right. Skip attacked squares. "
                        "If a row has no safe square, go back and move the previous queen."),
        7 / speed, "Strategy: go row by row, and back up whenever we get stuck. That's backtracking.")

    events, solution = trace(n)
    stats = {"place": 0, "conflict": 0, "backtrack": 0}
    first = set()
    for i, e in enumerate(events):
        stats[e["kind"]] += 1
        r, c, q = e["row"], e["col"], e["queens"]
        line = None
        if e["kind"] == "conflict":
            ar, ac, why = e["att"][0]
            img = p.frame(queens=q, ghost=(r, c, RED), tint={(r, c): RED},
                          lines=[((ar, ac), (r, c), RED)], current_row=r, stats=stats,
                          label=f"Step {i + 1} \u00b7 conflict",
                          message=f"Row {r + 1}, column {c + 1} is attacked by the queen in "
                                  f"row {ar + 1} ({why}). Skip it.")
            if "conflict" not in first:
                line = "Red means attacked: that square shares a column or diagonal with a queen."
        elif e["kind"] == "place":
            img = p.frame(queens=q, tint={(r, c): GREEN}, current_row=r, stats=stats,
                          label=f"Step {i + 1} \u00b7 place",
                          message=f"Row {r + 1}, column {c + 1} is safe. Place a queen and move to row {r + 2}.")
            if "place" not in first:
                line = "Green means safe, so we place a queen and move to the next row."
        else:
            img = p.frame(queens=q, ghost=(r, c, ORANGE), tint={(r, c): ORANGE}, current_row=r, stats=stats,
                          label=f"Step {i + 1} \u00b7 backtrack",
                          message=f"Row {r + 2} has no safe square left. Go back: remove the queen "
                                  f"from row {r + 1} and try the next column.")
            if "backtrack" not in first:
                line = "Dead end! No safe square left in the next row, so we backtrack."
        first.add(e["kind"])
        # first steps are slow enough to follow, then the search speeds up
        secs = max(0.25, 1.8 * 0.88 ** max(0, i - 8)) / speed
        if line:
            secs = max(secs, 2.5 / speed)          # linger on the first example of each colour
        elif i == 12:
            line = "From here the search speeds up. Watch it try, skip, place and backtrack."
        elif i == 40:
            line = "The boxes on the right are the program's memory: the column of the queen in each row."
        add(img, secs, line)

    if solution is not None:
        add(p.frame(queens=solution, tint={(r, c): GREEN for r, c in enumerate(solution)}, stats=stats,
                    label="Solved!",
                    message=f"All {n} queens are placed and none attack each other. "
                            f"Found after {len(events)} steps and {stats['backtrack']} backtracks."),
            6 / speed, "Solved! Every row has one queen, and no two queens attack each other.")
    else:
        add(p.frame(stats=stats, label="No solution",
                    message=f"Every option was tried. There is no way to place {n} queens."),
            6 / speed, f"Every option failed: {n} queens can't be placed on a {n}\u00d7{n} board.")

    add(p.frame(queens=solution or [], label="How many solutions?", panel="summary",
                message=f"N = {n} has {SOLUTION_COUNTS[n - 1]} solutions in total. The number explodes as N grows, "
                        "but backtracking prunes bad paths early."),
        7 / speed, "Backtracking throws away bad partial boards early, so it never checks every arrangement.")
    return scenes, narration


# ---------------------------------------------------------------- voice-over

def load_voice(voice_dir, count, tmp):
    """Recorded lines are named 01.wav, 02.m4a, ... (number = line in the script).
    Trims silence at both ends and returns {line_index: (wav_path, seconds)}."""
    trim = "silenceremove=start_periods=1:start_threshold=-45dB"
    voice = {}
    for f in sorted(Path(voice_dir).iterdir()):
        if not f.stem.isdigit():
            continue
        k = int(f.stem) - 1
        if not 0 <= k < count:
            print(f"  warning: {f.name} has no matching line in the script (1-{count}), ignored")
            continue
        wav = Path(tmp) / f"voice{k:02d}.wav"
        res = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-af",
                              f"{trim},areverse,{trim},areverse,aformat=sample_rates=48000:channel_layouts=stereo",
                              str(wav)], capture_output=True, text=True)
        if res.returncode:
            sys.exit(f"Could not read {f}:\n{res.stderr}")
        voice[k] = (wav, probe_duration(wav))
    missing = [f"{k + 1:02d}" for k in range(count) if k not in voice]
    if missing:
        print(f"  note: no recording for line(s) {', '.join(missing)} - those stay caption-only")
    return voice


def fit_timeline(scenes, narration, voice, gap=0.4):
    """Hold a frame longer wherever a recorded line would run into the next one.
    Returns the start time of every narration line and the total length."""
    for k, (idx, _) in enumerate(narration):
        if k not in voice:
            continue
        nxt = narration[k + 1][0] if k + 1 < len(narration) else len(scenes)
        window = sum(secs for _, secs in scenes[idx:nxt])
        need = voice[k][1] + gap
        if window < need:
            scenes[idx][1] += need - window
    starts, clock = {}, 0.0
    for i, (_, secs) in enumerate(scenes):
        starts[i] = clock
        clock += secs
    return [starts[idx] for idx, _ in narration], clock


def make_captions(narration, line_starts, voice, total):
    caps = []
    for k, (_, text) in enumerate(narration):
        start = line_starts[k]
        end = start + max(3.5, voice[k][1] + 0.3 if k in voice else 0)
        limit = line_starts[k + 1] - 0.05 if k + 1 < len(narration) else total
        caps.append((start, min(end, limit), text))
    return caps


def srt_time(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6, help="board size, 4-10 works best (default 6)")
    ap.add_argument("--theme", default="clean")
    ap.add_argument("--speed", type=float, default=1.0, help=">1 = faster video, <1 = slower")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", required=True,
                    help="output .mp4 (the .srt captions and .script.txt narration are written next to it)")
    ap.add_argument("--voice", help="folder of recorded lines (01.wav, 02.m4a, ...) to use as the voice-over")
    ap.add_argument("--script-only", action="store_true",
                    help="only write the narration script (to record before rendering)")
    args = ap.parse_args()
    if not 1 <= args.n <= 12:
        sys.exit("--n must be between 1 and 12")

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    script_path = out.with_suffix(".script.txt")

    with tempfile.TemporaryDirectory(prefix="nqueens_") as tmp:
        tmp = Path(tmp)
        painter = _NoPainter() if args.script_only else Painter(args.n, load_theme(args.theme))
        scenes, narration = build_scenes(args.n, painter, args.speed, tmp)
        script_path.write_text("".join(f"{k + 1:02d}  {text}\n" for k, (_, text) in enumerate(narration)))
        print(f"Wrote {script_path}  ({len(narration)} lines to record)")
        if args.script_only:
            return

        voice = load_voice(args.voice, len(narration), tmp) if args.voice else {}
        line_starts, total = fit_timeline(scenes, narration, voice)
        print(f"{len(scenes)} frames, {total:.1f}s of video, {len(voice)} voice line(s)")

        lines = [f"file '{png}'\nduration {secs:.3f}\n" for png, secs in scenes]
        lines.append(f"file '{scenes[-1][0]}'\n")    # concat demuxer needs the last file twice
        (tmp / "list.txt").write_text("".join(lines))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt")]
        graph = f"[0:v]fps={args.fps},format=yuv420p[v]"
        if voice:
            labels = ""
            for j, (k, (wav, _)) in enumerate(sorted(voice.items())):
                cmd += ["-i", str(wav)]
                ms = int(line_starts[k] * 1000)
                graph += f";[{j + 1}:a]adelay={ms}|{ms}[l{j}]"
                labels += f"[l{j}]"
            graph += f";{labels}amix=inputs={len(voice)}:normalize=0,apad[a]"
        cmd += ["-filter_complex", graph, "-map", "[v]"]
        if voice:
            cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-t", f"{total:.3f}", str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode:
            sys.exit(res.stderr)

    srt = out.with_suffix(".srt")
    srt.write_text("\n".join(f"{i + 1}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n"
                             for i, (a, b, text) in enumerate(make_captions(narration, line_starts, voice, total))))
    print(f"Wrote {out}\nWrote {srt}")


class _NoPainter:
    """Stands in for Painter when only the narration script is needed."""
    def frame(self, **_):
        return None


if __name__ == "__main__":
    main()
