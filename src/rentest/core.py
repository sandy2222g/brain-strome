"""Ridge regression from scratch (normal equations) on synthetic flat-rent data."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "rents.csv"
FEATURES = ("area_m2", "bedrooms", "distance_km", "age_years")
LAMBDA = 1.0  # ridge strength, applied to standardised features (intercept is not penalised)


class RentError(ValueError):
    """Raised for invalid input."""


def load_rows() -> tuple[list[list[float]], list[float]]:
    with DATA.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [[float(r[f]) for f in FEATURES] for r in rows], [float(r["rent"]) for r in rows]


Split = tuple[list[list[float]], list[float], list[list[float]], list[float]]


def split(x: list[list[float]], y: list[float], every: int = 5) -> Split:
    """Deterministic split: every `every`-th row is held out for testing."""
    tr = [i for i in range(len(x)) if i % every]
    te = [i for i in range(len(x)) if not i % every]
    return [x[i] for i in tr], [y[i] for i in tr], [x[i] for i in te], [y[i] for i in te]


def solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gauss-Jordan elimination with partial pivoting."""
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            raise RentError("singular system: features are linearly dependent")
        m[col], m[piv] = m[piv], m[col]
        m[col] = [v / m[col][col] for v in m[col]]
        for r in range(n):
            if r != col:
                f = m[r][col]
                m[r] = [v - f * p for v, p in zip(m[r], m[col], strict=True)]
    return [m[i][n] for i in range(n)]


@dataclass
class Model:
    mean: list[float]
    scale: list[float]
    intercept: float
    coef: list[float]  # on standardised features

    def predict(self, features: list[float]) -> float:
        if len(features) != len(FEATURES):
            raise RentError(f"expected {len(FEATURES)} features")
        z = [(v - m) / s for v, m, s in zip(features, self.mean, self.scale, strict=True)]
        return self.intercept + sum(c * v for c, v in zip(self.coef, z, strict=True))

    def per_unit(self) -> dict[str, float]:
        """Change in rent for one more unit of each feature, in original units."""
        return {f: c / s for f, c, s in zip(FEATURES, self.coef, self.scale, strict=True)}


def fit(x: list[list[float]], y: list[float], lam: float = LAMBDA) -> Model:
    if len(x) < len(FEATURES) + 2 or len(x) != len(y):
        raise RentError("need more training rows than features")
    n, p = len(x), len(FEATURES)
    mean = [sum(r[j] for r in x) / n for j in range(p)]
    scale = [math.sqrt(sum((r[j] - mean[j]) ** 2 for r in x) / n) or 1.0 for j in range(p)]
    z = [[(r[j] - mean[j]) / scale[j] for j in range(p)] for r in x]
    ybar = sum(y) / n
    yc = [v - ybar for v in y]
    gram = [[sum(row[i] * row[j] for row in z) + (lam if i == j else 0.0) for j in range(p)] for i in range(p)]
    rhs = [sum(row[i] * t for row, t in zip(z, yc, strict=True)) for i in range(p)]
    return Model(mean, scale, ybar, solve(gram, rhs))


def metrics(model: Model, x: list[list[float]], y: list[float]) -> dict[str, float]:
    pred = [model.predict(r) for r in x]
    sse = sum((p - t) ** 2 for p, t in zip(pred, y, strict=True))
    ybar = sum(y) / len(y)
    sst = sum((t - ybar) ** 2 for t in y)
    return {"rmse": round(math.sqrt(sse / len(y)), 2), "r2": round(1 - sse / sst, 4)}


def baseline_metrics(train_y: list[float], test_y: list[float]) -> dict[str, float]:
    """Baseline: always predict the training mean rent."""
    mean = sum(train_y) / len(train_y)
    sse = sum((mean - t) ** 2 for t in test_y)
    ybar = sum(test_y) / len(test_y)
    sst = sum((t - ybar) ** 2 for t in test_y)
    return {"rmse": round(math.sqrt(sse / len(test_y)), 2), "r2": round(1 - sse / sst, 4) if sst else 0.0}


def evaluate() -> dict[str, object]:
    x, y = load_rows()
    xt, yt, xe, ye = split(x, y)
    model = fit(xt, yt)
    return {
        "train": len(xt), "test": len(xe),
        "model": metrics(model, xe, ye), "baseline": baseline_metrics(yt, ye),
        "per_unit": {k: round(v, 2) for k, v in model.per_unit().items()},
    }


def trained() -> Model:
    x, y = load_rows()
    return fit(x, y)
