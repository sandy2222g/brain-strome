"""Top-level solver: try the fewest buses that could work, build, improve, keep the best plan."""

from __future__ import annotations

import math
import random

from busroutes.construct import savings, sweep
from busroutes.evaluate import Plan, route_cost
from busroutes.improve import local_search, two_opt
from busroutes.instance import Problem


def plan_score(p: Problem, plan: Plan) -> tuple[float, int, int, float]:
    """Lower is better: unserved students, minutes over the limit, buses used, kilometres."""
    km = over = 0.0
    for r in plan.used():
        rk, ro = route_cost(p, r)
        km, over = km + rk, over + ro
    unserved = sum(p.q[s] for s in plan.unassigned)
    return (unserved, round(over, 6), len(plan.used()), km)


def solve(p: Problem) -> Plan:
    """Fewest buses that serve everyone inside the ride limit; otherwise the least-bad plan on the whole fleet."""
    rng = random.Random(p.inst.seed)
    total = sum(p.q)
    k_min = max(1, math.ceil(total / p.cap))
    fleet = p.inst.buses
    ks = list(range(min(k_min, fleet), fleet + 1))
    best: Plan | None = None
    for k in ks:
        starts: list[Plan] = []
        for slack in (0, 3):
            for _ in range(8):
                starts.append(sweep(p, k, rng.randrange(p.n), slack))
        starts.append(savings(p))
        scored = []
        for plan in starts:
            if len(plan.used()) > fleet:
                continue
            plan.routes = [two_opt(p, r) for r in plan.routes]
            scored.append((plan_score(p, plan), len(scored), plan))
        scored.sort(key=lambda t: (t[0], t[1]))
        for _, _, plan in scored[:2]:
            plan.routes = local_search(p, plan.routes)
            plan.method = f"{plan.method} + local search"
            if best is None or plan_score(p, plan) < plan_score(p, best):
                best = plan
        if best is not None and plan_score(p, best)[:2] == (0, 0.0):
            break
    if best is None:
        raise RuntimeError("no starting plan fits the fleet")
    best.routes = [r for r in best.routes if r] + [[] for _ in range(fleet - len(best.used()))]
    return best
