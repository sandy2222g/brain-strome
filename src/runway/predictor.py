"""Ridge regression: expected exam score (0-100) from study habits."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

FEATURES = ["total_hours", "n_sessions", "spacing_days", "difficulty", "prior_confidence", "sleep_hours"]


class ScoreModel:
    def __init__(self) -> None:
        self.pipe = Pipeline(
            [
                ("poly", PolynomialFeatures(2, include_bias=False)),
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=3.0)),
            ]
        )
        self.metrics: dict[str, Any] = {}

    def fit(self, df: pd.DataFrame, seed: int = 42) -> dict[str, Any]:
        x_tr, x_te, y_tr, y_te = train_test_split(df[FEATURES], df["score"], test_size=0.25, random_state=seed)
        self.pipe.fit(x_tr, y_tr)
        pred = self.pipe.predict(x_te)
        baseline = float(mean_absolute_error(y_te, np.full(len(y_te), y_tr.mean())))
        self.metrics = {
            "test_mae": round(float(mean_absolute_error(y_te, pred)), 2),
            "baseline_mae": round(baseline, 2),
            "test_r2": round(float(r2_score(y_te, pred)), 3),
            "n_train": len(x_tr),
        }
        return self.metrics

    def predict(self, **features: float) -> float:
        row = pd.DataFrame([{k: features[k] for k in FEATURES}])
        return float(np.clip(self.pipe.predict(row)[0], 0, 100))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipe": self.pipe, "metrics": self.metrics}, path)

    @classmethod
    def load(cls, path: Path) -> ScoreModel:
        blob = joblib.load(path)
        m = cls()
        m.pipe, m.metrics = blob["pipe"], blob["metrics"]
        return m


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(FEATURES + ["score"]) - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    return df.dropna()
