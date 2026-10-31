"""
Step 5: predict whether a trip was NORMAL, DROWSY or AGGRESSIVE.

Two approaches:
  1. A simple rule on two risk indexes built from the Step 4 scores (easy to explain).
  2. Machine-learning models (scikit-learn) on the 7 risk numbers.

Both are tested with "leave one driver out": train on 5 drivers, predict the 6th, repeat for
every driver. So every prediction is made for a driver the method has never seen.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict

# Which Step 4 scores belong to which kind of risky driving
AGGRESSIVE_SCORES = ["accelerations", "brakings", "turnings", "overspeeding", "car_following"]
DROWSY_SCORES = ["weaving", "drifting"]

# Cut-offs learned from all 40 trips with fit_rule() (see notebooks/05_classification.ipynb)
RULE_CUTS = {"aggressive_risk": 26.3, "drowsy_risk": 30.9}

LABELS = ["NORMAL", "DROWSY", "AGGRESSIVE"]


def risk_indexes(scores):
    """Two numbers per trip, 0 = no risk, 100 = maximum risk.

    aggressive_risk = points lost on the 5 "aggressive" scores (average)
    drowsy_risk     = points lost on weaving and drifting (average)
    """
    return pd.DataFrame({
        "aggressive_risk": 100 - scores[AGGRESSIVE_SCORES].mean(axis=1),
        "drowsy_risk": 100 - scores[DROWSY_SCORES].mean(axis=1),
    }, index=scores.index)


def fit_rule(indexes, labels):
    """Put each cut-off halfway between the groups it has to separate.

    aggressive cut: between the lowest AGGRESSIVE trip and the highest non-aggressive trip
    drowsy cut:     between the lowest DROWSY trip and the highest NORMAL trip
    """
    a, d = indexes["aggressive_risk"], indexes["drowsy_risk"]
    return {
        "aggressive_risk": round((a[labels == "AGGRESSIVE"].min() + a[labels != "AGGRESSIVE"].max()) / 2, 1),
        "drowsy_risk": round((d[labels == "DROWSY"].min() + d[labels == "NORMAL"].max()) / 2, 1),
    }


def predict_rule(indexes, cuts=None):
    """AGGRESSIVE if aggressive_risk is above its cut, else DROWSY if drowsy_risk is above its cut,
    else NORMAL."""
    cuts = cuts or RULE_CUTS
    return pd.Series(np.where(indexes["aggressive_risk"] > cuts["aggressive_risk"], "AGGRESSIVE",
                              np.where(indexes["drowsy_risk"] > cuts["drowsy_risk"], "DROWSY", "NORMAL")),
                     index=indexes.index)


def rule_leave_one_driver_out(indexes, labels, drivers):
    """Learn the cut-offs on 5 drivers, predict the 6th; repeat for every driver."""
    predictions = pd.Series(index=indexes.index, dtype=object)
    cuts_per_driver = {}
    for driver in sorted(drivers.unique()):
        test = drivers == driver
        cuts = fit_rule(indexes[~test], labels[~test])
        predictions[test] = predict_rule(indexes[test], cuts)
        cuts_per_driver[driver] = cuts
    return predictions, pd.DataFrame(cuts_per_driver).T


def model_leave_one_driver_out(model, X, labels, drivers):
    """Same test for a scikit-learn model: train on 5 drivers, predict the 6th."""
    return pd.Series(cross_val_predict(model, X, labels, groups=drivers, cv=LeaveOneGroupOut()),
                     index=X.index)
