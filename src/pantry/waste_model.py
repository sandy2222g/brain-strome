"""Synthetic 'likely to be wasted' data and the scikit-learn model trained on it.

The label generator encodes plausible behaviour (perishables and long storage raise risk, larger households
use food up faster). It is NOT real consumer data; see README.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from pantry.catalog import CATEGORIES, DEFAULT_STORAGE, SHELF_DAYS, STORAGES

FEATURES = ["category", "storage", "days_since_purchase", "household_size"]
CATEGORY_BIAS = {"leafy": 0.9, "herb": 0.8, "seafood": 0.5, "bakery": 0.5, "produce": 0.3, "meat": 0.2, "dairy": 0.1}


def generate_waste_events(n: int = 6000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cats = rng.choice([c for c in CATEGORIES if c != "other"], n)
    rows = []
    for cat in cats:
        storage = DEFAULT_STORAGE[cat] if rng.random() < 0.75 else str(rng.choice(STORAGES))
        shelf = SHELF_DAYS[cat][storage]
        dsp = int(rng.integers(0, int(shelf * 1.4) + 2))
        hh = int(rng.integers(1, 7))
        ratio = dsp / shelf
        logit = 5.0 * (ratio - 0.8) + CATEGORY_BIAS.get(cat, 0.0) - 0.25 * (hh - 2) - 1.0
        wasted = int(rng.random() < 1 / (1 + np.exp(-logit)))
        rows.append((cat, storage, dsp, hh, wasted))
    return pd.DataFrame(rows, columns=[*FEATURES, "wasted"])


class WasteModel:
    """Predicts the probability that an item will end up in the bin."""

    def __init__(self, seed: int = 0) -> None:
        pre = ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), ["category", "storage"])],
            remainder="passthrough",
        )
        clf = GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=seed)
        self.pipeline = Pipeline([("pre", pre), ("clf", clf)])
        self.seed = seed
        self.metrics: dict[str, Any] = {}

    def fit(self, df: pd.DataFrame) -> WasteModel:
        train, test = train_test_split(df, test_size=0.25, random_state=self.seed, stratify=df["wasted"])
        self.pipeline.fit(train[FEATURES], train["wasted"])
        p = self.pipeline.predict_proba(test[FEATURES])[:, 1]
        base_rate = float(train["wasted"].mean())
        self.metrics = {
            "roc_auc": round(float(roc_auc_score(test["wasted"], p)), 4),
            "brier": round(float(brier_score_loss(test["wasted"], p)), 4),
            "brier_baseline": round(float(brier_score_loss(test["wasted"], np.full(len(test), base_rate))), 4),
            "accuracy": round(float(((p > 0.5) == test["wasted"]).mean()), 4),
            "train_rows": len(train),
            "test_rows": len(test),
            "data": "synthetic",
        }
        return self

    def predict_proba(self, rows: pd.DataFrame) -> np.ndarray:
        return self.pipeline.predict_proba(rows[FEATURES])[:, 1]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path) -> WasteModel:
        obj = joblib.load(path)
        if not isinstance(obj, WasteModel):
            raise TypeError("not a WasteModel artifact")
        return obj
