"""ASTRA-MINE Mission Control server - the Digital Twin.

Run (from the software/ folder):
    python -m astra.dashboard.server
    # then open http://127.0.0.1:8000 in a browser

Two modes, selectable in the browser:

* SIMULATION (default) - the full mission runs against the physics
  simulator. Terrain, resource ground truth, noisy perception, energy
  model: everything synthetic. Ideal for development, demos and the
  strategy experiments.

* REAL ROVER - the SAME brain (perception -> planner -> optimizer -> state
  machine) drives the physical rover over USB serial through RealRoverHAL.
  The world map starts UNKNOWN: rocks are discovered live by the ToF
  sensor, resource zones by the camera detector (vision.live) and by
  operator cueing - click a spot on the map to cue a resource zone, the
  same way orbiter data cues real rovers. What you see in the browser is
  the rover's actual pose, battery, decisions and yields in real time.

The browser page renders it as a live mission-control display; a complete
state snapshot streams over a WebSocket a couple of times per second.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from ..brain.mission import MissionController
from ..brain.perception import ResourceMapper
from ..config import STRATEGIES, Config
from ..hal.real_rover import RealRoverHAL
from ..hal.sim_rover import SimRoverHAL
from ..sim.world import generate_world, unknown_world

app = FastAPI(title="ASTRA-MINE Mission Control")
_STATIC = os.path.join(os.path.dirname(__file__), "static")

_active_thread: threading.Thread | None = None
_current_mission: MissionController | None = None
_fuse_lock = threading.Lock()   # belief-map fusion happens from 2-3 threads


# ---------------------------------------------------------------------- helpers
def snapshot(mission: MissionController, gm, include_maps: bool,
             mode: str = "sim") -> dict:
    """Full state snapshot for the dashboard."""
    tel = mission.rover.telemetry
    x, y, h = mission.rover.get_pose()
    path = mission.state.current_path
    payload = {
        "type": "telemetry",
        "mode": mode,
        "t": round(tel.get("time_s", 0.0), 1),
        "state": mission.state.name,
        "strategy": mission.cfg.mission.strategy,
        "seed": mission.cfg.mission.seed,
        "pose": {"x": round(x, 3), "y": round(y, 3), "h": round(h, 2)},
        "battery_pct": round(tel.get("battery_pct", 0.0), 1),
        "energy_wh": round(tel.get("energy_used_wh", 0.0), 3),
        "distance_m": round(tel.get("distance_m", 0.0), 2),
        "hopper_g": round(tel.get("hopper_g", 0.0), 1),
        "collected_g": round(tel.get("collected_g", 0.0), 1),
        "delivered_g": round(mission.metrics.delivered_g, 1),
        "sites_mined": mission.metrics.sites_mined,
        "g_per_wh": round(mission.metrics.yield_per_wh(), 1),
        "collisions": mission.metrics.collisions,
        "replans": mission.metrics.replans,
        "coverage_pct": round(100.0 * mission.mapper.coverage(), 1),
        "target": list(mission.state.current_target) if mission.state.current_target else None,
        "path": [[round(gm.center_of(r, c)[0], 3), round(gm.center_of(r, c)[1], 3)]
                 for r, c in path[::3]],
    }
    if tel.get("tof_cm") is not None:
        payload["tof_cm"] = tel["tof_cm"]
    if include_maps:
        payload["prob_map"] = np.round(gm.resource_prob, 2).tolist()
        payload["observed"] = gm.observed.astype(int).tolist()
        if mode == "real":
            # no ground truth exists here - show what the ToF has discovered
            payload["blocked"] = (~gm.traversable).astype(int).tolist()
    return payload


def run_mission_thread(cfg: Config, pace: float, push,
                       real: dict | None, session: dict) -> None:
    """Worker thread: runs the mission and pushes snapshots into the WS queue."""
    gm = unknown_world(cfg) if real else generate_world(cfg)

    # terrain description first (constant during the mission)
    push({
        "type": "world",
        "n": gm.n,
        "size_m": gm.size_m,
        "station_xy": list(cfg.world.station_xy),
        "start_xy": list(cfg.world.start_xy),
        "roughness": np.round(gm.roughness, 2).tolist(),
        "elevation": np.round(gm.elevation, 3).tolist(),
        "mode": "real" if real else "sim",
    })
    push({"type": "status", "status": "running",
          "mode": "real" if real else "sim",
          "seed": cfg.mission.seed, "strategy": cfg.mission.strategy})

    def on_event(ev: dict) -> None:
        push({"type": "event", **ev})

    global _current_mission
    mapper = ResourceMapper(cfg, gm)
    perceiver = None
    if real:
        rover = RealRoverHAL(cfg, real["port"],
                             station_port=real.get("station_port"))
        rover.set_world_offset(*cfg.world.start_xy)
        cam = real.get("camera")
        if cam not in (None, "", -1):
            from ..vision.live import LivePerceiver, ground_to_world

            def on_ground_point(fwd: float, lat: float, conf: float) -> None:
                px, py, ph = rover.get_pose()
                wx, wy = ground_to_world((px, py, ph), fwd, lat)
                r, c = gm.cell_of(wx, wy)
                with _fuse_lock:
                    mapper.fuse(r, c, min(0.9, max(0.3, conf)))

            perceiver = LivePerceiver(int(cam), on_ground_point)
            perceiver.start()
    else:
        rover = SimRoverHAL(cfg, gm, np.random.default_rng(cfg.mission.seed))

    mission = MissionController(cfg, rover, gm, mapper, on_event=on_event)
    _current_mission = mission
    session.update({"mission": mission, "gm": gm, "mapper": mapper,
                    "rover": rover, "mode": "real" if real else "sim"})

    dt = cfg.mission.dt
    last_map = 0.0
    try:
        while mission.step(dt):
            if real:
                rover.drain_percepts(gm)     # ToF discoveries -> planner map
            elif pace > 0:
                time.sleep(pace)             # real-time x speed pacing (sim)
            now = mission.metrics.time_s
            if now - last_map >= 0.5:        # full map ~2x per second
                last_map = now
                push(snapshot(mission, gm, include_maps=True,
                              mode="real" if real else "sim"))
    finally:
        if perceiver is not None:
            perceiver.stop()
        if real:
            rover.stop()                     # failsafe: motors off at mission end
    push(snapshot(mission, gm, include_maps=True, mode="real" if real else "sim"))
    push({"type": "status", "status": "finished",
          "mode": "real" if real else "sim",
          "done_reason": mission.state.done_reason,
          "summary": mission.metrics.summary()})


async def read_commands(sock: WebSocket, session: dict) -> None:
    """Listen for operator commands while the mission streams out."""
    while True:
        try:
            text = await sock.receive_text()
        except Exception:
            return
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            continue
        cmd = msg.get("cmd")
        if cmd == "stop":
            m = session.get("mission")
            if m is not None:
                m.stop_requested = True
        elif cmd == "mark":
            gm, mapper = session.get("gm"), session.get("mapper")
            if gm is None or mapper is None:
                continue
            x, y = float(msg.get("x", 0.0)), float(msg.get("y", 0.0))
            r, c = gm.cell_of(x, y)
            with _fuse_lock:
                mapper.fuse(r, c, 0.85)
                for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if gm.in_bounds(rr, cc):
                        mapper.fuse(rr, cc, 0.62)


# ------------------------------------------------------------------------ routes
@app.get("/")
async def index() -> HTMLResponse:
    with open(os.path.join(_STATIC, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/state")
async def state() -> JSONResponse:
    return JSONResponse({
        "busy": _active_thread is not None and _active_thread.is_alive(),
        "strategies": list(STRATEGIES),
    })


@app.websocket("/ws")
async def ws(sock: WebSocket) -> None:
    global _active_thread
    await sock.accept()
    session: dict = {}
    reader = None
    try:
        hello = json.loads(await sock.receive_text())
        if hello.get("cmd") == "stop":
            if _current_mission is not None:
                _current_mission.stop_requested = True
            await sock.close()
            return

        if _active_thread is not None and _active_thread.is_alive():
            await sock.send_json({"type": "status", "status": "busy"})
            await sock.close()
            return

        cfg = Config()
        cfg.mission.strategy = hello.get("strategy", "full")
        cfg.mission.seed = int(hello.get("seed", 7))
        speed = float(hello.get("speed", 4.0))

        real = None
        if hello.get("mode", "sim") == "real":
            real = {"port": hello.get("port", "COM5"),
                    "station_port": hello.get("station_port") or None,
                    "camera": hello.get("camera", -1)}
            pace = 0.0                      # the real rover paces itself
        else:
            pace = max(0.0, cfg.mission.dt / max(0.1, speed))

        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def push(msg: dict) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, msg)

        reader = asyncio.create_task(read_commands(sock, session))
        thread = threading.Thread(target=run_mission_thread,
                                  args=(cfg, pace, push, real, session),
                                  daemon=True)
        _active_thread = thread
        thread.start()

        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await sock.send_json(msg)
                if msg.get("type") == "status" and msg.get("status") == "finished":
                    break
            except asyncio.TimeoutError:
                await sock.send_json({"type": "ping", "t": time.time()})
    except WebSocketDisconnect:
        pass
    finally:
        if reader is not None:
            reader.cancel()
        try:
            await sock.close()
        except Exception:
            pass


def main() -> None:
    import uvicorn
    print("ASTRA-MINE Mission Control -> http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
