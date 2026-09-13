"""Grid map utilities shared by the simulator, the planner and the dashboard.

The world is a square grid. Cell (row r, col c) covers the square
[r*res, (r+1)*res) x [c*res, (c+1)*res) in world coordinates, where +x is
"east" and +y is "north". Row 0 is the TOP of the map (max y) when rendered,
which matches image conventions (row index grows downward).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class GridMap:
    size_m: float                 # world side length (m)
    res: float                    # cell size (m)
    n: int                        # number of cells per side

    # Ground truth (hidden from the rover's belief, known to the simulator)
    elevation: np.ndarray = None  # metres, relative
    roughness: np.ndarray = None  # 0 (smooth) .. 1 (impassable rocks)
    resource_amount: np.ndarray = None  # grams of extractable simulant per cell
    traversable: np.ndarray = None      # bool grid

    # Rover belief (updated by perception)
    resource_prob: np.ndarray = None    # believed probability, 0..1
    observed: np.ndarray = None         # bool: has this cell been observed?
    remaining: np.ndarray = None        # grams left after mining (sim bookkeeping)

    # ------------------------------------------------------------------ helpers
    def cell_of(self, x: float, y: float) -> tuple[int, int]:
        """World (x, y) metres -> (row, col) grid indices (clipped)."""
        c = int(np.clip(x / self.res, 0, self.n - 1))
        r = int(np.clip((self.size_m - y) / self.res, 0, self.n - 1))
        return r, c

    def center_of(self, r: int, c: int) -> tuple[float, float]:
        """(row, col) -> world coordinates of the cell centre (x, y) in metres."""
        x = (c + 0.5) * self.res
        y = self.size_m - (r + 0.5) * self.res
        return x, y

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.n and 0 <= c < self.n

    def is_drivable(self, r: int, c: int) -> bool:
        return self.in_bounds(r, c) and bool(self.traversable[r, c])

    @property
    def shape(self) -> tuple[int, int]:
        return (self.n, self.n)


def make_maps(cfg) -> GridMap:
    """Allocate an empty (all-flat, all-traversable) map for the given config."""
    n = cfg.n_cells
    z = lambda: np.zeros((n, n), dtype=np.float32)
    gm = GridMap(
        size_m=cfg.world.size_m, res=cfg.world.resolution, n=n,
        elevation=z(), roughness=z(),
        resource_amount=z(), traversable=np.ones((n, n), dtype=bool),
        resource_prob=np.full((n, n), cfg.sensor.prior_prob, dtype=np.float32),
        observed=np.zeros((n, n), dtype=bool),
        remaining=z(),
    )
    return gm
