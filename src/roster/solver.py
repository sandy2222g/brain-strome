"""Constructive greedy start, then simulated-annealing improvement. Pure Python, seeded, hard rules never broken."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from .fairness import gini, load
from .model import OFF, Grid, Instance, new_grid
from .rules import row_ok

# Soft-cost weights (what the solver trades off). Missing cover always dominates.
W_SHORT = 1000.0  # per missing person
W_SKILL = 800.0  # per missing skill holder
W_OFF_REQ = 8.0  # worked on a requested day off
W_AVOID = 4.0  # worked a shift kind they asked to avoid
W_NOT_PREF = 1.0  # worked a shift that is not one of their preferred kinds
W_UNDER = 0.7  # per hour under contract
W_OVER = 1.4  # per hour over contract
W_GINI_UNSOCIAL = 300.0
W_GINI_WEEKEND = 300.0
W_GINI_HOURS = 900.0


class State:
    """A grid plus cached cost parts so a move is scored by touching only the people and slots it changes."""

    def __init__(self, inst: Instance, grid: Grid | None = None) -> None:
        self.inst = inst
        self.grid: Grid = [r[:] for r in grid] if grid is not None else new_grid(inst)
        P, D, K = inst.P, inst.D, inst.K
        self.count = [[0] * K for _ in range(D)]
        self.skc: list[list[dict[str, int]]] = [
            [{s: 0 for s in inst.skill_need[d][k]} for k in range(K)] for d in range(D)
        ]
        for p in range(P):
            for d in range(D):
                if self.grid[p][d] != OFF:
                    self._add(p, d, self.grid[p][d], 1)
        self.pcost = [0.0] * P
        self.lw = [0.0] * P
        self.lu = [0.0] * P
        self.lh = [0.0] * P
        for p in range(P):
            self._refresh(p)
        self.cov = sum(self._slot_cost(d, k) for d in range(D) for k in range(K))
        self.total = self._compute_total()
        self._undo: tuple | None = None

    # -- cost parts ---------------------------------------------------------------------------------------------
    def _add(self, p: int, d: int, k: int, sign: int) -> None:
        self.count[d][k] += sign
        sk = self.skc[d][k]
        if sk:
            have = self.inst.skills[p]
            for s in sk:
                if s in have:
                    sk[s] += sign

    def _slot_cost(self, d: int, k: int) -> float:
        inst = self.inst
        short = inst.need[d][k] - self.count[d][k]
        c = W_SHORT * short if short > 0 else 0.0
        for s, req in inst.skill_need[d][k].items():
            miss = req - self.skc[d][k][s]
            if miss > 0:
                c += W_SKILL * miss
        return c

    def _refresh(self, p: int) -> None:
        inst = self.inst
        row = self.grid[p]
        hours = wk = un = 0
        pen = 0.0
        pref, avoid, off_req = inst.preferred[p], inst.avoid[p], inst.off_req[p]
        for d in range(inst.D):
            k = row[d]
            if k == OFF:
                continue
            hours += inst.hours[k]
            if inst.weekend[d]:
                wk += 1
            if inst.kinds[k] in ("evening", "night"):
                un += 1
            if d in off_req:
                pen += W_OFF_REQ
            if k in avoid:
                pen += W_AVOID
            if pref and k not in pref:
                pen += W_NOT_PREF
        dev = hours - inst.target[p]
        pen += W_UNDER * -dev if dev < 0 else W_OVER * dev
        contract = inst.problem.staff[p].contract_hours * inst.D / 7
        self.pcost[p] = pen
        self.lw[p] = load(wk, contract)
        self.lu[p] = load(un, contract)
        self.lh[p] = hours / max(contract, 8.0)

    def _fair(self) -> float:
        return W_GINI_WEEKEND * gini(self.lw) + W_GINI_UNSOCIAL * gini(self.lu) + W_GINI_HOURS * gini(self.lh)

    def _compute_total(self) -> float:
        return self.cov + sum(self.pcost) + self._fair()

    # -- moves --------------------------------------------------------------------------------------------------
    def _set(self, p: int, d: int, v: int) -> None:
        old = self.grid[p][d]
        if old == v:
            return
        if old != OFF:
            self._add(p, d, old, -1)
        if v != OFF:
            self._add(p, d, v, 1)
        self.grid[p][d] = v

    def propose(self, changes: list[tuple[int, int, int]]) -> float | None:
        """Apply changes tentatively. Returns the cost delta, or None (already reverted) if a hard rule breaks."""
        persons = {p for p, _, _ in changes}
        slots = set()
        for p, d, v in changes:
            if self.grid[p][d] != OFF:
                slots.add((d, self.grid[p][d]))
            if v != OFF:
                slots.add((d, v))
        old_cells = [(p, d, self.grid[p][d]) for p, d, _ in changes]
        saved_p = [(p, self.pcost[p], self.lw[p], self.lu[p], self.lh[p]) for p in persons]
        old_cov = sum(self._slot_cost(d, k) for d, k in slots)
        prev_total = self.total
        for p, d, v in changes:
            self._set(p, d, v)
        self._undo = (old_cells, saved_p)
        inst = self.inst
        for d, k in slots:
            if self.count[d][k] > inst.need[d][k]:
                self.reject()
                return None
        for p in persons:
            if not row_ok(inst, p, self.grid[p]):
                self.reject()
                return None
        for p in persons:
            self._refresh(p)
        new_cov = sum(self._slot_cost(d, k) for d, k in slots)
        self.cov += new_cov - old_cov
        self.total = self._compute_total()
        self._prev_total = prev_total
        self._cov_delta = new_cov - old_cov
        return self.total - prev_total

    def reject(self) -> None:
        assert self._undo is not None
        old_cells, saved_p = self._undo
        for p, d, v in reversed(old_cells):
            self._set(p, d, v)
        for p, pc, lw, lu, lh in saved_p:
            self.pcost[p], self.lw[p], self.lu[p], self.lh[p] = pc, lw, lu, lh
        if hasattr(self, "_prev_total") and self._prev_total is not None:
            self.cov -= self._cov_delta
            self.total = self._prev_total
        self._prev_total = None
        self._undo = None

    def accept(self) -> None:
        self._prev_total = None
        self._undo = None

    _prev_total: float | None = None
    _cov_delta: float = 0.0


@dataclass
class SolveResult:
    grid: Grid
    cost: float
    iterations: int
    accepted: int
    seconds: float
    greedy_cost: float


def _slot_order(inst: Instance) -> list[tuple[int, int]]:
    """Hardest slots first: those with skill needs and few people who could possibly work them."""
    keyed = []
    for d in range(inst.D):
        for k in range(inst.K):
            if inst.need[d][k] == 0:
                continue
            avail = [p for p in range(inst.P) if d not in inst.leave[p]]
            tight = 0.0
            for s, req in inst.skill_need[d][k].items():
                holders = sum(1 for p in avail if s in inst.skills[p])
                tight = max(tight, req / max(holders, 0.5))
            tight = max(tight, inst.need[d][k] / max(len(avail), 1))
            keyed.append((-tight, d, k))
    keyed.sort()
    return [(d, k) for _, d, k in keyed]


def greedy(inst: Instance, st: State) -> None:
    for d, k in _slot_order(inst):
        for _ in range(inst.need[d][k]):
            best: tuple[float, int] | None = None
            for p in range(inst.P):
                if st.grid[p][d] != OFF:
                    continue
                delta = st.propose([(p, d, k)])
                if delta is None:
                    continue
                st.reject()
                if best is None or delta < best[0] - 1e-9:
                    best = (delta, p)
            if best is None:
                break
            st.propose([(best[1], d, k)])
            st.accept()


def _propose_move(inst: Instance, st: State, rng: random.Random) -> list[tuple[int, int, int]] | None:
    """Pick a neighbouring roster. Most moves keep every shift's headcount, so they are exchanges."""
    P, D, K = inst.P, inst.D, inst.K
    grid = st.grid
    r = rng.random()
    if r < 0.5:  # hand a shift to someone else (or swap two people's shifts on the same day)
        d = rng.randrange(D)
        workers = [q for q in range(P) if grid[q][d] != OFF]
        if not workers:
            return None
        q = rng.choice(workers)
        p = rng.randrange(P)
        if p == q or grid[p][d] == grid[q][d]:
            return None
        return [(q, d, grid[p][d]), (p, d, grid[q][d])]
    if r < 0.85:  # exchange days: p and q trade shifts that sit on different days
        d1, d2 = rng.randrange(D), rng.randrange(D)
        if d1 == d2:
            return None
        p, q = rng.randrange(P), rng.randrange(P)
        if p == q:
            return None
        a, b = grid[p][d1], grid[q][d2]
        if a == OFF or b == OFF or grid[p][d2] != OFF or grid[q][d1] != OFF:
            return None
        return [(p, d1, OFF), (q, d2, OFF), (p, d2, b), (q, d1, a)]
    if r < 0.93:  # fill a vacancy
        d, k = rng.randrange(D), rng.randrange(K)
        if st.count[d][k] >= inst.need[d][k]:
            return None
        p = rng.randrange(P)
        if grid[p][d] != OFF:
            return None
        return [(p, d, k)]
    p, d = rng.randrange(P), rng.randrange(D)  # drop a shift (the cost function decides if that helps)
    if grid[p][d] == OFF:
        return None
    return [(p, d, OFF)]


def anneal(inst: Instance, st: State, rng: random.Random, iterations: int) -> tuple[Grid, float, int]:
    best_grid = [r[:] for r in st.grid]
    best_total = st.total
    t0, t1 = 14.0, 0.08
    accepted = 0
    for i in range(iterations):
        temp = t0 * (t1 / t0) ** (i / max(iterations - 1, 1))
        changes = _propose_move(inst, st, rng)
        if changes is None:
            continue
        delta = st.propose(changes)
        if delta is None:
            continue
        if delta <= 0 or rng.random() < math.exp(-delta / temp):
            st.accept()
            accepted += 1
            if st.total < best_total - 1e-9:
                best_total = st.total
                best_grid = [r[:] for r in st.grid]
        else:
            st.reject()
    return best_grid, best_total, accepted


def solve(inst: Instance, seed: int = 7, iterations: int | None = None) -> SolveResult:
    t = time.perf_counter()
    rng = random.Random(seed)
    st = State(inst)
    greedy(inst, st)
    greedy_cost = st.total
    iters = iterations if iterations is not None else 40000 * inst.weeks
    grid, cost, accepted = anneal(inst, st, rng, iters)
    return SolveResult(grid, cost, iters, accepted, round(time.perf_counter() - t, 3), greedy_cost)


def objective(inst: Instance, grid: Grid) -> float:
    return State(inst, grid).total
