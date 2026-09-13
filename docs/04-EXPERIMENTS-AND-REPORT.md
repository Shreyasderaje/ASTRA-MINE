# ASTRA-MINE — Experiments, Results & Report Structure

## 1. The research question (put this verbatim in the report)

> Can an autonomous rover use AI-based resource estimation and energy-aware
> target selection to maximize resource yield per unit energy, compared with
> naive target-selection strategies, in a lunar analogue environment?

## 2. Variables

| Type | Item |
|---|---|
| Independent | target-selection strategy: `nearest`, `shortest`, `resource`, `full` |
| Dependent | resource delivered (g), energy consumed (Wh), **g/Wh (headline)**, distance, mission time, sites mined |
| Controlled | terrain seed set, sensor noise, rover params, energy budget (1.2 Wh), station position |

The four strategies (`astra/brain/optimizer.py`):

1. **nearest** — go to the nearest believed resource zone (baseline)
2. **shortest** — go to the zone with the cheapest path (baseline)
3. **resource** — go to the highest-yield zone, ignore cost (baseline)
4. **full (ours)** — maximize `yield / ((E_travel + E_mine + E_return) × (1 + w·risk))`

## 3. Running the experiments

```bash
cd software
python -m astra.experiments.run_experiments --seeds 15
```

Produces in `software/results/`:

- `experiments.csv` — one row per (strategy, seed): raw data for the report
- `summary.txt` — the means table
- `comparison_bars.png` — delivered g / energy / g-per-Wh bar charts
- `comparison_boxplot.png` — per-seed distribution of g/Wh

Also save a mission-map figure for the report:

```bash
python -m astra.experiments.run_mission --strategy full --seed 7 --render results/mission_map_full.png
python -m astra.experiments.run_mission --strategy nearest --seed 7 --render results/mission_map_nearest.png
```

(Each figure shows terrain, elevation, believed probability map, ground truth
and the actual sites the rover chose — the clearest single picture of the
system working.)

### What the data shows (15-seed reference run — verify against your `results/summary.txt`)

| Strategy | Delivered (g) | Energy (Wh) | Distance (m) | **g/Wh** |
|---|---|---|---|---|
| nearest | 201.4 | 0.68 | 15.1 | 300.8 |
| shortest | 202.6 | 0.68 | 15.1 | 302.9 |
| resource | 256.2 | 0.76 | 17.6 | **345.6** |
| **full (ours)** | 228.0 | 0.69 | 15.2 | 337.2 |

Read these results honestly — this nuance is exactly what makes a good
discussion section:

- Both intelligent strategies (`resource`, `full`) beat the naive baselines
  by **~12%** on resource-per-energy.
- `full` delivers 89% of the grams that pure `resource`-greedy delivers, but
  using 9% less energy and 14% less travel — i.e. it achieves nearly the same
  efficiency with a markedly cheaper mission profile.
- On a **small 3 m testbed, travel energy is a minor cost** (electronics base
  power dominates), so pure resource-greedy performs similarly. The scale
  study below shows where the full optimizer's advantage grows.

### Scale sensitivity study (why the optimizer matters more "on the Moon")

**Measured result** (`results/scale_study.txt`, 15 seeds per scale, same 1.2 Wh
budget, only the terrain size changes):

| Scale | nearest | shortest | resource | **full (ours)** |
|---|---|---|---|---|
| 3 m testbed | 300.8 | 302.9 (+0.7%) | **345.6 (+14.9%)** | 337.2 (+12.1%) |
| 5 m terrain | 173.3 | 173.3 (+0.0%) | 185.5 (+7.0%) | **188.6 (+8.8%)** |

(values are g/Wh; improvement over `nearest` in brackets)

What the data shows — report this trend, it is the best discussion material
in the project:

1. **Every strategy loses efficiency at scale** — the baseline drops 42.4 %
   (300.8 → 173.3 g/Wh) because travel energy dominates on a big terrain.
2. **The strategy RANKING changes with scale**: at testbed scale pure
   resource-greedy leads (+14.9%); at 5 m the **full optimizer overtakes it
   (+8.8% vs +7.0%)** — exactly the trade-off it optimizes for. The full
   strategy reaches nearly the same yield as resource-greedy while travelling
   8.4% less (27.7 m vs 30.2 m).
3. Conclusion for the report: at prospecting-relevant distances (real
   traverses are 100 m–km scale), value-per-energy decision making is not an
   optimization detail — it is the difference between a viable mission and a
   dead rover.

## 4. Real-rover experiments (Phase 11 of the guide)

- ≥ 3 runs per strategy on the physical testbed (zones re-seeded identically —
  same layout, re-weighed markers).
- Report the same metrics using the INA219-integrated Wh (firmware) and the
  load-cell grams.
- Add a "model validation" table: simulated vs measured energy per metre,
  odometry error, mission time. Professors love validation.

## 5. Metrics definitions (report appendix)

- **Resource yield per energy (g/Wh)** = grams delivered to station ÷ total
  electrical energy from the battery (INA219 / simulated power model).
- **Coverage (%)** = observed drivable cells ÷ total drivable cells.
- **Decision quality** = chosen site's actual grams ÷ best site's actual grams.
- **Localization error** = final rover (x,y) vs measured true position.

## 6. Report skeleton (map your college template onto this)

1. **Introduction** — lunar ISRU motivation; the logistics problem; cite
   NASA IPEx, ESA Space Resources Challenge, ESA Prospect (from the ChatGPT
   blueprint's source list — verify each link before citing!)
2. **Problem Statement & Objectives** — the research question above; 4–5
   measurable objectives.
3. **Literature Review** — prior rovers/excavators; what exists; where the
   gap is (closed-loop resource-energy-risk decision making at student scale).
4. **System Design** — architecture diagram (README), state machine, the
   score formula, hardware block diagram (docs/03).
5. **Implementation** — sim-first methodology, HAL abstraction, perception
   pipeline, firmware, dashboard; include the escape-maneuver story (it's a
   great "real robotics happened to us" anecdote).
6. **Experimental Setup** — testbed description + photos, variables table.
7. **Results & Discussion** — Tables from CSV, the two comparison figures,
   map figures, real-rover validation table, limitations (simulant ≠ lunar
   soil, proxy sensing, no SLAM — odometry only).
8. **Conclusion & Future Work** — multi-rover coordination (NASA CADRE),
   reinforcement learning on the digital twin, spectral (NIR) proxy sensing.
9. **References** — verified NASA/ESA/ISRO links + the textbook-style
   robotics references (ROS 2, A*, hybrid-glu... no, keep it: A*, differential
   drive odometry, complementary filter).

## 7. Demo script (10 minutes)

1. (1 min) Problem: "future lunar bases can't ship every kg from Earth."
2. (2 min) Show the dashboard running a simulated mission at max speed —
   explain the map, the decision panel, the state machine.
3. (4 min) Live rover run on the testbed: survey → decision → mining →
   return → delivered grams on the load cell.
4. (2 min) Results: the comparison chart; the intelligent strategies beat the
   naive baselines by ~12–15% on resource-per-energy (your measured numbers).
5. (1 min) Future work + close: "we built the intelligence such a system
   would need."
6. Backup: pre-recorded demo video (record in Phase 9, don't improvise).
