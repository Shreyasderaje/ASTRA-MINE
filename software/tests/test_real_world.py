"""Real-mode map path: an UNKNOWN world driven by the standard mission brain.

On the physical rover the world map starts blank (nothing known) and fills in
from the ToF sensor, camera detector and operator cueing. These tests run
that exact map path with the simulator standing in for the hardware.
"""
import numpy as np

from astra.brain.mission import MissionController
from astra.brain.perception import ResourceMapper
from astra.config import Config
from astra.hal.sim_rover import SimRoverHAL
from astra.sim.world import unknown_world


def test_unknown_world_starts_blank():
    cfg = Config()
    cfg.mission.seed = 7
    gm = unknown_world(cfg)
    assert gm.traversable.all(), "nothing is known blocked before sensing"
    assert gm.resource_amount.sum() == 0, "no assumed resources"
    assert not gm.observed.any(), "nothing observed yet"
    assert np.allclose(gm.resource_prob, cfg.sensor.prior_prob)


def test_mission_on_unknown_world_ends_gracefully_without_perception():
    """No camera and no operator cues => the rover surveys, finds no
    credible targets and finishes with a clean reason. This is exactly what
    the real rover does if perception is unavailable - it must never crash
    or drive forever."""
    cfg = Config()
    cfg.mission.seed = 7
    cfg.mission.survey_target_frac = 0.05        # keep the test fast
    gm = unknown_world(cfg)
    rover = SimRoverHAL(cfg, gm, np.random.default_rng(7))
    mission = MissionController(cfg, rover, gm, ResourceMapper(cfg, gm))
    metrics = mission.run(max_wall_clock_s=90.0)

    assert mission.state.done_reason, "mission must end with a reason"
    assert metrics.summary()["delivered_g"] == 0


def test_operator_cue_creates_a_target_and_mission_mines_it():
    """Click-to-cue: fusing a high-probability observation into the belief
    map must make the optimizer select that site - the loop the real rover
    closes with a human in mission control."""
    cfg = Config()
    cfg.mission.seed = 7
    cfg.mission.survey_target_frac = 0.02
    gm = unknown_world(cfg)
    mapper = ResourceMapper(cfg, gm)
    rover = SimRoverHAL(cfg, gm, np.random.default_rng(7))
    mission = MissionController(cfg, rover, gm, mapper)

    # an operator cues a zone 0.8 m "east" of the start position
    cx = cfg.world.start_xy[0] + 0.8
    cy = cfg.world.start_xy[1]
    r, c = gm.cell_of(cx, cy)
    mapper.fuse(r, c, 0.85)
    for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if gm.in_bounds(rr, cc):
            mapper.fuse(rr, cc, 0.62)
            # the cue is CORRECT: simulant is really buried there (this is
            # what ResourceMapper.mark_mined expects to be able to extract)
            gm.resource_amount[rr, cc] = 40.0
            gm.remaining[rr, cc] = 40.0

    assert mapper.known_targets(cfg.mission.prob_threshold), \
        "the cued zone must appear as a mining target"

    metrics = mission.run(max_wall_clock_s=90.0)
    s = metrics.summary()
    assert s["sites_mined"] >= 1, "mission must mine the cued zone"
    assert s["delivered_g"] > 0, "and deliver it to the station"
