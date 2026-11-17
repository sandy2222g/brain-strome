"""Softmax (multinomial logistic) regression, written from scratch."""

from __future__ import annotations

import csv
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "days.csv"
CLASSES = ["light", "jumper", "coat", "raincoat"]
FEATURES = ["temp_c", "wind_kph", "rain_mm"]


class OutfitError(ValueError):
    """Invalid input."""


Row = tuple[list[float], str]


def load(path: Path = DATA) -> list[Row]:
    with path.open() as fh:
        return [([float(r[k]) for k in FEATURES], r["outfit"]) for r in csv.DictReader(fh)]


def split(rows: list[Row]) -> tuple[list[Row], list[Row]]:
    """Every 4th row is held out for testing."""
    return [r for i, r in enumerate(rows) if i % 4], [r for i, r in enumerate(rows) if i % 4 == 0]


def scaler(xs: list[list[float]]) -> tuple[list[float], list[float]]:
    n = len(xs)
    mean = [sum(x[j] for x in xs) / n for j in range(len(FEATURES))]
    sd = [math.sqrt(sum((x[j] - mean[j]) ** 2 for x in xs) / n) or 1.0 for j in range(len(FEATURES))]
    return mean, sd


def softmax(z: list[float]) -> list[float]:
    m = max(z)
    e = [math.exp(v - m) for v in z]
    s = sum(e)
    return [v / s for v in e]


class Model:
    def __init__(self, w: list[list[float]], mean: list[float], sd: list[float]) -> None:
        self.w, self.mean, self.sd = w, mean, sd

    def proba(self, x: list[float]) -> list[float]:
        z = [(v - m) / s for v, m, s in zip(x, self.mean, self.sd, strict=True)]
        return softmax([w[0] + sum(wj * zj for wj, zj in zip(w[1:], z, strict=True)) for w in self.w])

    def predict(self, x: list[float]) -> str:
        p = self.proba(x)
        return CLASSES[p.index(max(p))]


def train(rows: list[Row], epochs: int = 600, lr: float = 0.5, l2: float = 1e-3) -> Model:
    if len(rows) < 8:
        raise OutfitError("need at least 8 rows")
    xs = [r[0] for r in rows]
    mean, sd = scaler(xs)
    zs = [[(v - m) / s for v, m, s in zip(x, mean, sd, strict=True)] for x in xs]
    ys = [CLASSES.index(r[1]) for r in rows]
    k, d, n = len(CLASSES), len(FEATURES), len(rows)
    w = [[0.0] * (d + 1) for _ in range(k)]
    for _ in range(epochs):
        grad = [[0.0] * (d + 1) for _ in range(k)]
        for z, y in zip(zs, ys, strict=True):
            p = softmax([wc[0] + sum(a * b for a, b in zip(wc[1:], z, strict=True)) for wc in w])
            for c in range(k):
                err = p[c] - (1.0 if c == y else 0.0)
                grad[c][0] += err
                for j in range(d):
                    grad[c][j + 1] += err * z[j]
        for c in range(k):
            w[c][0] -= lr * grad[c][0] / n
            for j in range(d):
                w[c][j + 1] -= lr * (grad[c][j + 1] / n + l2 * w[c][j + 1])
    return Model(w, mean, sd)


def accuracy(model: Model, rows: list[Row]) -> float:
    return sum(model.predict(x) == y for x, y in rows) / len(rows)


def validate(temp_c: float, wind_kph: float, rain_mm: float) -> list[float]:
    if not -60 <= temp_c <= 60:
        raise OutfitError("temp_c must be within -60..60")
    if wind_kph < 0 or rain_mm < 0:
        raise OutfitError("wind and rain cannot be negative")
    return [temp_c, wind_kph, rain_mm]


def recommend(model: Model, temp_c: float, wind_kph: float, rain_mm: float) -> dict[str, object]:
    p = model.proba(validate(temp_c, wind_kph, rain_mm))
    best = p.index(max(p))
    return {"outfit": CLASSES[best], "confidence": round(p[best], 3),
            "probabilities": {c: round(v, 3) for c, v in zip(CLASSES, p, strict=True)}}


def evaluate() -> dict[str, object]:
    tr, te = split(load())
    m = train(tr)
    maj = max(CLASSES, key=lambda c: sum(1 for _, y in tr if y == c))
    return {"train": len(tr), "test": len(te), "accuracy": round(accuracy(m, te), 3),
            "majority_class": maj, "baseline": round(sum(y == maj for _, y in te) / len(te), 3)}
