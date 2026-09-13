# ASTRA-MINE — Step-by-Step Build Guide (Zero → Finished)

This is the master guide. Follow the phases in order. Every phase has a
**Definition of Done** — do not move on until it passes. Phases 0–3 need **no
hardware at all**: the entire AI + software system is finished and validated
in simulation first, which protects your budget and your semester.

Owners per phase are mapped in `docs/05-TIMELINE-AND-ROLES.md`.

---

## Phase 0 — Software setup (Week 1, everyone, ~2 hours)

1. Install **Python 3.11+** and **Git**.
2. Get the repo and set up the environment:

```bash
cd astra-mine/software
pip install -r requirements.txt
```

3. Verify the simulator runs:

```bash
python -m astra.experiments.run_mission --strategy full --seed 7
```

You should see a mission log ending with `MISSION COMPLETE` and a summary
table (delivered grams, energy, g/Wh).

**Definition of Done:** every teammate can run the mission on their laptop.

---

## Phase 1 — Understand the system (Week 1–2, team lead + all)

Read these in order (all are short):

1. `README.md` — architecture diagram, what talks to what.
2. `software/astra/config.py` — every physical constant of rover + world.
3. `software/astra/brain/mission.py` — the 5-state mission loop.
4. `software/astra/brain/optimizer.py` — the 4 strategies and the score formula.

Play with the dashboard:

```bash
python -m astra.dashboard.server     # → http://127.0.0.1:8000 → LAUNCH
```

Watch: how SURVEY builds the probability map, how SELECT picks different
targets per strategy (change the dropdown), how MINE/RETURN loop.

**Definition of Done:** each member can explain the mission loop and where
their subsystem sits in the diagram.

---

## Phase 2 — Run the core experiment (Week 2, team lead)

```bash
python -m astra.experiments.run_experiments --seeds 15
```

Outputs to `software/results/`: `experiments.csv`, `summary.txt`,
`comparison_bars.png`, `comparison_boxplot.png`.

**Expected result:** both intelligent strategies beat the naive baselines by
roughly +12% on resource-per-energy; the `full` optimizer delivers
`resource`-greedy-level efficiency with ~14% less travel (see
`docs/04` for the exact reference numbers — always report YOUR actual
`results/summary.txt`). **These charts and the CSV go directly into your
report and PPT.**

**Definition of Done:** `results/summary.txt` exists; the team agrees on the
headline number.

---

## Phase 3 — Vision pipeline (Week 3–4, software member, no hardware)

The camera identifies resource zones by colour/texture markers (the physical
testbed uses iron-oxide-coloured gravel as the resource proxy — same trick
real prospecting missions use with spectral proxies).

```bash
python -m astra.vision.dataset_gen --n 400     # synthetic labelled dataset
python -m astra.vision.detector                # self-test: zone vs empty frame
```

Optional (better accuracy, still no GPU needed for yolov8n at this size):

```bash
pip install ultralytics
yolo detect train data=vision_dataset/dataset.yaml model=yolov8n.pt epochs=30 imgsz=320
```

**Definition of Done:** detector self-test prints a high score on zone frames
and ~0 on empty frames; (optional) YOLO trained with mAP > 0.8 on the dataset.

---

## Phase 4 — Buy the hardware (Week 4, embedded member)

Full details in `docs/02-HARDWARE-BOM.md`. Order in **two batches**:

- **Batch 1 (mobility, ~₹12k):** chassis, 4× geared motors + wheels, motor
  driver, ESP32, encoders, battery + holder + buck, wires, switch.
- **Batch 2 (intelligence, ~₹15k):** Raspberry Pi 5, camera, IMU, INA219,
  ToF sensor, servo + scoop material, testbed materials.

**Definition of Done:** Batch 1 parts in hand; batch 2 ordered.

---

## Phase 5 — Build the rover chassis + power (Week 5, robotics member)

Follow `docs/03-ASSEMBLY-AND-WIRING.md`:
1. Assemble chassis, mount 4 motors, wire 2 sides in parallel to each channel.
2. Wire TB6612 → ESP32 per the pin table. **Triple-check polarity.**
3. Power rails: battery → switch → driver VM; buck 5V → ESP32/servo.
4. Test the drivetrain with a simple test sketch before any firmware.

**Definition of Done:** rover drives forward/back/turn from a test sketch;
nothing overheats; battery voltage under load ≥ nominal.

---

## Phase 6 — Flash firmware + bring-up (Week 6, embedded member)

1. Arduino IDE → install **ESP32 board support**, libraries `ESP32Servo`,
   `Adafruit INA219`, `Adafruit VL53L0X`.
2. Open `firmware/esp32_rover/esp32_rover.ino`, check the pin map matches
   your wiring, flash it. Full bench procedure + acceptance checks:
   **docs/06-REAL-TIME-OPERATION.md §3**.
3. From the Pi (or any PC) test the protocol:

```bash
pip install pyserial
python - <<'EOF'
import serial, time, json
s = serial.Serial("COM5", 115200, timeout=1)   # your port; on Pi: /dev/ttyUSB0 or ACM0
for _ in range(20):                             # dump telemetry lines
    line = s.readline().decode(errors="ignore").strip()
    if line: print(line)
s.write(b'{"cmd":"vel","v":0.08,"w":0.0}\n'); time.sleep(1)
s.write(b'{"cmd":"stop"}\n')
EOF
```

4. Verify: telemetry at 10 Hz, `x/y/h` advancing when you drive, `wh`
   increasing, `tilt` sane, watchdog stops the rover when you unplug commands.

**Definition of Done:** closed-loop `{"cmd":"vel"}` driving works; telemetry
verified; failsafe demonstrated.

> Then do the one-time **calibration session** (odometry scale, Wh/m, base
> power, scoop rate, camera geometry) — docs/06 §5. Without it the digital
> twin and the sim will not match the real rover.

---

## Phase 7 — Motion acceptance tests (Week 7, robotics + embedded)

Run and log (this becomes report data):
1. Straight-line 1 m: odometry error < 5%.
2. Square path (1 m × 4 turns): end-position error < 10 cm.
3. Measured energy per metre (compare with `config.py` model — update the
   config constants to match reality!).
4. Rock-avoidance: place obstacles, verify stop/slide behaviour.

**Definition of Done:** a table of measured vs simulated numbers (this
comparison is literally a report section: "model validation").

---

## Phase 8 — Real perception (Week 8, software member)

1. Mount the Pi camera top-down at ~0.8–1.2 m height on a small mast.
2. Calibrate `HSV_LOW/HSV_HIGH` in `astra/vision/detector.py` against your
   actual marker gravel under your room's lighting.
3. Place a resource patch; run the detector on live frames; tune until
   detection is stable at ≥ 2 m/s of rover-relative motion... (it's slow
   indoor driving — you're fine).
4. Feed detections into `ResourceMapper.fuse()` — the mapping from pixel
   bbox to grid cells is in `detector.frame_resource_score()`.

**Definition of Done:** detector runs live on the Pi at ≥ 5 FPS and scores
the known patch significantly higher than bare regolith.

---

## Phase 9 — Autonomy on the real rover (Week 9–11, everyone)

The moment of truth — **zero new code** is required. Two equivalent ways:

**A. Dashboard (recommended):** launch `python -m astra.dashboard.server`,
switch **Mode → REAL ROVER**, enter the rover's COM port (and the station
port if built), press **LAUNCH**. The map starts unknown; rocks appear as
the ToF discovers them; **click the map to cue resource zones** while the
rover surveys; watch pose, battery, decisions and measured grams live.

**B. Python:** only the HAL swap:

```python
from astra.hal.real_rover import RealRoverHAL
rover = RealRoverHAL(cfg, port="/dev/ttyACM0")   # or COM5 on Windows
rover.set_world_offset(*cfg.world.start_xy)      # rover placed at start
# everything else identical to the simulation
```

Run in stages:
1. **Teleop + mapping only:** drive manually, watch the resource map build
   on the dashboard (this alone is a great demo!).
2. **NAVIGATE only:** pick a fixed target cell, verify A* + waypoint
   following on the physical testbed.
3. **Full autonomous mission** on the analogue testbed (craters = shallow
   sand dips, rocks = stones, resource zones = marker gravel).

Keep a **manual override** (gamepad/keyboard) wired in at all times.

**Definition of Done:** one full autonomous survey→mine→deliver cycle filmed.

---

## Phase 10 — Processing station + ISRU model (Week 11–12, robotics+software)

1. Station: a hopper on a load cell (HX711) reporting grams delivered
   (optional but great: a second ESP32 streaming the weight).
2. The ISRU yield model (`dashboard` computes it): collected mass ×
   simulated recoverable fraction → theoretical H₂O → electrolysis → H₂/O₂
   theoretical yield. Modelled only — **never** real chemistry.

**Definition of Done:** dashboard shows real delivered grams from the load cell.

---

## Phase 11 — Final experiments (Week 13–14, team lead)

Repeat Phase 2's methodology on the real testbed if budget allows
(≥ 3 runs per strategy), plus the simulated 15-seed study. Compare and
discuss deviations in the report.

**Definition of Done:** results tables + charts frozen into the report.

---

## Phase 12 — Report + PPT + demo day (Week 14–16, everyone)

1. Report skeleton is in `docs/04-EXPERIMENTS-AND-REPORT.md`.
2. Demo script: problem (30 s) → live autonomous run → dashboard close-up →
   results table → "we built the intelligence such a system would need."
3. Record a 2-minute demo video of one full mission with the dashboard
   visible — this is your presentation centrepiece.

**Definition of Done:** report submitted, demo rehearsed twice, backup
slides with recorded video in case of live-demo failure.

---

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| Rover veers left/right | motor trim / wheel slip | add PWM trim constants; clean wheels |
| Odometry drifts | encoder counts wrong | check `ENC_TICKS_PER_REV`, both encoder edges |
| Telemetry freezes | serial buffer flood | Pi: `stty -F /dev/ttyACM0 raw 115200` |
| Detector finds nothing | lighting/HSV | re-calibrate HSV at the venue lighting |
| Mission ends instantly | energy budget | raise `MissionConfig.energy_budget_wh` |
| Rover gets stuck (sim) | that's real behaviour! | watch the escape maneuver in the log |
| Pi reboots under load | weak PSU | use 5V/5A official supply, separate servo BEC |
