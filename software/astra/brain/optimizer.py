"""AI Layer 3: mission optimization - "where should the rover go next?"

Four selectable target-selection strategies. Running all four on identical
terrain IS the core experiment of ASTRA-MINE (see experiments/run_experiments.py):

  nearest   : go to the nearest known resource zone (baseline)
  shortest  : go to the zone with the cheapest PATH (baseline)
  resource  : go to the zone with the highest expected yield, ignore cost
  full      : maximize  expected value / (energy + risk + travel cost)
              ^ the ASTRA-MINE closed-loop optimizer (our contribution)

Score formula (full strategy):

                P(target) * yield_g * value_per_g
  Score = ---------------------------------------------------
          (E_travel + E_mine + E_return) * (1 + w_risk * risk)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..common.gridmap import GridMap
from ..common.planner import plan_path
from .energy_model import mine_energy_wh, path_risk, travel_energy_wh


@dataclass
class TargetDecision:
    cell: tuple[int, int]
    path: list
    expected_yield_g: float
    e_travel_wh: float
    e_mine_wh: float
    risk: float
    score: float
    strategy: str
    reason: str


def _expected_yield_g(cfg, prob: float, cells_in_zone: int) -> float:
    """ grams we expect to scoop during one mine stop near this cell."""
    grams = cfg.rover.scoop_rate_gps * cfg.mission.mine_time_s
    return grams * prob  # expected value scales with believed probability


def select_target(cfg, gm: GridMap, mapper, rover_xy: tuple[float, float],
                  station_xy: tuple[float, float], strategy: str) -> TargetDecision | None:
    """Choose the next mining target from the rover's current belief."""
    targets = mapper.known_targets(cfg.mission.prob_threshold)
    if not targets:
        return None

    # cluster adjacent target cells into zones so we pick SITES not scattered cells
    zones = _cluster(targets, gm)
    rx, ry = rover_xy
    best: TargetDecision | None = None
    best_key = None

    for zone_cells, centroid_rc in zones:
        zx, zy = gm.center_of(*centroid_rc)
        path = plan_path(gm, gm.cell_of(rx, ry), centroid_rc)
        if path is None:
            continue
        path_back = plan_path(gm, centroid_rc, gm.cell_of(*station_xy))
        p = float(np_mean_prob(gm, zone_cells))
        e_travel = travel_energy_wh(cfg, gm, path)
        e_mine = mine_energy_wh(cfg, cfg.mission.mine_time_s)
        e_back = travel_energy_wh(cfg, gm, path_back) if path_back else 0.0
        risk = path_risk(gm, path)
        yield_g = _expected_yield_g(cfg, p, len(zone_cells))

        dist_m = math.hypot(zx - rx, zy - ry)
        if strategy == "nearest":
            key = (dist_m, )                      # closest zone wins
            score = 1.0 / (dist_m + 1e-6)
            reason = f"distance {dist_m:.2f} m"
        elif strategy == "shortest":
            key = (e_travel, )                    # cheapest path wins
            score = 1.0 / (e_travel + 1e-6)
            reason = f"path cost {e_travel*1000:.1f} mWh"
        elif strategy == "resource":
            key = (-yield_g, )                    # highest expected yield wins
            score = yield_g
            reason = f"expected yield {yield_g:.0f} g (p={p:.2f})"
        elif strategy == "full":
            denom = (e_travel + e_mine + e_back) * (1.0 + cfg.mission.risk_weight * risk)
            score = (yield_g * cfg.mission.prob_threshold) / (denom + 1e-9)
            key = (-score, )                      # highest value-per-energy wins
            reason = (f"score {score:.3f} = {yield_g:.0f}g x value / "
                      f"{(e_travel + e_mine + e_back) * 1000:.0f} mWh x (1+{risk:.2f} risk)")
        else:
            raise ValueError(f"unknown strategy '{strategy}'")

        dec = TargetDecision(
            cell=centroid_rc, path=path, expected_yield_g=yield_g,
            e_travel_wh=e_travel, e_mine_wh=e_mine, risk=risk,
            score=score, strategy=strategy, reason=reason)
        if best_key is None or key < best_key:
            best_key, best = key, dec
    return best


def _cluster(target_cells, gm, max_gap_cells: int = 4):
    """Greedy clustering of high-probability cells into mining zones.
    Returns list of (cells, centroid_rc)."""
    remaining = set(target_cells)
    zones = []
    while remaining:
        seed = remaining.pop()
        cluster = [seed]
        changed = True
        while changed:
            changed = False
            for cell in list(remaining):
                r, c = cell
                if any(abs(r - rr) <= max_gap_cells and abs(c - cc) <= max_gap_cells
                       for rr, cc in cluster):
                    remaining.discard(cell)
                    cluster.append(cell)
                    changed = True
        cluster = [(int(r), int(c)) for r, c in cluster]
        cr = sum(r for r, _ in cluster) / len(cluster)
        cc = sum(c for _, c in cluster) / len(cluster)
        centroid = min(cluster, key=lambda t: (t[0] - cr) ** 2 + (t[1] - cc) ** 2)
        zones.append((cluster, centroid))
    return zones


def np_mean_prob(gm: GridMap, cells) -> float:
    import numpy as np
    return float(np.mean([gm.resource_prob[r, c] for r, c in cells])) if cells else 0.0
