"""ASTRA-MINE project presentation builder - 15 slides, dark space theme.

Team SUDARSHAN | SPPN Space Research Team
Run:  python build_deck.py   ->   ASTRA-MINE_SUDARSHAN.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

# ---------------------------------------------------------------- design system
BG     = RGBColor.from_string("0A1120")   # deep space navy (dominant)
PANEL  = RGBColor.from_string("101A30")   # card surface
PANEL2 = RGBColor.from_string("0D1730")   # deeper card
LINE   = RGBColor.from_string("1D2C4D")   # hairline
PRIMARY= RGBColor.from_string("29D3FF")   # cyan (brand)
ACCENT = RGBColor.from_string("FFB03A")   # amber (sparingly)
TEXT   = RGBColor.from_string("D8E4FF")
MUTED  = RGBColor.from_string("6D82AD")
GREEN  = RGBColor.from_string("3DDC84")
RED    = RGBColor.from_string("FF5470")
WHITE  = RGBColor.from_string("FFFFFF")

F  = "Segoe UI"
FM = "Consolas"
W, H, M = 13.333, 7.5, 0.55

def blend(c1, c2, t):
    """c1 over c2 with opacity t (0..1) - both RGBColor."""
    return RGBColor(*[int(round(a * t + b * (1 - t))) for a, b in zip(c1, c2)])

GREEN_T = blend(GREEN, BG, 0.30)
CYAN_T  = blend(PRIMARY, BG, 0.16)
AMBER_T = blend(ACCENT, BG, 0.16)

prs = Presentation()
prs.slide_width  = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]
prs.core_properties.title = "ASTRA-MINE - SUDARSHAN | SPPN Space Research Team"
prs.core_properties.author = "SPPN Space Research Team"

def slide_new():
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid(); r.fill.fore_color.rgb = BG
    r.line.fill.background(); r.shadow.inherit = False
    return s

def box(s, x, y, w, h, fill=PANEL, line=LINE, radius=0.055, line_w=0.75):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try: sh.adjustments[0] = radius
    except Exception: pass
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    return sh

def rect(s, x, y, w, h, fill, line=None):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    return sh

def txt(s, x, y, w, h, runs, size=14, color=TEXT, bold=False, italic=False,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=F, spacing=None,
        space_after=None, wrap=True):
    """runs: str, or list of (text, overrides) tuples; '\n' splits paragraphs."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(runs, str):
        runs = [(runs, {})]
    paras = [[]]
    for text, o in runs:
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if i > 0: paras.append([])
            if part: paras[-1].append((part, o))
    first = True
    for para_runs in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        if spacing: p.line_spacing = spacing
        if space_after is not None: p.space_after = Pt(space_after)
        if not para_runs:
            continue
        for text, o in para_runs:
            r = p.add_run(); r.text = text
            r.font.name = o.get("font", font)
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.italic = o.get("italic", italic)
            r.font.color.rgb = o.get("color", color)
    return tb

def kicker(s, text, x=M, y=0.40):
    txt(s, x, y, 10.5, 0.3, text.upper(), size=11, color=PRIMARY, bold=True)
    # letter-spacing feel: use spaced text
def title(s, text, x=M, y=0.70, size=30, color=WHITE, w=None):
    txt(s, x, y, w or (W - 2 * M), 0.62, text, size=size, color=color, bold=True)

def footer(s, n):
    txt(s, M, H - 0.42, 6, 0.25, "ASTRA-MINE  ·  SUDARSHAN — SPPN Space Research Team",
        size=9, color=MUTED)
    txt(s, W - 1.2, H - 0.42, 0.65, 0.25, f"{n:02d}", size=9, color=MUTED, align=PP_ALIGN.RIGHT)

def chip(s, x, y, w, text, fill=PANEL, color=TEXT, size=10.5, h=0.34, line=LINE):
    box(s, x, y, w, h, fill=fill, line=line, radius=0.5)
    txt(s, x, y + 0.015, w, h, text, size=size, color=color, bold=True,
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

def arrow(s, x, y, w=0.30, h=0.22, color=PRIMARY):
    sh = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = color
    sh.line.fill.background(); sh.shadow.inherit = False
    return sh

def ring(s, cx, cy, d, color=LINE, w=1.2):
    sh = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - d/2), Inches(cy - d/2), Inches(d), Inches(d))
    sh.fill.background(); sh.line.color.rgb = color; sh.line.width = Pt(w)
    sh.shadow.inherit = False
    return sh

# ============================================================ 1 · TITLE
s = slide_new()
ring(s, 12.4, 1.1, 4.6); ring(s, 12.4, 1.1, 3.4, color=blend(LINE, BG, 0.5))
ring(s, 12.4, 1.1, 2.2); ring(s, 12.4, 1.1, 0.10, color=PRIMARY, w=6)
txt(s, M, 1.10, 9.5, 0.35, "S U D A R S H A N   ·   S P P N   S P A C E   R E S E A R C H   T E A M",
    size=12, color=PRIMARY, bold=True)
txt(s, M, 1.55, 11.5, 1.3, "ASTRA-MINE", size=66, color=WHITE, bold=True)
txt(s, M, 2.85, 11.0, 0.75,
    "Autonomous AI-Driven Extraterrestrial Resource Prospecting & ISRU Demonstrator",
    size=17, color=TEXT)
txt(s, M, 3.62, 10.0, 0.4, "\u201cMine the resource. Optimize the mission. Build the future.\u201d",
    size=14, color=ACCENT, italic=True)
chips = ["AI", "ROBOTICS", "EMBEDDED SYSTEMS", "SPACE TECHNOLOGY", "RESEARCH"]
cw = [1.15, 1.75, 2.6, 2.6, 1.7]
cx = M
for t, w in zip(chips, cw):
    chip(s, cx, 4.55, w, t, size=10.5); cx += w + 0.22
rect(s, M, 5.55, 2.2, 0.02, LINE)
txt(s, M, 5.75, 8, 0.35, "Mini-Project Presentation  ·  2026", size=12, color=MUTED)
txt(s, M, 6.75, 11, 0.3, "github.com/Shreyasderaje/ASTRA-MINE", size=11, color=MUTED)

# ============================================================ 2 · OBJECTIVES
s = slide_new(); kicker(s, "What we set out to do"); title(s, "Objectives")
footer(s, 2)
objs = [
    ("01", "Build an autonomous rover", "4-wheel prototype with AI 'brain' (Raspberry Pi 5) and real-time 'reflexes' (ESP32) on a 3 m lunar-analogue testbed"),
    ("02", "Map buried resources with AI", "Camera-proxy perception fused into a live resource-probability map of unknown terrain"),
    ("03", "Decide where to mine", "Resource-energy-risk target selection - the rover computes the best site per unit of energy"),
    ("04", "Close the autonomous loop", "Survey \u2192 decide \u2192 navigate \u2192 mine \u2192 return \u2192 deliver, with self re-planning"),
    ("05", "Benchmark the decision making", "Four strategies compared on identical terrain: resource yield per watt-hour (g/Wh)"),
    ("06", "Command it like a mission", "Live Mission Control digital twin streaming pose, battery, decisions and yields"),
]
gx, gy, gw, gh = M, 1.62, 5.98, 1.62
for i, (num, head, body) in enumerate(objs):
    x = gx + (i % 2) * (gw + 0.24); y = gy + (i // 2) * (gh + 0.20)
    box(s, x, y, gw, gh, fill=PANEL)
    txt(s, x + 0.25, y + 0.16, 1.0, 0.8, num, size=30, color=PRIMARY, bold=True)
    txt(s, x + 1.05, y + 0.18, gw - 1.3, 0.35, head, size=15, color=WHITE, bold=True)
    txt(s, x + 1.05, y + 0.55, gw - 1.3, 0.95, body, size=11.5, color=MUTED, spacing=1.08)

# ============================================================ 3 · PURPOSE
s = slide_new(); kicker(s, "Why this project exists"); title(s, "The Purpose")
footer(s, 3)
txt(s, M, 1.55, 12.2, 0.9,
    [("Every kilogram launched from Earth costs ", {}),
     ("thousands of dollars", {"color": ACCENT, "bold": True}),
     (" \u2014 and a lunar base needs water, oxygen and building material forever.", {})],
    size=19, color=TEXT, spacing=1.15)
# left chain: Earth logistics
box(s, M, 2.85, 5.9, 3.35, fill=PANEL2)
txt(s, M + 0.3, 3.05, 5.3, 0.3, "THE EARTH-SUPPLY PROBLEM", size=11, color=RED, bold=True)
chain = ["Launch everything from Earth", "Pay per kilogram, every mission",
         "No resupply independence", "Not scalable for a lunar economy"]
yy = 3.5
for step in chain:
    txt(s, M + 0.3, yy, 0.35, 0.3, "\u2715", size=13, color=RED, bold=True)
    txt(s, M + 0.68, yy + 0.02, 4.9, 0.35, step, size=13.5, color=TEXT)
    yy += 0.48
txt(s, M + 0.3, 5.55, 5.3, 0.5, "In-Situ Resource Utilization (ISRU) is NASA & ESA's active answer \u2014 use what is already there.",
    size=11.5, color=MUTED, spacing=1.1)
# right chain: ISRU
box(s, M + 6.2, 2.85, 6.05, 3.35, fill=PANEL)
txt(s, M + 6.5, 3.05, 5.4, 0.3, "THE ISRU CHAIN \u2014 WHAT ASTRA-MINE DEMONSTRATES", size=11, color=GREEN, bold=True)
chain2 = ["Find the resource (prospecting)", "Decide if it is worth the trip",
          "Extract and carry it", "Process \u2192 estimate usable yield"]
yy = 3.5
for step in chain2:
    txt(s, M + 6.5, yy, 0.35, 0.3, "\u2713", size=13, color=GREEN, bold=True)
    txt(s, M + 6.88, yy + 0.02, 5.1, 0.35, step, size=13.5, color=TEXT)
    yy += 0.48
txt(s, M + 6.5, 5.55, 5.5, 0.5, "Water near the lunar poles can even become rocket propellant \u2014 energy in space buys more missions.",
    size=11.5, color=MUTED, spacing=1.1)
txt(s, M, 6.45, 12.2, 0.5,
    [("Our purpose: ", {"bold": True, "color": WHITE}),
     ("build and measure the decision intelligence such a mining system would need \u2014 at student scale, with real hardware.", {})],
    size=13.5, color=TEXT)

# ============================================================ 4 · APPLICATIONS
s = slide_new(); kicker(s, "Where this technology lands"); title(s, "Uses & Applications")
footer(s, 4)
apps = [
    ("Planetary & surface robotics", "Lunar/Mars prospecting rovers; the same loop flies on future ISRU missions"),
    ("Autonomous mining", "Self-directed haul & dig decisions that optimize yield per litre of fuel"),
    ("Disaster response", "Robots that map rubble, find victims' zones and ration battery autonomy"),
    ("Unknown-terrain exploration", "Caves, tunnels, poles, ocean floors \u2014 anywhere GPS and maps do not exist"),
    ("Hazardous-site inspection", "Nuclear, chemical and deep-industrial sites where humans should not walk"),
    ("Precision agriculture", "Soil-sensing scouts that decide where sampling pays off per unit energy"),
]
gx, gy, gw, gh = M, 1.75, 3.94, 2.15
for i, (head, body) in enumerate(apps):
    x = gx + (i % 3) * (gw + 0.205); y = gy + (i // 3) * (gh + 0.24)
    box(s, x, y, gw, gh, fill=PANEL)
    txt(s, x + 0.24, y + 0.22, 0.5, 0.45, f"{i+1}", size=22, color=PRIMARY, bold=True)
    txt(s, x + 0.24, y + 0.78, gw - 0.48, 0.6, head, size=14.5, color=WHITE, bold=True, spacing=1.0)
    txt(s, x + 0.24, y + 1.38, gw - 0.48, 0.68, body, size=11, color=MUTED, spacing=1.1)
txt(s, M, 6.5, 12.2, 0.4,
    "One architecture \u2014 sense \u2192 believe \u2192 decide \u2192 act \u2014 transfers to every one of these domains.",
    size=13, color=TEXT, italic=True)

# ============================================================ 5 · LIMITS & ENVIRONMENT
s = slide_new(); kicker(s, "Honest engineering"); title(s, "Limitations & Environmental Impact")
footer(s, 5)
box(s, M, 1.7, 6.0, 4.6, fill=PANEL2)
txt(s, M + 0.3, 1.95, 5.4, 0.35, "HONEST LIMITATIONS", size=12, color=ACCENT, bold=True)
lims = [
    ("Terrestrial analogue", "we demonstrate the intelligence on proxy markers \u2014 not real lunar ice"),
    ("Proxy sensing", "colour-marked simulant stands in for spectral detection (future work: NIR)"),
    ("Odometry-only localization", "encoders + IMU drift a few %; no SLAM yet"),
    ("Small, self-made dataset", "vision model is trained on our own synthetic + testbed data"),
    ("Prototype-scale energy model", "calibrated to \u224815% on the testbed, not flight-grade"),
]
yy = 2.42
for head, body in lims:
    txt(s, M + 0.3, yy, 5.45, 0.30, head, size=13, color=WHITE, bold=True)
    txt(s, M + 0.3, yy + 0.30, 5.45, 0.45, body, size=11.5, color=MUTED, spacing=1.05)
    yy += 0.78
box(s, M + 6.25, 1.7, 6.0, 4.6, fill=PANEL)
txt(s, M + 6.55, 1.95, 5.4, 0.35, "ENVIRONMENTAL RESPONSIBILITY", size=12, color=GREEN, bold=True)
envs = [
    ("No real chemistry", "water \u2192 propellant is a modelled pathway; we never produce or store H\u2082/O\u2082"),
    ("No planetary contamination", "everything happens in an indoor sand testbed \u2014 the Moon stays untouched"),
    ("Reusable standard parts", "COTS electronics chosen for re-use across semesters \u2192 minimal e-waste"),
    ("Battery stewardship", "sealed Li-ion pack with BMS; retired cells routed to e-waste recycling"),
    ("Tiny energy footprint", "\u224840 Wh per mission \u2014 less than a laptop hour"),
]
yy = 2.42
for head, body in envs:
    txt(s, M + 6.55, yy, 5.45, 0.30, head, size=13, color=WHITE, bold=True)
    txt(s, M + 6.55, yy + 0.30, 5.45, 0.45, body, size=11.5, color=MUTED, spacing=1.05)
    yy += 0.78
txt(s, M, 6.55, 12.2, 0.4, "We say these out loud \u2014 scope honesty is part of the engineering.",
    size=12.5, color=TEXT, italic=True)

# ============================================================ 6 · SOFTWARE
s = slide_new(); kicker(s, "The brain \u2014 identical in simulation & on the rover"); title(s, "Software Architecture")
footer(s, 6)
flow = [("CAMERA +\nTOF", "sensing"), ("PERCEPTION", "OpenCV proxy"), ("BELIEF\nMAP", "probability"),
        ("MISSION\nOPTIMIZER", "score sites"), ("A* PLANNER", "energy + risk"), ("MISSION\nFSM", "state machine")]
bx, by, bw, bh, gap = M, 2.15, 1.78, 1.05, 0.32
for i, (name, sub) in enumerate(flow):
    x = bx + i * (bw + gap)
    box(s, x, by, bw, bh, fill=PANEL, line=PRIMARY if i in (2, 3) else LINE)
    txt(s, x, by + 0.16, bw, 0.55, name.replace("\n", " "), size=12.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER, spacing=0.95)
    txt(s, x, by + 0.72, bw, 0.25, sub, size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
    if i < len(flow) - 1:
        arrow(s, x + bw + 0.045, by + bh/2 - 0.10, 0.23, 0.20, color=PRIMARY)
# feedback loop line
txt(s, bx, by + 1.22, 11.6, 0.3, "\u25C0  closed loop: every delivery re-scores every remaining target  \u25C0",
    size=10.5, color=MUTED, align=PP_ALIGN.CENTER)
# HAL split
hy = 3.95
box(s, M, hy, 5.85, 1.5, fill=PANEL2)
txt(s, M + 0.3, hy + 0.18, 5.2, 0.3, "HARDWARE ABSTRACTION LAYER (HAL)", size=11, color=PRIMARY, bold=True)
txt(s, M + 0.3, hy + 0.55, 5.2, 0.75,
    "One interface, two worlds:  SIMULATOR (physics + noisy sensors)\nand REAL ROVER (ESP32 over serial) \u2014 zero brain changes.",
    size=12, color=TEXT, spacing=1.15)
box(s, M + 6.2, hy, 6.05, 1.5, fill=PANEL2)
txt(s, M + 6.5, hy + 0.18, 5.4, 0.3, "MISSION CONTROL \u2014 DIGITAL TWIN", size=11, color=PRIMARY, bold=True)
txt(s, M + 6.5, hy + 0.55, 5.4, 0.75,
    "FastAPI + WebSocket dashboard: live map, pose, battery,\nAI decisions, energy and yield \u2014 in the browser.",
    size=12, color=TEXT, spacing=1.15)
chips2 = [("Python", 1.1), ("OpenCV", 1.2), ("NumPy", 1.05), ("FastAPI", 1.15), ("21 automated tests", 2.3), ("100% run in CI-style suite", 2.9)]
cx = M
for t, w in chips2:
    chip(s, cx, 5.85, w, t, size=10.5); cx += w + 0.18
txt(s, M, 6.5, 12.2, 0.4, "GitHub: Shreyasderaje/ASTRA-MINE \u2014 full source, docs and experiments.",
    size=11.5, color=MUTED)

# ============================================================ 7 · DIGITAL TWIN (screenshot)
s = slide_new(); kicker(s, "Mission control, live"); title(s, "The Digital Twin \u2014 See It Working")
footer(s, 7)
img_w = 7.55; img_h = img_w / 1.6
box(s, M - 0.06, 1.60, img_w + 0.12, img_h + 0.12, fill=PANEL2, line=LINE)
s.shapes.add_picture("../docs/img/dashboard_live.png", Inches(M), Inches(1.66), width=Inches(img_w))
rows = [
    ("Live telemetry, 2\u00d7 / second", "pose, heading, battery, energy, AI decision, planned path, yield"),
    ("Map starts unknown", "rocks appear as the ToF finds them; resource zones from camera + operator cues"),
    ("Same code, two worlds", "SIMULATION mode today \u2014 REAL ROVER mode drives the physical rover"),
    ("Measured, not claimed", "energy integrated by the INA219 chip; grams weighed by the station load cell"),
]
yy = 1.75
for head, body in rows:
    txt(s, 8.45, yy, 4.35, 0.3, head, size=13.5, color=WHITE, bold=True)
    txt(s, 8.45, yy + 0.30, 4.35, 0.6, body, size=11, color=MUTED, spacing=1.1)
    yy += 1.12
txt(s, 8.45, 6.3, 4.35, 0.55,
    [("Live run shown: ", {"color": MUTED}), ("241 g delivered \u00b7 200 g/Wh \u00b7 0 collisions", {"color": GREEN, "bold": True})],
    size=12, color=MUTED, spacing=1.1)

# ============================================================ 8 · HARDWARE
s = slide_new(); kicker(s, "What we physically build"); title(s, "Hardware Architecture")
footer(s, 8)
bw1 = 5.8
box(s, M, 1.7, bw1, 1.7, fill=PANEL, line=PRIMARY)
txt(s, M, 1.92, bw1, 0.35, "RASPBERRY PI 5 \u2014 \u201cBRAIN\u201d", size=12.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(s, M + 0.25, 2.32, bw1 - 0.5, 0.95, "AI vision \u00b7 planning \u00b7 mission logic \u00b7 digital twin server \u00b7 Wi-Fi dashboard",
    size=10.5, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.1)
arrow(s, M + bw1 + 0.12, 2.42, 0.42, 0.26)
arrow(s, M + bw1 + 0.12, 2.42, 0.42, 0.26).rotation = 180
txt(s, M + bw1 + 0.02, 2.02, 0.62, 0.3, "USB", size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
ex = M + bw1 + 0.63
box(s, ex, 1.7, bw1, 1.7, fill=PANEL, line=PRIMARY)
txt(s, ex, 1.92, bw1, 0.35, "ESP32 \u2014 \u201cREFLEXES\u201d (50 Hz)", size=12.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(s, ex + 0.25, 2.32, bw1 - 0.5, 0.95, "real-time motor loop, odometry, gyro fusion, failsafes \u2014 things Linux cannot do",
    size=10.5, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.1)
txt(s, M, 3.62, 8.0, 0.3, "ONBOARD SENSORS & ACTUATORS", size=11, color=PRIMARY, bold=True)
sens = [("TB6612 \u2192 4\u00d7 DC motors", 2.75), ("wheel encoders", 1.85), ("MPU-6050 IMU", 1.7),
        ("INA219 power", 1.75), ("VL53L0X ToF", 1.6), ("scoop servo", 1.5)]
cx = M
for t, w in sens:
    chip(s, cx, 3.98, w, t, size=10, fill=PANEL2); cx += w + 0.14
box(s, M, 4.62, 5.9, 1.5, fill=PANEL2)
txt(s, M + 0.28, 4.82, 5.3, 0.3, "POWER", size=11, color=ACCENT, bold=True)
txt(s, M + 0.28, 5.16, 5.35, 0.8, "3S Li-ion 11.1 V (40 Wh) + BMS \u00b7 inline fuse \u00b7 buck converter 5 V rail \u00b7 common ground bus",
    size=11.5, color=MUTED, spacing=1.15)
box(s, M + 6.15, 4.62, 6.63, 1.5, fill=PANEL)
txt(s, M + 6.43, 4.82, 6.1, 0.3, "PROCESSING STATION \u2014 2nd ESP32 + HX711 load cell", size=11.5, color=WHITE, bold=True)
txt(s, M + 6.43, 5.16, 6.1, 0.8, "Weighs every delivery and streams the measured grams \u2014 the honest number behind g/Wh. Failsafes: 600 ms command watchdog \u00b7 tilt cut-off \u00b7 manual override.",
    size=11, color=MUTED, spacing=1.12)
box(s, M, 6.35, 12.23, 0.62, fill=PANEL)
specs = [("Max speed", "0.12 m/s"), ("Battery", "40 Wh"), ("Sensors", "6 onboard + camera"),
         ("Testbed", "3 m \u00d7 3 m"), ("Budget", "\u20b935k\u201350k"), ("Team", "4 \u00d7 16 weeks")]
cx = M + 0.3
for k, v in specs:
    txt(s, cx, 6.42, 1.05, 0.25, k, size=9, color=MUTED)
    txt(s, cx, 6.65, 1.9, 0.28, v, size=12, color=WHITE, bold=True)
    cx += 2.02

# ============================================================ 9 · AI BRAIN
s = slide_new(); kicker(s, "Our research contribution"); title(s, "The Rover Doesn't Follow a Path \u2014 It Decides")
footer(s, 9)
box(s, M, 1.72, 12.23, 1.45, fill=PANEL2, line=blend(PRIMARY, BG, 0.35))
txt(s, M, 1.95, 12.23, 0.45, "Mission Score  =  P(resource) \u00d7 expected yield", size=19, color=WHITE, bold=True,
    font=FM, align=PP_ALIGN.CENTER)
txt(s, M, 2.52, 12.23, 0.45, "\u00f7  ( E_travel + E_mine + E_return ) \u00d7 ( 1 + w\u00b7risk )",
    size=19, color=PRIMARY, bold=True, font=FM, align=PP_ALIGN.CENTER)
txt(s, M, 3.38, 12.23, 0.35, "Every reachable target re-scored after each delivery \u2014 a closed-loop autonomous prospector.",
    size=12.5, color=MUTED, align=PP_ALIGN.CENTER)
strats = [
    ("NEAREST", "always the closest zone", "baseline", PANEL, MUTED),
    ("SHORTEST PATH", "cheapest route wins", "baseline", PANEL, MUTED),
    ("RESOURCE-GREEDY", "richest zone, cost ignored", "baseline", PANEL, MUTED),
    ("FULL  (OURS)", "value \u00f7 energy \u00f7 risk \u2014 all three traded off", "our contribution", PANEL2, ACCENT),
]
gx, gy, gw, gh = M, 4.0, 2.93, 1.95
for i, (name, desc, tag, fill, edge) in enumerate(strats):
    x = gx + i * (gw + 0.17)
    box(s, x, gy, gw, gh, fill=fill, line=edge if i == 3 else LINE, line_w=1.4 if i == 3 else 0.75)
    txt(s, x + 0.2, gy + 0.22, gw - 0.4, 0.55, name, size=13.5, color=WHITE if i < 3 else ACCENT, bold=True)
    txt(s, x + 0.2, gy + 0.78, gw - 0.4, 0.7, desc, size=11, color=MUTED, spacing=1.1)
    txt(s, x + 0.2, gy + 1.55, gw - 0.4, 0.3, tag.upper(), size=9, color=GREEN if i == 3 else MUTED, bold=True)
txt(s, M, 6.35, 12.2, 0.4,
    [("Why it matters: ", {"bold": True, "color": WHITE}),
     ("a rover that spends 1 Wh to fetch 1 g is useless \u2014 the optimizer maximizes grams per watt-hour, the currency of deep-space robotics.", {"color": TEXT})],
    size=13)

# ============================================================ 10 · RESULTS
s = slide_new(); kicker(s, "15 terrains \u00d7 4 strategies \u00b7 identical energy budget"); title(s, "Results: Decisions Beat Default")
footer(s, 10)
chart_data = CategoryChartData()
chart_data.categories = ["nearest", "shortest\npath", "resource\ngreedy", "FULL\n(ours)"]
chart_data.add_series("g per Wh", (300.8, 302.9, 345.6, 337.2))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(M), Inches(1.72),
                        Inches(7.1), Inches(4.55), chart_data)
chart = gf.chart
chart.has_legend = False
chart.font.size = Pt(11); chart.font.name = F; chart.font.color.rgb = MUTED
# dark chart background
cs = chart._chartSpace
spPr = etree.SubElement(cs, qn("c:spPr"))
etree.SubElement(spPr, qn("a:solidFill")).append(etree.Element(qn("a:srgbClr"), val="101A30"))
ln = etree.SubElement(spPr, qn("a:ln")); etree.SubElement(ln, qn("a:noFill"))
plot = chart.plots[0]
plot.gap_width = 55
plot.has_data_labels = True
dl = plot.data_labels
dl.font.size = Pt(13); dl.font.bold = True; dl.font.color.rgb = TEXT
dl.position = XL_LABEL_POSITION.OUTSIDE_END
series = plot.series[0]
for i, colr in enumerate([MUTED, RGBColor.from_string("4A6FA5"), RGBColor.from_string("B8860B"), PRIMARY]):
    pt = series.points[i]
    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = colr
ca = chart.category_axis
ca.tick_labels.font.color.rgb = TEXT; ca.tick_labels.font.size = Pt(11)
ca.format.line.color.rgb = LINE; ca.has_major_gridlines = False
va = chart.value_axis
va.has_major_gridlines = False
va.tick_labels.font.color.rgb = MUTED; va.tick_labels.font.size = Pt(10)
box(s, M + 7.45, 1.72, 4.78, 4.55, fill=PANEL)
txt(s, M + 7.73, 1.98, 4.2, 0.3, "WHAT THE DATA SAYS", size=11, color=PRIMARY, bold=True)
txt(s, M + 7.73, 2.38, 4.2, 0.75, "+14.9%", size=44, color=GREEN, bold=True)
txt(s, M + 7.73, 3.18, 4.2, 0.55, "resource yield per watt-hour vs the nearest-target baseline (best strategy)",
    size=11.5, color=MUTED, spacing=1.1)
txt(s, M + 7.73, 3.92, 4.2, 0.5, "+12.1%", size=30, color=PRIMARY, bold=True)
txt(s, M + 7.73, 4.44, 4.2, 0.75, "our full optimizer vs baseline \u2014 same mission, 9% less energy and 14% less travel than resource-greedy",
    size=11.5, color=MUTED, spacing=1.1)
txt(s, M + 7.73, 5.42, 4.2, 0.75,
    "Honest note: at 3 m scale travel is cheap, so resource-greedy ties. The scale study (3 m \u2192 5 m) tests where the optimizer's edge grows.",
    size=10.5, color=MUTED, spacing=1.1)
txt(s, M, 6.45, 12.2, 0.35, "Source: our own experiment \u2014 software/results/experiments.csv, 15 seeded terrains, 1.2 Wh budget, 0 collisions across 60 runs.",
    size=10, color=MUTED)

# ============================================================ 11 · TESTBED + ISRU
s = slide_new(); kicker(s, "Our piece of the Moon"); title(s, "Lunar Analogue Testbed & ISRU Pathway")
footer(s, 11)
tb = box(s, M, 1.75, 5.9, 4.55, fill=PANEL2)
txt(s, M + 0.28, 1.95, 5.3, 0.3, "3 m \u00d7 3 m TESTBED \u2014 TOP VIEW", size=11, color=PRIMARY, bold=True)
tx, ty, tw, th = M + 0.35, 2.35, 5.2, 3.55
rect(s, tx, ty, tw, th, blend(PANEL, BG, 0.9), line=LINE)
import random
rnd = random.Random(7)
for _ in range(14):  # rocks
    rx = tx + 0.25 + rnd.random() * (tw - 0.6); ry = ty + 0.25 + rnd.random() * (th - 0.6)
    d = 0.12 + rnd.random() * 0.12
    ring(s, rx, ry, d, color=RGBColor.from_string("59617A"), w=1.0)
for (zx, zy, zd) in [(tx + 1.1, ty + 0.95, 0.85), (tx + 3.9, ty + 1.0, 0.7),
                     (tx + 1.3, ty + 2.7, 0.95), (tx + 4.0, ty + 2.6, 0.8)]:
    ring(s, zx, zy, zd, color=GREEN_T, w=1.0)
    ring(s, zx, zy, zd * 0.55, color=blend(GREEN, BG, 0.5), w=1.0)
stx, sty = tx + 0.45, ty + 2.85
rect(s, stx - 0.12, sty - 0.12, 0.24, 0.24, PRIMARY)
txt(s, stx - 0.45, sty + 0.18, 1.2, 0.25, "STATION", size=9, color=PRIMARY, bold=True)
rvx, rvy = tx + 4.55, ty + 1.75
tri = s.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(rvx - 0.11), Inches(rvy - 0.11), Inches(0.22), Inches(0.22))
tri.fill.solid(); tri.fill.fore_color.rgb = WHITE; tri.line.fill.background(); tri.shadow.inherit = False
txt(s, tx, ty + th + 0.12, tw, 0.3, "rocks \u25cb   resource zones \u25cb\u25cb   rover \u25b2   station \u25a0",
    size=10, color=MUTED, align=PP_ALIGN.CENTER)
txt(s, M + 0.28, 6.42, 5.5, 0.5, "Craters, slopes and rocks are rebuilt to match the simulator \u2014 the sim is a 1:1 model of this floor.",
    size=11, color=MUTED, spacing=1.1)
chain = [
    ("1", "SCOOP", "rover collects marked simulant"),
    ("2", "DELIVER", "returns to the processing station"),
    ("3", "WEIGH", "load cell measures the true grams"),
    ("4", "YIELD MODEL", "recoverable fraction \u2192 resource estimate"),
    ("5", "PROPELLANT MODEL", "electrolysis \u2192 theoretical H\u2082 + O\u2082 (modelled only)"),
]
yy = 1.85
for num, head, body in chain:
    box(s, M + 6.35, yy, 5.88, 0.82, fill=PANEL)
    txt(s, M + 6.62, yy + 0.14, 0.5, 0.5, num, size=20, color=ACCENT, bold=True)
    txt(s, M + 7.15, yy + 0.10, 4.85, 0.3, head, size=13, color=WHITE, bold=True)
    txt(s, M + 7.15, yy + 0.42, 4.85, 0.3, body, size=11, color=MUTED)
    yy += 0.95
txt(s, M + 6.35, 6.62, 5.88, 0.35, "Demonstrates the full ISRU chain \u2014 without ever producing a dangerous chemical.",
    size=11.5, color=MUTED, italic=True)

# ============================================================ 12 · TIMELINE
s = slide_new(); kicker(s, "16 weeks, 4 members"); title(s, "Execution Plan")
footer(s, 12)
phases = [
    ("WEEKS 1\u20134", "DESIGN + SIMULATION", "architecture \u00b7 world simulator \u00b7 vision dataset \u00b7 strategy experiments", GREEN, "SOFTWARE: DONE"),
    ("WEEKS 5\u20137", "ROVER BUILD", "chassis \u00b7 power \u00b7 firmware \u00b7 bring-up checks B1\u2013B10", PRIMARY, "build phase"),
    ("WEEKS 8\u20139", "PERCEPTION", "camera on Pi \u00b7 HSV/YOLO tuning \u00b7 live detector", PRIMARY, "integration"),
    ("WEEKS 10\u201312", "AUTONOMY", "calibration \u00b7 ToF rocks \u00b7 closed-loop missions on testbed", ACCENT, "the real thing"),
    ("WEEKS 13\u201316", "PROVE IT", "experiments \u00b7 report \u00b7 PPT \u00b7 filmed demo day", GREEN, "delivery"),
]
bw2, bh2 = 2.32, 3.1
byy = 2.1
rect(s, M + 0.1, byy - 0.28, W - 2 * M - 0.2, 0.025, LINE)
for i, (wk, head, body, colr, tag) in enumerate(phases):
    x = M + i * (bw2 + 0.16)
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.02), Inches(byy - 0.36), Inches(0.16), Inches(0.16))
    dot.fill.solid(); dot.fill.fore_color.rgb = colr; dot.line.fill.background(); dot.shadow.inherit = False
    box(s, x, byy + 0.15, bw2, bh2, fill=PANEL)
    txt(s, x + 0.2, byy + 0.35, bw2 - 0.4, 0.3, wk, size=11, color=colr, bold=True)
    txt(s, x + 0.2, byy + 0.72, bw2 - 0.4, 0.6, head, size=14, color=WHITE, bold=True, spacing=1.0)
    txt(s, x + 0.2, byy + 1.45, bw2 - 0.4, 1.2, body, size=10.5, color=MUTED, spacing=1.15)
    chip(s, x + 0.2, byy + 2.6, bw2 - 0.55, tag, size=9, fill=PANEL2, color=colr if i != 0 else GREEN)
txt(s, M, 5.85, 12.2, 0.6,
    [("Risk doctrine: ", {"bold": True, "color": WHITE}),
     ("manual override always wired \u00b7 MVP first \u00b7 modular mining mechanism \u00b7 no hazardous chemistry \u00b7 integration rehearsed weekly, not at the end.", {"color": TEXT})],
    size=13, spacing=1.15)

# ============================================================ 13 · BUDGET & TEAM
s = slide_new(); kicker(s, "What it takes"); title(s, "Budget & Team Roles")
footer(s, 13)
box(s, M, 1.72, 5.4, 4.85, fill=PANEL)
txt(s, M + 0.3, 1.95, 4.8, 0.3, "BUDGET — STUDENT JUGAAD BUILD", size=11, color=PRIMARY, bold=True)
txt(s, M + 0.3, 2.32, 4.8, 0.8, "\u20b95k \u2013 \u20b99k", size=44, color=GREEN, bold=True)
txt(s, M + 0.3, 3.25, 4.8, 0.4, "same science  \u00b7  ~20% of the \u20b935k\u201350k recommended build", size=11.5, color=MUTED)
split = [
    ("Brain: Pi Zero 2 W or ESP32-CAM + laptop", 3.1),
    ("BO motors + DIY plywood chassis", 2.6),
    ("Printed-paper encoder discs", 2.2),
    ("UPS battery + BMS (reclaimed)", 2.4),
    ("HC-SR04 / bump detection", 2.1),
    ("Kitchen scale + tarpaulin testbed", 2.5),
]
yy = 3.74
for t, w in split:
    chip(s, M + 0.3, yy, w, t, size=9.5, fill=PANEL2); yy += 0.40
txt(s, M + 0.3, 6.16, 4.85, 0.4, "Frugal engineering is real space engineering \u2014 Mangalyaan cost less than a movie about Mars.",
    size=10.5, color=ACCENT, italic=True, spacing=1.05)
roles = [
    ("Shreyas Deraje", "TEAM LEAD \u00b7 AI & SYSTEM ARCHITECTURE", "mission optimizer, perception, integration, research lead"),
    ("Pruthviraj Anchan", "ROBOTICS & MECHANISMS", "chassis, drivetrain, scoop design, testbed construction"),
    ("Puneeth", "EMBEDDED & POWER", "ESP32 firmware, wiring, battery system, sensor bring-up"),
    ("Naveen M", "SOFTWARE & DIGITAL TWIN", "dashboard, telemetry, data logging, experiments"),
]
yy = 1.72
for name, role, body in roles:
    box(s, M + 5.7, yy, 6.53, 1.05, fill=PANEL2)
    txt(s, M + 5.98, yy + 0.14, 3.0, 0.32, name, size=15, color=WHITE, bold=True)
    txt(s, M + 5.98, yy + 0.50, 5.95, 0.3, role, size=10, color=ACCENT if name.startswith("Shreyas") else PRIMARY, bold=True)
    txt(s, M + 5.98, yy + 0.76, 5.95, 0.28, body, size=10.5, color=MUTED)
    yy += 1.17

# ============================================================ 14 · FUTURE SCOPE
s = slide_new(); kicker(s, "Where ASTRA-MINE goes next"); title(s, "Future Scope")
footer(s, 14)
futs = [
    ("Multi-rover cooperative mining", "rover teams that split prospecting, mapping and hauling \u2014 the direction NASA's CADRE mission is flying"),
    ("Reinforcement learning on the twin", "the simulator is a safe gym: train smarter target policies, deploy the winner on the rover"),
    ("Spectral proxy sensing", "near-infrared reflectance instead of colour markers \u2014 a step toward real volatiles detection"),
    ("SLAM + field trials", "replace odometry drift with proper mapping; take the rover outdoors on rough terrain"),
    ("Open dataset release", "publish the ASTRA-MINE Lunar Analogue Dataset for other student teams to benchmark on"),
]
yy = 1.85
for i, (head, body) in enumerate(futs):
    box(s, M, yy, 12.23, 0.86, fill=PANEL if i % 2 == 0 else PANEL2)
    txt(s, M + 0.3, yy + 0.20, 0.55, 0.5, f"0{i+1}", size=17, color=PRIMARY, bold=True)
    txt(s, M + 1.0, yy + 0.12, 4.3, 0.6, head, size=14.5, color=WHITE, bold=True, spacing=1.0)
    txt(s, M + 5.4, yy + 0.22, 6.6, 0.5, body, size=11.5, color=MUTED, spacing=1.05)
    yy += 0.97
txt(s, M, 6.72, 12.2, 0.35, "The architecture is the product \u2014 every upgrade plugs into the same closed loop.",
    size=12.5, color=TEXT, italic=True)

# ============================================================ 15 · THANK YOU
s = slide_new()
ring(s, 1.2, 6.3, 4.0); ring(s, 1.2, 6.3, 2.9, color=blend(LINE, BG, 0.5))
txt(s, 0, 2.35, W, 1.2, "Thank You", size=60, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(s, 0, 3.62, W, 0.45, "ASTRA-MINE \u2014 Autonomous AI-Driven Extraterrestrial Resource Prospecting & ISRU Demonstrator",
    size=14, color=MUTED, align=PP_ALIGN.CENTER)
txt(s, 0, 4.12, W, 0.4, "Questions \u00b7 live demo \u00b7 github.com/Shreyasderaje/ASTRA-MINE",
    size=12.5, color=PRIMARY, align=PP_ALIGN.CENTER)
txt(s, 0, 5.05, W, 0.35, "T E A M   S U D A R S H A N   \u00b7   S P P N   S P A C E   R E S E A R C H   T E A M",
    size=11, color=MUTED, align=PP_ALIGN.CENTER)
names = [("Shreyas Deraje", "4VP24AI043"), ("Pruthviraj Anchan", "4VP24AI031"),
         ("Puneeth", "4VP25AI403"), ("Naveen M", "4VP25AI401")]
gx, gy, gw, gh = 1.10, 5.55, 2.62, 0.95
for i, (nm, usn) in enumerate(names):
    x = gx + i * (gw + 0.22)
    box(s, x, gy, gw, gh, fill=PANEL, line=LINE)
    txt(s, x, gy + 0.16, gw, 0.32, nm, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    txt(s, x, gy + 0.52, gw, 0.28, usn, size=11, color=PRIMARY, align=PP_ALIGN.CENTER)

prs.save("ASTRA-MINE_SUDARSHAN.pptx")
print(f"saved ASTRA-MINE_SUDARSHAN.pptx with {len(prs.slides.__iter__.__self__._sldIdLst)} slides")
