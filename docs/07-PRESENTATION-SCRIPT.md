# ASTRA-MINE — Presentation Script (10–12 minutes)

**Speaker:** Team Lead (Shreyas) — adjust "I/we" if presenting as a group.
**Style:** speak slowly, pause where marked [pause], point where marked 👉.
**Golden rule:** never read the slides aloud — the slides show, you tell.

---

## SLIDE 1 — Title (0:45)

> Good morning everyone. Respected professors and my dear friends — a very
> warm welcome to all of you.
>
> I am Shreyas, and along with my teammates Pruthviraj, Puneeth and Naveen,
> we are **Team SUDARSHAN** — the SPPN Space Research Team.
>
> Today we are presenting our mini-project: **ASTRA-MINE** — the Autonomous
> AI-Driven Extraterrestrial Resource Prospecting and ISRU Demonstrator.
>
> [pause] In simple words — we are building a small rover with an AI brain
> that teaches itself **where to mine, and whether mining is worth the
> energy**. And everything you will see today — the code, the experiments,
> this presentation — is already public on our GitHub. [move on confidently]

---

## SLIDE 2 — Objectives (0:50)

> Before the idea, here is exactly what we committed to build. [point down
> the numbers, don't read them word by word]
>
> We are building an autonomous four-wheel rover on an artificial lunar
> testbed. The rover's camera feeds an AI that builds a **resource
> probability map** — where are the riches buried? Then comes our main
> contribution: the rover **decides for itself** which site to mine, by
> balancing resource value against energy and risk. It completes the full
> loop — survey, decide, navigate, mine, and deliver to a processing
> station — and we benchmark its decisions against simpler strategies.
>
> And the whole mission streams live to a Mission Control dashboard — our
> digital twin.

---

## SLIDE 3 — Purpose (1:00)

> Now — why does this problem even matter?
>
> Every kilogram we launch from Earth costs thousands of dollars, and a
> future lunar base cannot afford to ship its water, oxygen and fuel from
> Earth forever. That is why NASA and ESA are seriously working on
> **ISRU — In-Situ Resource Utilization**: using the resources that are
> already there.
>
> But here is the part everyone misses. [pause] The hard question is not
> "can a robot dig?" The hard question is — **where should it dig, and is
> that trip worth the battery?** A rover that spends one watt-hour to bring
> back one gram is useless. That decision problem is exactly what our
> project attacks.

---

## SLIDE 4 — Uses & Applications (0:45)

> The same architecture — sense, believe, decide, act — is not limited to
> the Moon. [point across the cards]
>
> It transfers directly to autonomous mining and quarrying, disaster-response
> robots that map rubble, exploration of caves and tunnels where GPS does
> not exist, inspection of hazardous industrial sites where humans should
> not walk, and even precision agriculture — a scout that decides where
> soil sampling pays off.
>
> One brain, many bodies.

---

## SLIDE 5 — Limitations & Environment (0:50)

> Now, we want to be honest with you — because real engineering is about
> honest scoping. [pause]
>
> This is a **terrestrial analogue demonstrator**. Our "resources" are
> marked simulant zones — a proxy for real lunar ice. Our localization is
> odometry-based, so it drifts a few percent — SLAM is future work. And we
> say this clearly in our report.
>
> On the environment side: we never produce real hydrogen or oxygen — the
> propellant pathway is a mathematical model only. Everything happens in an
> indoor sand testbed. We use standard reusable electronics, and one mission
> consumes less energy than charging a laptop. [pause] So — ambitious in
> engineering, gentle on the planet.

---

## SLIDE 6 — Software Architecture (1:00)

> Here is the brain. [point at the flow]
>
> Camera and ToF data enter the **perception layer**, which builds a live
> **resource probability map** of the terrain. The **mission optimizer**
> scores every possible target — this is our novelty, I'll show the formula
> in a moment. The **A-star planner** finds the cheapest safe path, and the
> **mission state machine** runs the full survey-to-delivery cycle.
>
> The key design decision is this box — [point at HAL] — the Hardware
> Abstraction Layer. The brain talks to ONE interface. Behind it sits either
> our physics **simulator**, or the **real rover** over serial. The exact
> same AI code runs in both worlds. That is what makes our results
> trustworthy and our demo safe.
>
> All of it is Python, OpenCV and FastAPI — with twenty-one automated tests
> keeping it honest.

---

## SLIDE 7 — Digital Twin (1:00 + optional live demo)

> And this is what it actually looks like. [point at the screenshot]
>
> This is our **Mission Control — a live digital twin** running in a normal
> browser. You can see the lunar map with the AI's belief — green means
> resource, grey squares are discovered rocks. The white triangle is the
> rover, the dashed line is its planned path, and on the right you see live
> battery, energy, distance, and — most importantly — every AI decision with
> its score.
>
> 👉 *[If allowed, switch to the live dashboard and press LAUNCH]* — "and
> right now, I can start a fresh mission in front of you — watch the rover
> survey, decide, and mine on its own."
>
> The screenshot you see is a real completed run: **241 grams delivered at
> 200 gram-per-watt-hour, zero collisions.**

---

## SLIDE 8 — Hardware (1:00)

> On the hardware side, we split the system the way real space robots do.
>
> The **Raspberry Pi 5 is the brain** — vision, planning, dashboard. The
> **ESP32 is the reflexes** — it runs a real-time 50-hertz motor loop that
> Linux cannot guarantee. The Pi thinks, the ESP32 reacts. [point]
>
> Around them: four driven wheels with encoders, an IMU, an INA219 power
> monitor — that tiny chip measures the exact watt-hours behind our headline
> metric — a ToF sensor that discovers obstacles, and a servo scoop.
> A second ESP32 at the processing station **weighs every delivery** on a
> load cell — so our grams are measured, not claimed.
>
> And it is all safe: a 600-millisecond watchdog stops the motors if the
> link dies, and there is always a manual override.

---

## SLIDE 9 — The AI Brain (1:15)

> Now, our research contribution. [point at the formula, read it slowly]
>
> **Mission Score equals the probability of resource times the expected
> yield, divided by the total energy — travel plus mining plus return —
> multiplied by one plus risk.**
>
> In plain words: for every reachable site, the rover asks — *"how many
> grams will I get per watt-hour spent, and how risky is the road?"* — and
> it goes to the best one. Then the loop closes: after every delivery, every
> remaining target is re-scored with fresh data.
>
> To prove this matters, we compete against three baselines: go to the
> nearest zone, take the shortest path, or just be greedy about richness.
> Our strategy trades off all three at once.

---

## SLIDE 10 — Results (1:15)

> And here is the proof. We ran **fifteen different terrains, four
> strategies, identical energy budget** — sixty full missions. [pause]
>
> Both intelligent strategies beat the naive baselines. The best strategy
> gained **+14.9 percent resource per watt-hour** over the nearest-target
> baseline. Our full optimizer gained **+12 percent, with 9 percent less
> energy and 14 percent less travel** than the greedy strategy.
>
> And one honest finding we are proud of: on a small 3-metre testbed,
> travel is cheap, so plain greedy nearly ties with us. But when we scaled
> the terrain to 5 metres — closer to real prospecting distances — our full
> optimizer **overtook the greedy strategy**. [pause] In other words: the
> smarter the decision-making needs to be, the bigger the mission. That is
> exactly the argument for real lunar rovers.
>
> Everything is reproducible — the CSV files and charts are on our GitHub.

---

## SLIDE 11 — Testbed & ISRU (0:50)

> On the left is our "Moon" — a three-by-three-metre analogue testbed with
> craters, rocks, and buried resource zones, and the processing station in
> the corner. We build it to match the simulator one-to-one.
>
> On the right is the full ISRU chain we demonstrate: the rover scoops
> marked simulant, delivers it, the station **weighs it**, a yield model
> estimates the recoverable resource, and a model computes the theoretical
> hydrogen-oxygen propellant output. Modelled only — never produced — safe
> and still scientifically meaningful.

---

## SLIDE 12 — Timeline (0:40)

> How do four students build this in sixteen weeks? [point left to right]
>
> We deliberately started with the **hardest, cheapest part — the software
> and the experiments — which are already complete and tested**. Then rover
> build, perception, autonomy on the testbed, and finally experiments and
> the report. And our risk doctrine keeps us alive: manual fallback always
> ready, MVP first, integration rehearsed weekly — never at the end.

---

## SLIDE 13 — Budget & Team (0:40)

> We are students, so we engineered the budget like engineers. Our target
> build is **five to nine thousand rupees** — roughly twenty percent of the
> standard parts list — using a Pi Zero, reclaimed batteries, printed
> encoder discs and a tarpaulin Moon. [smile] As we like to say — Mangalyaan
> reached Mars for less than a movie about Mars. Frugal is not a
> compromise; it is the culture.
>
> And this is how the four of us divide it — [one line each: Shreyas on AI
> and architecture, Pruthviraj on robotics, Puneeth on embedded and power,
> Naveen on software and the digital twin].

---

## SLIDE 14 — Future Scope (0:40)

> ASTRA-MINE is designed to grow. Four directions: **multi-rover
> cooperative mining** — the direction NASA's CADRE mission is flying right
> now; **reinforcement learning** trained inside our digital twin — a safe
> gym for smarter policies; **near-infrared sensing** — a real step toward
> detecting actual volatiles; and releasing our testbed dataset so other
> student teams can benchmark on it.
>
> The architecture is the product — every upgrade plugs into the same loop.

---

## SLIDE 15 — Thank You (0:20)

> That was ASTRA-MINE — a small rover asking a big question: **not "can we
> mine space?", but "how should a machine decide to mine space?"**
>
> Thank you so much for your time and attention. We are happy to take
> questions — and the rover is listening too. [smile, pause, bow slightly]

---

# Likely questions & short answers

**Q: Has anyone already built this?**
A: Parts of it exist at agency level — NASA's IPEx excavator, ESA's Space
Resources Challenge. What does NOT exist is the closed-loop decision layer at
student scale, benchmarked on g/Wh. Our novelty is the integration and the
decision-making, and we cite the prior work honestly.

**Q: Is your rover really detecting water?**
A: No — and we never claim that. It detects marker zones as a proxy for
resource signatures. The method — belief mapping plus value-per-energy
decisions — is what transfers to real spectral sensing.

**Q: Why not reinforcement learning?**
A: RL needs millions of trials. Our testbed gives dozens. So v1 uses a
transparent utility function we can debug and measure — and the digital twin
is exactly the safe gym where we plan to train RL later.

**Q: What if the AI fails during the demo?**
A: Three safety layers: a 600 ms command watchdog, tilt protection, and a
manual override mode. A demo that cannot fail safely is not a demo.

**Q: Why is your budget so low — is it a toy?**
A: We consciously moved money from comfort to sensing, because our metric is
grams-per-watt-hour, not looks. Mangalyaan reached Mars for less than a
movie about Mars — frugal engineering is ISRO culture.

---

# Delivery tips

1. Total time ≈ 11 minutes + 2–3 min live demo. Practice with a timer once.
2. Pause after every number you say (14.9%… pause). Numbers need air.
3. Point at the diagram, not at the screen text.
4. If the live demo fails, laugh, say "and THIS is why we built a manual
   override," press ABORT, continue with the screenshot. Confidence intact.
5. Divide slides if all four must speak: Shreyas 1–5, Pruthviraj 6–8,
   Puneeth 9–11, Naveen 12–15 — hand over with "and now my teammate will
   explain…".
