"""
UAH-DriveSet data loader.

Reads the trip folders of the UAH-DriveSet (Romera, Bergasa, Arroyo, ITSC 2016)
into pandas DataFrames with named columns.

Usage:
    from uah_driveset import list_trips, load_trip

    trips = list_trips()            # one row per trip: driver, behavior, road, km, path
    trip = load_trip(trips.iloc[0]) # dict of DataFrames: trip["gps"], trip["accel"], ...

Column names follow the file descriptions in the paper and in the dataset README.
"""

from pathlib import Path

import pandas as pd

# Folder that contains D1 ... D6
DATA_ROOT = Path(__file__).parent / "UAH-DRIVESET-v1" / "UAH-DRIVESET-v1"

# Column names for each data file (column 1 is always seconds since trip start)
COLUMNS = {
    "RAW_GPS": [
        "time", "speed_kmh", "lat", "lon", "altitude",
        "vert_accuracy", "horiz_accuracy", "course", "course_change",
        "unused1", "unused2", "unused3",
    ],
    "RAW_ACCELEROMETERS": [
        "time", "active",
        "acc_x", "acc_y", "acc_z",           # raw, in g
        "acc_x_kf", "acc_y_kf", "acc_z_kf",  # Kalman-filtered, in g
        "roll", "pitch", "yaw",              # degrees
    ],
    "PROC_LANE_DETECTION": [
        "time", "lane_offset_m", "lane_angle_deg", "road_width_m", "lane_state",
    ],
    "PROC_VEHICLE_DETECTION": [
        "time", "dist_ahead_m", "time_to_impact_s", "num_vehicles", "speed_kmh",
    ],
    "PROC_OPENSTREETMAP_DATA": [
        "time", "speed_limit_kmh", "limit_reliability", "road_type",
        "lanes", "current_lane", "lat", "lon", "osm_delay_s", "speed_kmh",
    ],
    "EVENTS_LIST_LANE_CHANGES": [
        "time", "direction", "lat", "lon", "duration_s", "time_threshold_s",
    ],
    "EVENTS_INERTIAL": [
        "time", "event_type", "level", "lat", "lon", "datetime",
    ],
}

# Short names used as keys in the dict returned by load_trip()
SHORT_NAMES = {
    "RAW_GPS": "gps",
    "RAW_ACCELEROMETERS": "accel",
    "PROC_LANE_DETECTION": "lanes",
    "PROC_VEHICLE_DETECTION": "vehicles",
    "PROC_OPENSTREETMAP_DATA": "osm",
    "EVENTS_LIST_LANE_CHANGES": "lane_changes",
    "EVENTS_INERTIAL": "events",
}

EVENT_TYPES = {1: "braking", 2: "turning", 3: "acceleration"}
EVENT_LEVELS = {1: "low", 2: "medium", 3: "high"}

# SEMANTIC_FINAL.txt holds one value per line (54 values, see dataset README)
SEMANTIC_FINAL_NAMES = [
    "start_hour", "start_min", "start_sec", "avg_speed_kmh", "max_speed_kmh",
    "lanex_score", "driving_time_min", "end_hour", "end_min", "end_sec",
    "app_distance_km", "score_long_dist", "score_tran_dist", "score_speed_dist",
    "score_global_old", "alerts_long", "alerts_late", "alerts_lanex",
    "num_stops", "speed_variability", "accel_noise", "kinetic_energy",
    "driving_time_s", "num_curves", "power", "accel_events", "braking_events",
    "turning_events", "long_distraction_score", "tran_distraction_score",
    "long_dist_mean", "long_dist_std", "tran_dist_mean", "tran_dist_std",
    "acc_low", "acc_medium", "acc_high",
    "brake_low", "brake_medium", "brake_high",
    "turn_low", "turn_medium", "turn_high",
    "score_total", "score_accel", "score_braking", "score_turning",
    "score_weaving", "score_drifting", "score_overspeed", "score_carfollow",
    "ratio_normal", "ratio_drowsy", "ratio_aggressive",
]


def list_trips(root=DATA_ROOT):
    """Return a DataFrame with one row per trip, parsed from the folder names.

    Folder name format: <YYYYMMDDhhmmss>-<N>km-<driver>-<BEHAVIOR>[1|2]-<ROAD>
    """
    rows = []
    for folder in sorted(Path(root).glob("D*/*")):
        if not folder.is_dir():
            continue
        stamp, km, driver, behavior, road = folder.name.split("-")
        rows.append({
            "trip_id": folder.name,
            "driver": driver,
            "behavior": behavior.rstrip("12"),  # NORMAL1/NORMAL2 -> NORMAL
            "road": road,
            "distance_km": int(km.replace("km", "")),
            "start": pd.to_datetime(stamp, format="%Y%m%d%H%M%S"),
            "path": folder,
        })
    return pd.DataFrame(rows)


def read_file(trip_path, name):
    """Read one space-separated data file of a trip into a DataFrame."""
    path = Path(trip_path) / f"{name}.txt"
    cols = COLUMNS[name]
    if not path.exists() or path.stat().st_size == 0:
        df = pd.DataFrame(columns=cols)  # trip had no such events
    else:
        df = pd.read_csv(path, sep=r"\s+", header=None)
        df = df.iloc[:, :len(cols)]  # some lines have a trailing space
        df.columns = cols[:df.shape[1]]
    if name == "EVENTS_INERTIAL":
        df["event_name"] = df["event_type"].map(EVENT_TYPES)
        df["level_name"] = df["level"].map(EVENT_LEVELS)
    return df


def read_semantic_final(trip_path):
    """Read SEMANTIC_FINAL.txt (the app's own trip summary) as a pandas Series."""
    lines = (Path(trip_path) / "SEMANTIC_FINAL.txt").read_text().splitlines()
    # One value per line; the distance line is written like "16 km"
    values = [float(line.replace("km", "")) for line in lines if line.strip()]
    return pd.Series(values[:len(SEMANTIC_FINAL_NAMES)],
                     index=SEMANTIC_FINAL_NAMES[:len(values)])


def load_trip(trip):
    """Load every data file of one trip.

    `trip` can be a row of list_trips() or a path to a trip folder.
    Returns a dict: gps, accel, lanes, vehicles, osm, lane_changes, events, summary.
    """
    path = trip["path"] if isinstance(trip, (pd.Series, dict)) else Path(trip)
    data = {short: read_file(path, name) for name, short in SHORT_NAMES.items()}
    data["summary"] = read_semantic_final(path)
    return data


def load_summaries(trips=None):
    """Return one row per trip: folder info + the SEMANTIC_FINAL values."""
    if trips is None:
        trips = list_trips()
    summaries = pd.DataFrame([read_semantic_final(p) for p in trips["path"]])
    return pd.concat([trips.drop(columns="path").reset_index(drop=True),
                      summaries.reset_index(drop=True)], axis=1)
