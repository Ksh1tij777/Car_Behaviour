"""
Step 2: detect harsh driving events from the raw accelerometer.

We look for moments where the car is pushed harder than a threshold:
  - braking:      forward acceleration (acc_z_kf) goes strongly NEGATIVE
  - acceleration: forward acceleration (acc_z_kf) goes strongly POSITIVE
  - turning:      sideways acceleration (acc_y_kf) is strongly positive OR negative

Then we compare our events with the ones the DriveSafe app found (EVENTS_INERTIAL.txt).
"""

import numpy as np
import pandas as pd

# Thresholds in g (1 g = 9.81 m/s^2). An event starts when the signal goes above
# "low"; its level is decided by the highest value reached during the event.
# "merge_gap" (seconds): two pushes closer than this count as one manoeuvre.
# Values were tuned on drivers D1-D3 (see notebooks/02_event_detection.ipynb).
DEFAULT_THRESHOLDS = {
    "braking":      {"low": 0.12, "medium": 0.20, "high": 0.35, "merge_gap": 1.0},
    "acceleration": {"low": 0.09, "medium": 0.13, "high": 0.20, "merge_gap": 3.0},
    "turning":      {"low": 0.12, "medium": 0.17, "high": 0.30, "merge_gap": 3.0},
}

MIN_DURATION_S = 0.0   # ignore pushes shorter than this (0 = keep every push)
MERGE_GAP_S = 1.0      # used when a threshold entry has no "merge_gap"
MIN_SPEED_KMH = 5      # ignore anything while the car is (almost) stopped


def event_signal(accel, event_type):
    """Return the signal to watch for one event type (bigger = harsher)."""
    if event_type == "braking":
        return -accel["acc_z_kf"]
    if event_type == "acceleration":
        return accel["acc_z_kf"]
    if event_type == "turning":
        return accel["acc_y_kf"].abs()
    raise ValueError(event_type)


def add_speed(accel, gps):
    """Attach the GPS speed (interpolated) to every accelerometer row."""
    accel = accel.copy()
    if len(gps):
        accel["speed_kmh"] = np.interp(accel["time"], gps["time"], gps["speed_kmh"])
    else:
        accel["speed_kmh"] = np.nan
    return accel


def detect_events(accel, thresholds=None, min_duration=MIN_DURATION_S,
                  merge_gap=MERGE_GAP_S, min_speed=MIN_SPEED_KMH):
    """Find braking, acceleration and turning events in one trip.

    `accel` is the accelerometer table from load_trip(); add a `speed_kmh` column
    with add_speed() to ignore events while stopped.
    Returns one row per event: time, event_name, level_name, peak_g, duration_s.
    """
    thresholds = thresholds or DEFAULT_THRESHOLDS
    time = accel["time"].to_numpy()
    moving = (accel["speed_kmh"].to_numpy() >= min_speed
              if "speed_kmh" in accel else np.ones(len(accel), bool))
    events = []

    for event_type, th in thresholds.items():
        signal = event_signal(accel, event_type).to_numpy()
        fast_enough = moving
        if "min_speed" in th and "speed_kmh" in accel:
            fast_enough = accel["speed_kmh"].to_numpy() >= th["min_speed"]
        above = (signal > th["low"]) & fast_enough

        # 1. Find each stretch of time where the signal stays above the threshold
        edges = np.diff(np.concatenate([[0], above.astype(int), [0]]))
        starts = np.flatnonzero(edges == 1)
        ends = np.flatnonzero(edges == -1) - 1
        segments = [[s, e] for s, e in zip(starts, ends)]

        # 2. Join stretches that are very close together (one manoeuvre)
        gap = th.get("merge_gap", merge_gap)
        merged = []
        for seg in segments:
            if merged and time[seg[0]] - time[merged[-1][1]] <= gap:
                merged[-1][1] = seg[1]
            else:
                merged.append(seg)

        # 3. Keep stretches that last long enough, and grade them by their peak
        for s, e in merged:
            duration = time[e] - time[s]
            if duration < min_duration:
                continue
            peak_i = s + int(np.argmax(signal[s:e + 1]))
            peak = signal[peak_i]
            level = "high" if peak >= th["high"] else "medium" if peak >= th["medium"] else "low"
            events.append({
                "time": time[peak_i],
                "event_name": event_type,
                "level_name": level,
                "peak_g": round(float(peak), 3),
                "duration_s": round(float(duration), 2),
            })

    return pd.DataFrame(events, columns=["time", "event_name", "level_name", "peak_g", "duration_s"]
                        ).sort_values("time", ignore_index=True)


def match_events(ours, theirs, tolerance_s=2.0):
    """Pair our events with the app's events of the same type.

    Two events match if they are the same type and less than `tolerance_s` apart.
    Each event can be used only once. Returns a table with one row per event:
    status = "match" (both found it), "extra" (only we found it), "missed" (only the app).
    """
    rows = []
    for event_type in DEFAULT_THRESHOLDS:
        o = ours[ours["event_name"] == event_type].reset_index(drop=True)
        t = theirs[theirs["event_name"] == event_type].reset_index(drop=True)
        used = set()
        for _, ev in t.iterrows():
            gaps = (o["time"] - ev["time"]).abs()
            gaps = gaps[~gaps.index.isin(used) & (gaps <= tolerance_s)]
            if len(gaps):
                j = gaps.idxmin()
                used.add(j)
                rows.append({"event_name": event_type, "status": "match", "time": ev["time"],
                             "app_level": ev["level_name"], "our_level": o.loc[j, "level_name"]})
            else:
                rows.append({"event_name": event_type, "status": "missed", "time": ev["time"],
                             "app_level": ev["level_name"], "our_level": None})
        for j in o.index.difference(list(used)):
            rows.append({"event_name": event_type, "status": "extra", "time": o.loc[j, "time"],
                         "app_level": None, "our_level": o.loc[j, "level_name"]})
    return pd.DataFrame(rows, columns=["event_name", "status", "time", "app_level", "our_level"])


def score_matches(matches):
    """Precision, recall and F1 for each event type.

    precision = of the events WE found, how many the app also found
    recall    = of the events the APP found, how many we also found
    F1        = one number that balances both (1.0 = perfect)
    """
    rows = []
    for event_type, g in matches.groupby("event_name"):
        tp = (g["status"] == "match").sum()
        fp = (g["status"] == "extra").sum()
        fn = (g["status"] == "missed").sum()
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        same_level = (g.loc[g["status"] == "match", "app_level"] ==
                      g.loc[g["status"] == "match", "our_level"]).mean() if tp else np.nan
        rows.append({"event": event_type, "app_events": tp + fn, "our_events": tp + fp,
                     "matched": tp, "precision": precision, "recall": recall, "f1": f1,
                     "same_level": same_level})
    return pd.DataFrame(rows).set_index("event").round(2)
