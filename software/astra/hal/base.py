"""Hardware Abstraction Layer.

The mission brain (perception, planner, optimizer, state machine) talks ONLY
to the RoverInterface below. That single design decision is what lets the
exact same AI code run against:

  * the simulator  (astra.hal.sim_rover.SimRoverHAL)   - no hardware needed
  * the real rover (astra.hal.real_rover.RealRoverHAL) - ESP32 over serial

When your team builds the physical rover, you implement nothing new - you just
swap which HAL you pass to MissionController.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class RoverInterface(ABC):
    """Everything the mission brain is allowed to know about the hardware."""

    @abstractmethod
    def get_pose(self) -> tuple[float, float, float]:
        """Current (x, y, heading) in metres / radians (rover's own estimate)."""

    @abstractmethod
    def get_battery_wh(self) -> float:
        """Remaining battery energy in Wh (from the INA219 power monitor)."""

    @abstractmethod
    def observe_resource(self, r: int, c: int) -> float | None:
        """Noisy resource-probability observation of a cell within camera
        range, or None if the cell is out of sensor range."""

    @abstractmethod
    def drive_towards(self, tx: float, ty: float, dt: float) -> bool:
        """Closed-loop steering toward a waypoint. True = waypoint reached."""

    @abstractmethod
    def collect_sample(self, duration_s: float) -> float:
        """Run the collection mechanism; returns grams collected."""

    @abstractmethod
    def dump_hopper(self) -> float:
        """Deliver hopper contents to the processing station if in range;
        returns grams delivered (0 if too far)."""

    @abstractmethod
    def idle(self, dt: float) -> None:
        """Stand still for dt seconds (burns base power, advances physics)."""

    @property
    @abstractmethod
    def telemetry(self) -> dict:
        """Live metrics snapshot for the Mission Control dashboard."""
