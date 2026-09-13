"""AI Layer 1 + 2: perception and the resource probability map.

The ResourceMapper maintains the rover's BELIEF about where resources are.
Every cell within camera range gets a noisy observation which is fused into a
running probability estimate (simple Bayesian-style running mean with
confidence). Cells never observed keep the prior.

On the real rover the observations come from vision.detector (colour/texture
proxy detection on camera frames); in simulation they come from the world's
hidden ground truth through the same noisy observation function.
"""
from __future__ import annotations

import numpy as np

from ..common.gridmap import GridMap


class ResourceMapper:
    def __init__(self, cfg, gm: GridMap):
        self.cfg = cfg
        self.gm = gm
        self.n_obs: np.ndarray = np.zeros((gm.n, gm.n), dtype=np.int32)
        self.p_sum: np.ndarray = np.zeros((gm.n, gm.n), dtype=np.float32)

    # ------------------------------------------------------------------ update
    def sense_around_rover(self, rover) -> int:
        """Observe every in-range, not-yet-fused cell around the rover.
        `rover` must expose get_pose() and observe_resource(r, c).
        Returns the number of NEW observations fused."""
        x, y, _ = rover.get_pose()
        r0, c0 = self.gm.cell_of(x, y)
        rad = int(np.ceil(self.cfg.sensor.sensor_radius_m / self.gm.res))
        fused = 0
        for r in range(max(0, r0 - rad), min(self.gm.n, r0 + rad + 1)):
            for c in range(max(0, c0 - rad), min(self.gm.n, c0 + rad + 1)):
                dx, dy = self.gm.center_of(r, c)
                if (dx - x) ** 2 + (dy - y) ** 2 > self.cfg.sensor.sensor_radius_m ** 2:
                    continue
                p = rover.observe_resource(r, c)
                if p is None:
                    continue
                self.fuse(r, c, p)
                fused += 1
        return fused

    def fuse(self, r: int, c: int, p_obs: float) -> None:
        """Fuse one observation into the belief (running mean)."""
        self.n_obs[r, c] += 1
        self.p_sum[r, c] += p_obs
        self.gm.observed[r, c] = True
        self.gm.resource_prob[r, c] = self.p_sum[r, c] / self.n_obs[r, c]


    def mark_mined(self, r: int, c: int) -> None:
        """After scooping a site, the rover KNOWS the area is worked out.
        Fuse near-zero observations for the cell and its neighbours so the
        optimizer stops re-selecting it."""
        for rr, cc in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if self.gm.in_bounds(rr, cc):
                self.fuse(rr, cc, 0.05)
                self.fuse(rr, cc, 0.05)

    # ------------------------------------------------------------------ queries
    def coverage(self) -> float:
        """Fraction of drivable cells observed at least once."""
        driv = int(self.gm.traversable.sum())
        return float((self.gm.observed & self.gm.traversable).sum()) / max(1, driv)

    def known_targets(self, min_prob: float) -> list[tuple[int, int]]:
        """Drivable, observed cells above the probability threshold."""
        mask = (self.gm.observed & self.gm.traversable
                & (self.gm.resource_prob >= min_prob))
        return list(map(tuple, np.argwhere(mask)))

    def frontier_cells(self) -> list[tuple[int, int]]:
        """Drivable unobserved cells adjacent to observed ones - the survey
        frontier the rover walks to build its map."""
        obs = self.gm.observed & self.gm.traversable
        un = (~self.gm.observed) & self.gm.traversable
        frontier = set()
        idx = np.argwhere(un)
        for r, c in idx:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, c + dc
                if self.gm.in_bounds(rr, cc) and obs[rr, cc]:
                    frontier.add((int(r), int(c)))
                    break
        return sorted(frontier)
