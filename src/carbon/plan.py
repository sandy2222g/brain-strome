"""Plan builder: applies chosen levers to the answers together, so interacting levers are never double counted."""

from __future__ import annotations

from dataclasses import dataclass

from carbon.calculator import CATEGORIES, calculate
from carbon.factors import Factors
from carbon.levers import BY_ID, LEVERS, saving_kg
from carbon.schema import Answers

MAX_PLAN = 3


class PlanError(ValueError):
    """The requested plan is not valid (unknown lever, too many, or not applicable)."""


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    alone_t: float  # saving if this were the only change
    in_plan_t: float  # saving added when applied after the levers before it


@dataclass(frozen=True)
class Plan:
    baseline_t: float
    after_t: float
    saved_t: float
    saved_pct: float
    interaction_t: float  # combined saving minus the sum of "alone" savings (negative = overlap avoided)
    steps: list[PlanStep]
    after_by_category_kg: dict[str, float]


def build_plan(a: Answers, lever_ids: list[str], factors: Factors | None = None) -> Plan:
    ids = list(dict.fromkeys(lever_ids))
    if len(ids) > MAX_PLAN:
        raise PlanError(f"a plan holds at most {MAX_PLAN} levers")
    unknown = [i for i in ids if i not in BY_ID]
    if unknown:
        raise PlanError(f"unknown lever: {', '.join(unknown)}")
    base = calculate(a, factors)
    current, current_total = a, base.total_kg
    steps: list[PlanStep] = []
    for lever_id in ids:
        lever = BY_ID[lever_id]
        alone = saving_kg(lever, a, factors)
        changed = lever.apply(current)
        if alone is None or changed is None:
            raise PlanError(f"{lever_id} does not apply to this household")
        new_total = calculate(changed, factors).total_kg
        steps.append(
            PlanStep(lever_id, lever.title, round(alone / 1000, 3), round((current_total - new_total) / 1000, 3))
        )
        current, current_total = changed, new_total
    after = calculate(current, factors)
    saved_kg = base.total_kg - after.total_kg
    return Plan(
        baseline_t=round(base.total_t, 3),
        after_t=round(after.total_t, 3),
        saved_t=round(saved_kg / 1000, 3),
        saved_pct=round(100 * saved_kg / base.total_kg, 1) if base.total_kg else 0.0,
        interaction_t=round(saved_kg / 1000 - sum(s.alone_t for s in steps), 3),
        steps=steps,
        after_by_category_kg={c: after.by_category_kg[c] for c in CATEGORIES},
    )


def suggest_plan(a: Answers, k: int = MAX_PLAN, factors: Factors | None = None) -> list[str]:
    """Greedy pick: each round adds the lever with the best extra saving per effort given those already chosen."""
    chosen: list[str] = []
    current, total = a, calculate(a, factors).total_kg
    for _ in range(min(k, MAX_PLAN)):
        best: tuple[float, str, Answers, float] | None = None
        for lever in LEVERS:
            if lever.id in chosen:
                continue
            changed = lever.apply(current)
            if changed is None:
                continue
            new_total = calculate(changed, factors).total_kg
            gain = total - new_total
            if gain < 5:
                continue
            score = gain / lever.effort
            if best is None or score > best[0]:
                best = (score, lever.id, changed, new_total)
        if best is None:
            break
        chosen.append(best[1])
        current, total = best[2], best[3]
    return chosen
