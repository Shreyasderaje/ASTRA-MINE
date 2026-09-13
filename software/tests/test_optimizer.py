"""Target-selection strategies must disagree in a controlled scenario.

This pins down the BEHAVIOUR that the whole experiment depends on:
  * 'nearest'  prefers the close-but-poor zone
  * 'resource' prefers the far-but-rich zone
If these two ever pick the same site, the 4-strategy comparison is meaningless.
"""
import numpy as np

from astra.brain.optimizer import select_target
from astra.config import Config
from astra.sim.world import generate_world


class FakeMapper:
    """Stands in for ResourceMapper with a hand-planted belief map."""

    def __init__(self, cells):
        self.cells = list(cells)

    def known_targets(self, threshold):
        return list(self.cells)


def _world_with_two_zones(seed=7):
    cfg = Config()
    cfg.mission.seed = seed
    gm = generate_world(cfg)

    r0, c0 = gm.cell_of(*cfg.world.start_xy)
    near = far = None
    for dc in range(3, gm.n - c0):
        c = c0 + dc
        if not gm.is_drivable(r0, c):
            continue
        if near is None and dc >= 4:
            near = (r0, c)
        if dc >= 20:
            far = (r0, c)
            break
    if near is None or far is None:
        return None, None, None, None

    # near zone: barely above the 0.22 belief threshold; far zone: rich
    gm.resource_prob[near] = 0.30
    gm.resource_prob[far] = 0.95
    return cfg, gm, near, far


def test_nearest_picks_close_zone_resource_picks_rich_zone():
    cfg, gm, near, far = _world_with_two_zones()
    if near is None:
        # world layout leaves no clean corridor on the start row; skip
        import pytest
        pytest.skip("seed 7 world has no clean corridor for this scenario")

    mapper = FakeMapper([near, far])
    kw = dict(cfg=cfg, gm=gm, mapper=mapper,
              rover_xy=cfg.world.start_xy, station_xy=cfg.world.station_xy)

    d_near = select_target(strategy="nearest", **kw)
    d_rich = select_target(strategy="resource", **kw)

    assert d_near is not None and d_rich is not None
    assert d_near.cell == near, "'nearest' must pick the close, poor zone"
    assert d_rich.cell == far, "'resource' must pick the far, rich zone"


def test_full_strategy_scores_value_per_energy():
    cfg, gm, near, far = _world_with_two_zones()
    if near is None:
        import pytest
        pytest.skip("seed 7 world has no clean corridor for this scenario")

    mapper = FakeMapper([near, far])
    decision = select_target(cfg=cfg, gm=gm, mapper=mapper,
                             rover_xy=cfg.world.start_xy,
                             station_xy=cfg.world.station_xy,
                             strategy="full")
    assert decision is not None
    # the score must be a finite positive number and the decision must carry
    # the energy breakdown the dashboard displays
    assert 0.0 < decision.score < float("inf")
    assert decision.e_travel_wh > 0.0
    assert decision.e_mine_wh > 0.0
    assert decision.expected_yield_g > 0.0
