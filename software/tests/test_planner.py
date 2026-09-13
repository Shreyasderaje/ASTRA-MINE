"""A* planner: obstacle avoidance, detours, and unreachable goals."""
import math

from astra.common.planner import path_length_cells, plan_path
from astra.config import Config
from astra.sim.world import generate_world


def _world(seed=7):
    cfg = Config()
    cfg.mission.seed = seed
    return cfg, generate_world(cfg)


def _carve_wall(gm, gap_col=None):
    """Block an entire row, optionally leaving a 3-cell gap."""
    n = gm.n
    r_wall = n // 2
    for c in range(n):
        if gap_col is not None and abs(c - gap_col) <= 1:
            continue
        gm.traversable[r_wall, c] = False
        gm.roughness[r_wall, c] = 1.0
    return r_wall


def test_path_routes_through_gap_and_avoids_wall():
    cfg, gm = _world()
    n = gm.n
    gap_col = 3 * n // 4
    r_wall = _carve_wall(gm, gap_col=gap_col)

    start, goal = (2, n // 2), (n - 3, n // 2)
    path = plan_path(gm, start, goal)

    assert path is not None, "a gap exists so a path must exist"
    # never steps on a blocked cell
    for r, c in path:
        assert gm.is_drivable(r, c), f"path cell ({r},{c}) is not drivable"
    # crosses the wall row only through the gap
    crossing = [c for r, c in path if r == r_wall]
    assert crossing, "path must cross the wall row"
    assert max(abs(c - gap_col) for c in crossing) <= 1
    # and the detour is longer than the straight-line distance
    assert path_length_cells(path) > math.hypot(goal[0] - start[0],
                                                goal[1] - start[1]) + 1.0


def test_fully_blocked_wall_means_no_path():
    cfg, gm = _world()
    n = gm.n
    _carve_wall(gm, gap_col=None)          # no gap at all
    path = plan_path(gm, (2, n // 2), (n - 3, n // 2))
    assert path is None


def test_trivial_path_is_the_cell_itself():
    cfg, gm = _world()
    cell = (10, 10)
    assert plan_path(gm, cell, cell) == [cell]
