"""Hard rules. A roster that breaks any of these is invalid, never merely "worse"."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .model import OFF, Grid, Instance

RULE_LEAVE = "leave"
RULE_DOUBLE = "no_double_shift"
RULE_REST = "min_rest"
RULE_CONSEC = "max_consecutive_days"
RULE_WEEKLY = "max_weekly_hours"
RULE_CAPACITY = "headcount_cap"

RULE_TEXT = {
    RULE_LEAVE: "on leave",
    RULE_DOUBLE: "already working that day",
    RULE_REST: "blocked by the minimum rest rule",
    RULE_CONSEC: "blocked by the consecutive-days limit",
    RULE_WEEKLY: "blocked by the weekly hours cap",
    RULE_CAPACITY: "shift already full",
}


@dataclass(frozen=True)
class Violation:
    rule: str
    staff_id: str
    day: int
    message: str


def row_violations(inst: Instance, p: int, row: list[int]) -> Iterator[Violation]:
    """Yield every hard-rule violation in one person's row."""
    sid = inst.problem.staff[p].id
    name = inst.problem.staff[p].name
    rules = inst.problem.rules
    run = 0
    for d in range(inst.D):
        k = row[d]
        if k == OFF:
            run = 0
            continue
        if d in inst.leave[p]:
            yield Violation(RULE_LEAVE, sid, d, f"{name} is on leave on {inst.label(d)}.")
        if d + 1 < inst.D and row[d + 1] != OFF and inst.rest_conflict[k][row[d + 1]]:
            yield Violation(
                RULE_REST,
                sid,
                d + 1,
                f"{name} would have under {rules.min_rest_hours}h rest between {inst.slot_text(d, k)} "
                f"and {inst.slot_text(d + 1, row[d + 1])}.",
            )
        run += 1
        if run > inst.max_consec[p]:
            yield Violation(RULE_CONSEC, sid, d, f"{name} would work {run} days in a row (limit {inst.max_consec[p]}).")
    for w in range(inst.weeks):
        total = sum(inst.hours[k] for k in row[w * 7 : w * 7 + 7] if k != OFF)
        if total > rules.max_weekly_hours:
            yield Violation(
                RULE_WEEKLY, sid, w * 7, f"{name} would work {total}h in week {w + 1} (cap {rules.max_weekly_hours}h)."
            )


def row_ok(inst: Instance, p: int, row: list[int]) -> bool:
    return next(row_violations(inst, p, row), None) is None


def violations(inst: Instance, grid: Grid, doubles: list[tuple[int, int]] | None = None) -> list[Violation]:
    out: list[Violation] = []
    for p, d in doubles or []:
        s = inst.problem.staff[p]
        out.append(Violation(RULE_DOUBLE, s.id, d, f"{s.name} is given two shifts on {inst.label(d)}."))
    for p in range(inst.P):
        out.extend(row_violations(inst, p, grid[p]))
    for d in range(inst.D):
        for k in range(inst.K):
            n = sum(1 for p in range(inst.P) if grid[p][d] == k)
            if n > inst.need[d][k]:
                out.append(
                    Violation(
                        RULE_CAPACITY, "", d, f"{inst.slot_text(d, k)} has {n} people but needs {inst.need[d][k]}."
                    )
                )
    return out


def block_reason(inst: Instance, grid: Grid, p: int, d: int, k: int) -> str | None:
    """Why could person p not take shift k on day d right now? None means they could."""
    cur = grid[p][d]
    if cur != OFF:
        return RULE_DOUBLE if cur != k else None
    if d in inst.leave[p]:
        return RULE_LEAVE
    row = list(grid[p])
    row[d] = k
    for v in row_violations(inst, p, row):
        if v.rule != RULE_LEAVE:
            return v.rule
    return None
