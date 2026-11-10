"""Model training (with model selection + calibration), fairness audit and inference."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = ["age", "lead_days", "prior_visits", "prior_noshows", "hour", "weekday", "reminder_sent", "distance_km"]
CATEGORICAL = ["insurance"]
FEATURES = NUMERIC + CATEGORICAL
TARGET = "no_show"
INSURANCE_VALUES = ["public", "private", "none"]

# Risk bands (probability of no-show) and the action each triggers.
BANDS = [(0.55, "high", "Phone call to confirm; offer to reschedule; candidate for double-booking"),
         (0.30, "medium", "Send an extra SMS reminder 24h before"),
         (0.0, "low", "Standard reminder")]


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC),
            ("cat", OneHotEncoder(categories=[INSURANCE_VALUES], handle_unknown="ignore"), CATEGORICAL),
        ]
    )


def _candidates() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [("prep", _preprocessor()), ("clf", LogisticRegression(max_iter=2000))]
        ),
        "hist_gradient_boosting": Pipeline(
            [("prep", _preprocessor()),
             ("clf", HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=0))]
        ),
    }


def risk_band(p: float) -> tuple[str, str]:
    for threshold, name, action in BANDS:
        if p >= threshold:
            return name, action
    return BANDS[-1][1], BANDS[-1][2]


def age_group(age: float) -> str:
    return "<25" if age < 25 else ("25-60" if age <= 60 else ">60")


def fairness_audit(df: pd.DataFrame, proba: np.ndarray, threshold: float = 0.3) -> dict[str, Any]:
    """Per-group flag rate, actual no-show rate and AUC, for age band and insurance."""
    audit: dict[str, Any] = {}
    work = df.assign(_p=proba, _flag=(proba >= threshold).astype(int), _age=df["age"].map(age_group))
    for col, label in (("_age", "age_group"), ("insurance", "insurance")):
        rows = {}
        for g, sub in work.groupby(col):
            auc = roc_auc_score(sub[TARGET], sub["_p"]) if sub[TARGET].nunique() == 2 else None
            rows[str(g)] = {
                "n": int(len(sub)),
                "actual_rate": round(float(sub[TARGET].mean()), 3),
                "flag_rate": round(float(sub["_flag"].mean()), 3),
                "auc": None if auc is None else round(float(auc), 3),
            }
        audit[label] = rows
    return audit


@dataclass
class Prediction:
    probability: float
    band: str
    action: str


class NoShowModel:
    def __init__(self) -> None:
        self.pipeline: Any = None
        self.name: str = ""
        self.metrics: dict[str, Any] = {}

    def fit(self, df: pd.DataFrame, seed: int = 42) -> dict[str, Any]:
        x, y = df[FEATURES], df[TARGET]
        x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.25, random_state=seed, stratify=y)
        cv = {n: float(np.mean(cross_val_score(p, x_tr, y_tr, cv=4, scoring="roc_auc")))
              for n, p in _candidates().items()}
        self.name = max(cv, key=lambda k: cv[k])
        # Platt (sigmoid) calibration (isotonic gave hard 0/1 outputs at the extremes), so that
        # predicted probabilities can be summed into expected no-shows.
        self.pipeline = CalibratedClassifierCV(_candidates()[self.name], method="sigmoid", cv=4)
        self.pipeline.fit(x_tr, y_tr)
        proba = self.pipeline.predict_proba(x_te)[:, 1]
        base_rate = float(y_tr.mean())
        self.metrics = {
            "selected_model": self.name,
            "cv_auc": {k: round(v, 4) for k, v in cv.items()},
            "test_auc": round(float(roc_auc_score(y_te, proba)), 4),
            "test_pr_auc": round(float(average_precision_score(y_te, proba)), 4),
            "test_brier": round(float(brier_score_loss(y_te, proba)), 4),
            "baseline_brier": round(float(brier_score_loss(y_te, np.full(len(y_te), base_rate))), 4),
            "base_rate": round(base_rate, 4),
            "n_train": int(len(x_tr)),
            "n_test": int(len(x_te)),
            "fairness": fairness_audit(x_te.assign(**{TARGET: y_te.values}), proba),
        }
        return self.metrics

    def predict_proba(self, records: list[dict[str, Any]]) -> np.ndarray:
        df = pd.DataFrame(records)[FEATURES]
        return np.asarray(self.pipeline.predict_proba(df)[:, 1])

    def predict(self, record: dict[str, Any]) -> Prediction:
        p = float(self.predict_proba([record])[0])
        band, action = risk_band(p)
        return Prediction(round(p, 4), band, action)

    def plan_day(self, records: list[dict[str, Any]], max_overbook_share: float = 0.5) -> dict[str, Any]:
        """Rank a day's appointments and suggest how many extra slots can be double-booked.

        Expected no-shows = sum of calibrated probabilities; we suggest overbooking by
        floor(share * expected), capped, so a typical day still has few patient collisions.
        """
        probs = self.predict_proba(records)
        items = []
        for rec, p in zip(records, probs, strict=True):
            band, action = risk_band(float(p))
            items.append({**rec, "probability": round(float(p), 4), "band": band, "action": action})
        items.sort(key=lambda r: -r["probability"])
        expected = float(probs.sum())
        return {
            "appointments": len(items),
            "expected_no_shows": round(expected, 2),
            "suggested_overbook": int(expected * max_overbook_share),
            "items": items,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "name": self.name, "metrics": self.metrics}, path)
        path.with_suffix(".metrics.json").write_text(json.dumps(self.metrics, indent=2))

    @classmethod
    def load(cls, path: Path) -> NoShowModel:
        blob = joblib.load(path)
        m = cls()
        m.pipeline, m.name, m.metrics = blob["pipeline"], blob["name"], blob["metrics"]
        return m


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(FEATURES + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    return df.dropna(subset=FEATURES + [TARGET])


__all__ = ["NoShowModel", "Prediction", "asdict", "load_dataset"]
