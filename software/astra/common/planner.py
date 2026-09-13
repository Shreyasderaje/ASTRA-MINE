"""A* path planner over the terrain grid.

Cost of entering a neighbouring cell = distance * (1 + roughness penalty).
Cells with roughness >= 1.0 (rocks) are impassable. 8-connected grid.
Pure Python + heapq: fast enough for a 60x60 grid at mission runtime.
"""
from __future__ import annotations

import heapq
import math

import numpy as np

# (dr, dc, move distance in cell units)
_NEIGHBOURS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
               (-1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)),
               (1, -1, math.sqrt(2)), (1, 1, math.sqrt(2))]


def plan_path(gm, start_rc: tuple[int, int], goal_rc: tuple[int, int],
              roughness_weight: float = 3.0) -> list[tuple[int, int]] | None:
    """A* from start to goal. Returns list of (r, c) from start to goal
    (inclusive), or None if no drivable path exists."""
    if start_rc == goal_rc:
        return [start_rc]
    if not gm.is_drivable(*goal_rc):
        # allow goals on slightly rough cells by looking for a neighbour
        goal_rc = _nearest_drivable(gm, goal_rc)
        if goal_rc is None:
            return None

    n = gm.n
    rough = gm.roughness
    driv = gm.traversable

    def h(r, c):  # octile distance heuristic (admissible)
        dr, dc = abs(r - goal_rc[0]), abs(c - goal_rc[1])
        return (dr + dc) + (math.sqrt(2) - 2) * min(dr, dc)

    open_heap = [(h(*start_rc), 0.0, start_rc)]
    came = {start_rc: None}
    g_score = {start_rc: 0.0}

    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur == goal_rc:
            path, node = [], cur
            while node is not None:
                path.append(node)
                node = came[node]
            return path[::-1]
        if g > g_score.get(cur, math.inf):
            continue
        r, c = cur
        for dr, dc, dist in _NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < n and 0 <= nc < n) or not driv[nr, nc]:
                continue
            step_cost = dist * (1.0 + roughness_weight * float(rough[nr, nc]))
            ng = g + step_cost
            nb = (nr, nc)
            if ng < g_score.get(nb, math.inf):
                g_score[nb] = ng
                came[nb] = cur
                heapq.heappush(open_heap, (ng + h(nr, nc), ng, nb))
    return None


def _nearest_drivable(gm, rc) -> tuple[int, int] | None:
    """Breadth-first search for the closest drivable cell to rc."""
    from collections import deque
    q, seen = deque([rc]), {rc}
    while q:
        r, c = q.popleft()
        if gm.is_drivable(r, c):
            return (r, c)
        for dr, dc, _ in _NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if gm.in_bounds(nr, nc) and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc))
    return None


def path_length_cells(path) -> float:
    """Path length in cell units (for quick statistics)."""
    if path is None or len(path) < 2:
        return 0.0
    total = 0.0
    for (r1, c1), (r2, c2) in zip(path, path[1:]):
        total += math.hypot(r2 - r1, c2 - c1)
    return total
