# ASTRA-MINE — Real Rover: Build & Real-Time Digital Twin Operation

This is the bridge document: how the **software you already have** connects to
the **physical rover**, and how to run both together so that **when the rover
moves, the dashboard shows it live** — the digital twin.

Read `02-HARDWARE-BOM.md` (what to buy) and `03-ASSEMBLY-AND-WIRING.md` (how
to put it together) first. This document covers flashing, calibration and the
real-time operation that those two documents set up.

---

## 1. How the real-time twin works (the honest version)

```
 ┌────────────────────────── ROVER ──────────────────────────┐
 │  CAMERA ──► Raspberry Pi 5  ("the brain")                 │
 │              ├─ vision.live     frames → resource cues    │
 │              ├─ MissionController (same brain as sim!)    │
 │              └─ RealRoverHAL    JSON over USB serial      │
 │                            │                              │
 │  ESP32 ("the reflexes") ◄──┘── motors, encoders, IMU,     │
 │  50 Hz real-time loop         INA219 energy, ToF, scoop   │
 └────────────────────────────┬──────────────────────────────┘
                              │ USB serial ×2 (rover + station)
 ┌────────────────────────────▼──────────────────────────────┐
 │  LAPTOP BROWSER  —  Mission Control dashboard             │
 │  live pose · battery · energy · AI decisions · map · g/Wh │
 └───────────────────────────────────────────────────────────┘
        ▲
        └── STATION NODE (2nd ESP32 + HX711 load cell) streams
            the MEASURED delivered grams
```

The key design decision is the **HAL (Hardware Abstraction Layer)**:
`MissionController` talks only to the `RoverInterface` (see `hal/base.py`).
The simulator and the real rover both implement that same interface, so the
**exact same AI code, planner, optimizer and state machine** run in both
worlds. When you switch from sim to real, nothing in the brain changes —
only which object the brain talks to.

### What matches EXACTLY vs. what needs CALIBRATION

| Signal | Real-time behaviour | Match quality |
|---|---|---|
| Rover pose on the map | streamed from encoders + gyro, 10 Hz | live, but **odometry drifts** (±3–5 % of distance) — re-place rover at known points to re-anchor |
| Battery % / energy Wh | measured by the INA219, integrated on the ESP32 | **measured, exact** |
| Distance travelled | integrated from pose fixes | live, same drift as pose |
| AI decisions (target, score, reason) | the real optimizer, live | **identical logic to sim** |
| Resource map | built from camera detections + your clicks + ToF rocks | live, but it's a **proxy sensor** (coloured markers), not real water ice |
| Delivered grams | HX711 load cell at the station | **measured, exact** (falls back to scoop-timing estimate without the station node) |
| Energy model (Wh per metre) | config values until you calibrate | **calibrate** (section 5) — after calibration the sim predicts reality within ~10–15 % |

Say it exactly this way in the report: *"The digital twin mirrors the
rover's measured state in real time; the simulated energy model is
calibrated against INA219 measurements on the testbed."* Never claim the
simulation IS reality.

---

## 2. Software setup (do this BEFORE the rover exists)

On the laptop **and later on the Pi** (same steps):

```bash
# Python 3.10+ required
cd astra-mine/software
pip install -r requirements.txt

# verify everything works - all tests must pass:
python -m pytest tests/ -v

# verify the simulation end-to-end:
python -m astra.experiments.run_mission --strategy full --seed 7

# launch the dashboard and run a SIM mission first:
python -m astra.dashboard.server     # → http://127.0.0.1:8000
```

**Definition of done:** all 19 tests green; one full simulated mission
delivered grams; dashboard renders a live sim mission.

---

## 3. Flash the firmware (2 boards)

### 3.1 Arduino IDE setup

1. Install **Arduino IDE 2.x**.
2. Add ESP32 support: File → Preferences → Additional Board URLs →
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`,
   then Boards Manager → install **esp32 by Espressif**.
3. Library Manager → install: **ESP32Servo**, **Adafruit INA219**,
   **Adafruit VL53L0X**, **HX711** (station only).

### 3.2 Rover controller (`firmware/esp32_rover/esp32_rover.ino`)

1. Open the file; Board = "ESP32 Dev Module", Port = the ESP32's COM port.
2. **With nothing else connected**, upload. Open Serial Monitor at
   **115200 baud** — you must see:
   `{"boot":"astra-mine-esp32","fw":1.1}`
3. Type `{"cmd":"reset"}` + Enter → no crash = parser OK.
4. Wire motors (docs/03 §2), upload again, and test:
   `{"cmd":"vel","v":0.10,"w":0}` → **wheels must turn forward**.
   `{"cmd":"vel","v":0.05,"w":0.8}` → spins in place.
   `{"cmd":"stop"}` → stops.
5. Connect MPU-6050 → telemetry `"h"` changes as you rotate the board.
6. Connect INA219 → `"vbat"` shows your real battery voltage.
7. Connect VL53L0X → hold your hand 20 cm in front: `"dist"` ≈ 20.
8. Connect encoders → push the rover by hand: `"x"`/`"y"` change.

**Definition of done:** all 8 checks above pass on the bench. Do NOT
proceed to chassis assembly until they do.

### 3.3 Station node (`firmware/station_node/station_node.ino`)

1. Wire HX711 + load cell (docs/03 §3).
2. Upload, Serial Monitor 115200 → `{"boot":"astra-mine-station","fw":1.0}`.
3. **Calibrate the scale** (header comment of the file): tare empty, place a
   known 100 g mass, set `CALIBRATION_FACTOR` until it reads 100.0 ± 2 g.
4. Send `{"cmd":"tare"}` before every mission.

---

## 4. First integration (rover + laptop, no testbed yet)

1. Power the rover (battery → switch → buck → ESP32; Pi on its own PSU).
2. Connect the rover's ESP32 to the laptop by USB. Note the port
   (Windows: `COM5` in Device Manager; Linux: `/dev/ttyUSB0`).
3. If you built the station node, connect it on a second USB port.
4. Launch the dashboard, switch **Mode → REAL ROVER**, set the port(s),
   Camera = `-1` for now (camera comes later), press **LAUNCH**.
5. The map starts **blank** — this is correct: the rover knows nothing.
6. Lift the rover and move it slowly by hand:
   - the white triangle **tracks your motion** (pose),
   - the battery tile shows the **real** voltage/energy,
   - hold your hand in front of the ToF: the tile shows the range and a
     blocked blob appears on the map after the rover tries to drive there.
7. Click **ABORT** → motors stop immediately (also the 600 ms serial
   watchdog does this if the link dies).

**Definition of done:** the twin tracks hand-movement within a few cm and
the ToF tile reacts to your hand. This proves the whole real-time chain.

---

## 5. Calibration (one session, ~2 hours — makes the sim match reality)

Do these in order; each writes a number into `astra/config.py`:

| # | What | How | Config field |
|---|---|---|---|
| 1 | **Wheel/encoder scale** | mark a 2 m line, command `v=0.1` straight, measure actual distance `d` vs reported `x`. Divide firmware `WHEEL_RADIUS_M` by (reported/actual) if off by >5 % | firmware `WHEEL_RADIUS_M` |
| 2 | **Gyro heading** | rotate the rover 360° on the floor, reported heading should return to ~0°. Small drift is OK (encoder fusion compensates) | — (auto bias at boot) |
| 3 | **Energy per metre** | run 3 straight 2 m runs, read `wh` from telemetry: Wh/m = Δwh / 2 m. Update `RoverConfig.motor_power_w` / `rol_cost` until the SIM reports the same Wh/m | `RoverConfig` |
| 4 | **Base power draw** | rover idle (motors off), read `cur` × `vbat` on telemetry → watts → `base_power_w` | `RoverConfig.base_power_w` |
| 5 | **Scoop rate** | run `collect 10 s` over a pile, weigh the collected mass → g/s → `scoop_rate_gps` | `RoverConfig.scoop_rate_gps` |
| 6 | **Camera geometry** | place a marker 30 cm ahead / 10 cm left of the rover; click that spot on the dashboard map; adjust `vision/live.py` constants until detections land on the right cells | `FRAME_BOTTOM_DEPTH_M`, `PX_PER_M_LATERAL` |
| 7 | **ToF block threshold** | find the smallest real gap your rover fits through; keep `TOF_BLOCK_M` slightly below it (default 0.22 m) | `real_rover.TOF_BLOCK_M` |

**Definition of done:** a 2 m sim run and a 2 m real run agree on Wh within
~15 %, and odometry error over 2 m is < 10 cm.

---

## 6. Testbed day: the first REAL autonomous mission

**Safety checklist (read aloud with the team):**
- [ ] rover on the floor, wheels off the ground for the first LAUNCH
- [ ] everyone knows where ABORT is (browser button + unplug = kill)
- [ ] Li-ion pack charged, balanced, inspected; fuse inline
- [ ] camera mast tight, nothing hanging into the wheels
- [ ] testbed border stops the rover physically if it escapes

**Mission procedure:**
1. Lay out the testbed (docs/03 §7): simulant, rocks, and the **rust-orange
   marker pebbles** on ~4–5 zones (they simulate the resource signature).
2. Place the rover at the start point, pointing "east" (+x). Both USB cables
   to the laptop. Tare the station scale.
3. Dashboard → REAL ROVER → ports → LAUNCH.
4. Watch the twin: SURVEY (rover drives the frontier) → SELECT (the decision
   panel shows the score!) → NAVIGATE → MINE → RETURN → grams appear.
5. While it surveys, **click the map over each marker zone** — that's
   operator cueing (the stand-in for orbiter imagery; the camera does the
   same job automatically once calibrated).
6. After the run: Mission Event Log + measured grams = your report data.
   The ESP32's integrated `wh` is the energy denominator of g/Wh.

**If the AI fails:** switch strategy to `nearest`, or drive manually from
the bench with `{"cmd":"vel",...}` — always keep the demo alive.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Dashboard says busy | a previous mission thread is alive | close the tab, restart server |
| No telemetry, rover silent | wrong COM port / baud | Device Manager; 115200 |
| Wheels don't move but telemetry flows | TB6612 `STBY` low or VM unpowered | check docs/03 §2 |
| Rover veers | one motor reversed / uneven wheels | swap that motor's AINx pair |
| Pose drifts badly | encoder slipping or wheel radius wrong | calibration step 1 |
| `"h"` spins when driving straight | gyro sign / axis swapped | rotate the MPU-6050 90°, re-flash |
| `dist` always -1 | VL53L0X not detected | check I2C address 0x29, wiring |
| `bump` fires constantly | stall threshold too tight for your soil | increase firmware `0.6f` |
| g/Wh wildly off | energy model not calibrated | section 5, steps 3–4 |
| Camera detections nowhere near markers | geometry not calibrated | section 5, step 6 |
| Pi Wi-Fi dashboard laggy | run the server on the Pi, browser on laptop, same network | `http://raspberrypi:8000` |

---

## 8. Where each piece lives

| Piece | File |
|---|---|
| Rover firmware (motors, sensors, failsafes) | `firmware/esp32_rover/esp32_rover.ino` |
| Station firmware (load cell) | `firmware/station_node/station_node.ino` |
| Serial link + telemetry + ToF map marking | `software/astra/hal/real_rover.py` |
| Camera perception thread | `software/astra/vision/live.py` |
| Marker detector (HSV / YOLO) | `software/astra/vision/detector.py` |
| Real-mode mission loop + operator cueing | `software/astra/dashboard/server.py` |
| All physical constants to calibrate | `software/astra/config.py` |
| Tests that verify all of this WITHOUT hardware | `software/tests/test_real_rover.py`, `tests/test_real_world.py` |
