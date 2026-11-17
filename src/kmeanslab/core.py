"""k-means from scratch (pure Python): random vs k-means++ initialisation, inertia, elbow."""
from __future__ import annotations

import random

Point = tuple[float, float]


class KMeansError(ValueError):
    """Raised for invalid input."""


def blobs(n_per: int = 60, centres: list[Point] | None = None, spread: float = 0.9, seed: int = 0) -> list[Point]:
    """Synthetic 2-D clusters (think: shoppers by visits vs spend)."""
    rng = random.Random(seed)
    cs = centres or [(2.0, 2.0), (8.0, 3.0), (5.0, 8.0), (9.0, 9.0)]
    return [(rng.gauss(cx, spread), rng.gauss(cy, spread)) for cx, cy in cs for _ in range(n_per)]


def dist2(a: Point, b: Point) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def init_random(points: list[Point], k: int, rng: random.Random) -> list[Point]:
    return rng.sample(points, k)


def init_pp(points: list[Point], k: int, rng: random.Random) -> list[Point]:
    """k-means++: each new centre is picked with probability proportional to squared distance from the nearest one."""
    centres = [rng.choice(points)]
    while len(centres) < k:
        d = [min(dist2(p, c) for c in centres) for p in points]
        centres.append(rng.choices(points, weights=d)[0])
    return centres


def kmeans(points: list[Point], k: int, init: str = "pp", seed: int = 0, max_iter: int = 100) -> dict[str, object]:
    if not 1 <= k <= len(points):
        raise KMeansError("k must be between 1 and the number of points")
    if init not in ("pp", "random"):
        raise KMeansError("init must be 'pp' or 'random'")
    rng = random.Random(seed)
    centres = (init_pp if init == "pp" else init_random)(points, k, rng)
    labels = [0] * len(points)
    iters = 0
    for iters in range(1, max_iter + 1):
        new = [min(range(k), key=lambda j: dist2(p, centres[j])) for p in points]
        if new == labels and iters > 1:
            iters -= 1
            break
        labels = new
        for j in range(k):
            members = [p for p, lab in zip(points, labels, strict=True) if lab == j]
            if members:
                centres[j] = (sum(p[0] for p in members) / len(members), sum(p[1] for p in members) / len(members))
    inertia = sum(dist2(p, centres[lab]) for p, lab in zip(points, labels, strict=True))
    return {"centres": centres, "labels": labels, "inertia": inertia, "iterations": iters}


def best_of(points: list[Point], k: int, init: str, runs: int = 30) -> list[float]:
    return [float(kmeans(points, k, init, seed=s)["inertia"]) for s in range(runs)]  # type: ignore[arg-type]


def elbow(points: list[Point], max_k: int = 8) -> list[float]:
    return [min(best_of(points, k, "pp", 5)) for k in range(1, max_k + 1)]


def compare_inits(points: list[Point], k: int = 4, runs: int = 60) -> dict[str, dict[str, float]]:
    out = {}
    best = min(best_of(points, k, "pp", runs))
    for init in ("random", "pp"):
        v = best_of(points, k, init, runs)
        bad = sum(1 for x in v if x > best * 1.5)
        out[init] = {"mean_inertia": round(sum(v) / len(v), 1), "bad_runs_pct": round(100 * bad / len(v), 1)}
    return out
