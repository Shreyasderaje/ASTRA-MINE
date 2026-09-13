# ASTRA-MINE — Complete Project Repository

**Autonomous AI-Driven Extraterrestrial Resource Prospecting & ISRU Demonstrator**
Team **SUDARSHAN** · SPPN Space Research Team · Shreyas · Pruthviraj · Puneeth · Naveen

This repository contains **everything for the software side** of the mini project:
a full physics-accurate simulator, the rover's AI brain, the Mission Control
digital-twin dashboard, the strategy-comparison experiment, the camera vision
pipeline, the ESP32 firmware, and complete step-by-step build documentation.

---

## Repository layout

```
astra-mine/
├── README.md                        <- you are here
├── docs/
│   ├── 01-STEP-BY-STEP-GUIDE.md     THE master guide: zero → finished project
│   ├── 02-HARDWARE-BOM.md           every part, price, and why it's needed
│   ├── 02b-LOW-BUDGET-JUGAAD.md     student build at ₹5k–9k: same science, frugal parts
│   ├── 03-ASSEMBLY-AND-WIRING.md    chassis build, full wiring tables, bring-up
│   ├── 04-EXPERIMENTS-AND-REPORT.md how to run experiments + report structure
│   ├── 05-TIMELINE-AND-ROLES.md     16-week plan + who does what
│   └── 06-REAL-TIME-OPERATION.md    flashing, calibration, LIVE digital twin
├── firmware/
│   ├── esp32_rover/esp32_rover.ino  ESP32 low-level controller (motors, sensors)
│   └── station_node/station_node.ino processing station (HX711 load cell)
└── software/
    ├── astra/
    │   ├── config.py                every tunable constant (one file!)
    │   ├── common/                  grid map + A* path planner
    │   ├── sim/                     lunar world generator + rover physics
    │   ├── hal/                     RoverInterface: sim ↔ real hardware swap
    │   ├── brain/                   perception, energy model, optimizer, mission
    │   ├── vision/                  dataset generator + resource-zone detector
    │   ├── dashboard/               Mission Control server + web UI (sim + REAL)
    │   └── experiments/             mission runner + strategy comparison
    ├── tests/                       19 tests: brain, planner, real-mode serial
    ├── requirements.txt
    └── results/                     experiment CSV + charts (generated)
```

## Quick start (no hardware needed — pure simulation)

```bash
cd software
pip install -r requirements.txt

# 1. run one mission end-to-end (survey → decide → navigate → mine → deliver)
python -m astra.experiments.run_mission --strategy full --seed 7

# 2. save the report figures (terrain, resource map, decisions)
python -m astra.experiments.run_mission --strategy full --render ../report_fig.png

# 3. THE core experiment: compare 4 strategies over 15 terrains
python -m astra.experiments.run_experiments --seeds 15

# 4. scale sensitivity study (3 m testbed vs 5 m terrain)
python -m astra.experiments.run_scale_study --seeds 15

# 5. launch the Mission Control dashboard
python -m astra.dashboard.server
#    → open http://127.0.0.1:8000, press LAUNCH

# 6. vision: generate the synthetic dataset + test the detector
python -m astra.vision.dataset_gen --n 400
python -m astra.vision.detector

# 7. run the test suite (19 tests, no hardware needed)
python -m pytest tests/ -v
```

### Real rover mode (needs the hardware, docs/06)

The dashboard has a **REAL ROVER** mode: the same brain drives the physical
rover over USB serial, the map starts unknown and fills in live from the
ToF sensor, the camera and operator cueing (click the map to cue a resource
zone). You watch the rover's actual pose, battery, decisions and measured
delivered grams in real time — the digital twin. Full procedure:
**docs/06-REAL-TIME-OPERATION.md**.

## The architecture in one diagram

```
        ┌──────────────────────────────────────────────────┐
        │                 MISSION CONTROL                  │
        │   astra/dashboard: live digital twin (browser)   │
        └────────────────────▲─────────────────────────────┘
                             │ WebSocket telemetry
        ┌────────────────────┴─────────────────────────────┐
        │                MISSION CONTROLLER                │
        │   SURVEY → SELECT → NAVIGATE → MINE → RETURN     │
        └───▲──────────────▲──────────────▲────────────────┘
            │              │              │
   ┌────────┴───┐   ┌──────┴──────┐  ┌────┴────────┐
   │ PERCEPTION │   │  OPTIMIZER  │  │ A* PLANNER  │
   │ resource   │   │ 4 strategies│  │ + energy +  │
   │ belief map │   │ (our novelty│  │ risk models │
   └────────┬───┘   └──────┬──────┘  └────┬────────┘
            └──────────────┼──────────────┘
                           ▼
                 RoverInterface (HAL)  ← the only hardware boundary
                 ┌────────────┴────────────┐
                 ▼                         ▼
        SimRoverHAL (physics sim)   RealRoverHAL (ESP32 serial)
```

## The research contribution

The rover does **not** follow a fixed route. Every decision computes:

```
                       expected resource yield (g)
  Mission Score = ─────────────────────────────────────────
                   (travel + mining + return energy) × (1 + w·risk)
```

and picks the highest-scoring reachable site. Running the four strategies
(nearest / shortest-path / resource-greedy / full) on identical terrain is
the experiment in `docs/04`. **Measured result (15 seeds):** both intelligent
strategies beat the naive baselines by ~12–15% on resource-per-energy;
resource-greedy edges the full optimizer on raw g/Wh at testbed scale, while
the full optimizer delivers nearly the same yield at 9% lower energy and 14%
less travel — and it is the decision model that scales to real prospecting
distances (see the scale study). Report the nuance honestly; it makes the
project stronger, not weaker.

## Honest-scoping notes (say these in your review, professors love it)

- The prototype is a **terrestrial analogue demonstrator**, not a lunar machine.
- "Resources" are **marked simulant zones** (visual/weight proxies), not real
  lunar ice — the camera pipeline is explicitly a *resource-proxy estimator*.
- Water-to-propellant is a **modelled pathway** (the dashboard computes
  theoretical electrolysis yield) — we never produce real H₂/O₂.

© 2026 SUDARSHAN — SPPN Space Research Team
(Shreyas Deraje · Pruthviraj Anchan · Puneeth · Naveen M)
