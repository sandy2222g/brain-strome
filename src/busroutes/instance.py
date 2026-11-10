"""Synthetic town generator and the routing problem derived from it."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from typing import Any

from busroutes.geometry import Edge, Grid, edge_key

W, H, SPACING_KM = 24, 24, 0.4
SCHOOL_XY = (10, 12)
BRIDGE_ROWS = (3, 11, 20)
BRIDGE_NAMES = ("North Bridge", "Central Bridge", "South Bridge")
MIN_PER_KM = 2.0  # 30 km/h average including turns and traffic
CENTRES = [(5, 5, 0.19), (6, 17, 0.17), (10, 7, 0.14), (13, 19, 0.14), (20, 7, 0.18), (19, 17, 0.18)]


class PlanningError(ValueError):
    """The request cannot be turned into a solvable problem."""


def river_col(y: int) -> int:
    """Column just left of the river on row y (the river meanders)."""
    return 15 + round(1.5 * math.sin(y / 3.0))


@dataclass(frozen=True)
class Stop:
    id: str
    x: int
    y: int
    student_ids: tuple[str, ...]

    @property
    def students(self) -> int:
        return len(self.student_ids)


@dataclass(frozen=True)
class Road:
    """A named stretch of road that can be closed in a what-if."""

    id: str
    name: str
    kind: str  # "bridge" or "street"
    edges: tuple[Edge, ...]


@dataclass(frozen=True)
class Instance:
    seed: int
    stops: tuple[Stop, ...]
    school: tuple[int, int]
    buses: int
    capacity: int
    ride_limit_min: float
    bell_min: int
    arrive_before_min: int
    river_edges: tuple[Edge, ...]
    works_edges: tuple[Edge, ...]
    roads: tuple[Road, ...]
    closed: tuple[str, ...] = field(default=())

    def grid(self) -> Grid:
        blocked: set[Edge] = set(self.river_edges) | set(self.works_edges)
        by_id = {r.id: r for r in self.roads}
        for rid in self.closed:
            blocked.update(by_id[rid].edges)
        open_bridges = {e for r in self.roads if r.kind == "bridge" and r.id not in self.closed for e in r.edges}
        return Grid(W, H, SPACING_KM, blocked - open_bridges)

    def with_changes(
        self,
        buses: int | None = None,
        capacity: int | None = None,
        ride_limit_min: float | None = None,
        close: tuple[str, ...] = (),
    ) -> Instance:
        known = {r.id for r in self.roads}
        for rid in close:
            if rid not in known:
                raise PlanningError(f"unknown road '{rid}'")
        closed = tuple(dict.fromkeys(self.closed + tuple(close)))
        return replace(
            self,
            buses=self.buses if buses is None else buses,
            capacity=self.capacity if capacity is None else capacity,
            ride_limit_min=self.ride_limit_min if ride_limit_min is None else ride_limit_min,
            closed=closed,
        )


def generate(
    seed: int = 7,
    n_stops: int = 120,
    buses: int = 8,
    capacity: int = 36,
    ride_limit_min: float = 45.0,
    bell_min: int = 8 * 60 + 15,
    arrive_before_min: int = 5,
) -> Instance:
    """Build a fictional town. Same seed, same town."""
    if not 10 <= n_stops <= 400:
        raise PlanningError("n_stops must be between 10 and 400")
    rng = random.Random(seed)
    school = SCHOOL_XY
    used = {school}
    pts: list[tuple[int, int]] = []
    weights = [c[2] for c in CENTRES]
    while len(pts) < n_stops:
        cx, cy, _ = rng.choices(CENTRES, weights)[0]
        x, y = round(rng.gauss(cx, 2.3)), round(rng.gauss(cy, 2.3))
        if 0 <= x < W and 0 <= y < H and (x, y) not in used:
            used.add((x, y))
            pts.append((x, y))
    pts.sort(key=lambda p: (p[1], p[0]))
    sizes = rng.choices([1, 2, 3, 4], [0.3, 0.35, 0.25, 0.1], k=n_stops)
    counter = 1000 + rng.randrange(500)
    stops = []
    for i, ((x, y), q) in enumerate(zip(pts, sizes, strict=True), start=1):
        ids = tuple(f"P{counter + k:04d}" for k in range(q))
        counter += q
        stops.append(Stop(f"S{i:03d}", x, y, ids))

    g0 = Grid(W, H, SPACING_KM)

    def across(y: int) -> Edge:
        return edge_key(g0.node(river_col(y), y), g0.node(river_col(y) + 1, y))

    def left_bank(x: int, y: int) -> bool:
        return x <= river_col(y)

    cut: set[Edge] = set()
    for y in range(H):
        for x in range(W):
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if nx < W and ny < H and left_bank(x, y) != left_bank(nx, ny):
                    cut.add(edge_key(g0.node(x, y), g0.node(nx, ny)))
    river = tuple(sorted(cut))
    works = tuple(edge_key(g0.node(x, 8), g0.node(x + 1, 8)) for x in range(2, 6)) + tuple(
        edge_key(g0.node(18, y), g0.node(18, y + 1)) for y in range(9, 13)
    )
    roads = [
        Road(f"bridge-{name.split()[0].lower()}", name, "bridge", (across(y),))
        for name, y in zip(BRIDGE_NAMES, BRIDGE_ROWS, strict=True)
    ]
    oak = tuple(edge_key(g0.node(9, y), g0.node(9, y + 1)) for y in range(7, 17))
    market = tuple(edge_key(g0.node(x, 15), g0.node(x + 1, 15)) for x in range(3, 13))
    roads.append(Road("oak-avenue", "Oak Avenue", "street", oak))
    roads.append(Road("market-street", "Market Street", "street", market))
    return Instance(
        seed,
        tuple(stops),
        school,
        buses,
        capacity,
        ride_limit_min,
        bell_min,
        arrive_before_min,
        river,
        works,
        tuple(roads),
    )


@dataclass
class Problem:
    """Numbers the solver works with: stop indices 0..n-1, the school is index n."""

    inst: Instance
    grid: Grid
    n: int
    dist: list[list[float]]
    q: list[int]
    dwell: list[float]
    near: list[list[int]]
    mpk: float = MIN_PER_KM
    late_weight: float = 8.0  # km-equivalents charged per minute over the ride limit

    @property
    def cap(self) -> int:
        return self.inst.capacity

    @property
    def limit(self) -> float:
        return self.inst.ride_limit_min

    @property
    def school_arrival(self) -> float:
        return float(self.inst.bell_min - self.inst.arrive_before_min)

    def node(self, i: int) -> int:
        """Grid node of stop i (or of the school when i == n)."""
        if i == self.n:
            return self.grid.node(*self.inst.school)
        s = self.inst.stops[i]
        return self.grid.node(s.x, s.y)


def build_problem(inst: Instance) -> Problem:
    if inst.buses < 1 or not 8 <= inst.capacity <= 80 or inst.ride_limit_min < 5:
        raise PlanningError("need at least one bus, a capacity of 8-80 seats and a ride limit of 5+ minutes")
    biggest = max(s.students for s in inst.stops)
    if inst.capacity < biggest:
        raise PlanningError(f"capacity {inst.capacity} is smaller than the largest stop ({biggest} students)")
    grid = inst.grid()
    nodes = [grid.node(s.x, s.y) for s in inst.stops] + [grid.node(*inst.school)]
    n = len(inst.stops)
    dist = []
    for a in nodes:
        row = grid.km_from(a)
        dist.append([row[b] for b in nodes])
    for i in range(n):
        if math.isinf(dist[i][n]):
            raise PlanningError(f"stop {inst.stops[i].id} cannot reach the school with the current road closures")
    near = [sorted((j for j in range(n) if j != i), key=lambda j, i=i: dist[i][j])[:8] for i in range(n)]
    q = [s.students for s in inst.stops]
    dwell = [0.4 + 0.1 * s.students for s in inst.stops]
    return Problem(inst, grid, n, dist, q, dwell, near)


def instance_to_dict(inst: Instance) -> dict[str, Any]:
    g = inst.grid()

    def seg(edges: tuple[Edge, ...]) -> list[list[int]]:
        return [[*g.xy(a), *g.xy(b)] for a, b in edges]

    return {
        "seed": inst.seed,
        "grid": {"w": W, "h": H, "spacing_km": SPACING_KM},
        "school": {"x": inst.school[0], "y": inst.school[1]},
        "stops": [
            {"id": s.id, "x": s.x, "y": s.y, "students": s.students, "student_ids": list(s.student_ids)}
            for s in inst.stops
        ],
        "river": seg(inst.river_edges),
        "river_line": [[river_col(y) + 0.5, y] for y in range(H)],
        "works": seg(inst.works_edges),
        "roads": [
            {"id": r.id, "name": r.name, "kind": r.kind, "segments": seg(r.edges), "closed": r.id in inst.closed}
            for r in inst.roads
        ],
        "buses": inst.buses,
        "capacity": inst.capacity,
        "ride_limit_min": inst.ride_limit_min,
        "bell_min": inst.bell_min,
        "arrive_before_min": inst.arrive_before_min,
    }
