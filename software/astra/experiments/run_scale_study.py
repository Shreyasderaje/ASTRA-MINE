"""Scale sensitivity study: does the strategy ranking change with terrain size?

The 15-seed reference experiment (results/summary.txt) runs on the 3 m x 3 m
testbed, where travel energy is a minor cost and the electronics' base power
dominates. This script repeats the exact same 4-strategy comparison on a
larger 5 m x 5 m terrain with 7 resource zones, where every extra metre of
travel costs real energy and time - closer to real lunar prospecting, where
traverses are 100 m to kilometre scale.

Everything else (rover, sensors, energy budget 1.2 Wh, station position,
sensor radius) is held constant, so the ONLY changed variable is scale.

Usage (from the software/ folder):
    python -m astra.experiments.run_scale_study              # 15 seeds
    python -m astra.experiments.run_scale_study --seeds 10   # faster run

Outputs (results/):
    scale_study.csv    raw per-run metrics at both scales
    scale_study.txt    summary tables + the honest take-away
"""
from __future__ import annotations

import argparse
import csv
import os
import time

import numpy as np

from ..brain.mission import MissionController
from ..brain.perception import ResourceMapper
from ..config import STRATEGIES, Config
from ..hal.sim_rover import SimRoverHAL
from ..sim.world import generate_world

# (key, label, world overrides). Rock/crater counts scale with area so that
# terrain DENSITY stays comparable - size is the only real change.
SCALES = [
    ("3m", "3 m x 3 m testbed (reference)",
     dict(size_m=3.0, n_resource_zones=5, n_rocks=26, n_craters=5)),
    ("5m", "5 m x 5 m terrain (large)",
     dict(size_m=5.0, n_resource_zones=7, n_rocks=60, n_craters=10)),
]

FIELDS = ["delivered_g", "energy_wh", "distance_m", "time_s",
          "resource_per_wh", "sites_mined", "replans", "collisions"]


def run_single(strategy: str, seed: int, max_sites: int,
               world_overrides: dict) -> dict:
    cfg = Config()
    cfg.mission.strategy = strategy
    cfg.mission.seed = seed
    cfg.mission.max_sites = max_sites
    for key, value in world_overrides.items():
        setattr(cfg.world, key, value)

    gm = generate_world(cfg)
    rover = SimRoverHAL(cfg, gm, np.random.default_rng(seed))
    mission = MissionController(cfg, rover, gm, ResourceMapper(cfg, gm))
    metrics = mission.run(max_wall_clock_s=240.0)

    s = metrics.summary()
    s.update({"strategy": strategy, "seed": seed,
              "done_reason": mission.state.done_reason})
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description="ASTRA-MINE scale sensitivity study")
    ap.add_argument("--seeds", type=int, default=15,
                    help="terrain seeds per (scale, strategy)")
    ap.add_argument("--sites", type=int, default=5,
                    help="max mining sites per mission")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rows, t0 = [], time.time()
    for scale_key, scale_label, overrides in SCALES:
        for strategy in STRATEGIES:
            for seed in range(1, args.seeds + 1):
                row = run_single(strategy, seed, args.sites, overrides)
                row["scale"] = scale_key
                rows.append(row)
                print(f"[{time.time()-t0:6.1f}s] {scale_key} {strategy:9s} "
                      f"seed={seed:2d} delivered={row['delivered_g']:6.1f} g  "
                      f"g/Wh={row['resource_per_wh']:7.1f}", flush=True)

    # ----------------------------------------------------------------- CSV
    csv_path = os.path.join(args.out, "scale_study.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[csv] {csv_path}")

    # -------------------------------------------------------------- summary
    lines = [f"ASTRA-MINE scale sensitivity study - {args.seeds} seeds, "
             f"max {args.sites} sites, energy budget 1.2 Wh at both scales",
             "=" * 78]
    means = {}
    for scale_key, scale_label, _ in SCALES:
        lines += ["", f"--- {scale_label} ---",
                  f"{'strategy':<12}" + "".join(f"{k:>16}" for k in FIELDS)]
        means[scale_key] = {}
        for strategy in STRATEGIES:
            sel = [r for r in rows
                   if r["scale"] == scale_key and r["strategy"] == strategy]
            m = {k: float(np.mean([r[k] for r in sel])) for k in FIELDS}
            means[scale_key][strategy] = m
            lines.append(f"{strategy:<12}" + "".join(f"{m[k]:>16.2f}" for k in FIELDS))

    # improvement of each smart strategy over 'nearest', per scale
    lines += ["", "g/Wh improvement over 'nearest' baseline:"]
    for scale_key, scale_label, _ in SCALES:
        base = means[scale_key]["nearest"]["resource_per_wh"]
        parts = [f"{s}: {100*(means[scale_key][s]['resource_per_wh']/base-1):+.1f}%"
                 for s in STRATEGIES if s != "nearest"]
        lines.append(f"  {scale_label}:  " + "   ".join(parts))

    # how the baseline itself degrades with scale
    lines += ["", "Nearest-strategy g/Wh by scale "
              "(how much efficiency is lost when travel matters):"]
    base3 = means["3m"]["nearest"]["resource_per_wh"]
    base5 = means["5m"]["nearest"]["resource_per_wh"]
    lines.append(f"  3m: {base3:.1f} g/Wh   5m: {base5:.1f} g/Wh   "
                 f"change: {100*(base5/base3-1):+.1f}%")

    text = "\n".join(lines)
    with open(os.path.join(args.out, "scale_study.txt"), "w",
              encoding="utf-8") as f:
        f.write(text + "\n")
    print("\n" + text)


if __name__ == "__main__":
    main()
