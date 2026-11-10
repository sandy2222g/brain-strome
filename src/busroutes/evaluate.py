"""Scoring: route cost, pick-up times worked back from the bell, ride-limit risk and plan summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from busroutes.geometry import corners
from busroutes.instance import Problem


@dataclass
class Plan:
    """Ordered stop indices per bus (the bus drives them in order, then the school)."""

    routes: list[list[int]]
    unassigned: list[int] = field(default_factory=list)
    method: str = ""

    def used(self) -> list[list[int]]:
        return [r for r in self.routes if r]


def route_cost(p: Problem, route: list[int]) -> tuple[float, float]:
    """(kilometres, minutes by which student rides exceed the limit, summed over stops)."""
    d, dw, mpk, lim = p.dist, p.dwell, p.mpk, p.limit
    km = t = over = 0.0
    prev = p.n
    for s in reversed(route):
        leg = d[s][prev]
        km += leg
        t += leg * mpk + dw[s]
        if t > lim:
            over += t - lim
        prev = s
    return km, over


def penalised(p: Problem, route: list[int]) -> float:
    km, over = route_cost(p, route)
    return km + p.late_weight * over


@dataclass
class StopReport:
    index: int
    arrive_min: float
    ride_min: float
    status: str  # ok, tight or over
    reason: str


@dataclass
class RouteStats:
    stops: list[StopReport]
    load: int
    km: float
    minutes: float
    longest_ride: float


def format_clock(minutes: float) -> str:
    total = int(round(minutes))
    h, m = divmod(total, 60)
    return f"{(h - 1) % 12 + 1}:{m:02d} {'am' if h < 12 else 'pm'}"


def _reason(p: Problem, route: list[int], pos: int, ride: float, status: str) -> str:
    s = route[pos]
    st = p.inst.stops[s]
    direct = p.dist[s][p.n] * p.mpk + p.dwell[s]
    parts = []
    if direct > p.limit * 0.9:
        parts.append(f"lives {p.dist[s][p.n]:.1f} km from school by road, {direct:.0f} min on a direct trip")
    after = len(route) - pos - 1
    extra = ride - direct
    if extra > 3 and after:
        parts.append(
            f"bus makes {after} more stop{'s' if after != 1 else ''} first, adding {extra:.0f} min over a direct trip"
        )
    a, b = p.node(s), p.node(p.n)
    manhattan = p.grid.manhattan_km(a, b)
    if manhattan and p.dist[s][p.n] > manhattan + 0.3:
        parts.append(f"river or closed road adds {p.dist[s][p.n] - manhattan:.1f} km")
    if not parts:
        parts.append(f"{st.students} student{'s' if st.students != 1 else ''} boards late in a long route")
    head = "Over the limit" if status == "over" else "Close to the limit"
    return f"{head}: " + "; ".join(parts) + "."


def route_stats(p: Problem, route: list[int]) -> RouteStats:
    rides = [0.0] * len(route)
    t = 0.0
    prev = p.n
    km = 0.0
    for pos in range(len(route) - 1, -1, -1):
        s = route[pos]
        leg = p.dist[s][prev]
        km += leg
        t += leg * p.mpk + p.dwell[s]
        rides[pos] = t
        prev = s
    reports = []
    for pos, s in enumerate(route):
        ride = rides[pos]
        status = "over" if ride > p.limit else "tight" if ride >= 0.9 * p.limit else "ok"
        reason = _reason(p, route, pos, ride, status) if status != "ok" else ""
        reports.append(StopReport(s, p.school_arrival - ride, ride, status, reason))
    load = sum(p.q[s] for s in route)
    return RouteStats(reports, load, km, rides[0] if rides else 0.0, max(rides, default=0.0))


def summarise(p: Problem, plan: Plan) -> dict[str, Any]:
    stats = [route_stats(p, r) for r in plan.used()]
    over = sum(1 for st in stats for s in st.stops if s.status == "over")
    tight = sum(1 for st in stats for s in st.stops if s.status == "tight")
    unserved = sum(p.q[s] for s in plan.unassigned)
    return {
        "method": plan.method,
        "buses_used": len(stats),
        "students": sum(p.q) - unserved,
        "total_km": round(sum(st.km for st in stats), 2),
        "total_minutes": round(sum(st.minutes for st in stats), 1),
        "longest_ride_min": round(max((st.longest_ride for st in stats), default=0.0), 1),
        "stops_over_limit": over,
        "stops_close_to_limit": tight,
        "unserved_students": unserved,
        "unserved_stops": len(plan.unassigned),
        "feasible": over == 0 and not plan.unassigned,
    }


def plan_to_dict(p: Problem, plan: Plan) -> dict[str, Any]:
    cache: dict[int, list[int]] = {}
    routes = []
    for bus, route in enumerate(plan.used(), start=1):
        st = route_stats(p, route)
        seq = [p.node(s) for s in route] + [p.node(p.n)]
        poly: list[tuple[int, int]] = []
        for a, b in zip(seq, seq[1:], strict=False):
            if a not in cache:
                cache[a] = []
            leg = corners(p.grid, p.grid.path(a, b))
            poly.extend(leg if not poly else leg[1:])
        routes.append(
            {
                "bus": bus,
                "load": st.load,
                "capacity": p.cap,
                "km": round(st.km, 2),
                "minutes": round(st.minutes, 1),
                "longest_ride_min": round(st.longest_ride, 1),
                "first_pickup": format_clock(st.stops[0].arrive_min),
                "path": [list(pt) for pt in poly],
                "stops": [
                    {
                        "id": p.inst.stops[r.index].id,
                        "x": p.inst.stops[r.index].x,
                        "y": p.inst.stops[r.index].y,
                        "students": p.q[r.index],
                        "pickup": format_clock(r.arrive_min),
                        "pickup_min": round(r.arrive_min, 1),
                        "ride_min": round(r.ride_min, 1),
                        "status": r.status,
                        "reason": r.reason,
                    }
                    for r in st.stops
                ],
            }
        )
    return {
        "summary": summarise(p, plan),
        "routes": routes,
        "unassigned": [p.inst.stops[s].id for s in plan.unassigned],
        "school_arrival": format_clock(p.school_arrival),
    }
