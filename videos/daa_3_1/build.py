#!/usr/bin/env python3
"""Build Video 3.1 (Backtracking Strategy Fundamentals).

    python3 videos/daa_3_1/build.py schedule [--estimate]   # timeline from the voice lines
    python3 videos/daa_3_1/build.py render --quality l       # quick preview render
    python3 videos/daa_3_1/build.py all                      # schedule + 1080p render + final mix
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
    "hook_maze": (None, "bright"),
    "syllabus": ("Today's plan", "calm"),
    "bf_problem": ("Brute force vs backtracking", "calm"),
    "tuple": ("Tuples & constraints", "calm"),
    "t_intro": ("State space tree", "pulse"),
    "n_states": ("Tree terminology", "calm"),
    "d_order": ("Depth-first search", "pulse"),
    "a_code": ("Control abstraction", "quiet"),
    "p_intro": ("Practice", "pulse"),
    "tip1": ("Exam tips", "pulse"),
    "recap": ("Recap", "bright"),
}
# lines whose animation needs more time than the narration takes
MIN_WINDOW = {"hook_maze": 9.5, "hook_name": 5.5, "hook_mascot": 6.0, "bf_brute": 5.5, "t_c": 8.5,
              "d_order": 5.0, "d_bfs": 6.0, "p_pause": 6.0, "p_tree": 7.0, "p_answer": 5.5}

if __name__ == "__main__":
    main(beats, HERE / "scene.py", HERE.parents[1] / "projects" / "daa-3.1", SECTIONS, MIN_WINDOW,
         {"title": beats.TITLE, "code": beats.CODE, "unit": beats.UNIT, "end_secs": 15.0, "title_suffix": "State Space Tree Explained",
          "summary": "What is backtracking, and why is it so much faster than brute force? Using a simple seating "
                     "puzzle, we build the state space tree step by step, explain explicit and implicit constraints, "
                     "problem, solution and answer states, live, E- and dead nodes, the bounding function, "
                     "depth-first search and the control abstraction for backtracking, with a practice question "
                     "and exam tips.",
          "hashtags": "#DAA #Backtracking #StateSpaceTree #Algorithms #DESPU",
          "tags": "daa, design and analysis of algorithms, backtracking, state space tree, explicit constraints, "
                  "implicit constraints, bounding function, control abstraction, live node, e-node, dead node, "
                  "depth first search, daa unit 3, etcs329"})
