"""A CART decision tree written from scratch, applied to a made-up plant-watering problem."""
from __future__ import annotations

import random
from dataclasses import dataclass

FEATURES = ["soil_moisture", "days_since_watering", "sunlight_hours", "temperature_c"]
LABELS = ["skip", "water"]
Row = list[float]


class TreeError(ValueError):
    pass


def truth(r: Row) -> int:
    """The made-up gardener's rule that generates the labels (the tree never sees it)."""
    moisture, days, sun, temp = r
    thirst = (35 - moisture) / 35 * 2 + days / 7 + sun / 12 + max(0.0, temp - 22) / 20
    return int(thirst > 1.7 or (moisture < 12 and days >= 2))


def make_data(n: int, seed: int, noise: float = 0.08) -> tuple[list[Row], list[int]]:
    """Synthetic plants; `noise` of the labels are flipped to mimic inconsistent human choices."""
    rng = random.Random(seed)
    xs: list[Row] = []
    ys: list[int] = []
    for _ in range(n):
        r = [round(rng.uniform(5, 60), 1), float(rng.randint(0, 14)), round(rng.uniform(0, 12), 1),
             round(rng.uniform(12, 36), 1)]
        y = truth(r)
        if rng.random() < noise:
            y = 1 - y
        xs.append(r)
        ys.append(y)
    return xs, ys


def gini(ys: list[int]) -> float:
    if not ys:
        return 0.0
    p = sum(ys) / len(ys)
    return 2 * p * (1 - p)


@dataclass
class Node:
    counts: tuple[int, int]
    feature: int = -1
    threshold: float = 0.0
    left: Node | None = None
    right: Node | None = None
    depth: int = 0

    @property
    def leaf(self) -> bool:
        return self.left is None

    @property
    def label(self) -> int:
        return int(self.counts[1] > self.counts[0])


def best_split(xs: list[Row], ys: list[int], min_leaf: int) -> tuple[int, float, float] | None:
    """Feature and threshold with the lowest weighted Gini; None if nothing improves on the parent."""
    best: tuple[int, float, float] | None = None
    parent = gini(ys)
    n = len(ys)
    for f in range(len(xs[0])):
        order = sorted(range(n), key=lambda i: xs[i][f])
        left_pos = 0
        total_pos = sum(ys)
        for k in range(1, n):
            left_pos += ys[order[k - 1]]
            a, b = xs[order[k - 1]][f], xs[order[k]][f]
            if a == b or k < min_leaf or n - k < min_leaf:
                continue
            gl = 2 * (left_pos / k) * (1 - left_pos / k)
            rp = total_pos - left_pos
            gr = 2 * (rp / (n - k)) * (1 - rp / (n - k))
            score = (k * gl + (n - k) * gr) / n
            if score < parent - 1e-12 and (best is None or score < best[2]):
                best = (f, (a + b) / 2, score)
    return best


def fit(xs: list[Row], ys: list[int], max_depth: int = 3, min_leaf: int = 3, depth: int = 0) -> Node:
    if not xs or len(xs) != len(ys) or max_depth < 0:
        raise TreeError("need matching non-empty data and max_depth >= 0")
    node = Node((ys.count(0), ys.count(1)), depth=depth)
    if depth >= max_depth or len(set(ys)) == 1:
        return node
    s = best_split(xs, ys, min_leaf)
    if s is None:
        return node
    f, t, _ = s
    li = [i for i, r in enumerate(xs) if r[f] <= t]
    ri = [i for i, r in enumerate(xs) if r[f] > t]
    node.feature, node.threshold = f, t
    node.left = fit([xs[i] for i in li], [ys[i] for i in li], max_depth, min_leaf, depth + 1)
    node.right = fit([xs[i] for i in ri], [ys[i] for i in ri], max_depth, min_leaf, depth + 1)
    return node


def predict(node: Node, r: Row) -> int:
    while not node.leaf:
        assert node.left and node.right
        node = node.left if r[node.feature] <= node.threshold else node.right
    return node.label


def explain(node: Node, r: Row) -> list[str]:
    """The questions asked on the way to the answer, in plain words."""
    out = []
    while not node.leaf:
        assert node.left and node.right
        go_left = r[node.feature] <= node.threshold
        name = FEATURES[node.feature].replace("_", " ")
        out.append(f"{name} is {'at most' if go_left else 'above'} {node.threshold:.1f}")
        node = node.left if go_left else node.right
    c = node.counts
    out.append(f"-> {LABELS[node.label]} (seen {c[0]} skip, {c[1]} water here)")
    return out


def rules(node: Node, indent: str = "") -> list[str]:
    if node.leaf:
        return [f"{indent}-> {LABELS[node.label]}  ({node.counts[0]} skip / {node.counts[1]} water)"]
    assert node.left and node.right
    name = FEATURES[node.feature]
    return ([f"{indent}if {name} <= {node.threshold:.1f}:"] + rules(node.left, indent + "  ")
            + [f"{indent}else:  # {name} > {node.threshold:.1f}"] + rules(node.right, indent + "  "))


def accuracy(node: Node, xs: list[Row], ys: list[int]) -> float:
    return sum(predict(node, r) == y for r, y in zip(xs, ys, strict=True)) / len(ys)


def size(node: Node) -> int:
    return 1 if node.leaf else 1 + size(node.left) + size(node.right)  # type: ignore[arg-type]


def splits() -> tuple[tuple[list[Row], list[int]], tuple[list[Row], list[int]], tuple[list[Row], list[int]]]:
    xs, ys = make_data(1000, seed=11)
    return (xs[:600], ys[:600]), (xs[600:800], ys[600:800]), (xs[800:], ys[800:])


def evaluate(depths: range = range(0, 9)) -> list[dict[str, float]]:
    (tx, ty), (vx, vy), _ = splits()
    out = []
    for d in depths:
        t = fit(tx, ty, d)
        out.append({"depth": d, "train": round(accuracy(t, tx, ty), 3), "validation": round(accuracy(t, vx, vy), 3),
                    "nodes": size(t)})
    return out


def best_depth(scores: list[dict[str, float]]) -> int:
    top = max(s["validation"] for s in scores)
    return int(min(s["depth"] for s in scores if s["validation"] == top))  # simplest tree among the best
