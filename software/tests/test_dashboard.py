"""Dashboard integration test: a full mission through the real server.

Uses FastAPI's in-process TestClient (no ports, no browser). Verifies the
exact pipeline the team sees in Mission Control: handshake → world → live
telemetry snapshots → events → finished status with a summary.
"""
import pytest
from fastapi.testclient import TestClient

from astra.dashboard.server import app


def test_sim_mission_streams_and_finishes():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"cmd": "start", "mode": "sim", "strategy": "full",
                      "seed": 7, "speed": 50})
        got = {"world": False, "telemetry": False, "event": False}
        for _ in range(6000):                       # bounded message budget
            msg = ws.receive_json()
            t = msg.get("type")
            if t in got:
                got[t] = True
            if t == "telemetry":
                assert msg["mode"] == "sim"
                assert "pose" in msg and "battery_pct" in msg
            if t == "status" and msg.get("status") == "finished":
                s = msg["summary"]
                assert s["delivered_g"] > 0
                assert s["sites_mined"] >= 1
                assert s["energy_wh"] > 0
                break
        else:
            pytest.fail("mission never finished within the message budget")
        assert all(got.values()), got


def test_api_state_endpoint():
    client = TestClient(app)
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.json()
    assert body["strategies"] == ["nearest", "shortest", "resource", "full"]
    assert "busy" in body
