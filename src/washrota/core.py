"""Assign laundry slots to residents with the most preference satisfaction.

Each resident ranks acceptable slots (first = best). Cost = rank position (0 best); an unranked slot
costs a large penalty so it is only used when nothing better exists. Assignment is solved exactly with
the Hungarian algorithm (minimum-cost perfect matching on a padded square matrix).
"""

from __future__ import annotations

PENALTY = 10


class RotaError(ValueError):
    """Invalid input."""


def hungarian(cost: list[list[float]]) -> list[int]:
    """Min-cost assignment for a square matrix; returns column chosen for each row. O(n^3)."""
    n = len(cost)
    if n == 0 or any(len(r) != n for r in cost):
        raise RotaError("cost matrix must be square and non-empty")
    inf = float("inf")
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
    p, way = [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], inf, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    result = [0] * n
    for j in range(1, n + 1):
        result[p[j] - 1] = j - 1
    return result


def build_cost(slots: list[str], prefs: dict[str, list[str]]) -> tuple[list[str], list[list[float]]]:
    if len(set(slots)) != len(slots):
        raise RotaError("slots must be unique")
    names = list(prefs)
    if len(names) > len(slots):
        raise RotaError("more residents than slots")
    for n, ranked in prefs.items():
        bad = [s for s in ranked if s not in slots]
        if bad or len(set(ranked)) != len(ranked):
            raise RotaError(f"{n}: unknown or repeated slots")
    size = len(slots)
    rows = []
    for n in names:
        r = prefs[n]
        rows.append([float(r.index(s)) if s in r else float(PENALTY) for s in slots])
    rows += [[0.0] * size for _ in range(size - len(names))]  # dummy residents absorb spare slots
    return names, rows


def assign(slots: list[str], prefs: dict[str, list[str]]) -> dict[str, str]:
    names, cost = build_cost(slots, prefs)
    cols = hungarian(cost)
    return {n: slots[cols[i]] for i, n in enumerate(names)}


def rank_of(prefs: dict[str, list[str]], who: str, slot: str) -> int | None:
    r = prefs[who]
    return r.index(slot) if slot in r else None


def total_cost(prefs: dict[str, list[str]], plan: dict[str, str]) -> int:
    return sum(PENALTY if rank_of(prefs, w, s) is None else rank_of(prefs, w, s) or 0 for w, s in plan.items())


def first_come(slots: list[str], prefs: dict[str, list[str]]) -> dict[str, str]:
    """Baseline: residents in order each take their best free slot (else the first free one)."""
    free, out = list(slots), {}
    for who, ranked in prefs.items():
        pick = next((s for s in ranked if s in free), free[0])
        free.remove(pick)
        out[who] = pick
    return out


def summary(prefs: dict[str, list[str]], plan: dict[str, str]) -> dict[str, float]:
    ranks = [rank_of(prefs, w, s) for w, s in plan.items()]
    got = [r for r in ranks if r is not None]
    return {
        "first_choice": sum(1 for r in got if r == 0),
        "got_a_choice": len(got),
        "no_choice": len(ranks) - len(got),
        "total_cost": total_cost(prefs, plan),
    }
