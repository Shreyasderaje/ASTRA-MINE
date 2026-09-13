"""Real-mode chain tests: RealRoverHAL against a fake serial port.

No hardware needed - the fake speaks the exact ESP32 firmware JSON protocol,
so protocol parsing, telemetry accumulation, ToF obstacle marking and the
station load-cell link are all verified here. The physical bench tests
(docs/06) then only need to confirm the real board behaves the same.
"""
import json

import pytest

from astra.config import Config
from astra.hal.real_rover import RealRoverHAL
from astra.sim.world import unknown_world


class FakeSerial:
    """Duck-typed pyserial.Serial backed by a list of canned lines."""

    def __init__(self, lines=()):
        self.written = []
        self._lines = list(lines)
        self.timeout = 0.0

    def write(self, data):
        self.written.append(data.decode("ascii"))
        return len(data)

    def readline(self):
        return self._lines.pop(0).encode("ascii") if self._lines else b""


def telemetry(t, x, y, h, wh, dist=-1, bump=0, scoop=0):
    """One firmware telemetry line, exactly as esp32_rover.ino prints it."""
    return json.dumps({"t": t, "x": x, "y": y, "h": h, "v": 0.1,
                       "vbat": 11.8, "cur": 0.8, "wh": wh, "tilt": 2.0,
                       "enc": 1000, "scoop": scoop, "dist": dist,
                       "bump": bump}) + "\n"


@pytest.fixture()
def cfg():
    return Config()


def test_protocol_parsing_and_accumulators(cfg, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    dev = FakeSerial([
        telemetry(0.1, 0.0, 0.0, 0.0, 0.000),
        telemetry(1.1, 0.12, 0.0, 0.0, 0.050),
        telemetry(2.1, 0.24, 0.0, 0.0, 0.100, bump=1),
    ])
    rover = RealRoverHAL(cfg, "COMx", serial_dev=dev)
    rover.set_world_offset(cfg.world.start_xy[0], cfg.world.start_xy[1])

    x, y, _ = rover.get_pose()
    assert x == pytest.approx(cfg.world.start_xy[0] + 0.24, abs=1e-6)
    assert y == pytest.approx(cfg.world.start_xy[1], abs=1e-6)

    tel = rover.telemetry
    assert tel["time_s"] == pytest.approx(2.1)
    assert tel["distance_m"] == pytest.approx(0.24, abs=0.01)   # first fix not counted
    assert tel["energy_used_wh"] == pytest.approx(0.100, abs=0.005)
    assert tel["battery_wh"] == pytest.approx(cfg.rover.battery_wh - 0.100, abs=0.005)
    assert tel["collisions"] == 1            # exactly one rising bump edge

    # the HAL must stop + reset the rover on connect
    cmds = [json.loads(w) for w in dev.written]
    assert {"cmd": "stop"} in cmds
    assert {"cmd": "reset"} in cmds


def test_drive_towards_sends_velocity_commands(cfg, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    dev = FakeSerial([telemetry(0.1, 0.0, 0.0, 0.0, 0.0)])
    rover = RealRoverHAL(cfg, "COMx", serial_dev=dev)
    rover.set_world_offset(0.0, 0.0)

    reached = rover.drive_towards(0.20, 0.0, 0.1)   # target 20 cm ahead (+x)
    assert reached is False
    vels = [json.loads(w) for w in dev.written if '"vel"' in w]
    assert vels, "drive_towards must command velocity"
    assert vels[-1]["v"] > 0.0                      # forward
    assert abs(vels[-1]["w"]) < 0.3                 # heading error ~0


def test_tof_marks_blocked_cells_on_the_belief_map(cfg, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    dev = FakeSerial([telemetry(0.1, 1.5, 1.5, 0.0, 0.0, dist=15.0)])
    rover = RealRoverHAL(cfg, "COMx", serial_dev=dev)
    rover.set_world_offset(0.0, 0.0)

    gm = unknown_world(cfg)
    assert gm.traversable.all()                     # unknown world: all clear
    marked = rover.drain_percepts(gm)
    assert marked > 0

    x, y, _ = rover.get_pose()
    fr, fc = gm.cell_of(x + 0.15, y)                # 15 cm straight ahead
    assert not gm.traversable[fr, fc], "the rock must be marked blocked"


def test_station_link_measures_delivery(cfg, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    rover_dev = FakeSerial([telemetry(0.1, 0.0, 0.0, 0.0, 0.0, scoop=1),
                            telemetry(12.1, 0.0, 0.0, 0.0, 0.1, scoop=0)])
    station_dev = FakeSerial([json.dumps({"g": 0.0}) + "\n",
                              json.dumps({"g": 42.5}) + "\n"])
    rover = RealRoverHAL(cfg, "COMx", serial_dev=rover_dev,
                         station_dev=station_dev)
    rover.set_world_offset(0.0, 0.0)

    rover.collect_sample(12.0)                      # returns the timing estimate
    delivered = rover.dump_hopper()                 # MEASURED by the load cell
    assert delivered == pytest.approx(42.5)


def test_without_station_delivery_falls_back_to_estimate(cfg, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    rover_dev = FakeSerial([telemetry(0.1, 0.0, 0.0, 0.0, 0.0, scoop=1),
                            telemetry(2.1, 0.0, 0.0, 0.0, 0.02, scoop=0)])
    rover = RealRoverHAL(cfg, "COMx", serial_dev=rover_dev)
    rover.set_world_offset(0.0, 0.0)

    got = rover.collect_sample(2.0)
    assert got > 0
    assert rover.dump_hopper() == pytest.approx(got)   # documented fallback
