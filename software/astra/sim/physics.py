"""Simulated rover physics: differential-drive kinematics, terrain-following
motion with obstacle blocking, battery drain and the mining mechanism.

This module IS the digital twin of the physical rover. The energy parameters
in config.RoverConfig were chosen to match the real bill of materials so that
simulated energy metrics transfer to the hardware demonstrator.
"""
from __future__ import annotations

import math

import numpy as np

from ..common.gridmap import GridMap
from ..config import Config


class SimRover:
    def __init__(self, cfg: Config, gm: GridMap, rng: np.random.Generator):
        self.cfg = cfg
        self.gm = gm
        self.rng = rng
        self.x, self.y = cfg.world.start_xy
        self.heading = math.pi / 2  # face "north"
        self.battery_wh = cfg.rover.battery_wh
        self.hopper_g = 0.0
        # mission telemetry accumulators
        self.distance_m = 0.0
        self.energy_used_wh = 0.0
        self.time_s = 0.0
        self.collected_total_g = 0.0
        self.collisions = 0

    # ------------------------------------------------------------------ state
    @property
    def pose(self) -> tuple[float, float, float]:
        return self.x, self.y, self.heading

    @property
    def pose_noisy(self) -> tuple[float, float, float]:
        """What the rover's own odometry reports (slightly drifted)."""
        s = 0.01
        return (self.x + self.rng.normal(0, s),
                self.y + self.rng.normal(0, s),
                (self.heading + self.rng.normal(0, 0.01)) % (2 * math.pi))

    # ------------------------------------------------------------------ drive
    def step(self, v: float, omega: float, dt: float) -> None:
        """Advance the physics by dt seconds with commanded velocities."""
        cfg = self.cfg
        v = float(np.clip(v, 0.0, cfg.rover.max_speed_mps))
        omega = float(np.clip(omega, -cfg.rover.max_omega, cfg.rover.max_omega))

        # battery drain: electronics + drive + turning
        drive_frac = abs(v) / cfg.rover.max_speed_mps
        turn_frac = abs(omega) / cfg.rover.max_omega
        power_w = (cfg.rover.base_power_w
                   + cfg.rover.motor_power_w * (0.35 + 0.65 * drive_frac)
                   + 1.0 * turn_frac)
        e_wh = power_w * dt / 3600.0
        self.battery_wh = max(0.0, self.battery_wh - e_wh)
        self.energy_used_wh += e_wh
        self.time_s += dt

        if v <= 1e-4 and abs(omega) <= 1e-4:
            return

        # integrate heading, then try to move (blocked by rocks / walls).
        # If the direct move is blocked, try axis-separated "wall sliding"
        # so the rover glances along obstacles instead of jamming forever.
        self.heading = (self.heading + omega * dt) % (2 * math.pi)
        nx = self.x + v * math.cos(self.heading) * dt
        ny = self.y + v * math.sin(self.heading) * dt
        moved = False

        def free(px: float, py: float) -> bool:
            if not (0.02 <= px <= cfg.world.size_m - 0.02
                    and 0.02 <= py <= cfg.world.size_m - 0.02):
                return False
            r, c = self.gm.cell_of(px, py)
            return bool(self.gm.traversable[r, c])

        if free(nx, ny):
            step = math.hypot(nx - self.x, ny - self.y)
            self.x, self.y = nx, ny
            self.distance_m += step
            moved = True
        elif free(nx, self.y):          # slide along the x axis
            step = abs(nx - self.x)
            self.x = nx
            self.distance_m += step
            moved = True
        elif free(self.x, ny):          # slide along the y axis
            step = abs(ny - self.y)
            self.y = ny
            self.distance_m += step
            moved = True
        if not moved:
            self.collisions += 1

    def drive_towards(self, tx: float, ty: float, dt: float) -> bool:
        """P-controller that steers the rover toward (tx, ty).
        Returns True when the waypoint is reached."""
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < self.cfg.mission.waypoint_tol_m:
            self.step(0.0, 0.0, dt)
            return True
        target_heading = math.atan2(dy, dx)
        err = (target_heading - self.heading + math.pi) % (2 * math.pi) - math.pi
        omega = float(np.clip(2.5 * err, -self.cfg.rover.max_omega, self.cfg.rover.max_omega))
        # slow down for sharp turns, keep some speed when roughly on-heading
        speed = self.cfg.rover.max_speed_mps * (1.0 if abs(err) < 0.35 else 0.35)
        self.step(speed, omega, dt)
        return False

    # ------------------------------------------------------------------ mining
    def collect_sample(self, duration_s: float) -> float:
        """Run the scoop for duration_s; returns grams actually collected."""
        cfg = self.cfg
        if duration_s <= 0:
            return 0.0
        power = cfg.rover.base_power_w + cfg.rover.scoop_power_w
        self.battery_wh = max(0.0, self.battery_wh - power * duration_s / 3600.0)
        self.energy_used_wh += power * duration_s / 3600.0
        self.time_s += duration_s

        r, c = self.gm.cell_of(self.x, self.y)
        want = min(cfg.rover.scoop_rate_gps * duration_s,
                   max(0.0, cfg.rover.scoop_max_g - self.hopper_g))
        if want <= 0:
            return 0.0
        # scoop the centre cell plus the 4 neighbours (scoop width > 1 cell),
        # always bounded by what is left in the ground AND by hopper capacity
        got = 0.0
        spots = [(r, c, 1.0), (r - 1, c, 0.25), (r + 1, c, 0.25),
                 (r, c - 1, 0.25), (r, c + 1, 0.25)]
        for rr, cc, frac in spots:
            room = cfg.rover.scoop_max_g - self.hopper_g - got
            if room <= 0:
                break
            if not self.gm.in_bounds(rr, cc):
                continue
            take = float(min(want * frac, self.gm.remaining[rr, cc], room))
            if take > 0:
                self.gm.remaining[rr, cc] -= take
                got += take
        self.hopper_g += got
        self.collected_total_g += got
        return got

    def dump_hopper_at_station(self, station_xy: tuple[float, float],
                               dump_radius_m: float = 0.25) -> float:
        """If close enough to the processing station, empty the hopper.
        Returns grams delivered (0 if too far)."""
        if math.hypot(self.x - station_xy[0], self.y - station_xy[1]) > dump_radius_m:
            return 0.0
        delivered = self.hopper_g
        self.hopper_g = 0.0
        return delivered
