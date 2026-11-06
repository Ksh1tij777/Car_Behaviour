"""Copy the charts used in the report out of the executed notebooks into report/figures/."""

import base64
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "figures"

# (output name, notebook, text that appears in the cell that draws the chart)
FIGURES = [
    ("fig1_accelerations.png", "01_explore_data.ipynb", "D1, secondary road: accelerations"),
    ("fig2_detector.png", "02_event_detection.ipynb", 'row = trips[(trips.driver == "D1")'),
    ("fig3_tuning.png", "02_event_detection.ipynb", "train_ids = trips"),
    ("fig4_event_rates.png", "02_event_detection.ipynb", "per_trip = []"),
    ("fig5_behaviours.png", "03_behaviour_features.ipynb", "titles = {"),
    ("fig6_score_vs_app.png", "04_scores.ipynb", "Overall trip score, one dot per trip"),
    ("fig7_scores_by_style.png", "04_scores.ipynb", "Where each driving style loses points"),
    ("fig8_risk_map.png", "05_classification.ipynb", "idx = cl.risk_indexes(scores)"),
    ("fig9_accuracy.png", "05_classification.ipynb", "Predicting Normal / Drowsy / Aggressive"),
    ("fig10_safety_bands.png", "06_safety_score.ipynb", 'ax.set_title("Each dot is one trip")'),
    ("fig11_driver_scores.png", "06_safety_score.ipynb", "Each driver's score in each driving style"),
]

OUT.mkdir(exist_ok=True)
for name, notebook, marker in FIGURES:
    nb = nbformat.read(ROOT / "notebooks" / notebook, as_version=4)
    cell = next(c for c in nb.cells if c.cell_type == "code" and marker in c.source)
    png = next(o["data"]["image/png"] for o in cell.outputs if "image/png" in o.get("data", {}))
    (OUT / name).write_bytes(base64.b64decode(png))
    print("saved", name)
