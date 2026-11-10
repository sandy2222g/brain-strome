"""Swap check: would exchanging two assignments break a hard rule, lose skill cover, or change fairness?"""

from __future__ import annotations

from typing import Any

from .fairness import fairness_report, person_stats
from .model import OFF, Assignment, Instance, assignments_to_grid
from .rules import violations


def swap_check(inst: Instance, assignments: list[Assignment], a: tuple[str, int], b: tuple[str, int]) -> dict[str, Any]:
    """Person A takes B's shift and person B takes A's shift.

    If B has no shift on that day the check is a hand-over: A's shift goes to B (same day only).
    """
    grid, doubles = assignments_to_grid(inst, assignments)
    for sid, day in (a, b):
        if sid not in inst.staff_index:
            raise ValueError(f"unknown staff id {sid}")
        if not 0 <= day < inst.D:
            raise ValueError(f"day {day} is outside the period")
    pa, da = inst.staff_index[a[0]], a[1]
    pb, db = inst.staff_index[b[0]], b[1]
    ka, kb = grid[pa][da], grid[pb][db]
    if ka == OFF:
        raise ValueError("the first cell has no shift to swap")
    if (pa, da) == (pb, db):
        raise ValueError("choose two different assignments")
    if kb == OFF and da != db:
        raise ValueError("a shift can only be handed to someone with no shift on the same day")

    before_viol = {(v.rule, v.staff_id, v.day) for v in violations(inst, grid, doubles)}
    new = [r[:] for r in grid]
    new[pa][da] = OFF
    new[pb][db] = OFF
    new_doubles = list(doubles)
    for p, d, k in ((pa, db, kb), (pb, da, ka)):
        if k == OFF:
            continue
        if new[p][d] != OFF:
            new_doubles.append((p, d))
        else:
            new[p][d] = k
    found = [v for v in violations(inst, new, new_doubles) if (v.rule, v.staff_id, v.day) not in before_viol]

    lost = []
    for d, k in {(da, ka), (db, kb)}:
        if k == OFF:
            continue
        for s, req in inst.skill_need[d][k].items():
            got = sum(1 for p in range(inst.P) if new[p][d] == k and s in inst.skills[p])
            was = sum(1 for p in range(inst.P) if grid[p][d] == k and s in inst.skills[p])
            if got < req <= was:
                lost.append(
                    {"day": d, "kind": inst.kinds[k], "skill": s, "text": f"{inst.slot_text(d, k)} would lose its {s}"}
                )

    s0, s1 = person_stats(inst, grid), person_stats(inst, new)
    f0, f1 = fairness_report(s0), fairness_report(s1)
    u0, u1 = sum(s.unmet for s in s0), sum(s.unmet for s in s1)
    ok = not found
    if not ok:
        verdict = "Blocked: " + found[0].message
    elif lost:
        verdict = "Allowed by the rules, but " + lost[0]["text"] + "."
    else:
        verdict = "Allowed. No rule is broken and skill cover is kept."
    return {
        "ok": ok,
        "coverage_ok": not lost,
        "verdict": verdict,
        "violations": [v.__dict__ for v in found],
        "coverage_lost": lost,
        "fairness": {"before": f0["score"], "after": f1["score"], "delta": round(f1["score"] - f0["score"], 1)},
        "unmet_preferences": {"before": u0, "after": u1, "delta": u1 - u0},
        "hours": {
            a[0]: {"before": s0[pa].hours, "after": s1[pa].hours},
            b[0]: {"before": s0[pb].hours, "after": s1[pb].hours},
        },
    }
