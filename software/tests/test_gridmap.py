"""Sanity checks on the simulated lunar world generator."""
from astra.config import Config
from astra.sim.world import generate_world


def _world(seed=7):
    cfg = Config()
    cfg.mission.seed = seed
    return cfg, generate_world(cfg)


def test_world_shapes_and_content():
    cfg, gm = _world()
    n = cfg.world.cells
    assert gm.n == n
    assert gm.traversable.shape == (n, n)
    assert gm.roughness.shape == (n, n)
    assert gm.resource_prob.shape == (n, n)
    # the world must actually contain mineable resource
    assert float(gm.resource_amount.sum()) > 0.0
    # some ground must be drivable, some must be blocked by rocks
    assert gm.traversable.any()
    assert not gm.traversable.all()


def test_start_and_station_are_drivable():
    cfg, gm = _world()
    assert gm.is_drivable(*gm.cell_of(*cfg.world.start_xy))
    assert gm.is_drivable(*gm.cell_of(*cfg.world.station_xy))


def test_world_is_reproducible_for_a_seed():
    _, gm1 = _world(seed=11)
    _, gm2 = _world(seed=11)
    import numpy as np
    assert np.array_equal(gm1.traversable, gm2.traversable)
    assert np.allclose(gm1.resource_amount, gm2.resource_amount)
