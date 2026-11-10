"""Weekly meal plan: greedy day-by-day selection with stock consumption and no repeated recipes."""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from datetime import date, timedelta

from pantry.catalog import CATALOG, normalize
from pantry.recipes import RecipeRanker, ScoredRecipe
from pantry.urgency import PantryItem, RawItem, enrich
from pantry.waste_model import WasteModel

MIN_PLAN_SCORE = 0.5  # below this a recipe saves too little food to be worth the shopping trip


@dataclass
class PlanDay:
    day: date
    pick: ScoredRecipe | None


@dataclass
class Plan:
    days: list[PlanDay]
    waste_kg: float
    waste_value: float
    left_over_at_risk: list[PantryItem] = field(default_factory=list)


def plan_week(
    raws: list[RawItem],
    ranker: RecipeRanker,
    model: WasteModel,
    today: date,
    household: int = 2,
    days: int = 7,
) -> Plan:
    """Each day cook the best-scoring recipe given what is left and how urgent it has become that day.

    Greedy by expiry-weighted score is the knapsack-style heuristic: a recipe's "value" is the urgency it
    rescues, its "cost" is the ingredients it uses up (consumed so later days see the reduced stock).
    """
    stock = [copy(r) for r in raws]
    chosen: set[int] = set()
    out: list[PlanDay] = []
    kg = value = 0.0
    for d in range(days):
        day = today + timedelta(days=d)
        ranked = ranker.rank(enrich(stock, day, household, model), limit=1, exclude=chosen)
        if not ranked or ranked[0].score < MIN_PLAN_SCORE:
            out.append(PlanDay(day, None))
            continue
        best = ranked[0]
        chosen.add(best.recipe.id)
        for u in best.used:
            ing = CATALOG[normalize(u.canonical)]
            stock[u.idx].quantity = max(0.0, stock[u.idx].quantity - u.kg / ing.unit_kg)
        kg += best.waste_kg
        value += best.waste_value
        out.append(PlanDay(day, best))
    horizon = today + timedelta(days=days - 1)
    leftovers = [i for i in enrich(stock, today, household, model) if 0 <= i.days_left and i.expiry <= horizon]
    return Plan(out, round(kg, 3), round(value, 2), leftovers)
