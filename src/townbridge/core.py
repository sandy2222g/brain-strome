"""Find the roads (bridges) and junctions (articulation points) whose loss disconnects a town."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "town.json"
Edge = tuple[str, str]


class TownError(ValueError):
    pass


@dataclass(frozen=True)
class Town:
    places: dict[str, tuple[float, float]]
    roads: list[Edge]

    def adjacency(self, skip: Edge | None = None) -> dict[str, list[str]]:
        adj: dict[str, list[str]] = {p: [] for p in self.places}
        for a, b in self.roads:
            if skip and {a, b} == set(skip):
                continue
            adj[a].append(b)
            adj[b].append(a)
        return adj


def load_town(path: Path = DATA) -> Town:
    raw = json.loads(path.read_text())
    places = {k: (float(v[0]), float(v[1])) for k, v in raw["places"].items()}
    roads = [(a, b) for a, b in raw["roads"]]
    for a, b in roads:
        if a not in places or b not in places or a == b:
            raise TownError(f"bad road {a}-{b}")
    return Town(places, roads)


def components(adj: dict[str, list[str]]) -> list[list[str]]:
    seen: set[str] = set()
    out: list[list[str]] = []
    for s in adj:
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        out.append(sorted(comp))
    return out


def tarjan(adj: dict[str, list[str]]) -> tuple[list[Edge], list[str]]:
    """Bridges and articulation points in one depth-first pass (low-link values), iterative."""
    disc: dict[str, int] = {}
    low: dict[str, int] = {}
    bridges: list[Edge] = []
    cut: set[str] = set()
    t = 0
    for root in adj:
        if root in disc:
            continue
        disc[root] = low[root] = t = t + 1
        children = 0
        stack = [(root, "", iter(adj[root]))]
        while stack:
            u, parent, it = stack[-1]
            nxt = next(it, None)
            if nxt is not None:
                if nxt == parent:
                    continue
                if nxt in disc:
                    low[u] = min(low[u], disc[nxt])
                else:
                    disc[nxt] = low[nxt] = t = t + 1
                    stack.append((nxt, u, iter(adj[nxt])))
                    if u == root:
                        children += 1
            else:
                stack.pop()
                if stack:
                    p = stack[-1][0]
                    low[p] = min(low[p], low[u])
                    if low[u] > disc[p]:
                        bridges.append((p, u))
                    if p != root and low[u] >= disc[p]:
                        cut.add(p)
        if children > 1:
            cut.add(root)
    return sorted(tuple(sorted(e)) for e in bridges), sorted(cut)  # type: ignore[misc]


def brute_bridges(town: Town) -> list[Edge]:
    """Slow check: remove each road in turn and see whether the number of pieces grows."""
    base = len(components(town.adjacency()))
    return sorted(tuple(sorted(r)) for r in town.roads if len(components(town.adjacency(r))) > base)  # type: ignore[misc]


def closure(town: Town, road: Edge) -> list[list[str]]:
    if not any({a, b} == set(road) for a, b in town.roads):
        raise TownError("no such road")
    return components(town.adjacency(road))


def best_new_roads(town: Town, top: int = 3) -> list[dict[str, object]]:
    """Try every missing road; report the ones that remove the most weak links."""
    have = {frozenset(r) for r in town.roads}
    names = sorted(town.places)
    before = len(tarjan(town.adjacency())[0])
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if frozenset((a, b)) in have:
                continue
            t2 = Town(town.places, town.roads + [(a, b)])
            left = len(tarjan(t2.adjacency())[0])
            out.append({"road": [a, b], "bridges_left": left, "fixed": before - left})
    out.sort(key=lambda r: (r["bridges_left"], r["road"]))  # type: ignore[arg-type, return-value]
    return out[:top]
