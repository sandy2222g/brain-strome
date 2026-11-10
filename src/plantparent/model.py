"""Watering-interval model: gradient boosting on log(days) with a measured uncertainty band."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC = ["base_days", "pot_cm", "temp_c", "humidity"]
CATEGORICAL = ["material", "light", "season"]
FEATURES = NUMERIC + CATEGORICAL
MATERIALS = ["terracotta", "plastic", "ceramic"]
LIGHTS = ["low", "medium", "bright"]
SEASONS = ["winter", "spring", "summer", "autumn"]


def season_for(month: int, hemisphere: str = "north") -> str:
    """Meteorological season for a month; flips for the southern hemisphere."""
    season = {
        12: "winter",
        1: "winter",
        2: "winter",
        3: "spring",
        4: "spring",
        5: "spring",
        6: "summer",
        7: "summer",
        8: "summer",
    }.get(month, "autumn")
    if hemisphere == "south":
        season = {"winter": "summer", "summer": "winter", "spring": "autumn", "autumn": "spring"}[season]
    return season


class IntervalModel:
    def __init__(self) -> None:
        pre = ColumnTransformer(
            [("cat", OneHotEncoder(categories=[MATERIALS, LIGHTS, SEASONS], handle_unknown="ignore"), CATEGORICAL)],
            remainder="passthrough",
        )
        self.pipe = Pipeline(
            [("pre", pre), ("gb", GradientBoostingRegressor(n_estimators=250, max_depth=3, random_state=0))]
        )
        self.rel_error_p80 = 0.15
        self.metrics: dict[str, Any] = {}

    def fit(self, df: pd.DataFrame, seed: int = 0) -> dict[str, Any]:
        x, y = df[FEATURES], np.log(df["days_until_dry"])
        x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.25, random_state=seed)
        self.pipe.fit(x_tr, y_tr)
        pred = np.exp(self.pipe.predict(x_te))
        truth = np.exp(y_te.to_numpy())
        rel = np.abs(pred - truth) / truth
        self.rel_error_p80 = float(np.quantile(rel, 0.8))
        baseline = float(mean_absolute_error(truth, x_te["base_days"]))
        self.metrics = {
            "test_mae_days": round(float(mean_absolute_error(truth, pred)), 2),
            "baseline_mae_days_species_only": round(baseline, 2),
            "p80_relative_error": round(self.rel_error_p80, 3),
            "n_train": int(len(x_tr)),
        }
        return self.metrics

    def predict_days(self, rows: list[dict[str, Any]]) -> np.ndarray:
        return np.exp(self.pipe.predict(pd.DataFrame(rows)[FEATURES]))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipe": self.pipe, "metrics": self.metrics, "err": self.rel_error_p80}, path)

    @classmethod
    def load(cls, path: Path) -> IntervalModel:
        blob = joblib.load(path)
        m = cls()
        m.pipe, m.metrics, m.rel_error_p80 = blob["pipe"], blob["metrics"], blob["err"]
        return m
