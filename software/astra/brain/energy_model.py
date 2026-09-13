"""Energy + risk models used by the mission optimizer.

These functions predict what a candidate plan will COST in Wh before the
rover spends anything - that prediction is the heart of ASTRA-MINE's
"resource-energy-risk aware" decision making.

Formulas (documented in the project report):
  E_travel = P_base * T + (P_drive * D / v)     flat-ground approximation
  E_mine   = (P_base + P_scoop) * t_mine
  risk     = mean(roughness along path)         0..1
"""
from __future__ import annotations

import numpy as np

from ..common.gridmap import GridMap
from ..common.planner import path_length_cells


def travel_energy_wh(cfg, gm: GridMap, path) -> float:
    """Predicted energy (Wh) to follow `path` (list of (r, c)) at cruise speed."""
    if not path or len(path) < 2:
        return 0.0
    dist_m = path_length_cells(path) * gm.res
    v = cfg.rover.max_speed_mps
    t_s = dist_m / v
    drive_frac = 0.35 + 0.65  # motors engaged the whole time (see physics.step)
    power = (cfg.rover.base_power_w
             + cfg.rover.motor_power_w * drive_frac)
    return power * t_s / 3600.0


def mine_energy_wh(cfg, mine_time_s: float) -> float:
    """Predicted energy (Wh) for one collection stop."""
    power = cfg.rover.base_power_w + cfg.rover.scoop_power_w
    return power * mine_time_s / 3600.0


def path_risk(gm: GridMap, path) -> float:
    """Mean roughness along the path (0 smooth .. 1 rocky)."""
    if not path:
        return 0.0
    vals = [float(gm.roughness[r, c]) for r, c in path]
    return float(np.mean(vals))


def return_energy_wh(cfg, gm: GridMap, path_back) -> float:
    """Energy to return to the station (same model as travel)."""
    return travel_energy_wh(cfg, gm, path_back)
