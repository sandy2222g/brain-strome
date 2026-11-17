"""Holt-Winters (additive) demand forecasting for a small cafe, from scratch (synthetic sales)."""

from __future__ import annotations

import csv
import itertools
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "sales.csv"
SEASON = 7
GRID = (0.1, 0.3, 0.5, 0.7)
Z_90 = 1.2816  # one-sided 90% service level


class ForecastError(ValueError):
    """Raised for invalid input."""


def load() -> tuple[list[date], list[float]]:
    with DATA.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [date.fromisoformat(r["date"]) for r in rows], [float(r["sold"]) for r in rows]


@dataclass
class State:
    level: float
    trend: float
    seasonal: list[float]  # seasonal[i] applies to the day i steps after the last observed day (cyclic)


def _init(y: list[float]) -> tuple[float, float, list[float]]:
    first, second = y[:SEASON], y[SEASON : 2 * SEASON]
    m1, m2 = sum(first) / SEASON, sum(second) / SEASON
    return m1, (m2 - m1) / SEASON, [v - m1 for v in first]


def run(y: list[float], alpha: float, beta: float, gamma: float) -> tuple[State, list[float]]:
    """Run the filter; return the final state and the one-step-ahead errors from day SEASON onward."""
    level, trend, seas = _init(y)
    errors = []
    for t in range(SEASON, len(y)):
        s = seas[t % SEASON]
        pred = level + trend + s
        errors.append(y[t] - pred)
        new_level = alpha * (y[t] - s) + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        seas[t % SEASON] = gamma * (y[t] - new_level) + (1 - gamma) * s
        level = new_level
    n = len(y)
    return State(level, trend, [seas[(n + i) % SEASON] for i in range(SEASON)]), errors


def fit(y: list[float]) -> tuple[tuple[float, float, float], State, float]:
    """Grid-search (alpha, beta, gamma) on one-step squared error; return params, final state and error sigma."""
    if len(y) < 3 * SEASON:
        raise ForecastError(f"need at least {3 * SEASON} days of history")
    if any(v < 0 for v in y):
        raise ForecastError("sales cannot be negative")
    best: tuple[float, tuple[float, float, float]] | None = None
    for a, b, g in itertools.product(GRID, repeat=3):
        _, errs = run(y, a, b, g)
        sse = sum(e * e for e in errs)
        if best is None or sse < best[0]:
            best = (sse, (a, b, g))
    assert best is not None
    state, errs = run(y, *best[1])
    sigma = math.sqrt(sum(e * e for e in errs) / len(errs))
    return best[1], state, sigma


def forecast(state: State, h: int) -> list[float]:
    return [max(0.0, state.level + (k + 1) * state.trend + state.seasonal[k % SEASON]) for k in range(h)]


def seasonal_naive(y: list[float], h: int) -> list[float]:
    """Baseline: each day equals the same weekday last week."""
    return [y[len(y) - SEASON + (k % SEASON)] for k in range(h)]


def mae(pred: list[float], actual: list[float]) -> float:
    return sum(abs(p - a) for p, a in zip(pred, actual, strict=True)) / len(actual)


def evaluate(holdout: int = 14) -> dict[str, object]:
    dates, y = load()
    train, test = y[:-holdout], y[-holdout:]
    params, state, _ = fit(train)
    hw, naive = forecast(state, holdout), seasonal_naive(train, holdout)
    return {
        "holdout_days": holdout,
        "params": list(params),
        "mae_holdw": round(mae(hw, test), 2),
        "mae_naive": round(mae(naive, test), 2),
        "dates": [d.isoformat() for d in dates],
        "history": y[:-holdout],
        "actual": test,
        "forecast": [round(v, 1) for v in hw],
        "naive": [round(v, 1) for v in naive],
    }


def plan_bakes(y: list[float], last_day: date, h: int = 7) -> dict[str, object]:
    """Forecast the next h days and a bake quantity covering demand with ~90% probability."""
    if not 1 <= h <= 28:
        raise ForecastError("h must be between 1 and 28")
    params, state, sigma = fit(y)
    fc = forecast(state, h)
    days = [
        {
            "date": (last_day + timedelta(days=k + 1)).isoformat(),
            "weekday": (last_day + timedelta(days=k + 1)).strftime("%a"),
            "forecast": round(v, 1),
            "bake": math.ceil(v + Z_90 * sigma),
        }
        for k, v in enumerate(fc)
    ]
    return {"params": list(params), "sigma": round(sigma, 2), "days": days}
