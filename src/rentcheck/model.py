"""Three quantile gradient-boosting models (p10 / p50 / p90) with split-conformal widening."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from rentcheck.config import (
    CATEGORICAL,
    DISTRICTS,
    FEATURES,
    LABELS,
    MODEL_PATH,
    NUMERIC,
    QUANTILES,
    SEED,
    TARGET,
    TARGET_COVERAGE,
)


@dataclass(frozen=True)
class Range:
    p10: float
    p50: float
    p90: float


def _pipeline(alpha: float) -> Pipeline:
    pre = ColumnTransformer(
        [("district", OneHotEncoder(categories=[list(DISTRICTS)], sparse_output=False), CATEGORICAL)],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    gbr = GradientBoostingRegressor(
        loss="quantile",
        alpha=alpha,
        n_estimators=260,
        learning_rate=0.06,
        max_depth=3,
        subsample=0.8,
        min_samples_leaf=15,
        random_state=SEED,
    )
    return Pipeline([("pre", pre), ("gbr", gbr)])


def _round5(x: float) -> float:
    return float(np.round(x / 5.0) * 5.0)


class RentModel:
    """Predicts a fair-rent range. Models are fitted on log(rent) so effects are proportional."""

    def __init__(self) -> None:
        self.pipes: dict[float, Pipeline] = {}
        self.offset = 0.0  # conformal widening on the log scale
        self.baselines: dict[str, dict[str, float]] = {}
        self.listings: pd.DataFrame = pd.DataFrame()
        self.metrics: dict[str, Any] = {}

    # ----- training -----------------------------------------------------------------
    def fit(self, df: pd.DataFrame) -> RentModel:
        """Fit on 60% of ``df``, calibrate the band on 20%, report held-out metrics on the last 20%."""
        self.listings = df.reset_index(drop=True)
        rest, test = train_test_split(df, test_size=0.2, random_state=SEED)
        train, calib = train_test_split(rest, test_size=0.25, random_state=SEED)
        y = np.log(train[TARGET].to_numpy())
        self.pipes = {q: _pipeline(q).fit(train[FEATURES], y) for q in QUANTILES}

        # Conformalised quantile regression: widen the band so ~80% of unseen rents fall inside.
        raw_lo, _, raw_hi = self._log_quantiles(calib[FEATURES])
        yc = np.log(calib[TARGET].to_numpy())
        score = np.maximum(raw_lo - yc, yc - raw_hi)
        n = len(score)
        level = min(1.0, np.ceil((n + 1) * TARGET_COVERAGE) / n)
        self.offset = float(max(0.0, np.quantile(score, level)))

        self._fit_baselines(train)
        self.metrics = self._evaluate(test, len(train), len(calib))
        return self

    def _fit_baselines(self, df: pd.DataFrame) -> None:
        for name, grp in df.groupby("district"):
            self.baselines[str(name)] = {c: float(grp[c].median()) for c in NUMERIC}

    def _log_quantiles(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        preds = np.vstack([self.pipes[q].predict(X[FEATURES]) for q in QUANTILES])
        preds = np.sort(preds, axis=0)  # repair any quantile crossing
        return preds[0], preds[1], preds[2]

    def predict_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        lo, mid, hi = self._log_quantiles(X)
        return pd.DataFrame(
            {"p10": np.exp(lo - self.offset), "p50": np.exp(mid), "p90": np.exp(hi + self.offset)}, index=X.index
        )

    def _evaluate(self, test: pd.DataFrame, n_train: int, n_calib: int) -> dict[str, Any]:
        pred = self.predict_frame(test)
        y = test[TARGET].to_numpy(dtype=float)
        raw_lo, _, raw_hi = self._log_quantiles(test)
        raw_cov = float(np.mean((np.log(y) >= raw_lo) & (np.log(y) <= raw_hi)))
        inside = (y >= pred["p10"].to_numpy()) & (y <= pred["p90"].to_numpy())
        return {
            "mae": round(float(np.mean(np.abs(y - pred["p50"].to_numpy()))), 2),
            "mape_pct": round(float(np.mean(np.abs(y - pred["p50"].to_numpy()) / y) * 100), 2),
            "interval_coverage": round(float(inside.mean()), 4),
            "raw_interval_coverage": round(raw_cov, 4),
            "target_coverage": TARGET_COVERAGE,
            "below_p10_share": round(float(np.mean(y < pred["p10"].to_numpy())), 4),
            "above_p90_share": round(float(np.mean(y > pred["p90"].to_numpy())), 4),
            "median_band_width": round(float(np.median(pred["p90"] - pred["p10"])), 2),
            "n_train": n_train,
            "n_calibration": n_calib,
            "n_test": len(test),
            "conformal_offset_log": round(self.offset, 4),
        }

    # ----- inference ----------------------------------------------------------------
    @staticmethod
    def _frame(listing: dict[str, Any]) -> pd.DataFrame:
        return pd.DataFrame([{k: listing[k] for k in FEATURES}])

    def estimate_range(self, listing: dict[str, Any]) -> Range:
        row = self.predict_frame(self._frame(listing)).iloc[0]
        return Range(_round5(row["p10"]), _round5(row["p50"]), _round5(row["p90"]))

    def explain(self, listing: dict[str, Any]) -> dict[str, Any]:
        """Ablation: swap one feature at a time for the district-typical value and see how the median moves."""
        base = self.baselines[listing["district"]]
        rows = [dict(listing)]
        for f in NUMERIC:
            alt = dict(listing)
            alt[f] = base[f]
            rows.append(alt)
        rows.append({**listing, **base})
        X = pd.DataFrame(rows)[FEATURES]
        mids = np.exp(self.pipes[0.5].predict(X))
        actual, ablated, typical = float(mids[0]), mids[1:-1], float(mids[-1])
        items = []
        for f, a in zip(NUMERIC, ablated, strict=True):
            delta = actual - float(a)
            if abs(delta) < 0.5:
                continue
            items.append(
                {
                    "feature": f,
                    "label": LABELS[f],
                    "amount": round(delta, 1),
                    "yours": listing[f],
                    "typical": base[f],
                }
            )
        items.sort(key=lambda d: abs(d["amount"]), reverse=True)
        other = actual - typical - sum(i["amount"] for i in items)
        return {
            "typical_flat": round(typical, 1),
            "estimate": round(actual, 1),
            "drivers": items,
            "interactions": round(other, 1),
        }

    def district_table(self) -> list[dict[str, Any]]:
        d = self.listings.assign(ppm=self.listings[TARGET] / self.listings["size_m2"])
        g = d.groupby("district").agg(
            median_rent=(TARGET, "median"), median_per_m2=("ppm", "median"), listings=(TARGET, "size")
        )
        out = [
            {
                "district": name,
                "median_rent": float(r.median_rent),
                "median_per_m2": round(float(r.median_per_m2), 2),
                "listings": int(r.listings),
            }
            for name, r in g.iterrows()
        ]
        return sorted(out, key=lambda r: r["median_per_m2"], reverse=True)

    # ----- persistence --------------------------------------------------------------
    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path = MODEL_PATH) -> RentModel:
        model = joblib.load(path)
        if not isinstance(model, RentModel):
            raise TypeError("not a RentModel file")
        return model
