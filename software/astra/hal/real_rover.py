"""Real rover HAL: talks to the ESP32 rover controller over USB serial.

Protocol (one JSON object per line, 115200 baud):

  PC  -> ESP32:  {"cmd":"vel","v":0.10,"w":0.3}      set linear/angular velocity
                 {"cmd":"collect","ms":12000}        run scoop for N ms
                 {"cmd":"reset"}                     zero the odometry
                 {"cmd":"stop"}                      immediate stop
  ESP32 -> PC:   {"t":12.4,"x":0.51,"y":0.83,"h":1.21,"v":0.10,
                 "vbat":11.8,"cur":0.84,"wh":3.12,"tilt":4.2,
                 "enc":4821,"scoop":0,"dist":24.5,"bump":0}

The ESP32 reports dead-reckoned pose from wheel encoders + gyro heading
(MPU-6050, complementary filter), and integrates battery Wh from the INA219 -
this is the MEASURED energy behind the g/Wh metric. `dist` is the forward
ToF range (cm) used to mark rocks on the belief map; `bump` is a stall flag.

Optionally a second serial link connects to the PROCESSING STATION node
(firmware/station_node) whose HX711 load cell reports {"g":grams}; deliveries
are then MEASURED instead of estimated.

The ESP32 odometry starts at (0,0); call set_world_offset(start_xy) once the
rover is placed on the testbed so the HAL reports WORLD-frame coordinates the
mission brain and dashboard expect. This is the same closed-loop interface
the simulator implements - MissionController cannot tell the difference.

Requires:  pip install pyserial
"""
from __future__ import annotations

import json
import math
import time

from .base import RoverInterface
from ..config import Config

TOF_BLOCK_M = 0.22          # closer than this = rock, mark it on the map
TOF_MAX_MARK_M = 0.30       # don't trust the ToF beyond this range


class RealRoverHAL(RoverInterface):
    def __init__(self, cfg: Config, port: str, baud: int = 115200,
                 station_port: str | None = None,
                 serial_dev=None, station_dev=None):
        """`serial_dev`/`station_dev` are injectable for unit tests; in
        production they are pyserial ports opened from `port`/`station_port`."""
        if serial_dev is None:
            try:
                import serial  # pyserial
            except ImportError as e:
                raise RuntimeError(
                    "pyserial is required for the real rover:  pip install pyserial") from e
            serial_dev = serial.Serial(port, baud, timeout=0.02)
        self.ser = serial_dev
        self._station = station_dev
        if station_dev is None and station_port:
            import serial
            self._station = serial.Serial(station_port, 115200, timeout=0.02)

        self.cfg = cfg
        self._offset = (0.0, 0.0)            # odometry frame -> world frame
        self._pose = (cfg.world.start_xy[0], cfg.world.start_xy[1], 0.0)
        self._first_fix = True               # first telemetry sets, not adds
        self._raw: dict = {}
        self._battery_wh = cfg.rover.battery_wh
        self._time_s = 0.0
        self._distance_m = 0.0
        self._collisions = 0
        self._prev_bump = False
        self._hopper_g = 0.0
        self._collected_g = 0.0
        self._station_g: float | None = None
        self._station_g_last_dump = 0.0
        self._send({"cmd": "stop"})
        self._send({"cmd": "reset"})
        self._pump_station()

    # ------------------------------------------------------------------ comms
    def _send(self, obj: dict) -> None:
        self.ser.write((json.dumps(obj) + "\n").encode("ascii"))

    def _pump_serial(self) -> None:
        """Read all pending telemetry lines and update cached state."""
        while True:
            line = self.ser.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("ascii", errors="ignore").strip())
            except (json.JSONDecodeError, ValueError, TypeError):
                continue  # ignore corrupt lines
            if "boot" in msg or "t" not in msg:
                self._raw = msg
                continue
            self._raw = msg
            ox, oy = float(msg.get("x", 0.0)), float(msg.get("y", 0.0))
            lx, ly, _ = self._pose
            wx, wy = ox + self._offset[0], oy + self._offset[1]
            if self._first_fix:
                self._first_fix = False      # first fix: set, don't accumulate
                self._pose = (wx, wy, float(msg.get("h", 0.0)))
            else:
                self._distance_m += math.hypot(wx - lx, wy - ly)
                self._pose = (wx, wy, float(msg.get("h", 0.0)))
            self._time_s = float(msg.get("t", self._time_s))
            if "wh" in msg:  # ESP32 integrates Wh from the INA219
                self._battery_wh = self.cfg.rover.battery_wh - float(msg["wh"])
            bump = bool(msg.get("bump", 0))
            if bump and not self._prev_bump:
                self._collisions += 1
            self._prev_bump = bump

    def _pump_station(self) -> None:
        """Read pending grams reports from the processing-station node."""
        if self._station is None:
            return
        while True:
            line = self._station.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("ascii", errors="ignore").strip())
                if "g" in msg:
                    self._station_g = float(msg["g"])
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    # ------------------------------------------------------------ real-mode API
    def set_world_offset(self, x: float, y: float) -> None:
        """Call once with the rover's known placement (e.g. start_xy) so the
        HAL reports world-frame coordinates instead of raw odometry."""
        self._offset = (x, y)
        self._first_fix = True               # re-anchor the pose cleanly

    def drain_percepts(self, gm) -> int:
        """Mark rocks on the belief map from the ToF sensor.

        Called by the dashboard's real-mode loop BEFORE mission.step() so the
        planner sees newly discovered obstacles. Returns cells marked."""
        self._pump_serial()
        dist_cm = self._raw.get("dist")
        if dist_cm is None:
            return 0
        dist_m = float(dist_cm) / 100.0
        if dist_m < 0 or dist_m > TOF_MAX_MARK_M:
            return 0
        x, y, heading = self.get_pose()
        marked = 0
        # the obstacle lies in a ~±20° arc straight ahead at the measured range
        for da in (-0.35, -0.17, 0.0, 0.17, 0.35):
            px = x + dist_m * math.cos(heading + da)
            py = y + dist_m * math.sin(heading + da)
            r, c = gm.cell_of(px, py)
            for rr in (r - 1, r, r + 1):        # mark a small disc: the rock is
                for cc in (c - 1, c, c + 1):    # wider than one 5 cm cell
                    if gm.in_bounds(rr, cc) and gm.traversable[rr, cc]:
                        gm.traversable[rr, cc] = False
                        gm.roughness[rr, cc] = 1.0
                        marked += 1
        return marked

    def stop(self) -> None:
        """Failsafe: immediate motor stop (also used on mission end)."""
        self._send({"cmd": "stop"})

    # ------------------------------------------------------------ RoverInterface
    def get_pose(self) -> tuple[float, float, float]:
        self._pump_serial()
        return self._pose

    def get_battery_wh(self) -> float:
        self._pump_serial()
        return self._battery_wh

    def observe_resource(self, r: int, c: int) -> float | None:
        """Real perception comes from the camera pipeline (vision.live) and
        operator cueing, which call ResourceMapper.fuse() directly from the
        dashboard thread. Kept returning None for interface parity."""
        return None

    def drive_towards(self, tx: float, ty: float, dt: float) -> bool:
        x, y, h = self.get_pose()
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        if dist < self.cfg.mission.waypoint_tol_m:
            self._send({"cmd": "vel", "v": 0.0, "w": 0.0})
            return True
        err = (math.atan2(dy, dx) - h + math.pi) % (2 * math.pi) - math.pi
        w = max(-self.cfg.rover.max_omega, min(self.cfg.rover.max_omega, 2.5 * err))
        v = self.cfg.rover.max_speed_mps * (1.0 if abs(err) < 0.35 else 0.35)
        self._send({"cmd": "vel", "v": round(v, 3), "w": round(w, 3)})
        time.sleep(dt)
        self._pump_serial()
        return False

    def collect_sample(self, duration_s: float) -> float:
        self._send({"cmd": "collect", "ms": int(duration_s * 1000)})
        deadline = time.time() + duration_s + 2.0
        while time.time() < deadline:
            self._pump_serial()
            if self._raw.get("scoop", 1) == 0:
                break
            time.sleep(0.1)
        # grams are estimated from scoop timing here; the MEASURED number
        # comes from the station load cell at delivery (dump_hopper below)
        got = self.cfg.rover.scoop_rate_gps * duration_s
        self._hopper_g += got
        self._collected_g += got
        return got

    def dump_hopper(self) -> float:
        """Deliver hopper contents at the processing station.

        With a station node attached, the delivered grams are MEASURED as the
        load-cell change since the previous delivery. Without one, the scoop
        timing estimate is used (documented in the report as such)."""
        self._pump_station()
        if self._station_g is not None:
            delivered = max(0.0, self._station_g - self._station_g_last_dump)
            self._station_g_last_dump = self._station_g
        else:
            delivered = self._hopper_g
        self._hopper_g = 0.0
        return delivered

    def idle(self, dt: float) -> None:
        self._send({"cmd": "vel", "v": 0.0, "w": 0.0})
        time.sleep(dt)
        self._pump_serial()

    @property
    def telemetry(self) -> dict:
        self._pump_serial()
        return {
            "x": self._pose[0], "y": self._pose[1], "heading": self._pose[2],
            "battery_wh": self._battery_wh,
            "battery_pct": 100.0 * self._battery_wh / self.cfg.rover.battery_wh,
            "energy_used_wh": self.cfg.rover.battery_wh - self._battery_wh,
            "distance_m": self._distance_m,
            "time_s": self._time_s,
            "hopper_g": self._hopper_g,
            "collected_g": self._collected_g,
            "collisions": self._collisions,
            "tof_cm": self._raw.get("dist"),
            "raw": self._raw,
        }
