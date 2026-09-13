# ASTRA-MINE — Hardware Bill of Materials

Two buying batches protect your budget: **Batch 1 proves mobility**, Batch 2
adds intelligence. Prices are Indicative Indian-market ranges (Robu/
Robocraze/local electronics shops, 2026) — treat as engineering estimates.

## Batch 1 — Mobility core (~₹11,500 – ₹16,500)

| # | Item | Spec to ask for | Qty | Est. price | Why / notes |
|---|------|-----------------|-----|-----------|-------------|
| 1 | Chassis kit | 4WD acrylic/metal, ≥ 20×20 cm deck, aluminium motor mounts | 1 | ₹800–₹2,000 | mount Pi + mast later; bigger deck = easier wiring |
| 2 | Geared DC motors | 12 V, 200–300 RPM, high torque (e.g. 37 mm 25GA-370 or Johnson 300 RPM) | 4 | ₹1,600–₹3,200 | slow + torquey = terrain stability; do NOT use yellow TT motors for load |
| 3 | Wheels | 65–80 mm rubber tyres | 4 | ₹400–₹800 | match `config.RoverConfig.wheel_radius_m` |
| 4 | Motor driver | **TB6612FNG** (1 A/ch) or L298N (2 A, lossy) | 1–2 | ₹120–₹350 | TB6612 preferred: efficient, low heat |
| 5 | ESP32 dev board | ESP32-WROOM-32 DevKit V1 (38-pin) | 1 | ₹350–₹500 | the real-time controller |
| 6 | Wheel encoders | magnetic encoder kits / GP2A slotted sensors + encoder discs | 2 | ₹200–₹600 | odometry + energy model input |
| 7 | Battery | 3S 18650 pack (11.1 V) ≥ 3000 mAh **with BMS**, or 3S LiPo 3300 mAh | 1 | ₹900–₹1,800 | run-time + safety; never LiPo without BMS/balance |
| 8 | Battery holder + fuse + switch | inline fuse 5 A, rocker switch, XT60 connectors | 1 | ₹250–₹500 | safety basics |
| 9 | Buck converter | LM2596 / MP1584 5 V 3 A (set BEFORE connecting) | 1–2 | ₹150–₹300 | 5 V rail for ESP32 + servo |
| 10 | Wires, connectors, heatshrink | 22 AWG silicone wire, Dupont, crimps | 1 lot | ₹400–₹800 | — |
| 11 | Misc hardware | standoffs, nuts/bolts, double-tape, zip ties | 1 lot | ₹300–₹500 | — |

## Batch 2 — Intelligence + perception (~₹17,000 – ₹26,000)

| # | Item | Spec | Qty | Est. price | Why / notes |
|---|------|------|-----|-----------|-------------|
| 12 | Raspberry Pi 5 | 4 GB kit (PSU + SD + case) | 1 | ₹7,500–₹10,500 | the AI "brain"; 8 GB if you train YOLO on it |
| 13 | Pi camera | Pi Camera Module 3 or cheap IMX219 clone | 1 | ₹400–₹2,500 | top-down perception on a mast |
| 14 | Camera mount mast | 20–30 cm aluminium standoffs | 1 | ₹200–₹400 | look-ahead view of ground |
| 15 | IMU | MPU-6050 (GY-521) | 1 | ₹120–₹250 | heading fusion, tilt protection |
| 16 | Power monitor | INA219 module | 1 | ₹150–₹300 | **the g/Wh metric depends on this** |
| 17 | ToF distance sensor | VL53L0X | 1–2 | ₹250–₹600 | forward obstacle stop (beyond camera FOV) |
| 18 | Scoop servo | MG996R metal gear (or 2× SG90) | 1 | ₹250–₹500 | collection mechanism |
| 19 | Scoop mechanism | small bucket/conveyor + aluminium sheet + servo linkage | DIY | ₹500–₹1,500 | keep it SIMPLE: scoop that works > excavator that jams |
| 20 | Optional: LiDAR | RPLidar A1 / EAI X4 | 1 | ₹4,500–₹9,000 | only if budget allows; NOT required |
| 21 | Optional: load cell | HX711 + 1–5 kg load cell | 1 | ₹250–₹500 | station weight reporting (great demo) |
| 22 | Optional: second ESP32 | station telemetry | 1 | ₹350–₹500 | streams load-cell grams to dashboard |

## Testbed — the "Moon" (~₹3,000 – ₹7,000)

| Item | Spec | Est. price |
|---|---|---|
| Frame | wooden sandbox 3 m × 3 m, edges 15 cm high (or tarpaulin border) | ₹1,000–₹2,500 |
| Regolith simulant | fine crusher dust / plaster sand + coco peat mix (document your mix!) | ₹800–₹2,000 |
| Rocks | assorted stones 5–12 cm | ₹0 (free) |
| Craters | shaped mounds/dips, pre-formed and documented | — |
| **Resource markers** | iron-oxide (rust) coloured gravel ~5–10 kg — the visual proxy the camera detects | ₹600–₹1,500 |
| Ground-truth kit | kitchen scale (0.1 g), measuring cups, marker cones | ₹600–₹1,000 |

**Rule:** document the testbed layout per experiment run (photos + sketch +
seeded digital twin) so simulations and hardware runs are comparable.

## Totals

| Scope | Budget |
|---|---|
| Basic (Batch 1 only + minimal testbed, sim-first demo) | **₹15,000 – ₹24,000** |
| Recommended (Batch 1 + 2 + testbed) | **₹32,000 – ₹50,000** |
| Advanced (adds LiDAR + load cell + spares) | ₹55,000 – ₹65,000 |

## What NOT to buy

- ❌ Vacuum chamber, real regolith simulants from NASA-grade suppliers
- ❌ Electrolysis / hydrogen equipment (the ISRU stage is **modelled**)
- ❌ GPU (YOLO-nano trains fine on laptop CPU for this dataset size)
- ❌ 6-wheel rocker-bogie (cool, but eats budget; 4WD is enough)
- ❌ Zigbee/LoRa radio (Pi + laptop on the same Wi-Fi is plenty indoors)

## Safety notes

- Li-ion/LiPo: BMS mandatory, charge unattended never, fuse everything.
- Set the buck converter output **before** connecting any 5 V device.
- Common ground between battery, ESP32, Pi and servo rails — always.
- Manual e-stop (the switch) within reach during every autonomous run.
