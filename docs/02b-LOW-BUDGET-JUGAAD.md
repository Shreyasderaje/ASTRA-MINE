# ASTRA-MINE — Low-Budget "Jugaad" Build (₹5k–₹9k)

Same project. Same science. Same code. Fewer rupees.
This is the alternate BOM for teams building on a student budget. Every swap
below keeps the software 100% compatible — you are trading comfort and polish,
never the research contribution (the g/Wh metric and the decision-making loop
stay intact).

**The golden rule of jugaad:** spend money only on what generates your DATA
(sensors that produce the report's numbers), save on everything that carries,
holds, or looks nice.

---

## The swap table

| # | Original (docs/02) | ₹ | Jugaad version | ₹ | Trade-off you accept |
|---|---|---|---|---|---|
| 1 | Raspberry Pi 5 kit | 7,500–10,500 | **Raspberry Pi Zero 2 W** (or used Pi 3B+) | 1,800–2,500 | Vision runs at 2–5 FPS (fine — rover moves 0.12 m/s!). Train YOLO on a laptop, deploy the light HSV detector on the Pi. Same code, same ports. |
| 2 | — (brain on rover) | — | **or zero Pi at all: ESP32-CAM (₹450) streams frames over Wi-Fi, your LAPTOP runs the brain + dashboard** | 450–600 | Laptop must be on the same Wi-Fi during demos. Tiny transport adapter needed (TCP instead of serial). |
| 3 | Pi Camera Module 3 | 400–2,500 | Old USB webcam from home / cheapest clone | 0–400 | Slightly worse optics; HSV detector is tuned at calibration anyway |
| 4 | 37mm geared motors ×4 | 1,600–3,200 | **BO 300 RPM motors ×4** (rover must stay < 1.5 kg) | 500–800 | Less torque → gentler craters, lighter chassis, no slopes > 10° |
| 5 | Chassis kit + wheels | 1,200–2,800 | 6 mm plywood / PVC sheet + toy wheels + peanut-butter-lid hubs | 300–600 | Ugly is fine. Balanced and rigid is not optional. |
| 6 | TB6612FNG | 120–350 | **L298N** (the red one, every shop has it) | 120 | ~2 V drop → slightly less runtime. Zero code change. |
| 7 | Magnetic encoders | 200–600 | **IR slotted sensor + printed paper encoder discs** (print the disc, tape it to the wheel) | 100–200 | Paper discs wear — carry spares. Odometry accuracy is still fine. |
| 8 | 3S Li-ion pack + BMS | 900–1,800 | **Old UPS 12 V 7 Ah battery (free from any dead UPS)** — heavy but safe and free | 0–150 | +1 kg mass. Charge with the UPS's own charger. OR reclaimed laptop 18650s **only if** every cell tests ≥ 3.7 V and you use a BMS — never skip that. |
| 9 | Buck converter | 150–300 | Old phone charger (5 V) for the ESP32 rail | 0–80 | Needs a socket glued to the chassis — fine |
| 10 | VL53L0X ToF | 250–600 | **HC-SR04 ultrasonic (₹60)** — or SKIP it in v1: the firmware already detects stalls ("bump") and the escape maneuver un-wedges the rover | 0–60 | Ultrasonic needs a small firmware patch (10 lines — ask ZCode). Skipping it means the map discovers rocks more slowly; slow speed keeps you safe. |
| 11 | MG996R servo + fabricated scoop | 750–2,000 | SG90 (₹100) + scoop bent from an aluminium sheet / plastic container | 200–350 | SG90 is weaker — scoop narrower, collect slower. Same demonstration. |
| 12 | Processing station (2nd ESP32 + HX711) | 600–1,000 | **Mama's kitchen weighing scale** — weigh the bin after each delivery, type the grams into the mission log | 0 | Manual measurement — still honest if you log it as manual. (HX711 is only ₹350 if budget allows later.) |
| 13 | Testbed (framed sandbox) | 1,000–2,500 | Tarpaulin + wooden edge strips; crusher dust **free** from a construction site (ask the engineer nicely); rocks free; resource markers = pebbles sprayed rust-orange (₹60 paint) | 300–600 | Rebuild it flat before each demo — that's it |
| 14 | Wires, connectors, misc | 400–800 | Salvaged DuPont wires, tape, solder from college lab | 150–300 | — |

## The two things you do NOT cut

1. **INA219 (₹150)** — it measures the Wh that your entire headline metric
   (g/Wh) is built on. A voltage divider + ACS712 (₹100) is the desperate
   fallback, but the INA219 is too cheap to skip.
2. **Battery safety (BMS + fuse)** — a ₹150 BMS and a ₹20 fuse protect a
   ₹0 budget from becoming a ₹0 rover and a burnt hostel room. Never
   charge reclaimed cells unattended.

## The resulting budget

| Variant | Total | What you get |
|---|---|---|
| **Full jugaad** (UPS battery, laptop-brain option, manual scale) | **₹5,000 – 7,000** | everything demonstrated, vision on laptop |
| **Comfortable jugaad** (Pi Zero 2 W, UPS battery, HC-SR04) | **₹7,000 – 9,000** | autonomous vision on the rover itself |
| Safe-no-scrap battery (new 3S pack added to either) | + ₹900 | better sleep at night |

Compare: the recommended build in docs/02 is ₹35k–50k. **You are running the
same experiments, the same AI, the same digital twin for ~15–20% of the cost.**

## What you lose (say it in the report, it's a strength)

- FPS and polish, not science: lower camera framerate, heavier rover, uglier
  chassis.
- Your viva answer: *"We consciously moved budget from comfort to sensing,
  because the research metric is grams-per-watt-hour — and frugal engineering
  is exactly what real planetary programs practice."*
  (ISRO's Mangalyaan cost less than a Hollywood movie about Mars. Say that.)
