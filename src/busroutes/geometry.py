"""Road network on a square grid: blocked edges, shortest paths and detours."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

Edge = tuple[int, int]


def edge_key(a: int, b: int) -> Edge:
    """Order-independent key for the road segment between two nodes."""
    return (a, b) if a < b else (b, a)


class Grid:
    """A w x h lattice of intersections joined by road segments, some of them blocked."""

    def __init__(self, w: int, h: int, spacing_km: float, blocked: Iterable[Edge] = ()) -> None:
        if w < 2 or h < 2 or spacing_km <= 0:
            raise ValueError("grid must be at least 2x2 with a positive spacing")
        self.w, self.h, self.spacing_km = w, h, spacing_km
        self.blocked: frozenset[Edge] = frozenset(edge_key(a, b) for a, b in blocked)
        self._adj = [self._neighbours(n) for n in range(w * h)]

    def node(self, x: int, y: int) -> int:
        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError(f"({x}, {y}) is outside the {self.w}x{self.h} grid")
        return y * self.w + x

    def xy(self, n: int) -> tuple[int, int]:
        return n % self.w, n // self.w

    def _neighbours(self, n: int) -> list[int]:
        x, y = self.xy(n)
        out = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.w and 0 <= ny < self.h:
                m = ny * self.w + nx
                if edge_key(n, m) not in self.blocked:
                    out.append(m)
        return out

    def steps_from(self, src: int) -> tuple[list[int], list[int]]:
        """Breadth-first search: (steps to every node or -1 if unreachable, parent of every node)."""
        dist = [-1] * (self.w * self.h)
        parent = [-1] * (self.w * self.h)
        dist[src] = 0
        queue = deque([src])
        while queue:
            n = queue.popleft()
            for m in self._adj[n]:
                if dist[m] < 0:
                    dist[m] = dist[n] + 1
                    parent[m] = n
                    queue.append(m)
        return dist, parent

    def km_from(self, src: int) -> list[float]:
        """Road kilometres from src to every node (inf when cut off)."""
        steps, _ = self.steps_from(src)
        return [s * self.spacing_km if s >= 0 else float("inf") for s in steps]

    def path(self, a: int, b: int) -> list[int]:
        """One shortest road path from a to b as a node list; empty when unreachable."""
        steps, parent = self.steps_from(a)
        if steps[b] < 0:
            return []
        out = [b]
        while out[-1] != a:
            out.append(parent[out[-1]])
        return out[::-1]

    def straight_km(self, a: int, b: int) -> float:
        """Straight-line distance, ignoring roads."""
        (ax, ay), (bx, by) = self.xy(a), self.xy(b)
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 * self.spacing_km

    def manhattan_km(self, a: int, b: int) -> float:
        """Distance if every street were open."""
        (ax, ay), (bx, by) = self.xy(a), self.xy(b)
        return (abs(ax - bx) + abs(ay - by)) * self.spacing_km


def corners(grid: Grid, path: list[int]) -> list[tuple[int, int]]:
    """Reduce a node path to its turning points so it draws as a short polyline."""
    pts = [grid.xy(n) for n in path]
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for prev, cur, nxt in zip(pts, pts[1:], pts[2:], strict=False):
        if (cur[0] - prev[0], cur[1] - prev[1]) != (nxt[0] - cur[0], nxt[1] - cur[1]):
            out.append(cur)
    out.append(pts[-1])
    return out
