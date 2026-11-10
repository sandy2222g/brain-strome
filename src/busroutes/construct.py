"""Building first plans: sweep clustering, nearest-neighbour routes, Clarke-Wright savings, naive baseline."""

from __future__ import annotations

import math

from busroutes.evaluate import Plan, penalised, route_cost
from busroutes.instance import Problem


def nn_route(p: Problem, stops: list[int]) -> list[int]:
    """Start at the stop farthest from the school, then always drive to the nearest unvisited stop."""
    if not stops:
        return []
    left = set(stops)
    cur = max(stops, key=lambda s: (p.dist[s][p.n], -s))
    left.remove(cur)
    out = [cur]
    while left:
        cur = min(left, key=lambda s: (p.dist[cur][s], s))
        left.remove(cur)
        out.append(cur)
    return out


def _angle(p: Problem, s: int) -> float:
    st = p.inst.stops[s]
    return math.atan2(st.y - p.inst.school[1], st.x - p.inst.school[0])


def _insert_cheapest(p: Problem, routes: list[list[int]], loads: list[int], s: int) -> bool:
    best: tuple[float, int, int] | None = None
    for ri, r in enumerate(routes):
        if loads[ri] + p.q[s] > p.cap:
            continue
        base = penalised(p, r)
        for pos in range(len(r) + 1):
            delta = penalised(p, r[:pos] + [s] + r[pos:]) - base
            if best is None or delta < best[0]:
                best = (delta, ri, pos)
    if best is None:
        return False
    _, ri, pos = best
    routes[ri].insert(pos, s)
    loads[ri] += p.q[s]
    return True


def sweep(p: Problem, k: int, offset: int = 0, slack: int = 0) -> Plan:
    """Cut the stops, ordered by angle around the school, into at most k loads; overflow is inserted cheaply."""
    order = sorted(range(p.n), key=lambda s: (_angle(p, s), s))
    order = order[offset % p.n :] + order[: offset % p.n]
    total = sum(p.q)
    target = min(p.cap, math.ceil(total / k) + slack)
    groups: list[list[int]] = [[]]
    load = 0
    for s in order:
        if load + p.q[s] > target and groups[-1]:
            groups.append([])
            load = 0
        groups[-1].append(s)
        load += p.q[s]
    loads = [sum(p.q[s] for s in g) for g in groups]
    extra: list[int] = []
    if len(groups) > k:
        for g in groups[k:]:
            extra.extend(g)
        groups, loads = groups[:k], loads[:k]
    unassigned: list[int] = []
    for s in sorted(extra, key=lambda s: -p.q[s]):
        if not _insert_cheapest(p, groups, loads, s):
            unassigned.append(s)
    routes = [nn_route(p, g) for g in groups]
    routes += [[] for _ in range(k - len(routes))]
    return Plan(routes, sorted(unassigned), "sweep")


def savings(p: Problem) -> Plan:
    """Clarke-Wright savings adapted to a one-way trip that ends at the school."""
    routes: dict[int, list[int]] = {s: [s] for s in range(p.n)}
    owner = list(range(p.n))
    load = list(p.q)
    pairs = sorted(
        ((p.dist[i][p.n] - p.dist[i][j], i, j) for i in range(p.n) for j in range(p.n) if i != j),
        reverse=True,
    )
    for gain, i, j in pairs:
        if gain <= 0:
            break
        ra, rb = owner[i], owner[j]
        if ra == rb or routes[ra][-1] != i or routes[rb][0] != j or load[ra] + load[rb] > p.cap:
            continue
        merged = routes[ra] + routes[rb]
        if route_cost(p, merged)[1] > 0:
            continue
        routes[ra] = merged
        load[ra] += load[rb]
        for s in routes[rb]:
            owner[s] = ra
        del routes[rb]
    return Plan([routes[r] for r in sorted(routes)], [], "savings")


def naive_baseline(p: Problem) -> Plan:
    """Nearest-stop-first single sweep: one long tour, sliced into buses whenever a bus fills up.

    It ignores the ride limit and the fleet size, which is what a first attempt on paper looks like.
    """
    tour = nn_route(p, list(range(p.n)))
    routes: list[list[int]] = [[]]
    load = 0
    for s in tour:
        if load + p.q[s] > p.cap:
            routes.append([])
            load = 0
        routes[-1].append(s)
        load += p.q[s]
    return Plan(routes, [], "naive")
