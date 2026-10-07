"""Every number and result Video 3.1 states, recomputed from scratch.

qa_check.py runs check(); a wrong claim fails the video before upload.
"""
from itertools import product


def backtrack(values, n, ok):
    """All answers in the order backtracking finds them, plus how many nodes it generated."""
    x, answers, nodes = [], [], [0]

    def solve(k):
        for v in values:
            nodes[0] += 1                     # every value tried is a generated node (live or killed)
            if ok(x + [v]):
                x.append(v)
                if k == n - 1:
                    answers.append("".join(x))
                else:
                    solve(k + 1)
                x.pop()
    solve(0)
    return answers, nodes[0]


def seating_ok(t):
    if len(set(t)) < len(t):                  # nobody on two seats
        return False
    return all({a, b} != {"A", "B"} for a, b in zip(t, t[1:]))   # Aman and Bhavna not neighbours


def binary_ok(t):
    return all(not (a == "1" and b == "1") for a, b in zip(t, t[1:]))


def check():
    """-> [(claim as said in the video, passed?)]"""
    results = []
    space = list(product("ABC", repeat=3))
    results.append(("3 x 3 x 3 = 27 arrangements in the solution space", len(space) == 27))
    brute = sorted("".join(t) for t in space if seating_ok(list(t)))
    answers, nodes = backtrack("ABC", 3, seating_ok)
    results.append(("seating has exactly two answers, A C B and B C A", sorted(answers) == brute == ["ACB", "BCA"]))
    results.append(("backtracking finds A C B first", answers[0] == "ACB"))
    results.append(("backtracking generates 24 nodes", nodes == 24))
    results.append(("the full tree has 39 nodes (3 + 9 + 27)", 3 + 9 + 27 == 39))
    results.append(("Chirag on seat 1 leads to no answer", not any(a.startswith("C") for a in answers)))
    bins, _ = backtrack("01", 3, binary_ok)
    results.append(("binary strings of length 3 without adjacent 1s: 000, 001, 010, 100, 101",
                    bins == ["000", "001", "010", "100", "101"]))
    return results


if __name__ == "__main__":
    for claim, ok in check():
        print(("PASS " if ok else "FAIL ") + claim)
