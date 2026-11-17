"""Linear regression by gradient descent, built from scratch to show why learning rate and scaling matter."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


class GDError(ValueError):
    pass


def make_data(n: int = 120, seed: int = 4) -> tuple[list[float], list[float]]:
    """Made-up scooter trips: distance in km -> fare in dollars (base 1.50 + 0.85 per km + noise)."""
    rng = random.Random(seed)
    xs = [round(rng.uniform(0.5, 15), 2) for _ in range(n)]
    return xs, [round(1.5 + 0.85 * x + rng.gauss(0, 0.7), 2) for x in xs]


def mse(xs: list[float], ys: list[float], w: float, b: float) -> float:
    return sum((w * x + b - y) ** 2 for x, y in zip(xs, ys, strict=True)) / len(xs)


def closed_form(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """The exact least-squares line: the answer gradient descent is trying to reach."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0:
        raise GDError("all x values are the same")
    w = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / var
    return w, my - w * mx


@dataclass(frozen=True)
class Run:
    losses: list[float]
    w: float
    b: float
    diverged: bool
    steps_to_1pct: int | None  # steps until loss is within 1% of the best possible, if ever


def descend(xs: list[float], ys: list[float], lr: float, steps: int = 400, scale: bool = False) -> Run:
    if lr <= 0 or not 1 <= steps <= 5000:
        raise GDError("lr must be positive and steps 1-5000")
    n = len(xs)
    mean, sd = (sum(xs) / n, math.sqrt(sum((x - sum(xs) / n) ** 2 for x in xs) / n)) if scale else (0.0, 1.0)
    z = [(x - mean) / sd for x in xs]
    best = mse(xs, ys, *closed_form(xs, ys))
    w = b = 0.0
    losses: list[float] = []
    hit: int | None = None
    for step in range(steps):
        loss = mse(z, ys, w, b)
        if not math.isfinite(loss) or loss > 1e12:
            return Run(losses, math.nan, math.nan, True, hit)
        losses.append(loss)
        if hit is None and loss <= best * 1.01:
            hit = step
        gw = 2 / n * sum((w * x + b - y) * x for x, y in zip(z, ys, strict=True))
        gb = 2 / n * sum(w * x + b - y for x, y in zip(z, ys, strict=True))
        w, b = w - lr * gw, b - lr * gb
    if scale:  # convert back to the original units of x
        w, b = w / sd, b - w * mean / sd
    return Run(losses, w, b, False, hit)


def experiment(xs: list[float], ys: list[float], lrs: list[float], steps: int = 400) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for scale in (False, True):
        for lr in lrs:
            r = descend(xs, ys, lr, steps, scale)
            out.append({"scaled": scale, "lr": lr, "diverged": r.diverged, "steps_to_1pct": r.steps_to_1pct,
                        "final_loss": None if r.diverged else round(r.losses[-1], 4)})
    return out
