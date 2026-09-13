"""Simulated rover wrapped in the RoverInterface."""
from __future__ import annotations

import numpy as np

from ..common.gridmap import GridMap
from ..config import Config
from ..sim.physics import SimRover
from ..sim.world import observe_ground_truth
from .base import RoverInterface


class SimRoverHAL(RoverInterface):
    """Connects the mission brain to the physics simulator."""

    def __init__(self, cfg: Config, gm: GridMap, rng: np.random.Generator):
        self.cfg = cfg
        self.gm = gm
        self.rover = SimRover(cfg, gm, rng)

    def get_pose(self) -> tuple[float, float, float]:
        return self.rover.pose_noisy

    def get_battery_wh(self) -> float:
        return self.rover.battery_wh

    def observe_resource(self, r: int, c: int) -> float | None:
        # the camera must be within sensor range of the cell being observed
        x, y, _ = self.rover.pose_noisy
        cx, cy = self.gm.center_of(r, c)
        if (x - cx) ** 2 + (y - cy) ** 2 > self.cfg.sensor.sensor_radius_m ** 2:
            return None
        return observe_ground_truth(self.gm, r, c, self.cfg.sensor.obs_noise_sigma, self.rover.rng)

    def drive_towards(self, tx: float, ty: float, dt: float) -> bool:
        return self.rover.drive_towards(tx, ty, dt)

    def collect_sample(self, duration_s: float) -> float:
        return self.rover.collect_sample(duration_s)

    def dump_hopper(self) -> float:
        return self.rover.dump_hopper_at_station(self.cfg.world.station_xy)

    def idle(self, dt: float) -> None:
        self.rover.step(0.0, 0.0, dt)

    @property
    def telemetry(self) -> dict:
        return {
            "x": self.rover.x, "y": self.rover.y,
            "heading": self.rover.heading,
            "battery_wh": self.rover.battery_wh,
            "battery_pct": 100.0 * self.rover.battery_wh / self.cfg.rover.battery_wh,
            "energy_used_wh": self.rover.energy_used_wh,
            "distance_m": self.rover.distance_m,
            "time_s": self.rover.time_s,
            "hopper_g": self.rover.hopper_g,
            "collected_g": self.rover.collected_total_g,
            "collisions": self.rover.collisions,
        }
