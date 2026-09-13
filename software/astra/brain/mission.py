"""The ASTRA-MINE mission state machine - the rover's "brain".

Closed loop (this is the research contribution):

    SURVEY  ->  SELECT  ->  NAVIGATE  ->  MINE  ->  RETURN  ->  (SELECT ...)
      |                                                          |
      +------------- until coverage target met ------------------+

  SURVEY   : drive to frontier cells, observe ground, build resource map
  SELECT   : optimizer picks the best next mining target (strategy-dependent)
  NAVIGATE : A* path, followed waypoint by waypoint (re-plans if blocked)
  MINE     : scoop for mine_time_s, log grams collected
  RETURN   : drive back to the processing station, dump the hopper
  DONE     : battery reserve reached, site budget exhausted, or no targets

Every step() advances the HAL by dt seconds - identical control flow on the
simulator and the real rover.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np

from ..common.gridmap import GridMap
from ..common.planner import plan_path
from .optimizer import select_target
from .perception import ResourceMapper


@dataclass
class MissionMetrics:
    delivered_g: float = 0.0        # grams delivered to the processing station
    collected_g: float = 0.0        # grams scooped in total
    sites_mined: int = 0
    distance_m: float = 0.0
    energy_wh: float = 0.0
    time_s: float = 0.0
    collisions: int = 0
    replans: int = 0
    decisions: list = field(default_factory=list)   # optimizer decision log

    def yield_per_wh(self) -> float:
        return self.delivered_g / self.energy_wh if self.energy_wh > 1e-6 else 0.0

    def summary(self) -> dict:
        return {
            "delivered_g": round(self.delivered_g, 1),
            "collected_g": round(self.collected_g, 1),
            "sites_mined": self.sites_mined,
            "distance_m": round(self.distance_m, 2),
            "energy_wh": round(self.energy_wh, 3),
            "time_s": round(self.time_s, 1),
            "resource_per_wh": round(self.yield_per_wh(), 1),
            "collisions": self.collisions,
            "replans": self.replans,
        }


@dataclass
class MissionState:
    name: str = "SURVEY"
    current_path: list = field(default_factory=list)
    path_idx: int = 0
    current_target: tuple | None = None
    survey_visits: int = 0
    blocked_steps: int = 0
    escape_counter: int = 0
    done_reason: str = ""


class MissionController:
    def __init__(self, cfg, rover, gm: GridMap, mapper: ResourceMapper | None = None,
                 on_event=None):
        self.cfg = cfg
        self.rover = rover          # a RoverInterface (sim or real)
        self.gm = gm
        self.mapper = mapper or ResourceMapper(cfg, gm)
        self.metrics = MissionMetrics()
        self.state = MissionState()
        self.log: list[str] = []
        self._on_event = on_event   # dashboard callback: fn(event_dict)
        self._rng = np.random.default_rng(cfg.mission.seed)
        self._t_start = time.time()
        self._last_map_push = 0.0
        # no-progress (stuck) detection state
        self._progress_pos: tuple | None = None
        self._progress_timer = 0.0
        # sensing runs at a lower rate than physics (camera frame rate proxy)
        self._sense_interval = 0.5
        self._sense_timer = self._sense_interval  # sense on the very first step
        self.stop_requested = False               # dashboard emergency-stop flag

    # ------------------------------------------------------------------ helpers
    def _event(self, kind: str, **kw) -> None:
        if self._on_event:
            self._on_event({"kind": kind, "state": self.state.name,
                            "t": self.metrics.time_s, **kw})

    def _say(self, msg: str) -> None:
        stamp = f"[{self.metrics.time_s:7.1f}s] {self.state.name:8s} | {msg}"
        self.log.append(stamp)
        self._event("log", message=msg)

    # ------------------------------------------------------------------ main loop
    def step(self, dt: float) -> bool:
        """Advance the mission by dt seconds. Returns False when finished."""
        m = self.cfg.mission
        if self.stop_requested:
            return self._finish("stopped by operator")

        # 1. always sense first (closed loop!) - at camera frame rate, not physics rate
        self._sense_timer += dt
        if self._sense_timer >= self._sense_interval:
            self._sense_timer = 0.0
            self.mapper.sense_around_rover(self.rover)

        # 2. update accumulators from the rover telemetry
        tel = self.rover.telemetry
        self.metrics.distance_m = tel["distance_m"]
        self.metrics.energy_wh = tel["energy_used_wh"]
        self.metrics.time_s = tel["time_s"]
        self.metrics.collisions = tel["collisions"]

        # 3. terminal conditions
        if self.rover.get_battery_wh() <= m.battery_reserve_wh:
            return self._finish("battery reserve reached")
        if self.metrics.energy_wh >= m.energy_budget_wh:
            return self._finish("energy budget exhausted")
        if self.metrics.sites_mined >= m.max_sites:
            return self._finish("site budget exhausted")

        # 4. state machine
        st = self.state.name
        if st == "SURVEY":
            self._do_survey(dt)
        elif st == "SELECT":
            self._do_select()
        elif st == "NAVIGATE":
            self._do_navigate(dt)
        elif st == "MINE":
            self._do_mine()
        elif st == "RETURN":
            self._do_return(dt)
        elif st == "DONE":
            return False
        return self.state.name != "DONE"

    def run(self, max_wall_clock_s: float = 120.0) -> MissionMetrics:
        """Run the whole mission (blocking). Safety timeout in wall-clock time."""
        dt = self.cfg.mission.dt
        t0 = time.time()
        while self.step(dt):
            if time.time() - t0 > max_wall_clock_s:
                self._finish("wall-clock safety timeout")
                break
        return self.metrics

    # ------------------------------------------------------------------ states
    def _do_survey(self, dt: float) -> None:
        m = self.cfg.mission
        # enough coverage and at least one promising zone known? -> start mining
        if (self.mapper.coverage() >= m.survey_target_frac
                and self.mapper.known_targets(m.prob_threshold)):
            self._say(f"survey complete: coverage {self.mapper.coverage()*100:.0f}%, "
                      f"{len(self.mapper.known_targets(m.prob_threshold))} promising cells")
            self.state.name = "SELECT"
            return

        frontier = self.mapper.frontier_cells()
        if not frontier:
            if self.mapper.coverage() < 0.01:
                self.rover.idle(dt)   # wait for the first camera frame
                return
            self._say(f"no frontier left (coverage {self.mapper.coverage()*100:.0f}%); "
                      f"switching to mining phase")
            self.state.name = "SELECT"
            return

        # walk to the nearest unobserved frontier cell (information gain per metre)
        if not self.state.current_path:
            x, y, _ = self.rover.get_pose()
            here = self.gm.cell_of(x, y)
            path = plan_path(self.gm, here, min(
                frontier, key=lambda rc: math.hypot(rc[0] - here[0], rc[1] - here[1])))
            if path is None:
                frontier.remove(min(frontier))
                return
            self.state.current_path, self.state.path_idx = path, 1
            self.state.survey_visits += 1

        if not self._follow_path(dt):
            self.state.current_path = []  # reached frontier waypoint; pick next

    def _do_select(self) -> None:
        m = self.cfg.mission
        x, y, _ = self.rover.get_pose()
        dec = select_target(self.cfg, self.gm, self.mapper, (x, y),
                            self.cfg.world.station_xy, m.strategy)
        if dec is None:
            return self._finish("no known resource targets remaining")
        self.state.current_target = dec.cell
        self.state.current_path, self.state.path_idx = dec.path, 1
        self.metrics.decisions.append(dec)
        self._say(f"TARGET selected ({dec.strategy}): cell {dec.cell} | {dec.reason}")
        self._event("decision", cell=list(dec.cell), reason=dec.reason,
                    score=round(dec.score, 4),
                    expected_yield_g=round(dec.expected_yield_g, 1))
        self.state.name = "NAVIGATE"

    def _do_navigate(self, dt: float) -> None:
        if self._follow_path(dt):
            self._say(f"arrived at target {self.state.current_target}")
            self.state.current_path = []      # path fully consumed
            self.state.name = "MINE"
        # NOTE: _follow_path handles blocked re-planning internally

    def _do_mine(self) -> None:
        m = self.cfg.mission
        got = self.rover.collect_sample(m.mine_time_s)
        self.metrics.collected_g += got
        self.metrics.sites_mined += 1
        self._say(f"mining complete: +{got:.1f} g "
                  f"(mission total {self.metrics.collected_g:.1f} g)")
        self._event("mined", grams=round(got, 1))
        # the rover has now SEEN what this site actually held: update the
        # belief so the optimizer does not keep re-selecting a worked-out site
        if self.state.current_target is not None:
            self.mapper.mark_mined(*self.state.current_target)
        self.state.current_path = []
        self.state.name = "RETURN"

    def _do_return(self, dt: float) -> None:
        station_rc = self.gm.cell_of(*self.cfg.world.station_xy)
        if not self.state.current_path:
            x, y, _ = self.rover.get_pose()
            path = plan_path(self.gm, self.gm.cell_of(x, y), station_rc)
            if path is None:
                return self._finish("no path back to station")
            self.state.current_path, self.state.path_idx = path, 1
        if self._follow_path(dt):
            delivered = self.rover.dump_hopper()
            self.metrics.delivered_g += delivered
            self._say(f"delivered {delivered:.1f} g to processing station "
                      f"(total {self.metrics.delivered_g:.1f} g)")
            self._event("delivered", grams=round(delivered, 1))
            self.state.current_path = []
            self.state.current_target = None
            self.state.name = "SELECT"

    def _follow_path(self, dt: float) -> bool:
        """Follow self.state.current_path. True = path finished.
        If blocked for too long, re-plan once, then abandon the target."""
        path = self.state.current_path
        if not path or self.state.path_idx >= len(path):
            self.state.current_path = []
            return True
        r, c = path[self.state.path_idx]
        tx, ty = self.gm.center_of(r, c)
        reached = self.rover.drive_towards(tx, ty, dt)
        if reached:
            self.state.path_idx += 1
            self.state.blocked_steps = 0
            return self.state.path_idx >= len(path)

        # stuck? track actual displacement over a 2 s window - catches both
        # "pressing against a rock far away" and "oscillating just outside
        # the waypoint tolerance"
        x, y, _ = self.rover.get_pose()
        self._progress_timer += dt
        if self._progress_timer >= 2.0:
            if self._progress_pos is not None:
                moved = math.hypot(x - self._progress_pos[0], y - self._progress_pos[1])
                if moved < 0.03:            # < 3 cm in 2 s => not making progress
                    self.state.blocked_steps += 1
                else:
                    self.state.blocked_steps = 0
            self._progress_pos = (x, y)
            self._progress_timer = 0.0
        if self.state.blocked_steps >= 3:   # stuck for ~6 s => re-plan
            self.state.blocked_steps = 0
            self.metrics.replans += 1
            self.state.escape_counter += 1
            if self.state.escape_counter >= 3:
                # re-planning repeatedly failed: perform an escape maneuver -
                # back up 0.12 m and rotate ~90 deg, like a real rover would
                self.state.escape_counter = 0
                self._say("still stuck - performing escape maneuver (back up + turn)")
                self._escape_maneuver(x, y)
                self.state.current_path = []
                return False
            self._say("blocked - re-planning path")
            here = self.gm.cell_of(x, y)
            new_path = plan_path(self.gm, here, path[-1])
            if new_path is None:
                self._say("no alternative path; abandoning target")
                self.state.current_path = []
                self.state.current_target = None
                self.state.name = "SELECT"
                return False
            self.state.current_path, self.state.path_idx = new_path, 1
        return False

    def _escape_maneuver(self, x: float, y: float) -> None:
        """Reverse 0.12 m and rotate ~90 deg to un-wedge the rover."""
        _, _, heading = self.rover.get_pose()
        bx, by = x - 0.12 * math.cos(heading), y - 0.12 * math.sin(heading)
        for _ in range(40):               # up to 4 s of backing up
            if self.rover.drive_towards(bx, by, self.cfg.mission.dt):
                break
        self.rover.drive_towards(x - 0.10 * math.cos(heading),
                                 y - 0.10 * math.sin(heading),
                                 self.cfg.mission.dt)  # brief settle
        # rotate in place via a point behind-left
        ex, ey = x - 0.001 * math.cos(heading + 1.6), y - 0.001 * math.sin(heading + 1.6)
        for _ in range(20):
            self.rover.drive_towards(ex, ey, self.cfg.mission.dt)

    # ------------------------------------------------------------------ finish
    def _finish(self, reason: str) -> bool:
        if self.state.name != "DONE":
            self._say(f"MISSION COMPLETE: {reason}")
            self.state.done_reason = reason
            self.state.name = "DONE"
            self._event("done", reason=reason)
        return False
