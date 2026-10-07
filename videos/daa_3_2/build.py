#!/usr/bin/env python3
"""Build Video 3.2 (8-Queens & Graph Coloring).

    python3 videos/daa_3_2/build.py schedule [--estimate]   # timeline from the voice lines
    python3 videos/daa_3_2/build.py render --quality l       # quick preview render
    python3 videos/daa_3_2/build.py all                      # schedule + 1080p render + final mix
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
import beats  # noqa: E402
from production import main  # noqa: E402

# section title shown in the header + background music mood, set at the section's first line
SECTIONS = {
    "hook_board": (None, "bright"),
    "syllabus": ("Today's plan", "calm"),
    "recap1": ("Backtracking · Quick recap", "calm"),
    "q_rules": ("8-Queens · The rules", "calm"),
    "t_intro": ("4-Queens · State space tree", "pulse"),
    "e_lapse": ("8-Queens · Full board", "pulse"),
    "a_code": ("The algorithm", "quiet"),
    "g_intro": ("Graph coloring", "calm"),
    "g_v1": ("Graph coloring · Step by step", "pulse"),
    "g_code": ("Graph coloring · Algorithm", "quiet"),
    "w_intro": ("Worked example \u00b7 Is m = 2 enough?", "pulse"),
    "w_m3": ("Worked example \u00b7 Now m = 3", "pulse"),
    "cmp": ("The common pattern", "calm"),
    "tip1": ("Exam tips", "pulse"),
    "recap": ("Recap", "bright"),
}
# lines whose animation needs more time than the narration takes
MIN_WINDOW = {"hook_board": 5.5, "hook_count": 6.5, "hook_mascot": 6.0, "t_solved": 6.0, "t_tree": 5.0,
              "e_lapse": 15.0, "e_result": 7.0, "e_count": 7.5, "g_done": 5.0, "w_dead": 7.5, "w_m3": 6.0}

if __name__ == "__main__":
    main(beats, HERE / "scene.py", HERE.parents[1] / "projects" / "daa-3.2", SECTIONS, MIN_WINDOW,
         {"title": beats.TITLE, "code": beats.CODE, "unit": beats.UNIT,
          "summary": "How do you place 8 queens on a chessboard so that none attack each other, and how do you "
                     "schedule exams so no student has a clash? Both are solved with backtracking. We build the "
                     "4-queens state space tree step by step, watch the full 8-queens search, and colour an exam "
                     "timetable graph with 3 colours, then cover the algorithms (Place, NQueens, mColoring), "
                     "their time complexity, a second worked example (is m = 2 enough?) and exam tips.",
          "hashtags": "#DAA #Backtracking #NQueens #GraphColoring #Algorithms #DESPU",
          "tags": "daa, design and analysis of algorithms, backtracking, 8 queens problem, n queens, graph coloring, "
                  "m coloring, state space tree, chromatic number, daa unit 3, etcs329"})
