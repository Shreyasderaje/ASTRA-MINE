"""Procedural lunar analogue world generator.

Creates the simulated 3 m x 3 m testbed: craters (smooth elevation dips with
gentle slopes), rocks (impassable / high-roughness discs) and buried resource
clusters (spatially correlated gaussian blobs of simulant, like the physical
marker zones the team will lay out in the real testbed).

The ground truth stored here is HIDDEN from the rover's belief; the rover only
ever receives noisy local observations, exactly like the real camera proxy.
"""
from __future__ import annotations

import math

import numpy as np

from ..common.gridmap import GridMap, make_maps
from ..config import Config


def generate_world(cfg: Config) -> GridMap:
    rng = np.random.default_rng(cfg.mission.seed)
    gm = make_maps(cfg)
    n, res, size = gm.n, gm.res, gm.size_m

    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx = (xx + 0.5) * res
    cy = size - (yy + 0.5) * res  # world y (up = +y)

    # --- craters: gaussian dips with a slight rim -------------------------
    for _ in range(cfg.world.n_craters):
        px, py = rng.uniform(0.4, size - 0.4, 2)
        radius = rng.uniform(0.18, 0.38)
        d2 = (cx - px) ** 2 + (cy - py) ** 2
        gm.elevation -= 0.05 * np.exp(-d2 / (2 * (radius * 0.55) ** 2))
        gm.elevation += 0.012 * np.exp(-d2 / (2 * radius ** 2))   # rim
        # craters have gentle slopes: small roughness inside
        gm.roughness += 0.10 * np.exp(-d2 / (2 * (radius * 0.8) ** 2))

    # --- rocks: discs of high roughness -----------------------------------
    for _ in range(cfg.world.n_rocks):
        px, py = rng.uniform(0.15, size - 0.15, 2)
        radius = rng.uniform(0.025, 0.065)
        d2 = (cx - px) ** 2 + (cy - py) ** 2
        gm.roughness = np.where(d2 < radius ** 2, 1.0, gm.roughness)

    # keep the start and station areas clear
    for sx, sy in (cfg.world.start_xy, cfg.world.station_xy):
        d2 = (cx - sx) ** 2 + (cy - sy) ** 2
        gm.roughness = np.where(d2 < 0.12 ** 2, np.minimum(gm.roughness, 0.05), gm.roughness)

    gm.traversable = gm.roughness < 0.95

    # --- buried resource clusters ------------------------------------------
    # K gaussian blobs; each blob has a peak richness, cells get a share.
    # Resources are ONLY placed on drivable ground (you cannot mine a rock).
    placed = 0
    tries = 0
    centers: list[tuple[float, float]] = []
    peaks: list[float] = []
    while placed < cfg.world.n_resource_zones and tries < 400:
        tries += 1
        px, py = rng.uniform(0.5, size - 0.5, 2)
        # spread zones apart so near-vs-far and rich-vs-poor tradeoffs exist
        if any(math.hypot(px - ox, py - oy) < 0.9 for ox, oy in centers):
            continue
        radius = rng.uniform(0.22, 0.40)
        peak = rng.uniform(0.25, 1.0)   # heterogeneous richness
        centers.append((px, py))
        peaks.append(peak)
        d2 = (cx - px) ** 2 + (cy - py) ** 2
        blob = peak * np.exp(-d2 / (2 * (radius * 0.5) ** 2))
        gm.resource_amount = np.maximum(gm.resource_amount, blob * cfg.world.max_resource_per_cell_g)
        placed += 1
    gm.resource_amount *= gm.traversable
    gm.remaining = gm.resource_amount.copy()

    # belief arrays already initialised in make_maps (prior + unobserved)
    return gm


def unknown_world(cfg: Config) -> GridMap:
    """An UNKNOWN world for real-rover operation.

    make_maps() already allocates exactly the right thing: flat, all-
    traversable, zero resources, prior belief everywhere. On the physical
    testbed the ground truth lives in reality - rocks are discovered by the
    ToF sensor (real_rover.RealRoverHAL.drain_percepts), resource zones by
    the camera detector (vision.live) and operator cueing in the dashboard.
    The mission brain plans on this belief map exactly as it does in
    simulation, which is what makes the digital twin honest.
    """
    return make_maps(cfg)


def observe_ground_truth(gm: GridMap, r: int, c: int, sigma: float,
                         rng: np.random.Generator) -> float:
    """One noisy resource-probability observation of a cell (the 'sensor')."""
    amount = gm.remaining[r, c]
    gt_prob = float(np.clip(amount / 40.0, 0.0, 1.0))  # normalise like the real proxy
    noisy = gt_prob + rng.normal(0.0, sigma)
    return float(np.clip(noisy, 0.0, 1.0))
