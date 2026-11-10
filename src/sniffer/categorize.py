"""Merchant category classifier (character n-gram TF-IDF + logistic regression)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline

BILL_CATEGORIES = {"housing", "utilities", "insurance"}


def _pipe() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=2000, C=20.0)),
        ]
    )


class CategoryModel:
    def __init__(self) -> None:
        self.pipe = _pipe()
        self.metrics: dict[str, Any] = {}

    def fit(self, merchants: pd.DataFrame) -> dict[str, Any]:
        x, y = merchants["merchant"].tolist(), merchants["category"].tolist()
        folds = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
        scores = cross_val_score(_pipe(), x, y, cv=folds, scoring="accuracy")
        self.pipe.fit(x, y)
        self.metrics = {"category_cv_accuracy": round(float(np.mean(scores)), 3), "n_merchants": len(x)}
        return self.metrics

    def predict(self, merchant: str) -> str:
        return str(self.pipe.predict([merchant])[0])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipe": self.pipe, "metrics": self.metrics}, path)

    @classmethod
    def load(cls, path: Path) -> CategoryModel:
        blob = joblib.load(path)
        m = cls()
        m.pipe, m.metrics = blob["pipe"], blob["metrics"]
        return m
