"""The ML helper: fills skipped answers, estimates a footprint from quick answers with a band, ranks peers.

The calculator stays the main engine. This model only (1) imputes the detailed answers a household skipped,
(2) gives a quick estimate with an uncertainty band, and (3) places the result among synthetic households.
"""

from __future__ import annotations

import bisect
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from carbon.schema import DETAILED_FIELDS, Answers

CATEGORICAL = ["heating", "insulation", "commute_mode", "car_type", "diet", "shopping_level", "recycling"]
NUMERIC = ["log_size", "log_home", "thermostat_c", "flights_short", "flights_long", "meat_free_days", "green_tariff"]
QUICK_FIELDS = [
    "household_size",
    "home_size_m2",
    "thermostat_c",
    "flights_short",
    "flights_long",
    "meat_free_days",
    "green_tariff",
    *CATEGORICAL,
]
TARGET = "footprint_t"
BAND_LEVEL = 0.8
FIELD_MINIMUMS = {name: 0.0 for name in DETAILED_FIELDS}


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df[QUICK_FIELDS].copy()
    out["green_tariff"] = out["green_tariff"].astype(int)
    out["log_size"] = np.log(out["household_size"].astype(float))
    out["log_home"] = np.log(out["home_size_m2"].astype(float))
    return out[NUMERIC + CATEGORICAL]


def answers_frame(answers: Answers) -> pd.DataFrame:
    return feature_frame(pd.DataFrame([answers.model_dump()]))


def load_dataset(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def percentile_rank(value: float, sorted_reference: list[float]) -> float:
    """Percent of reference values below `value`, counting ties as half (0 to 100)."""
    if not sorted_reference:
        raise ValueError("empty reference")
    below = bisect.bisect_left(sorted_reference, value)
    equal = bisect.bisect_right(sorted_reference, value) - below
    return round(100 * (below + 0.5 * equal) / len(sorted_reference), 1)


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric: Any = StandardScaler() if scale else "passthrough"
    return ColumnTransformer([("num", numeric, NUMERIC), ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])


class CarbonModel:
    """Imputer (ridge), footprint estimator (gradient boosting quantiles + calibrated band), peer reference."""

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.imputer: Pipeline | None = None
        self.quantiles: dict[float, Pipeline] = {}
        self.band_pad_t = 0.0
        self.reference_per_person: list[float] = []
        self.metrics: dict[str, Any] = {}

    # ---- training -------------------------------------------------------------------------------------------
    def fit(self, df: pd.DataFrame) -> CarbonModel:
        train, rest = train_test_split(df, test_size=0.3, random_state=self.seed)
        calib, test = train_test_split(rest, test_size=0.5, random_state=self.seed)
        x_train, y_train = feature_frame(train), train[TARGET].to_numpy()

        for alpha in (0.1, 0.5, 0.9):
            gbr = GradientBoostingRegressor(
                loss="quantile",
                alpha=alpha,
                n_estimators=250,
                max_depth=3,
                learning_rate=0.06,
                subsample=0.8,
                random_state=self.seed,
            )
            self.quantiles[alpha] = Pipeline([("prep", _preprocessor(False)), ("gbr", gbr)]).fit(x_train, y_train)

        # Conformalised quantile regression: widen the band by the amount that makes calibration coverage hold.
        lo_c, hi_c = self._band_raw(feature_frame(calib))
        y_c = calib[TARGET].to_numpy()
        scores = np.maximum(lo_c - y_c, y_c - hi_c)
        n = len(scores)
        level = min(1.0, np.ceil((n + 1) * BAND_LEVEL) / n)
        self.band_pad_t = float(max(0.0, np.quantile(scores, level)))

        targets = np.log1p(train[list(DETAILED_FIELDS)].to_numpy())
        self.imputer = Pipeline([("prep", _preprocessor(True)), ("ridge", Ridge(alpha=3.0))]).fit(x_train, targets)

        self.reference_per_person = sorted((df[TARGET] / df["household_size"]).round(4).tolist())
        self.metrics = self._evaluate(test, train)
        return self

    def _band_raw(self, x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        lo = self.quantiles[0.1].predict(x)
        hi = self.quantiles[0.9].predict(x)
        return np.minimum(lo, hi), np.maximum(lo, hi)

    def _evaluate(self, test: pd.DataFrame, train: pd.DataFrame) -> dict[str, Any]:
        x, y = feature_frame(test), test[TARGET].to_numpy()
        mid = self.quantiles[0.5].predict(x)
        lo, hi = self._band_raw(x)
        lo, hi = np.maximum(0, lo - self.band_pad_t), hi + self.band_pad_t
        fills = self._predict_fields(x)
        per_field = {}
        for i, name in enumerate(DETAILED_FIELDS):
            truth = test[name].to_numpy()
            per_field[name] = {
                "mae": round(float(mean_absolute_error(truth, fills[:, i])), 3),
                "r2": round(float(r2_score(truth, fills[:, i])), 3),
            }
        baseline = np.full_like(y, train[TARGET].mean(), dtype=float)
        return {
            "n_train": len(train),
            "n_test": len(test),
            "footprint_mae_t": round(float(mean_absolute_error(y, mid)), 3),
            "footprint_r2": round(float(r2_score(y, mid)), 3),
            "baseline_mae_t": round(float(mean_absolute_error(y, baseline)), 3),
            "band_nominal": BAND_LEVEL,
            "band_coverage": round(float(np.mean((y >= lo) & (y <= hi))), 3),
            "band_mean_width_t": round(float(np.mean(hi - lo)), 3),
            "imputer": per_field,
        }

    # ---- prediction -----------------------------------------------------------------------------------------
    def _predict_fields(self, x: pd.DataFrame) -> np.ndarray:
        assert self.imputer is not None
        return np.maximum(np.expm1(self.imputer.predict(x)), 0)

    def fill(self, answers: Answers) -> tuple[Answers, dict[str, float]]:
        """Return answers with every skipped detailed field estimated, plus the values that were filled in."""
        missing = answers.missing()
        if not missing:
            return answers, {}
        values = self._predict_fields(answers_frame(answers))[0]
        filled: dict[str, float] = {}
        for i, name in enumerate(DETAILED_FIELDS):
            if name in missing:
                v = float(values[i])
                filled[name] = round(v) if name in ("clothes_items_year", "electricity_kwh_month") else round(v, 1)
        return answers.model_copy(update=filled), filled

    def estimate(self, answers: Answers) -> dict[str, float]:
        """Quick estimate (tonnes a year) from the quick answers alone, with an 80% band."""
        x = answers_frame(answers)
        mid = float(self.quantiles[0.5].predict(x)[0])
        lo, hi = self._band_raw(x)
        low = max(0.0, float(lo[0]) - self.band_pad_t)
        high = float(hi[0]) + self.band_pad_t
        return {"tonnes": round(max(mid, 0.0), 2), "low_t": round(low, 2), "high_t": round(max(high, mid), 2)}

    def peer_percentile(self, total_t: float, household_size: int) -> float:
        """Where this household's per-person footprint sits among synthetic households (higher = more CO2e)."""
        return percentile_rank(total_t / household_size, self.reference_per_person)

    # ---- persistence ----------------------------------------------------------------------------------------
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path) -> CarbonModel:
        model = joblib.load(path)
        if not isinstance(model, CarbonModel):
            raise TypeError("not a CarbonModel file")
        return model
