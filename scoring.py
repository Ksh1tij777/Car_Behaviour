"""
Step 4: turn the risk numbers from Steps 2 and 3 into scores out of 100, like the DriveSafe app.

Every behaviour uses the same simple formula:

    if risk <= allowance:  score = 100                     (a little is forgiven)
    else:                  score = 100 * 0.5 ** ((risk - allowance) / half_at)

i.e. every extra `half_at` units of risk above the allowance HALVES the score.
The overall trip score is the plain average of the 7 behaviour scores (as in the app).
"""

import numpy as np
import pandas as pd

# behaviour -> the risk number it is based on (columns of results/step3_trip_features.csv)
BEHAVIOURS = {
    "accelerations": "acceleration_weighted_per10km",
    "brakings": "braking_weighted_per10km",
    "turnings": "turning_weighted_per10km",
    "weaving": "weaving_per_min",
    "drifting": "drifting_pct",
    "overspeeding": "speeding_pct",
    "car_following": "tailgating_pct",
}

# The app's own score for each behaviour (columns of load_summaries())
APP_SCORES = {
    "accelerations": "score_accel",
    "brakings": "score_braking",
    "turnings": "score_turning",
    "weaving": "score_weaving",
    "drifting": "score_drifting",
    "overspeeding": "score_overspeed",
    "car_following": "score_carfollow",
}

# Fitted on drivers D1-D3 with fit_curve() (see notebooks/04_scores.ipynb)
SCORE_PARAMS = {
    "accelerations": {"allowance": 0.71, "half_at": 12.57},
    "brakings":      {"allowance": 2.50, "half_at": 3.09},
    "turnings":      {"allowance": 0.00, "half_at": 9.09},
    "weaving":       {"allowance": 3.16, "half_at": 0.36},
    "drifting":      {"allowance": 0.00, "half_at": 21.54},
    "overspeeding":  {"allowance": 0.00, "half_at": 41.14},
    "car_following": {"allowance": 1.59, "half_at": 12.57},
}


def add_weighted_events(features):
    """Count harsh events with severity: a low event counts 1, a medium or high event counts 2."""
    features = features.copy()
    for event in ["acceleration", "braking", "turning"]:
        features[f"{event}_weighted_per10km"] = (features[f"{event}_per10km"]
                                                 + features[f"{event}_high_med_per10km"])
    return features


def behaviour_score(risk, allowance, half_at):
    """Score out of 100: 100 up to the allowance, then halves every `half_at` units of extra risk."""
    extra = np.clip(np.asarray(risk, dtype=float) - allowance, 0, None)
    return 100 * 0.5 ** (extra / half_at)


def score_trips(features, params=None):
    """One row per trip: a score out of 100 for each behaviour, plus the overall average."""
    params = params or SCORE_PARAMS
    features = add_weighted_events(features)
    scores = pd.DataFrame(index=features.index)
    for behaviour, column in BEHAVIOURS.items():
        scores[behaviour] = behaviour_score(features[column], **params[behaviour])
    scores["total"] = scores[list(BEHAVIOURS)].mean(axis=1)
    return scores.round(1)


def fit_curve(risk, app_score, n_allowance=25, n_half=80):
    """Try many (allowance, half_at) pairs; keep the one closest to the app's score.

    "Closest" = smallest average gap in points between our score and the app's score.
    Returns (allowance, half_at, average_gap).
    """
    risk, app_score = np.asarray(risk, float), np.asarray(app_score, float)
    best = None
    for allowance in np.linspace(0, np.quantile(risk, 0.6), n_allowance):
        for half_at in np.geomspace(0.03, 150, n_half):
            gap = np.abs(behaviour_score(risk, allowance, half_at) - app_score).mean()
            if best is None or gap < best[2]:
                best = (allowance, half_at, gap)
    return tuple(round(float(v), 2) for v in best)
