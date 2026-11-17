"""Maze generation (3 algorithms) and solving (3 algorithms), with measured comparisons."""
from __future__ import annotations

import heapq
import random
from collections import deque
from dataclasses import dataclass

Cell = tuple[int, int]
Edge = tuple[Cell, Cell]


class MazeError(ValueError):
    """Raised for invalid maze requests."""


@dataclass(frozen=True)
class Maze:
    width: int
    height: int
    passages: frozenset[Edge]

    def neighbours(self, c: Cell) -> list[Cell]:
        x, y = c
        out = []
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if edge(c, n) in self.passages:
                out.append(n)
        return out


def edge(a: Cell, b: Cell) -> Edge:
    return (a, b) if a <= b else (b, a)


def _check(width: int, height: int) -> None:
    if not (2 <= width <= 60 and 2 <= height <= 60):
        raise MazeError("width and height must be between 2 and 60")


def _grid_neighbours(c: Cell, w: int, h: int) -> list[Cell]:
    x, y = c
    return [(a, b) for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if 0 <= a < w and 0 <= b < h]


def backtracker(w: int, h: int, rng: random.Random) -> set[Edge]:
    """Depth-first carving: long winding corridors."""
    seen = {(0, 0)}
    stack = [(0, 0)]
    out: set[Edge] = set()
    while stack:
        cur = stack[-1]
        options = [n for n in _grid_neighbours(cur, w, h) if n not in seen]
        if not options:
            stack.pop()
            continue
        nxt = rng.choice(options)
        out.add(edge(cur, nxt))
        seen.add(nxt)
        stack.append(nxt)
    return out


def kruskal(w: int, h: int, rng: random.Random) -> set[Edge]:
    """Randomised Kruskal with union-find: many short branches."""
    parent = {(x, y): (x, y) for x in range(w) for y in range(h)}

    def find(c: Cell) -> Cell:
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    walls = [edge((x, y), n) for x in range(w) for y in range(h) for n in _grid_neighbours((x, y), w, h) if (x, y) < n]
    rng.shuffle(walls)
    out: set[Edge] = set()
    for a, b in walls:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            out.add((a, b))
    return out


def prim(w: int, h: int, rng: random.Random) -> set[Edge]:
    """Randomised Prim: grows like a blob, with lots of tiny dead ends."""
    seen = {(0, 0)}
    frontier = [edge((0, 0), n) for n in _grid_neighbours((0, 0), w, h)]
    out: set[Edge] = set()
    while frontier:
        a, b = frontier.pop(rng.randrange(len(frontier)))
        new = b if a in seen and b not in seen else a if b in seen and a not in seen else None
        if new is None:
            continue
        out.add((a, b))
        seen.add(new)
        frontier.extend(edge(new, n) for n in _grid_neighbours(new, w, h) if n not in seen)
    return out


GENERATORS = {"backtracker": backtracker, "kruskal": kruskal, "prim": prim}


def generate(width: int, height: int, algorithm: str = "backtracker", seed: int = 0) -> Maze:
    _check(width, height)
    if algorithm not in GENERATORS:
        raise MazeError(f"unknown algorithm {algorithm!r}; choose from {sorted(GENERATORS)}")
    return Maze(width, height, frozenset(GENERATORS[algorithm](width, height, random.Random(seed))))


@dataclass(frozen=True)
class Solution:
    path: list[Cell]
    expanded: int  # how many cells the solver looked at


def _rebuild(prev: dict[Cell, Cell | None], end: Cell) -> list[Cell]:
    path: list[Cell] = []
    cur: Cell | None = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


def solve(maze: Maze, method: str = "bfs") -> Solution:
    """Solve from top-left to bottom-right using bfs, dfs or astar."""
    start, goal = (0, 0), (maze.width - 1, maze.height - 1)
    prev: dict[Cell, Cell | None] = {start: None}
    expanded = 0
    if method in ("bfs", "dfs"):
        pool: deque[Cell] = deque([start])
        while pool:
            cur = pool.popleft() if method == "bfs" else pool.pop()
            expanded += 1
            if cur == goal:
                return Solution(_rebuild(prev, cur), expanded)
            for n in maze.neighbours(cur):
                if n not in prev:
                    prev[n] = cur
                    pool.append(n)
    elif method == "astar":
        def h(c: Cell) -> int:
            return abs(goal[0] - c[0]) + abs(goal[1] - c[1])

        best = {start: 0}
        heap = [(h(start), 0, start)]
        done: set[Cell] = set()
        while heap:
            _, g, cur = heapq.heappop(heap)
            if cur in done:
                continue
            done.add(cur)
            expanded += 1
            if cur == goal:
                return Solution(_rebuild(prev, cur), expanded)
            for n in maze.neighbours(cur):
                if g + 1 < best.get(n, 10**9):
                    best[n] = g + 1
                    prev[n] = cur
                    heapq.heappush(heap, (g + 1 + h(n), g + 1, n))
    else:
        raise MazeError(f"unknown solver {method!r}; choose bfs, dfs or astar")
    raise MazeError("no path found")


def dead_ends(maze: Maze) -> int:
    return sum(1 for x in range(maze.width) for y in range(maze.height) if len(maze.neighbours((x, y))) == 1)


def compare(width: int = 25, height: int = 25, trials: int = 100) -> list[dict[str, object]]:
    """Average solution length, dead ends and solver effort per generator over many seeds."""
    rows = []
    for name in GENERATORS:
        tot = {"length": 0, "dead": 0, "bfs": 0, "dfs": 0, "astar": 0}
        for s in range(trials):
            m = generate(width, height, name, s)
            tot["length"] += len(solve(m, "bfs").path)
            tot["dead"] += dead_ends(m)
            for k in ("bfs", "dfs", "astar"):
                tot[k] += solve(m, k).expanded
        rows.append({"generator": name, **{k: round(v / trials, 1) for k, v in tot.items()}})
    return rows
