"""BFS, Dijkstra and A* on a weighted grid. Cost = sum of the cost of every cell entered."""

from __future__ import annotations

import heapq
import json
from collections import deque
from pathlib import Path

MAPS = Path(__file__).resolve().parents[2] / "data" / "maps.json"
COST = {".": 1, "S": 1, "G": 1, "s": 3, "^": 5}  # road/start/goal, sand, hill; '#' wall and '~' water are blocked
BLOCKED = "#~"
MAX_SIDE = 80
Cell = tuple[int, int]


class TrailError(ValueError):
    """Invalid map or algorithm."""


class Grid:
    def __init__(self, text: str) -> None:
        rows = [r for r in text.strip("\n").splitlines() if r]
        if not rows or len({len(r) for r in rows}) != 1:
            raise TrailError("map must be a non-empty rectangle")
        if len(rows) > MAX_SIDE or len(rows[0]) > MAX_SIDE:
            raise TrailError(f"map is limited to {MAX_SIDE}x{MAX_SIDE}")
        bad = {c for r in rows for c in r} - set(COST) - set(BLOCKED)
        if bad:
            raise TrailError(f"unknown map characters: {''.join(sorted(bad))}")
        self.rows, self.h, self.w = rows, len(rows), len(rows[0])
        starts = [(y, x) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "S"]
        goals = [(y, x) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "G"]
        if len(starts) != 1 or len(goals) != 1:
            raise TrailError("map needs exactly one S and one G")
        self.start, self.goal = starts[0], goals[0]

    def cost(self, c: Cell) -> int:
        return COST[self.rows[c[0]][c[1]]]

    def neighbours(self, c: Cell) -> list[Cell]:
        out = []
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            y, x = c[0] + dy, c[1] + dx
            if 0 <= y < self.h and 0 <= x < self.w and self.rows[y][x] not in BLOCKED:
                out.append((y, x))
        return out


def path_cost(g: Grid, path: list[Cell]) -> int:
    return sum(g.cost(c) for c in path[1:])


def _result(g: Grid, prev: dict[Cell, Cell | None], seen: set[Cell]) -> dict[str, object]:
    path: list[Cell] = []
    cur: Cell | None = g.goal if g.goal in prev else None
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return {"found": bool(path), "path": [list(c) for c in path], "cost": path_cost(g, path) if path else None,
            "steps": max(len(path) - 1, 0), "expanded": len(seen), "explored": sorted(list(c) for c in seen)}


def bfs(g: Grid) -> dict[str, object]:
    prev: dict[Cell, Cell | None] = {g.start: None}
    q, seen = deque([g.start]), set()
    while q:
        cur = q.popleft()
        seen.add(cur)
        if cur == g.goal:
            break
        for n in g.neighbours(cur):
            if n not in prev:
                prev[n] = cur
                q.append(n)
    return _result(g, prev, seen)


def best_first(g: Grid, use_heuristic: bool) -> dict[str, object]:
    """Dijkstra (heuristic 0) or A* (Manhattan distance, admissible because every step costs at least 1)."""
    def h(c: Cell) -> int:
        return abs(c[0] - g.goal[0]) + abs(c[1] - g.goal[1]) if use_heuristic else 0

    dist = {g.start: 0}
    prev: dict[Cell, Cell | None] = {g.start: None}
    heap = [(h(g.start), 0, g.start)]
    seen: set[Cell] = set()
    while heap:
        _, d, cur = heapq.heappop(heap)
        if cur in seen:
            continue
        seen.add(cur)
        if cur == g.goal:
            break
        for n in g.neighbours(cur):
            nd = d + g.cost(n)
            if nd < dist.get(n, 10**9):
                dist[n] = nd
                prev[n] = cur
                heapq.heappush(heap, (nd + h(n), nd, n))
    return _result(g, prev, seen)


def solve(text: str, algorithm: str) -> dict[str, object]:
    g = Grid(text)
    if algorithm == "bfs":
        return bfs(g)
    if algorithm == "dijkstra":
        return best_first(g, False)
    if algorithm == "astar":
        return best_first(g, True)
    raise TrailError("algorithm must be bfs, dijkstra or astar")


def maps() -> list[dict[str, str]]:
    return json.loads(MAPS.read_text())  # type: ignore[no-any-return]


def evaluate() -> list[dict[str, object]]:
    rows = []
    for m in maps():
        row: dict[str, object] = {"name": m["name"]}
        for a in ("bfs", "dijkstra", "astar"):
            r = solve(m["text"], a)
            row[a] = {"cost": r["cost"], "expanded": r["expanded"]}
        rows.append(row)
    return rows
