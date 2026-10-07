"""Every number and result Video 3.2 states, recomputed from scratch.

qa_check.py runs check(); a wrong claim fails the video before upload.
"""
from math import comb


def nqueens(n, all_solutions=False):
    x, sols, stats = [], [], {"place": 0, "kill": 0, "back": 0}

    def safe(k, i):
        return all(x[j] != i and abs(x[j] - i) != abs(j - k) for j in range(k))

    def solve(k):
        if k == n:
            sols.append([c + 1 for c in x])
            return not all_solutions
        for i in range(n):
            if safe(k, i):
                x.append(i)
                stats["place"] += 1
                if solve(k + 1):
                    return True
                x.pop()
                stats["back"] += 1
            else:
                stats["kill"] += 1
        return False
    solve(0)
    return sols, stats


def coloring(adj, n, m):
    x, stats = {}, {"back": 0}

    def solve(k):
        if k > n:
            return True
        for c in range(1, m + 1):
            if all(x.get(j) != c for j in adj[k] if j < k):
                x[k] = c
                if solve(k + 1):
                    return True
                del x[k]
                stats["back"] += 1
        return False
    ok = solve(1)
    return (dict(x) if ok else None), stats


def adjacency(edges, n):
    adj = {k: set() for k in range(1, n + 1)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def check():
    """-> [(claim as said in the video, passed?)]"""
    results = []
    results.append(("more than four billion ways to place 8 queens (4,426,165,368)", comb(64, 8) == 4426165368))
    all8, full = nqueens(8, all_solutions=True)
    results.append(("8-queens has 92 solutions", len(all8) == 92))
    first8, s8 = nqueens(8)
    results.append(("first 8-queens solution is 1,5,8,6,3,7,2,4", first8[0] == [1, 5, 8, 6, 3, 7, 2, 4]))
    results.append(("found after 113 placements", s8["place"] == 113))
    results.append(("all 92 found with 15,720 squares checked", full["place"] + full["kill"] == 15720))
    first4, _ = nqueens(4)
    results.append(("4-queens answer is 2,4,1,3", first4[0] == [2, 4, 1, 3]))
    exam = adjacency([(1, 2), (1, 3), (2, 3), (2, 5), (3, 4), (3, 5), (4, 5)], 5)
    col, st = coloring(exam, 5, 3)
    results.append(("exam graph: 3 slots, coloring R,G,B,G,R", col == {1: 1, 2: 2, 3: 3, 4: 2, 5: 1}))
    results.append(("exam graph: exactly one backtrack (vertex 4)", st["back"] == 1))
    results.append(("exam graph cannot be done in 2 slots (chromatic number 3)", coloring(exam, 5, 2)[0] is None))
    ex2 = adjacency([(1, 2), (2, 3), (3, 4), (4, 1), (1, 3)], 4)
    results.append(("worked example 2: two colors are not enough", coloring(ex2, 4, 2)[0] is None))
    results.append(("worked example 2: m = 3 gives 1,2,3,2", coloring(ex2, 4, 3)[0] == {1: 1, 2: 2, 3: 3, 4: 2}))
    return results


if __name__ == "__main__":
    for claim, ok in check():
        print(("PASS " if ok else "FAIL ") + claim)
