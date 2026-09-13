"""End-to-end smoke test: one full simulated mission, survey to delivery.

This is the 'does the whole system actually work' test. It exercises world
generation, perception, planning, the optimizer, the state machine, rover
physics, the energy model and the metrics pipeline in one go.
"""
import numpy as np

from astra.brain.mission import MissionController
from astra.brain.perception import ResourceMapper
from astra.config import Config
from astra.hal.sim_rover import SimRoverHAL
from astra.sim.world import generate_world


def _mission(strategy: str, seed: int = 7):
    cfg = Config()
    cfg.mission.strategy = strategy
    cfg.mission.seed = seed
    gm = generate_world(cfg)
    rover = SimRoverHAL(cfg, gm, np.random.default_rng(seed))
    mission = MissionController(cfg, rover, gm, ResourceMapper(cfg, gm))
    metrics = mission.run(max_wall_clock_s=120.0)
    return cfg, gm, mission, metrics


def test_full_strategy_mission_completes_and_delivers():
    cfg, gm, mission, metrics = _mission("full")
    s = metrics.summary()

    assert mission.state.done_reason, "mission must end with a reason"
    assert s["delivered_g"] > 0, "rover must deliver something to the station"
    assert s["sites_mined"] >= 1
    assert 0 < s["energy_wh"] <= cfg.mission.energy_budget_wh * 1.5
    assert s["distance_m"] > 0
    assert s["resource_per_wh"] > 0


def test_all_four_strategies_run_clean():
    for strategy in ("nearest", "shortest", "resource", "full"):
        cfg, gm, mission, metrics = _mission(strategy)
        s = metrics.summary()
        assert s["energy_wh"] > 0, f"{strategy}: no energy consumed?"
        assert s["delivered_g"] >= 0
        assert s["collisions"] == 0, f"{strategy}: rover hit rocks"


def test_two_strategies_can_disagree_on_choice():
    """Sanity check that strategy choice actually changes behaviour."""
    delivered = {}
    for strategy in ("nearest", "resource"):
        _, _, _, metrics = _mission(strategy, seed=3)
        delivered[strategy] = metrics.summary()["delivered_g"]
    # not a strict guarantee on every seed, but on seed 3 the greedy
    # resource strategy should out-deliver the distance-driven one
    assert delivered["resource"] != delivered["nearest"]
