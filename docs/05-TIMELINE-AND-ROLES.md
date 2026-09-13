# ASTRA-MINE — 16-Week Timeline & Team Roles

Team SUDARSHAN (SPPN): the four members own four subsystems; the team lead
integrates. Code folders map 1:1 to roles so nobody is blocked on anybody.

## Role map (rename members as needed)

| Role | Owner (SPPN initial) | Owns in this repo | Key docs |
|---|---|---|---|
| **Team Lead / AI & Mission** | S — Shreyas | `astra/brain/`, `astra/experiments/`, integration, report | 04 |
| **Robotics / Mechanical** | P — Pruthviraj | chassis, scoop, testbed, assembly | 02, 03 |
| **Embedded / Electronics** | P — Puneeth | `firmware/`, power, sensors, `astra/hal/real_rover.py` | 02, 03 |
| **Software / Vision & Digital Twin** | N — Naveen | `astra/vision/`, `astra/dashboard/`, telemetry, data logging | 01 |

The team-lead role is **integration responsibility**, not seniority: every
subsystem owner validates their own part; the lead owns the seams.

## 16-week plan

| Weeks | Phase (guide) | Milestone / deliverable | Lead |
|---|---|---|---|
| 1 | P0–P1 | everyone runs the sim; roles understood | All |
| 2 | P2 | `results/` frozen: strategy comparison + charts | S |
| 3–4 | P3 | detector works; dataset generated; (opt.) YOLO trained | N |
| 4 | P4 | Batch 1 ordered | P |
| 5 | P5 | rover drives (RC/test sketch) | Pr + Pu |
| 6 | P6 | firmware flashed; protocol verified; failsafes shown | Pu |
| 7 | P7 | acceptance tests: odometry error < 5–10%, energy/metre table | Pr + Pu |
| 8 | P8 | live perception ≥ 5 FPS on Pi; HSV calibrated | N |
| 9 | P9a | teleop + live mapping demo on real testbed | S + N |
| 10 | P9b | autonomous NAVIGATE to a fixed target on hardware | S + Pu |
| 11 | P9c | full autonomous mission filmed | All |
| 11–12 | P10 | station + load cell + ISRU yield model on dashboard | Pr + N |
| 13–14 | P11 | real-rover experiments (≥3 runs/strategy) + report data freeze | S |
| 14–15 | P12a | report written; figures from `results/` | S + N |
| 15–16 | P12b | PPT, demo video, 2 rehearsals, submission | All |

## Weekly rhythm (30-minute standup, twice a week)

1. Each owner: what works / what's blocked.
2. Lead checks the Definition of Done of the current phase.
3. Anything hardware → update the BOM/assembly doc the same day.

## Risk register (review every 2 weeks)

| Risk | Probability | Mitigation |
|---|---|---|
| Rover unreliable → demo at risk | High | manual mode always ready; sim demo fallback |
| AI/perception accuracy poor | Medium | colour markers are forgiving; YOLO upgrade path |
| Mining mechanism jams | Medium | simplest possible scoop; spares printed |
| Budget overrun | Medium | two-batch buying; LiDAR is optional |
| Team builds everything at the end | **Highest** | the phase gates in this repo exist precisely for this |
| Member falls sick in demo week | Medium | demo video + every member can run the dashboard |

## Where each deliverable for college comes from

| College requirement | Source |
|---|---|
| Synopsis | `README.md` + `docs/04` section 1–3 |
| Block diagram | README architecture + `docs/03` power diagram |
| Literature review | blueprint source list (NASA IPEx, ESA SRC, Prospect) — verify links |
| Methodology | `docs/01` phases + `docs/04` variables table |
| Results | `software/results/*.csv|png`, real-rover tables |
| Budget | `docs/02` totals |
| Future scope | `docs/04` section 8 |
