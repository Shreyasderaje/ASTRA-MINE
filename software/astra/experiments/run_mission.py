"""Run a single ASTRA-MINE mission in simulation.

Usage (from the software/ folder):
    python -m astra.experiments.run_mission                          # full strategy, seed 7
    python -m astra.experiments.run_mission --strategy nearest
    python -m astra.experiments.run_mission --seed 3 --render out.png
    python -m astra.experiments.run_mission --save results/mission.json

Prints the mission log and the final metrics table, optionally renders the
resource map / path figures used in the project report.
"""
from __future__ import annotations

import argparse
import json
import os

from ..brain.mission import MissionController
from ..brain.perception import ResourceMapper
from ..common.gridmap import make_maps
from ..hal.sim_rover import SimRoverHAL
from ..sim.world import generate_world
from ..config import STRATEGIES, Config


def build_mission(cfg: Config):
    gm = generate_world(cfg)
    rng = __import__("numpy").random.default_rng(cfg.mission.seed)
    rover = SimRoverHAL(cfg, gm, rng)
    mapper = ResourceMapper(cfg, gm)
    return MissionController(cfg, rover, gm, mapper), gm, rover


def render_maps(cfg: Config, mission: MissionController, gm, out_png: str) -> None:
    """Report figures: terrain, believed resource map, actual resources, path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 4, figsize=(20, 5.2))
    title = (f"ASTRA-MINE mission - strategy: {cfg.mission.strategy}, "
             f"seed: {cfg.mission.seed}")

    def decorate(ax, img, t):
        ax.imshow(img, cmap="cividis", origin="upper")
        ax.set_title(t, fontsize=10)
        ax.invert_yaxis()  # row 0 = top = max y
        # mark station + start
        for (wx, wy), marker, col in ((cfg.world.station_xy, "s", "cyan"),
                                      (cfg.world.start_xy, "^", "white")):
            r, c = gm.cell_of(wx, wy)
            ax.plot(c, r, marker, color=col, ms=8, mec="k")

    decorate(axes[0], gm.roughness, "Terrain roughness (rocks = bright)")
    decorate(axes[1], gm.elevation, "Elevation (craters)")
    decorate(axes[2], gm.resource_prob, "Believed resource probability")
    im = axes[3].imshow(gm.resource_amount / max(1e-6, gm.resource_amount.max()),
                        cmap="inferno")
    axes[3].set_title("Ground truth resource amount", fontsize=10)
    fig.colorbar(im, ax=axes[3], fraction=0.046)

    # overlay the mining decisions of the chosen path
    for dec in mission.metrics.decisions:
        r, c = dec.cell
        axes[2].plot(c, r, "o", ms=12, mfc="none", mec="red", mew=2)
        axes[3].plot(c, r, "o", ms=12, mfc="none", mec="cyan", mew=2)

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=140)
    print(f"[render] map figure saved -> {out_png}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one ASTRA-MINE simulated mission")
    ap.add_argument("--strategy", default="full", choices=STRATEGIES)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--sites", type=int, default=None, help="max mining sites")
    ap.add_argument("--render", default=None, help="save a map figure PNG here")
    ap.add_argument("--save", default=None, help="save metrics JSON here")
    ap.add_argument("--quiet", action="store_true", help="hide the event log")
    args = ap.parse_args()

    cfg = Config()
    cfg.mission.strategy = args.strategy
    cfg.mission.seed = args.seed
    if args.sites:
        cfg.mission.max_sites = args.sites

    mission, gm, rover = build_mission(cfg)
    metrics = mission.run(max_wall_clock_s=90.0)

    if not args.quiet:
        print("=" * 74)
        print("ASTRA-MINE MISSION LOG")
        print("=" * 74)
        for line in mission.log:
            print(line)

    s = metrics.summary()
    print("=" * 74)
    print("MISSION SUMMARY (strategy=%s, seed=%d)" % (cfg.mission.strategy, cfg.mission.seed))
    print("-" * 74)
    for k, v in s.items():
        print(f"  {k:18s} : {v}")
    print("-" * 74)
    print(f"  ground-truth resource on map : {gm.resource_amount.sum():.0f} g")
    print(f"  yield / energy (headline)    : {s['resource_per_wh']} g/Wh")

    if args.render:
        render_maps(cfg, mission, gm, args.render)
    if args.save:
        os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump({
                "config": {"strategy": cfg.mission.strategy, "seed": cfg.mission.seed},
                "metrics": s,
                "decisions": [{"cell": list(d.cell), "reason": d.reason,
                               "score": round(d.score, 5)} for d in metrics.decisions],
                "log": mission.log,
            }, f, indent=2)
        print(f"[save] metrics -> {args.save}")


if __name__ == "__main__":
    main()
