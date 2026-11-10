"""Local search: 2-opt inside a route, relocate and swap between routes."""

from __future__ import annotations

from busroutes.evaluate import penalised, route_cost
from busroutes.instance import Problem

EPS = 1e-9


def two_opt(p: Problem, route: list[int]) -> list[int]:
    """Reverse segments while that shortens the route without making student rides later than allowed."""
    best = list(route)
    km, over = route_cost(p, best)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                ckm, cover = route_cost(p, cand)
                if ckm < km - EPS and cover <= over + EPS:
                    best, km, over = cand, ckm, cover
                    improved = True
    return best


def local_search(p: Problem, routes: list[list[int]], rounds: int = 30) -> list[list[int]]:
    """Relocate and swap stops between routes (capacity respected), tidying each route with 2-opt."""
    rs = [list(r) for r in routes]
    q, cap = p.q, p.cap
    for _ in range(rounds):
        improved = False
        costs = [penalised(p, r) for r in rs]
        loads = [sum(q[s] for s in r) for r in rs]
        owner = {s: ri for ri, r in enumerate(rs) for s in r}
        for s in range(p.n):
            if s not in owner:
                continue
            ra = owner[s]
            a_wo = [x for x in rs[ra] if x != s]
            ca_wo = penalised(p, a_wo)
            best_delta, best_move = -EPS, None
            for m in p.near[s]:
                rb = owner.get(m)
                if rb is None:
                    continue
                if rb != ra and loads[rb] + q[s] <= cap:
                    base = rs[rb]
                    j = base.index(m)
                    for pos in (j, j + 1):
                        nb = base[:pos] + [s] + base[pos:]
                        delta = ca_wo + penalised(p, nb) - costs[ra] - costs[rb]
                        if delta < best_delta:
                            best_delta, best_move = delta, ("move", rb, nb, a_wo, None)
                elif rb == ra:
                    j = a_wo.index(m)
                    for pos in (j, j + 1):
                        nb = a_wo[:pos] + [s] + a_wo[pos:]
                        delta = penalised(p, nb) - costs[ra]
                        if delta < best_delta:
                            best_delta, best_move = delta, ("inside", ra, nb, None, None)
                if rb != ra and loads[ra] - q[s] + q[m] <= cap and loads[rb] - q[m] + q[s] <= cap:
                    na = [m if x == s else x for x in rs[ra]]
                    nb = [s if x == m else x for x in rs[rb]]
                    delta = penalised(p, na) + penalised(p, nb) - costs[ra] - costs[rb]
                    if delta < best_delta:
                        best_delta, best_move = delta, ("swap", rb, nb, na, m)
            if best_move is None:
                continue
            kind, rb, nb, na, m = best_move
            if kind == "inside":
                rs[rb] = nb
            else:
                rs[ra] = na if kind == "swap" else a_wo
                rs[rb] = nb
            for ri in {ra, rb}:
                costs[ri] = penalised(p, rs[ri])
                loads[ri] = sum(q[x] for x in rs[ri])
            owner = {x: ri for ri, r in enumerate(rs) for x in r}
            improved = True
        rs = [two_opt(p, r) for r in rs]
        if not improved:
            break
    return rs
