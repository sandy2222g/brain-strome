"""The naive comparison: a round-robin rota that ignores preferences and fairness but still obeys the hard rules."""

from __future__ import annotations

from .model import OFF, Grid, Instance, new_grid
from .rules import row_ok


def round_robin(inst: Instance) -> Grid:
    """Walk the slots in calendar order and hand each place to the next person in the rotation who can take it.

    Skill places go to the next qualified person first. Nobody's wishes are looked at.
    """
    grid = new_grid(inst)
    ptr = 0

    def take(d: int, k: int, skill: str | None) -> bool:
        nonlocal ptr
        for step in range(inst.P):
            p = (ptr + step) % inst.P
            if grid[p][d] != OFF or d in inst.leave[p]:
                continue
            if skill is not None and skill not in inst.skills[p]:
                continue
            grid[p][d] = k
            if row_ok(inst, p, grid[p]):
                ptr = (p + 1) % inst.P
                return True
            grid[p][d] = OFF
        return False

    for d in range(inst.D):
        for k in range(inst.K):
            for skill, req in inst.skill_need[d][k].items():
                have = sum(1 for p in range(inst.P) if grid[p][d] == k and skill in inst.skills[p])
                for _ in range(max(0, req - have)):
                    if sum(1 for p in range(inst.P) if grid[p][d] == k) >= inst.need[d][k] or not take(d, k, skill):
                        break
            while sum(1 for p in range(inst.P) if grid[p][d] == k) < inst.need[d][k]:
                if not take(d, k, None):
                    break
    return grid
