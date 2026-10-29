# Car Behaviour — Driver Safety Scoring (UAH-DriveSet)

A proof-of-concept for a **telematics-based driver safety score** — a "CIBIL-style"
score for driving behaviour — built on the public **UAH-DriveSet**. The idea: turn
raw driving sensor data into a single portable score that benefits both drivers
(lower premiums, faster/preferential claims, rewards) and insurers (better risk
pricing, fraud/liability signal at claim time).

This is a research / academic prototype. See the **License** note below.

---

## The Product Idea

A behaviour-based insurance (UBI/BBI, "pay-how-you-drive") scoring engine.

- **Inputs (per trip):** hard braking, hard acceleration, hard/sharp turns,
  speeding, lane-change frequency, tailgating, trip duration, and time of driving
  (e.g. night driving).
- **Output:** a normalized safety score (0–100, or a 300–900 CIBIL-style band).
- **For drivers:** safe driving → higher score → lower premiums, priority claims,
  rewards.
- **For insurers:** sharper risk pricing, lower loss ratios, and a behavioural
  signal at claim time (was the driver aggressive at the moment of incident?).

Commercial analogs: Progressive Snapshot, Root Insurance, other "pay-how-you-drive"
programs.

---

## The Dataset — UAH-DriveSet

Naturalistic driving dataset from the University of Alcalá, collected with the
**DriveSafe** smartphone app mounted in real cars.

- **6 drivers** (D1–D6), different ages and vehicles
- **40 recording sessions**, ~500 minutes of driving
- **2 road types:** 18 motorway + 22 secondary road
- Every session is **pre-labeled with a driving style** (ground truth):
  - **17 NORMAL**, **11 AGGRESSIVE**, **12 DROWSY**

The labels are what make this valuable: a score can be *trained and validated*
against real behaviour labels, not just guessed at with arbitrary thresholds.

### Folder layout

```
UAH-DRIVESET-v1/UAH-DRIVESET-v1/<Dx>/<timestamp-km-Dx-STYLE-ROADTYPE>/*.txt
```

Folder names encode: recording datetime, distance (km), driver ID, driving style
(NORMAL/AGGRESSIVE/DROWSY), and road type (MOTORWAY/SECONDARY).

### Files in each session (space-separated `.txt`, column 1 = timestamp seconds)

| File | Contents | Use for scoring |
|---|---|---|
| `RAW_GPS.txt` | speed, lat/lon, altitude, course, GPS quality (12 cols) | Trip duration, distance, speeding, time-of-day |
| `RAW_ACCELEROMETERS.txt` | raw + filtered X/Y/Z accel, roll/pitch/yaw (11 cols) | **Hard braking, hard acceleration, hard turns** (core sensor) |
| `EVENTS_INERTIAL.txt` | pre-detected braking/accel/turning events + type/severity + GPS + datetime | Pre-counted harsh events |
| `EVENTS_LIST_LANE_CHANGES.txt` | lane-change events, direction, duration, threat level | Erratic / risky maneuvering |
| `PROC_VEHICLE_DETECTION.txt` | distance to car ahead, estimated collision time | Tailgating / following distance |
| `PROC_OPENSTREETMAP_DATA.txt` | matched road / OSM context (some sessions) | Road context |
| `SEMANTIC_FINAL.txt` | ~30 aggregated per-trip scores (app's own risk metrics) | Benchmark to compare our score against |
| `SEMANTIC_ONLINE.txt` | streaming/online aggregated scores | Benchmark |

---

## Proposed Scoring Pipeline

1. **Extract per-trip features** — harsh-brake / harsh-accel / harsh-turn counts
   (from `EVENTS_INERTIAL`), speeding %, avg/max speed, trip duration, night-driving
   flag & time-of-day, lane-change frequency, tailgating time.
2. **Normalize** per km / per hour so long trips aren't unfairly penalized.
3. **Weight & combine** into a 0–100 (or 300–900) score. Calibrate the weights
   against the NORMAL/AGGRESSIVE/DROWSY labels — train a simple classifier/regression
   so the score cleanly separates aggressive from normal driving. This is the
   validation story.
4. **Map score → insurance action** (premium band, claim-priority tier).

---

## Code

| File | What it does |
|---|---|
| `uah_driveset.py` | Loader: `list_trips()`, `load_trip()`, `load_summaries()` read every trip file into named pandas tables |
| `notebooks/01_explore_data.ipynb` | Step 1: dataset overview, Normal vs Aggressive vs Drowsy plots, baseline accuracy of the app's own ratios |
| `event_detection.py` | Step 2: threshold-based detector for braking / acceleration / turning events, plus matching and scoring against the app's `EVENTS_INERTIAL` |
| `notebooks/02_event_detection.ipynb` | Step 2: our detector vs the app (tuned on D1–D3, tested on D4–D6), per-trip event rates by driving style |
| `results/step2_trip_events.csv` | Step 2 output: our harsh-event rates per 10 km for every trip (features for later steps) |
| `behaviour_features.py` | Step 3: speeding (% time >10% over the OSM limit), tailgating (% time <0.5 s behind the car ahead), drifting (% time >0.5 m off lane centre), weaving (drift-and-correct per minute), lane changes per 10 km |
| `notebooks/03_behaviour_features.ipynb` | Step 3: how each rule was chosen, Normal vs Drowsy vs Aggressive, agreement with the app's scores |
| `results/step3_trip_features.csv` | Step 3 output: all Step 2 + Step 3 features, one row per trip |

Requirements: `pip install pandas numpy matplotlib jupyter`

Accelerometer axes (Kalman-filtered columns, checked against labelled events):
`acc_z_kf` = forward (braking is negative), `acc_y_kf` = sideways (turning), `acc_x_kf` = vertical.

---

## Caveats

- **License:** UAH-DriveSet is **Creative Commons BY-NC 4.0** — personal and
  research use only, **no commercial use** without a separate license from the
  authors. Fine for a mini-project / thesis / prototype; not shippable commercially
  as-is.
- **Small N:** only 6 drivers — enough to build and demonstrate the method, not to
  claim a production-grade model. Frame it as a **proof-of-concept scoring engine**.

## Dataset access

The raw dataset (~3.5 GB) is **not committed** to this repo (see `.gitignore`;
it also exceeds GitHub's file-size limits). Download it from the authors:

- http://www.robesafe.uah.es/personal/eduardo.romera/uah-driveset/

Place it so the path `UAH-DRIVESET-v1/UAH-DRIVESET-v1/D1/...` resolves from the repo
root. A Python reader tool (`uah_driveset_reader`) ships with the dataset.

## Credits

Dataset: E. Romera, L. M. Bergasa, R. Arroyo — UAH-DriveSet, University of Alcalá.
