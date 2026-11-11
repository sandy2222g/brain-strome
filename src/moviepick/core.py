"""Matrix-factorisation recommender (ALS) plus group aggregation strategies.

Ratings R (users x films) are approximated as P @ Q.T + bias with rank-k factors fitted by
alternating ridge regressions on the observed entries only. A group's pick maximises either the
average predicted rating or the *least misery* (the lowest predicted rating among members).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[2] / "data" / "ratings.json"


class PickError(ValueError):
    """Invalid request."""


@dataclass
class Model:
    p: np.ndarray
    q: np.ndarray
    mean: float
    user_bias: np.ndarray
    film_bias: np.ndarray

    def predict(self) -> np.ndarray:
        raw = self.mean + self.user_bias[:, None] + self.film_bias[None, :] + self.p @ self.q.T
        return np.clip(raw, 1.0, 5.0)


def biases(r: np.ndarray, mask: np.ndarray, mean: float, reg: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
    """Shrunken film then user offsets from the global mean (more ratings -> less shrinkage)."""
    resid = np.where(mask, r - mean, 0.0)
    fb = resid.sum(axis=0) / (mask.sum(axis=0) + reg)
    resid2 = np.where(mask, r - mean - fb[None, :], 0.0)
    ub = resid2.sum(axis=1) / (mask.sum(axis=1) + reg)
    return ub, fb


def to_matrix(ratings: list[list[int]], n_users: int, n_films: int) -> tuple[np.ndarray, np.ndarray]:
    r = np.zeros((n_users, n_films))
    mask = np.zeros((n_users, n_films), dtype=bool)
    for u, f, v in ratings:
        r[u, f], mask[u, f] = v, True
    return r, mask


def fit(r: np.ndarray, mask: np.ndarray, rank: int = 3, reg: float = 3.0, iters: int = 25, seed: int = 0) -> Model:
    if not mask.any():
        raise PickError("no ratings to learn from")
    rng = np.random.default_rng(seed)
    mean = float(r[mask].mean())
    ub, fb = biases(r, mask, mean)
    resid = np.where(mask, r - mean - ub[:, None] - fb[None, :], 0.0)
    n_u, n_f = r.shape
    p = rng.normal(0, 0.1, (n_u, rank))
    q = rng.normal(0, 0.1, (n_f, rank))
    eye = reg * np.eye(rank)
    for _ in range(iters):
        for u in range(n_u):
            idx = mask[u]
            if idx.any():
                qi = q[idx]
                p[u] = np.linalg.solve(qi.T @ qi + eye, qi.T @ resid[u, idx])
        for f in range(n_f):
            idx = mask[:, f]
            if idx.any():
                pi = p[idx]
                q[f] = np.linalg.solve(pi.T @ pi + eye, pi.T @ resid[idx, f])
    return Model(p, q, mean, ub, fb)


def rmse(pred: np.ndarray, truth: np.ndarray, mask: np.ndarray) -> float:
    return float(np.sqrt(((pred - truth)[mask] ** 2).mean()))


def holdout(mask: np.ndarray, frac: float = 0.2, seed: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Split observed ratings into train/test masks, keeping at least one train rating per user."""
    rng = np.random.default_rng(seed)
    test = mask & (rng.random(mask.shape) < frac)
    train = mask & ~test
    for u in range(mask.shape[0]):
        if not train[u].any() and test[u].any():
            j = int(np.flatnonzero(test[u])[0])
            train[u, j], test[u, j] = True, False
    return train, test


def baselines(r: np.ndarray, train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Global-mean and per-film-mean predictions."""
    g = float(r[train].mean())
    counts = train.sum(axis=0)
    sums = np.where(train, r, 0.0).sum(axis=0)
    film_mean = np.where(counts > 0, sums / np.maximum(counts, 1), g)
    return np.full(r.shape, g), np.tile(film_mean, (r.shape[0], 1))


def group_pick(
    pred: np.ndarray, members: list[int], seen: np.ndarray, strategy: str = "least_misery", top: int = 5
) -> list[dict[str, float]]:
    """Rank films nobody in the group has seen by group score."""
    if not members:
        raise PickError("pick at least one viewer")
    if strategy not in {"least_misery", "average"}:
        raise PickError("strategy must be least_misery or average")
    sub = pred[members]
    score = sub.min(axis=0) if strategy == "least_misery" else sub.mean(axis=0)
    blocked = seen[members].any(axis=0)
    order = [int(f) for f in np.argsort(-score) if not blocked[f]]
    return [
        {
            "film": f,
            "score": round(float(score[f]), 2),
            "min": round(float(sub[:, f].min()), 2),
            "mean": round(float(sub[:, f].mean()), 2),
        }
        for f in order[:top]
    ]


def load(path: Path = DATA) -> dict[str, object]:
    return json.loads(path.read_text())


def evaluate_groups(
    pred: np.ndarray, true: np.ndarray, seen: np.ndarray, size: int = 4, trials: int = 200, seed: int = 3
) -> dict[str, float]:
    """For random groups, compare the *true* score of the film each strategy picks.

    Reports the mean and the worst member's true rating of the pick, so least misery should win on the
    second number while average may win on the first.
    """
    rng = np.random.default_rng(seed)
    out: dict[str, list[float]] = {
        k: []
        for k in (
            "least_misery_min",
            "average_min",
            "popular_min",
            "random_min",
            "least_misery_mean",
            "average_mean",
            "popular_mean",
            "random_mean",
        )
    }
    popularity = pred.mean(axis=0)
    for _ in range(trials):
        members = [int(x) for x in rng.choice(pred.shape[0], size, replace=False)]
        for name in ("least_misery", "average"):
            pick = group_pick(pred, members, seen, name, top=1)[0]["film"]
            out[f"{name}_min"].append(float(true[members, pick].min()))
            out[f"{name}_mean"].append(float(true[members, pick].mean()))
        blocked = seen[members].any(axis=0)
        pop = int(next(f for f in np.argsort(-popularity) if not blocked[f]))
        free = np.flatnonzero(~blocked)
        rnd = int(rng.choice(free))
        out["random_min"].append(float(true[members, rnd].min()))
        out["random_mean"].append(float(true[members, rnd].mean()))
        out["popular_min"].append(float(true[members, pop].min()))
        out["popular_mean"].append(float(true[members, pop].mean()))
    return {k: round(float(np.mean(v)), 3) for k, v in out.items()}
