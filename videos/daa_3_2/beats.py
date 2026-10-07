"""Video 3.2 - 8-Queens & Graph Coloring (DAA Unit III).

Each beat = one narration line. The key ties it to its animation in scene.py,
the mood steers delivery and background music, "|" marks caption breaks.
"""

TITLE = "8-Queens & Graph Coloring"
CODE = "3.2"
UNIT = "III"

BEATS = [
    # ---- hook
    ("hook_board", "curious", "Imagine an ordinary chessboard and eight queens. | How do you place all eight so that no queen can attack another?"),
    ("hook_count", "excited", "There are more than four billion ways to put eight queens on sixty-four squares. | Only ninety-two of them work!"),
    ("hook_mascot", "warm", "Welcome to the DAA series by Abhijeet Karve. | I'm Algo, and I'll guide you through every algorithm, step by step."),
    ("syllabus", "explain", "This is Unit Three, Backtracking. | Today we solve two classic problems: the eight queens problem, and graph coloring."),
    ("exam", "explain", "Both are favourite exam questions, | so stay till the end for the exam tips."),
    # ---- backtracking recap
    ("recap1", "explain", "Quick recap. | Backtracking builds the answer one choice at a time."),
    ("recap2", "explain", "After every choice, we check a bounding function. | If the partial answer can never become a solution, we stop and go back."),
    ("recap3", "warm", "That is why backtracking is so much faster than trying everything. | Whole branches of the search tree are cut away early."),
    # ---- 8-queens: the model
    ("q_rules", "explain", "First, the rules. | A queen attacks every square in her row, her column, and both diagonals."),
    ("q_explicit", "explain", "Since two queens can never share a row, | we simply put queen k in row k."),
    ("q_vector", "explain", "So the whole answer is just a list x, | where x of k is the column of the queen in row k."),
    ("q_implicit", "emphatic", "Now the real test. | A new queen is safe only if no earlier queen is in the same column, or on the same diagonal."),
    ("q_diag", "explain", "Two queens share a diagonal when the difference of their columns | equals the difference of their rows."),
    ("q_place", "explain", "This check is the function Place of k and i. | It returns true only if queen k can safely go in column i."),
    # ---- 4-queens trace with the state space tree
    ("t_intro", "curious", "Let's see it in action on a smaller board, with four queens, | and draw the state space tree as we go."),
    ("t_q1", "warm", "Queen one goes in column one. | That is the first node of our tree."),
    ("t_q2", "explain", "For queen two, columns one and two are attacked, so those branches die. | Column three is safe."),
    ("t_dead", "emphatic", "But now look at row three. | Every column is attacked. Dead end!"),
    ("t_back", "explain", "So we backtrack. | Queen two moves to column four, and queen three finds column two."),
    ("t_dead2", "emphatic", "Row four is completely blocked again. | We backtrack all the way to queen one."),
    ("t_q1b", "warm", "Queen one moves to column two. | Queen two goes to column four, | and queen three to column one."),
    ("t_solved", "excited", "And queen four fits in column three. | Solved! The answer is two, four, one, three."),
    ("t_tree", "explain", "Look at the tree. | The red nodes were killed by the bounding function, so we never searched below them."),
    # ---- 8-queens time-lapse
    ("e_lapse", "excited", "Now watch the same algorithm on the full eight by eight board."),
    ("e_result", "explain", "After one hundred and thirteen placements, it finds the first solution: | one, five, eight, six, three, seven, two, four."),
    ("e_count", "explain", "If we keep going, backtracking finds all ninety-two solutions, | while checking only a tiny part of those four billion boards."),
    # ---- the algorithm
    ("a_code", "explain", "Here is the algorithm. | N Queens of k tries every column i for row k."),
    ("a_code2", "explain", "If Place says it is safe, we set x of k to i. | If k equals n, we print the solution, otherwise we move on to row k plus one."),
    ("a_complex", "explain", "In the worst case the tree has about n factorial leaves, | so the time complexity is order of n factorial."),
    # ---- graph coloring
    ("g_intro", "curious", "Now our second problem. | Can you schedule five exams in just three time slots?"),
    ("g_graph", "explain", "Each subject is a vertex. | An edge means some students take both subjects, so those two exams cannot share a slot."),
    ("g_def", "explain", "This is graph coloring. | Give every vertex one of m colors, so that no two adjacent vertices get the same color."),
    ("g_chromatic", "explain", "The smallest such m is called the chromatic number of the graph."),
    ("g_x", "explain", "Just like the queens, | x of k is the color of vertex k, and we fill the vertices one by one."),
    ("g_v1", "warm", "Here m is three: red, green and blue. | Vertex one gets red."),
    ("g_v2", "explain", "Vertex two touches vertex one, so red is not allowed. | It gets green."),
    ("g_v3", "explain", "Vertex three touches both one and two. | Red and green are taken, so it gets blue."),
    ("g_v4", "warm", "Vertex four only touches three and five. | Red is fine."),
    ("g_dead", "emphatic", "Now vertex five touches green, blue and red. | No color is left. Dead end!"),
    ("g_back", "explain", "So we backtrack to vertex four, | and try its next color, green."),
    ("g_done", "excited", "Now vertex five can be red. | All five exams fit into three slots!"),
    ("g_code", "explain", "In code, Next Value of k finds the next color | that no adjacent vertex is already using."),
    ("g_complex", "explain", "There are m to the power n possible colorings, | and each check takes order n time, so the worst case is order of n times m to the n."),
    # ---- comparison, exam tips, recap
    ("cmp", "explain", "Notice the pattern. | Both problems use the same control abstraction: choose, check the bound, go deeper, and backtrack."),
    ("tip1", "emphatic", "Exam tip one. | You will often be asked to draw the state space tree for four queens. Mark the killed nodes clearly."),
    ("tip2", "emphatic", "Exam tip two. | Write the Place function, and explain the diagonal condition in words."),
    ("tip3", "emphatic", "Exam tip three. | For graph coloring, show the color array at every step, and point out where you backtrack."),
    ("recap", "warm", "To recap: | backtracking builds a solution step by step, | and kills a branch the moment it breaks a rule."),
    ("next", "warm", "In the next video, we use the same idea for sum of subsets and the Hamiltonian cycle. | See you there!"),
]


def script_text():
    """Narration script in the format the voice tools read: '01  {mood} text'."""
    return "".join(f"{i + 1:02d}  {{{mood}}} {text}\n" for i, (_, mood, text) in enumerate(BEATS))


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("script.txt")
    out.write_text(script_text())
    words = sum(len(t.replace("|", " ").split()) for _, _, t in BEATS)
    print(f"Wrote {out}: {len(BEATS)} beats, {words} words (~{words / 140:.1f} min at 140 wpm)")
