"""Plain-language reasons: why a person is on a shift, why a wish was not granted, why a place is empty."""

from __future__ import annotations

from collections import Counter

from .fairness import PersonStats
from .model import OFF, Grid, Instance
from .rules import RULE_TEXT, block_reason


def _join(counter: Counter[str], total: int) -> str:
    parts = [f"{n} {label}" for label, n in counter.most_common()]
    return f"{total} colleagues checked: " + ", ".join(parts)


def blockers(inst: Instance, grid: Grid, d: int, k: int, skill: str | None = None, skip: int | None = None) -> str:
    """Why couldn't each other person take shift k on day d? One short sentence listing the counts."""
    counter: Counter[str] = Counter()
    total = 0
    for q in range(inst.P):
        if q == skip or grid[q][d] == k:
            continue
        if skill is not None and skill not in inst.skills[q]:
            continue
        total += 1
        why = block_reason(inst, grid, q, d, k)
        counter[RULE_TEXT[why] if why else "free but would break something else"] += 1
    if total == 0:
        return f"nobody on the team holds {skill}" if skill else "no other staff"
    return _join(counter, total)


def gap_reason(inst: Instance, grid: Grid, d: int, k: int) -> str:
    """Reason a slot is short of people or of a required skill."""
    have = sum(1 for p in range(inst.P) if grid[p][d] == k)
    missing = inst.need[d][k] - have
    bits = []
    if missing > 0:
        bits.append(f"{missing} place{'s' if missing > 1 else ''} empty. " + blockers(inst, grid, d, k))
    for s, req in inst.skill_need[d][k].items():
        got = sum(1 for p in range(inst.P) if grid[p][d] == k and s in inst.skills[p])
        if got < req:
            bits.append(f"needs {req - got} more with {s}: " + blockers(inst, grid, d, k, skill=s))
    return " | ".join(bits)


def unmet_reason(inst: Instance, grid: Grid, p: int, d: int, k: int) -> str:
    """Why was p kept on shift k at day d even though they asked otherwise? Try handing it to each colleague."""
    counter: Counter[str] = Counter()
    total = 0
    needed = [s for s in inst.skill_need[d][k] if s in inst.skills[p]]
    for q in range(inst.P):
        if q == p:
            continue
        total += 1
        if grid[q][d] != OFF:
            counter["already working that day"] += 1
            continue
        why = block_reason(inst, grid, q, d, k)
        if why:
            counter[RULE_TEXT[why]] += 1
        elif any(
            s not in inst.skills[q] and sum(1 for r in range(inst.P) if grid[r][d] == k and s in inst.skills[r]) <= 1
            for s in needed
        ):
            counter["lacking the required skill"] += 1
        elif d in inst.off_req[q]:
            counter["also asked for that day off"] += 1
        else:
            counter["free, but the hand-over costs more fairness or hours elsewhere"] += 1
    return _join(counter, total)


def assignment_why(inst: Instance, grid: Grid, stats: list[PersonStats], p: int, d: int) -> str:
    k = grid[p][d]
    st = stats[p]
    parts: list[str] = []
    needed = [s for s in inst.skill_need[d][k] if s in inst.skills[p]]
    if needed:
        pool = sum(1 for q in range(inst.P) if d not in inst.leave[q] and needed[0] in inst.skills[q])
        skills = " + ".join(needed)
        parts.append(
            f"Covers the required {skills} on this shift (one of {pool} {needed[0]} holders available that day)"
        )
    else:
        parts.append(f"Fills one of the {inst.need[d][k]} places on {inst.slot_text(d, k)}")
    if d in inst.off_req[p]:
        parts.append("Against their day-off request. " + unmet_reason(inst, grid, p, d, k))
    elif k in inst.avoid[p]:
        parts.append(f"Against their wish to avoid {inst.kinds[k]}s. " + unmet_reason(inst, grid, p, d, k))
    elif k in inst.preferred[p]:
        parts.append(f"Matches their preferred {inst.kinds[k]} shift")
    n = len(stats)
    if inst.weekend[d]:
        avg = sum(s.weekends for s in stats) / n
        parts.append(f"Weekend shift {st.weekends} for them (team average {avg:.1f})")
    elif inst.kinds[k] in ("evening", "night"):
        avg = sum(s.unsocial for s in stats) / n
        parts.append(f"Evening/night shift {st.unsocial} for them (team average {avg:.1f})")
    else:
        parts.append(f"Brings them to {st.hours}h against a {st.contract:g}h contract")
    return ". ".join(x.rstrip(".") for x in parts) + "."
