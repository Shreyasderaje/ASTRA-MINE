# ASTRA-MINE — Assembly, Wiring & Bring-Up

## 1. Power architecture (build this first, alone, before anything else)

```
 3S Li-ion pack (11.1 V)
   │
   ├── inline 5 A fuse ── rocker switch ──┬── TB6612 VM  (motors)
   │                                      │
   │                                      └── Buck #1 (set 5.0 V) ──┬── ESP32 5V/VIN
   │                                                                └── Servo rail (+)
   │
   └── (separate, recommended) 5 V/5 A supply or official PSU ── Raspberry Pi 5

  ALL GROUNDS COMMON:  battery − = driver GND = buck GND = ESP32 GND = Pi GND = servo −
```

Rules:
- Set and **measure** the buck output before connecting anything.
- The servo gets its own thick 5 V feed — never power it from the ESP32 3V3.
- The Pi is powered from its own supply (brownouts corrupt SD cards).

## 2. ESP32 ↔ TB6612FNG pin map (matches `firmware/esp32_rover.ino`)

| TB6612 pin | ESP32 GPIO | Function |
|---|---|---|
| PWMA | 14 | left motors PWM (2 motors in parallel) |
| AIN1 | 13 | left direction |
| AIN2 | 12 | left direction |
| PWMB | 25 | right motors PWM |
| BIN1 | 27 | right direction |
| BIN2 | 26 | right direction |
| STBY | 33 | driver enable (HIGH = on) |
| VM | battery + (after switch) | motor power |
| VCC | 5 V (buck) | logic power |
| GND | common GND | — |

L298N alternative: IN1→13, IN2→12, ENA→14 (jumper removed), IN3→27, IN4→26,
ENB→25, 12V→battery, 5V rail from its onboard regulator (jumper on) — less
efficient, runs hot, but works.

## 3. Sensors

| Device | ESP32 pins | Bus / notes |
|---|---|---|
| MPU-6050 (GY-521) | SDA→21, SCL→22, VCC 3V3, GND | I2C 0x68, AD0→GND |
| INA219 | SDA→21, SCL→22 (shared bus) | I2C 0x40; Vin+ in SERIES with battery + ; Vin− to load |
| **VL53L0X ToF** | SDA→21, SCL→22 (shared bus) | I2C 0x29; front-facing at the rover nose, level with the bumper; feeds the `"dist"` telemetry field (live rock discovery) |
| Encoder left | out→34 | input-only pin, needs pull-up if open collector |
| Encoder right | out→35 | same |
| Scoop servo | signal→32 | power from 5 V servo rail, common GND |

> Only ONE device may drive each I2C address. MPU-6050 (0x68) + INA219 (0x40)
> + VL53L0X (0x29) coexist fine on the same two wires.

### 3b. Processing station node (optional, strongly recommended)

A second ESP32 + HX711 + 1–5 kg load cell under the collection bin:

| Connection | Pin |
|---|---|
| HX711 DT | GPIO 16 |
| HX711 SCK | GPIO 4 |
| HX711 VCC / GND | 3V3 / GND |
| Load cell E+ / E− / A+ / A− | red / black / white / green |

Firmware: `firmware/station_node/station_node.ino` — streams `{"g":grams}`
every 200 ms on its own USB serial link. The dashboard's REAL ROVER mode
takes the station's port in the **Station port** field; deliveries are then
**measured**, not estimated (docs/06 §5). Calibrate with a known 100 g mass
before first use.

## 4. Pi 5 connections

- Camera → CSI ribbon (top-down mast, aiming 0.5–1.2 m ahead of the rover).
- ESP32 USB-C → Pi USB (this is the `RealRoverHAL` serial link, `/dev/ttyACM0`).
- Pi joins the same Wi-Fi as the Mission Control laptop (dashboard runs on
  the Pi itself or remotely — the WebSocket makes it location-agnostic).

## 5. Mechanical build order (2–3 sessions)

1. **Drivetrain:** motors → chassis, wheels on, encoders + discs aligned
   (0.5–1 mm gap). Spin each wheel by hand: encoder should pulse cleanly.
2. **Power:** mount battery low & centered, fuse + switch reachable,
   buck set to 5.0 V, wire common ground bus (a small terminal block helps).
3. **Driver + ESP32:** wire per tables above, standoffs, label every wire
   with tape flags — future-you during debugging will thank present-you.
4. **Mast + camera:** mast at the FRONT edge, tilted slightly forward
   (top-down at 0.8–1.2 m ground coverage ≈ 0.9 m frame width — this matches
   `detector.frame_resource_score()`).
5. **Scoop:** front servo + simple bucket that rotates down into the soil and
   back up over a hopper. Add a 3D-printed or sheet-metal lip. DO NOT build a
   bucket-drum excavator — that's NASA IPEx's specialty, not yours.

## 6. Bring-up sequence (never skip steps)

| Step | Test | Pass criterion |
|---|---|---|
| B1 | Continuity: every GND common, no shorts | multimeter beep test |
| B2 | Buck at 5.00 V before load | measured |
| B3 | ESP32 boots, telemetry at 10 Hz | serial monitor JSON lines |
| B4 | Wheels off ground: `{"cmd":"vel","v":0.1,"w":0}` — both sides forward | direction correct |
| B5 | `w` test: turn left/right in place | correct directions |
| B6 | Encoders: drive 1 m, compare `x` telemetry | error < 5% |
| B7 | INA219: `wh` increases when driving | plausible W values |
| B8 | Tilt: lift nose > 35° → motors stop | failsafe fires |
| B9 | Watchdog: send vel, then silence → rover stops within 0.6 s | failsafe fires |
| B10 | Pi ↔ ESP32 serial via `RealRoverHAL`, drive from Python | waypoint reached |

## 7. Testbed construction

1. Mark a 3 m × 3 m area; frame it or tape a tarp border.
2. Lay 2–3 cm of your documented simulant mix; pre-form 5 craters
   (gentle! ≤ 10° slopes), scatter 20–30 rocks (document positions).
3. Place 4–5 resource zones: mix rust-coloured gravel into the top layer,
   weigh and record the exact grams per zone (ground truth!).
4. Fix the processing station at the map corner (0.25, 0.25) m.
5. Photograph everything top-down with a scale bar → this becomes your
   digital-twin calibration reference (`config.WorldConfig`).
