"""Video 3.1 - Backtracking Strategy Fundamentals (DAA Unit III).

Each beat = one narration line. The key ties it to its animation in scene.py,
the mood steers delivery and background music, "|" marks caption breaks.

Running example: seat Aman (A), Bhavna (B) and Chirag (C) on three seats in a
row, but Aman and Bhavna must not sit next to each other.
"""

TITLE = "Backtracking Strategy Fundamentals"
CODE = "3.1"
UNIT = "III"

BEATS = [
    # ---- hook
    ("hook_maze", "curious", "Imagine you are in a maze. | At every junction you pick a path, and at a dead end, you walk back to the last junction and try another."),
    ("hook_name", "excited", "That simple idea, go forward, and step back when stuck, | is one of the most powerful strategies in computer science: backtracking."),
    ("hook_mascot", "warm", "Welcome to the DAA series by Abhijeet Karve. | I'm Algo, and I'll guide you through every algorithm, step by step."),
    ("syllabus", "explain", "This is Unit Three, video one, the foundation of backtracking. | Today: the state space tree, explicit and implicit constraints, depth first search, and the control abstraction."),
    ("exam", "explain", "Every one of these is a direct exam question, | so stay till the end for the exam tips."),
    # ---- brute force vs backtracking
    ("bf_problem", "curious", "Here is our problem. | Three students, Aman, Bhavna and Chirag, must sit on three seats in a row."),
    ("bf_rule", "explain", "But Aman and Bhavna chat all the time, | so the teacher says they must not sit next to each other."),
    ("bf_brute", "explain", "Brute force would first write down every possible arrangement, | and only then check each one."),
    ("bf_count", "emphatic", "Three choices for each seat: three times three times three, | twenty seven arrangements to build and test."),
    ("bf_idea", "warm", "Backtracking is smarter. | It fills one seat at a time, and checks the rules after every single choice."),
    ("bf_kill", "explain", "The moment a partial arrangement breaks a rule, it is thrown away, | with everything that could have grown from it."),
    # ---- the solution tuple and the two kinds of constraints
    ("tuple", "explain", "First, how we write a solution. | Backtracking always builds the answer as a tuple: x one, x two, up to x n."),
    ("tuple_ex", "explain", "Here, x i is the student on seat i. | So the tuple A, C, B means Aman, then Chirag, then Bhavna."),
    ("c_intro", "curious", "Every backtracking problem has two kinds of rules: | explicit constraints and implicit constraints."),
    ("c_explicit", "explain", "Explicit constraints restrict each x i on its own, to a set of allowed values. | Here, every seat must hold A, B or C."),
    ("c_space", "explain", "All tuples that satisfy the explicit constraints form the solution space: | here, the twenty seven arrangements."),
    ("c_implicit", "explain", "Implicit constraints relate the x i's to each other, | and decide which tuples are real answers."),
    ("c_implicit_ex", "emphatic", "Here there are two. | No student can sit on two seats, and Aman and Bhavna must not be neighbours."),
    ("c_trick", "warm", "Remember: explicit is about one variable, | implicit is about how the variables relate."),
    # ---- state space tree
    ("t_intro", "explain", "Now let's organise the search as a tree, called the state space tree. | The root is the empty arrangement."),
    ("t_levels", "explain", "Level one chooses seat one, level two chooses seat two, and level three chooses seat three. | Each edge is one choice."),
    ("t_a", "warm", "Seat one gets Aman. | That is a new node."),
    ("t_a2", "explain", "For seat two, Aman is already seated, so that branch dies. | Bhavna would sit next to Aman, so that dies too. | Chirag is fine."),
    ("t_acb", "excited", "For seat three, only Bhavna is left, and she is not next to Aman. | A, C, B. Our first answer!"),
    ("t_back", "explain", "Now we backtrack, | all the way up to seat one, and try Bhavna there."),
    ("t_bca", "excited", "The same thing happens in mirror image. | B, C, A is our second answer."),
    ("t_c", "explain", "Finally, Chirag on seat one. | Aman and Bhavna are now forced together on seats two and three, so everything below dies."),
    ("t_result", "warm", "Done. Two answers, | from only twenty four nodes, instead of the thirty nine in the full tree."),
    # ---- terminology
    ("n_states", "explain", "Some names you must know. | Every node in this tree is a problem state."),
    ("n_solution", "explain", "Nodes whose path gives a complete tuple are solution states, | and those that satisfy every constraint are answer states."),
    ("n_live", "explain", "While searching, a live node is a node that has been generated, | but whose children have not all been generated yet."),
    ("n_enode", "explain", "The E node is the live node being expanded right now. | A dead node is never expanded again."),
    ("n_bound", "emphatic", "The test that kills nodes is the bounding function. | It returns false when a partial tuple can never become an answer."),
    # ---- depth first search
    ("d_order", "curious", "Now look at the order in which the nodes were created."),
    ("d_dfs", "explain", "We always went as deep as possible first, | and came back up only when we were stuck. That is depth first search."),
    ("d_bfs", "explain", "Going level by level would be breadth first search, | the idea behind branch and bound, in video three point four."),
    # ---- control abstraction
    ("a_code", "explain", "Now the general algorithm, the control abstraction. | Backtrack of k fills position k, once x one to x k minus one are chosen."),
    ("a_for", "explain", "T gives every possible value for x k. | That is where the explicit constraints come in."),
    ("a_bound", "explain", "B k is the bounding function, where the implicit constraints are checked. | Only values that pass it are kept."),
    ("a_answer", "explain", "If the tuple is a complete answer, we write it out. | If there are more positions to fill, we call Backtrack of k plus one."),
    ("a_map", "warm", "For our seating problem, T is the three students, | and B checks that nobody is seated twice and Aman is not next to Bhavna."),
    ("a_eff", "explain", "Its speed depends on four things: | the time to generate x k, how many values satisfy the explicit constraints, | the time for the bounding function, and how many values pass it."),
    ("a_worst", "explain", "In the worst case the tree is still exponential, | but a good bounding function makes backtracking fast in practice."),
    # ---- practice
    ("p_intro", "curious", "Your turn. | List all binary strings of length three, with no two ones next to each other."),
    ("p_pause", "warm", "Pause the video, and draw the state space tree. | I'll wait!"),
    ("p_tree", "explain", "Each level chooses zero or one, | and a node dies the moment it puts a one right after another one."),
    ("p_answer", "excited", "So there are five answers: | zero zero zero, zero zero one, zero one zero, one zero zero, and one zero one."),
    # ---- exam tips, recap
    ("tip1", "emphatic", "Exam tip one. | Define explicit and implicit constraints, with an example like today's."),
    ("tip2", "emphatic", "Exam tip two. | Draw the state space tree, number the nodes in the order they are generated, and cross out the dead ones."),
    ("tip3", "emphatic", "Exam tip three. | Write the control abstraction, and explain T and the bounding function in one line each."),
    ("recap", "warm", "To recap: | backtracking builds a tuple one choice at a time, | searches the state space tree depth first, | and kills a node the moment it fails the bounding function."),
    ("next", "warm", "In the next video, we use all of this to solve the eight queens problem and graph coloring. | See you there!"),
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
