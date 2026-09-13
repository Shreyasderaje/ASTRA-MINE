"""THE core ASTRA-MINE experiment: compare target-selection strategies.

Runs the same simulated mission with all four strategies across many seeds
and terrains, then reports mean performance and generates the comparison
charts used in the project report and PPT.

Usage (from the software/ folder):
    python -m astra.experiments.run_experiments                # 10 seeds
    python -m astra.experiments.run_experiments --seeds 25
    python -m astra.experiments.run_experiments --seeds 10 --sites 6

Outputs (results/):
    experiments.csv              raw per-run metrics
    comparison_bars.png          bar chart: strategy vs mean metrics
    comparison_boxplot.png       distribution of g/Wh per strategy
    summary.txt                  the numbers (copy into the report)
"""
from __future__ import annotations

import argparse
import csv
import os
import time

from ..brain.mission import MissionController
from ..brain.perception import ResourceMapper
from ..hal.sim_rover import SimRoverHAL
from ..sim.world import generate_world
from ..config import STRATEGIES, Config


def run_single(strategy: str, seed: int, max_sites: int) -> dict:
    cfg = Config()
    cfg.mission.strategy = strategy
    cfg.mission.seed = seed
    cfg.mission.max_sites = max_sites

    gm = generate_world(cfg)
    import numpy as np
    rover = SimRoverHAL(cfg, gm, np.random.default_rng(seed))
    mission = MissionController(cfg, rover, gm, ResourceMapper(cfg, gm))
    metrics = mission.run(max_wall_clock_s=120.0)

    s = metrics.summary()
    s.update({
        "strategy": strategy,
        "seed": seed,
        "map_resource_g": round(float(gm.resource_amount.sum()), 1),
        "done_reason": mission.state.done_reason,
    })
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description="ASTRA-MINE strategy comparison experiment")
    ap.add_argument("--seeds", type=int, default=10, help="number of terrain seeds")
    ap.add_argument("--sites", type=int, default=5, help="max mining sites per mission")
    ap.add_argument("--out", default="results", help="output directory")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rows = []
    t0 = time.time()
    for strategy in STRATEGIES:
        for seed in range(1, args.seeds + 1):
            row = run_single(strategy, seed, args.sites)
            rows.append(row)
            print(f"[{time.time()-t0:6.1f}s] {strategy:9s} seed={seed:2d} "
                  f"delivered={row['delivered_g']:6.1f} g  "
                  f"energy={row['energy_wh']:.3f} Wh  "
                  f"g/Wh={row['resource_per_wh']:7.1f}  "
                  f"dist={row['distance_m']:6.2f} m")

    # ---------------------------------------------------------------- CSV
    csv_path = os.path.join(args.out, "experiments.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[csv] {csv_path}")

    # ---------------------------------------------------------------- stats
    import numpy as np
    fields = ["delivered_g", "energy_wh", "distance_m", "time_s",
              "resource_per_wh", "sites_mined", "replans", "collisions"]
    lines = [f"ASTRA-MINE strategy comparison - {args.seeds} seeds, "
             f"max {args.sites} sites", "=" * 78,
             f"{'strategy':<12}" + "".join(f"{k:>16}" for k in fields)]
    summary_means = {}
    for strategy in STRATEGIES:
        sel = [r for r in rows if r["strategy"] == strategy]
        means = {k: float(np.mean([r[k] for r in sel])) for k in fields}
        summary_means[strategy] = means
        lines.append(f"{strategy:<12}" + "".join(f"{means[k]:>16.2f}" for k in fields))

    best = max(summary_means, key=lambda s: summary_means[s]["resource_per_wh"])
    lines += ["", f"Best g/Wh strategy: {best}"]
    lines.append(f"Improvement of '{best}' over 'nearest': "
                 f"{100*(summary_means[best]['resource_per_wh'] / summary_means['nearest']['resource_per_wh'] - 1):+.1f}%")
    text = "\n".join(lines)
    with open(os.path.join(args.out, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print("\n" + text)

    # ---------------------------------------------------------------- plots
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1. bar chart of means
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    colors = {"nearest": "#888888", "shortest": "#4a6fa5",
              "resource": "#b8860b", "full": "#c62828"}
    for ax, field, label in zip(
            axes, ["delivered_g", "energy_wh", "resource_per_wh"],
            ["Resource delivered (g)", "Energy consumed (Wh)",
             "Resource yield per energy (g/Wh)"]):
        means = [summary_means[s][field] for s in STRATEGIES]
        bars = ax.bar(STRATEGIES, means, color=[colors[s] for s in STRATEGIES],
                      edgecolor="black", linewidth=0.6)
        ax.bar_label(bars, fmt="%.1f", fontsize=9)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle(f"ASTRA-MINE: target-selection strategy comparison ({args.seeds} seeds)",
                 fontsize=13)
    fig.tight_layout()
    p1 = os.path.join(args.out, "comparison_bars.png")
    fig.savefig(p1, dpi=140)
    print(f"[plot] {p1}")

    # 2. boxplot of g/Wh distributions
    fig, ax = plt.subplots(figsize=(8, 5))
    data = [[r["resource_per_wh"] for r in rows if r["strategy"] == s]
            for s in STRATEGIES]
    bp = ax.boxplot(data, tick_labels=STRATEGIES, patch_artist=True)
    for patch, s in zip(bp["boxes"], STRATEGIES):
        patch.set_facecolor(colors[s])
        patch.set_alpha(0.7)
    ax.set_ylabel("Resource yield per energy (g/Wh)")
    ax.set_title("Distribution across terrain seeds")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p2 = os.path.join(args.out, "comparison_boxplot.png")
    fig.savefig(p2, dpi=140)
    print(f"[plot] {p2}")


if __name__ == "__main__":
    main()
