"""
Step 3: the other risky behaviours from the paper (GPS + camera).

  - speeding:   GPS speed compared with the road's speed limit (OpenStreetMap)
  - tailgating: time gap to the car ahead (camera)
  - drifting:   car far from the centre of its lane (lane camera)
  - weaving:    drifting away from the lane centre and then correcting back (lane camera)
  - lane changes: how often the driver changes lane (lane camera)

Every function returns one number per trip, so trips of different length can be compared.
"""

import numpy as np
import pandas as pd

SPEEDING_MARGIN = 0.10      # speeding = more than 10% over the speed limit
TAILGATING_GAP_S = 0.5      # tailgating = less than 0.5 s behind the car ahead
MIN_SPEED_KMH = 10          # ignore the car-ahead data in slow traffic / when stopped
DRIFT_M = 0.5               # drifting = car centre more than 0.5 m from the lane centre
WEAVE_OUT_M = 0.6           # weaving = drift more than 0.6 m away ...
WEAVE_BACK_M = 0.2          # ... and then come back within 0.2 m of the centre
LANE_TRACKING_OK = 2        # lane_state value when the camera sees the lane clearly


def speed_vs_limit(gps, osm):
    """GPS speed with the road's speed limit next to it (one row per GPS reading)."""
    osm = osm[osm["limit_reliability"] >= 1]  # keep rows where the limit is known
    if osm.empty:
        return pd.DataFrame(columns=["time", "speed_kmh", "speed_limit_kmh"])
    merged = pd.merge_asof(gps[["time", "speed_kmh"]].sort_values("time"),
                           osm[["time", "speed_limit_kmh"]].sort_values("time"),
                           on="time", direction="nearest", tolerance=10)
    return merged.dropna()


def speeding_pct(gps, osm, margin=SPEEDING_MARGIN):
    """% of driving time spent more than `margin` over the speed limit."""
    s = speed_vs_limit(gps, osm)
    if s.empty:
        return np.nan
    return (s["speed_kmh"] > (1 + margin) * s["speed_limit_kmh"]).mean() * 100


def time_gap_to_car_ahead(vehicles, min_speed=MIN_SPEED_KMH):
    """Seconds between us and the car ahead: distance / our speed.

    Rows with no car ahead get NaN. Rows below `min_speed` are dropped.
    """
    v = vehicles[vehicles["speed_kmh"] >= min_speed].copy()
    v["gap_s"] = np.where(v["dist_ahead_m"] > 0, v["dist_ahead_m"] / (v["speed_kmh"] / 3.6), np.nan)
    return v


def tailgating_pct(vehicles, gap_s=TAILGATING_GAP_S):
    """% of driving time spent less than `gap_s` seconds behind the car ahead."""
    v = time_gap_to_car_ahead(vehicles)
    if v.empty:
        return np.nan
    return (v["gap_s"] < gap_s).mean() * 100


def tracked_lane(lanes):
    """Only the lane-camera rows where the lane was detected clearly."""
    return lanes[lanes["lane_state"] == LANE_TRACKING_OK]


def drifting_pct(lanes, drift_m=DRIFT_M):
    """% of time the car is more than `drift_m` metres from the lane centre."""
    l = tracked_lane(lanes)
    if l.empty:
        return np.nan
    return (l["lane_offset_m"].abs() > drift_m).mean() * 100


def weaving_per_min(lanes, out_m=WEAVE_OUT_M, back_m=WEAVE_BACK_M):
    """How many times per minute the car drifts away from the lane centre and is corrected back."""
    l = tracked_lane(lanes)
    if len(l) < 2:
        return np.nan
    count, drifted = 0, False
    for offset in l["lane_offset_m"].abs():
        if offset > out_m:
            drifted = True
        elif drifted and offset < back_m:
            count += 1
            drifted = False
    minutes = (l["time"].iloc[-1] - l["time"].iloc[0]) / 60
    return count / minutes


def lane_changes_per_10km(lane_changes, distance_km):
    """Lane changes per 10 km."""
    return len(lane_changes) / distance_km * 10


def trip_behaviour_features(trip, distance_km):
    """All Step 3 features for one trip (`trip` is the dict from load_trip())."""
    return {
        "speeding_pct": speeding_pct(trip["gps"], trip["osm"]),
        "tailgating_pct": tailgating_pct(trip["vehicles"]),
        "drifting_pct": drifting_pct(trip["lanes"]),
        "weaving_per_min": weaving_per_min(trip["lanes"]),
        "lane_changes_per10km": lane_changes_per_10km(trip["lane_changes"], distance_km),
    }
