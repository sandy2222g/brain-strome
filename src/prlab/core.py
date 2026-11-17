"""PageRank from scratch: power iteration, dangling pages, damping, and a check against a direct linear solve."""
from __future__ import annotations

# An invented network of a town's local websites: page -> pages it links to.
TOWN: dict[str, list[str]] = {
    "town-hall": ["library", "school", "market", "clinic"],
    "library": ["school", "town-hall"],
    "school": ["library", "town-hall", "sports-club"],
    "market": ["town-hall", "bakery", "florist"],
    "bakery": ["market", "town-hall"],
    "florist": ["market"],
    "clinic": ["town-hall"],
    "sports-club": ["school", "town-hall", "cafe"],
    "cafe": ["sports-club", "bakery"],
    "old-news": ["town-hall"],
    "gazette": ["town-hall", "market", "school", "library", "sports-club"],
}


class RankError(ValueError):
    """Raised for invalid graphs or parameters."""


def validate(graph: dict[str, list[str]]) -> list[str]:
    nodes = sorted(set(graph) | {t for ts in graph.values() for t in ts})
    if not nodes:
        raise RankError("graph is empty")
    return nodes


def pagerank(
    graph: dict[str, list[str]], damping: float = 0.85, tol: float = 1e-12, max_iter: int = 1000
) -> dict[str, float]:
    """Power iteration. Pages with no links ('dangling') spread their rank evenly over all pages."""
    if not 0 <= damping < 1:
        raise RankError("damping must be in [0, 1)")
    nodes = validate(graph)
    n = len(nodes)
    rank = {v: 1 / n for v in nodes}
    for _ in range(max_iter):
        dangling = sum(rank[v] for v in nodes if not graph.get(v))
        new = {v: (1 - damping) / n + damping * dangling / n for v in nodes}
        for v in nodes:
            out = graph.get(v, [])
            for t in out:
                new[t] += damping * rank[v] / len(out)
        if sum(abs(new[v] - rank[v]) for v in nodes) < tol:
            rank = new
            break
        rank = new
    return rank


def pagerank_exact(graph: dict[str, list[str]], damping: float = 0.85) -> dict[str, float]:
    """Solve (I - d*M) r = (1-d)/n directly with Gaussian elimination, as an independent check."""
    nodes = validate(graph)
    n = len(nodes)
    idx = {v: i for i, v in enumerate(nodes)}
    a = [[0.0] * n + [(1 - damping) / n] for _ in range(n)]
    for i in range(n):
        a[i][i] += 1.0
    for v in nodes:
        out = graph.get(v, [])
        if out:
            for t in out:
                a[idx[t]][idx[v]] -= damping / len(out)
        else:
            for j in range(n):
                a[j][idx[v]] -= damping / n
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col], strict=True)]
    return {v: a[idx[v]][n] / a[idx[v]][idx[v]] for v in nodes}


def ranking(graph: dict[str, list[str]], damping: float = 0.85) -> list[tuple[str, float]]:
    r = pagerank(graph, damping)
    return sorted(r.items(), key=lambda kv: (-kv[1], kv[0]))


def indegree_ranking(graph: dict[str, list[str]]) -> list[tuple[str, int]]:
    nodes = validate(graph)
    deg = dict.fromkeys(nodes, 0)
    for ts in graph.values():
        for t in set(ts):
            deg[t] += 1
    return sorted(deg.items(), key=lambda kv: (-kv[1], kv[0]))


def damping_sweep(graph: dict[str, list[str]], values: list[float]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {v: [] for v in validate(graph)}
    for d in values:
        r = pagerank(graph, d)
        for k, x in r.items():
            out[k].append(round(x, 4))
    return out
