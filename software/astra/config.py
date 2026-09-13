"""
ASTRA-MINE global configuration.

Every physical constant used by the simulation, the mission brain and the
energy model lives here, so experiments are reproducible and easy to tune
when you move from the simulator to the real rover.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class WorldConfig:
    """Lunar analogue testbed (simulated 1:1 with the physical testbed)."""
    size_m: float = 3.0            # testbed side length in metres (3m x 3m)
    resolution: float = 0.05       # grid cell size in metres (60x60 cells)
    n_resource_zones: int = 5      # number of buried "resource" clusters
    n_rocks: int = 26              # number of rock obstacles
    n_craters: int = 5             # number of shallow craters / slopes
    max_resource_per_cell_g: float = 40.0   # grams of simulant a full cell holds
    resource_contrast: float = 0.55  # visual contrast of resource zones (0..1)
    station_xy: tuple = (0.25, 0.25)  # processing station position (m, m)
    start_xy: tuple = (0.45, 0.25)    # rover start position (m, m)

    @property
    def cells(self) -> int:
        return int(round(self.size_m / self.resolution))


@dataclass
class RoverConfig:
    """Physical rover parameters (match the real built rover)."""
    mass_kg: float = 3.5           # rover + battery mass
    wheel_radius_m: float = 0.033  # 65 mm wheels
    wheel_base_m: float = 0.18     # distance between left/right wheels
    max_speed_mps: float = 0.12    # safe indoor speed
    max_omega: float = 1.6         # rad/s turning rate
    rol_cost: float = 0.12         # rolling resistance coefficient
    drivetrain_eff: float = 0.60   # motor + gearbox efficiency
    base_power_w: float = 6.0      # Pi 5 + ESP32 + camera idle draw (W)
    motor_power_w: float = 4.0     # extra electrical draw at full drive (W)
    scoop_power_w: float = 2.0     # servo power while collecting (W)
    scoop_rate_gps: float = 8.0    # grams of simulant collected per second
    scoop_max_g: float = 120.0     # hopper capacity (grams)
    battery_wh: float = 40.0       # 3S 3.3Ah Li-ion ~ 36-40 Wh usable


@dataclass
class SensorConfig:
    """Perception sensor parameters."""
    sensor_radius_m: float = 0.45  # camera can classify ground within this radius
    obs_noise_sigma: float = 0.12  # noise on a single resource observation
    prior_prob: float = 0.15       # prior resource probability for unseen cells
    obs_per_update: int = 1        # observations fused per cell visit


@dataclass
class MissionConfig:
    """Mission-level rules and budget."""
    strategy: str = "full"         # nearest | shortest | resource | full
    survey_target_frac: float = 0.35  # survey until this fraction of cells observed
    prob_threshold: float = 0.22   # a cell with prob above this is a mining target
    max_sites: int = 99            # effectively unlimited - missions are ENERGY bound
    mine_time_s: float = 12.0      # seconds of scooping per site
    energy_budget_wh: float = 1.2  # mission ends when this much energy is spent
    battery_reserve_wh: float = 6.0   # stop mission below this remaining energy
    dt: float = 0.1                # simulation step (s)
    waypoint_tol_m: float = 0.045  # distance at which a waypoint counts as reached
    risk_weight: float = 1.5       # penalty multiplier for rough terrain
    seed: int = 7


@dataclass
class Config:
    world: WorldConfig = field(default_factory=WorldConfig)
    rover: RoverConfig = field(default_factory=RoverConfig)
    sensor: SensorConfig = field(default_factory=SensorConfig)
    mission: MissionConfig = field(default_factory=MissionConfig)

    @property
    def n_cells(self) -> int:
        return self.world.cells


STRATEGIES = ("nearest", "shortest", "resource", "full")
