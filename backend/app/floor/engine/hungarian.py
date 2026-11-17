"""A minimum-cost assignment, standard library only (design add-floor-pools D1).

The shortest-augmenting-path method (Crouse 2016) that
`scipy.optimize.linear_sum_assignment` implements, followed step for step —
including its tie-breaking, which prefers a column that ends the path — so
the ported draw places fencers where the original did.
"""

from collections.abc import Sequence

INF = float("inf")


def assign(cost: Sequence[Sequence[float]]) -> list[int]:
    """For each row, its column, minimising the total. Rows ≤ columns."""
    rows = len(cost)
    if rows == 0:
        return []
    cols = len(cost[0])
    if rows > cols:
        raise ValueError("more rows than columns")
    u = [0.0] * rows
    v = [0.0] * cols
    shortest = [INF] * cols
    path = [-1] * cols
    col4row = [-1] * rows
    row4col = [-1] * cols
    remaining = [0] * cols

    for current in range(rows):
        sr = [False] * rows
        sc = [False] * cols
        for index in range(cols):
            shortest[index] = INF
            remaining[index] = cols - index - 1
        left = cols
        min_val = 0.0
        sink = -1
        i = current
        while sink == -1:
            index = -1
            lowest = INF
            sr[i] = True
            for it in range(left):
                j = remaining[it]
                reduced = min_val + cost[i][j] - u[i] - v[j]
                if reduced < shortest[j]:
                    path[j] = i
                    shortest[j] = reduced
                # among equal lows, a column that ends the path wins
                if shortest[j] < lowest or (shortest[j] == lowest and row4col[j] == -1):
                    lowest = shortest[j]
                    index = it
            min_val = lowest
            if min_val == INF:
                raise ValueError("no assignment")
            j = remaining[index]
            if row4col[j] == -1:
                sink = j
            else:
                i = row4col[j]
            sc[j] = True
            left -= 1
            remaining[index] = remaining[left]

        u[current] += min_val
        for r in range(rows):
            if sr[r] and r != current:
                u[r] += min_val - shortest[col4row[r]]
        for c in range(cols):
            if sc[c]:
                v[c] -= min_val - shortest[c]

        j = sink
        while True:
            r = path[j]
            row4col[j] = r
            col4row[r], j = j, col4row[r]
            if r == current:
                break
    return col4row
