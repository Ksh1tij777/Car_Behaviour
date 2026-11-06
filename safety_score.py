"""
Step 6: a driver safety score from 300 to 900, like a CIBIL credit score, for insurance.

    trip overall score (0-100, from Step 4)
        -> safety score 300-900 for the trip
        -> distance-weighted average over a driver's trips
        -> band (Excellent / Good / Average / Risky) -> premium change

Every point lost can be traced back to one of the 7 behaviours, so each score comes with reasons.
"""

import numpy as np
import pandas as pd

from scoring import BEHAVIOURS

MIN_SCORE, MAX_SCORE = 300, 900
FLOOR = 50   # a trip overall score of 50 or less gets the minimum 300 (no trip in the data is below 58)
POINTS_PER_UNIT = (MAX_SCORE - MIN_SCORE) / (100 - FLOOR)   # 12 safety points per point of the 0-100 score

# (lowest score in the band, band name, premium change). Illustrative values for this prototype.
BANDS = [
    (750, "Excellent", -0.20),
    (650, "Good", -0.10),
    (550, "Average", 0.00),
    (MIN_SCORE, "Risky", +0.25),
]


def to_safety_score(overall):
    """Map the Step 4 overall score (0-100) to 300-900: 50 -> 300, 100 -> 900, in a straight line."""
    return np.clip(MIN_SCORE + POINTS_PER_UNIT * (np.asarray(overall, float) - FLOOR), MIN_SCORE, MAX_SCORE)


def band(score):
    """Band name and premium change for one safety score."""
    for lowest, name, premium_change in BANDS:
        if score >= lowest:
            return name, premium_change
    return BANDS[-1][1], BANDS[-1][2]


def points_lost(scores):
    """Safety points lost to each behaviour (one row per trip).

    The overall score is the average of the 7 behaviour scores, so a behaviour that scores s
    costs (100 - s) / 7 overall points, i.e. 12 * (100 - s) / 7 safety points.
    These add up to 900 minus the safety score (unless the score hit the 300 floor).
    """
    return (100 - scores[list(BEHAVIOURS)]) / len(BEHAVIOURS) * POINTS_PER_UNIT


def explain(lost_row, top=2, min_points=10):
    """Short reason text: the behaviours that cost the most points."""
    worst = lost_row.sort_values(ascending=False)
    worst = worst[worst >= min_points].head(top)
    if worst.empty:
        return "no major issues"
    return ", ".join(f"{name.replace('_', '-')} (-{points:.0f})" for name, points in worst.items())


def driver_score(trip_scores, distances):
    """A driver's score over several trips: average of the trip scores, weighted by kilometres."""
    return float(np.average(trip_scores, weights=distances))


def premium(base_premium, score):
    """Yearly premium after the band's discount or surcharge."""
    return base_premium * (1 + band(score)[1])


def score_table(scores, distances):
    """Safety score, band, premium change and reasons for every trip."""
    lost = points_lost(scores)
    out = pd.DataFrame(index=scores.index)
    out["distance_km"] = distances
    out["safety_score"] = to_safety_score(scores["total"]).round(0).astype(int)
    out["band"] = [band(s)[0] for s in out["safety_score"]]
    out["premium_change"] = [band(s)[1] for s in out["safety_score"]]
    out["reasons"] = [explain(lost.loc[i]) for i in scores.index]
    return out
