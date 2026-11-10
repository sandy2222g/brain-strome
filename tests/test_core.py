from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from pantry.catalog import CATALOG, STAPLES, normalize, resolve
from pantry.planner import plan_week
from pantry.recipes import MISSING_PENALTY, TFIDF_WEIGHT, RecipeRanker
from pantry.urgency import RawItem, enrich, prioritize, status_for, time_urgency
from pantry.waste_model import WasteModel, generate_waste_events

TODAY = date(2026, 1, 12)


def raw(name: str, days: int, qty: float = 1.0) -> RawItem:
    return RawItem(name, TODAY + timedelta(days=days), qty)


def test_normalize_and_resolve() -> None:
    assert normalize("Tomatoes") == normalize("tomato")
    assert normalize("Eggs") == "egg"
    assert resolve("cherry tomatoes") is CATALOG["tomato"]
    assert resolve("chicken breasts") is CATALOG["chicken breast"]
    assert resolve("unobtainium") is None


def test_every_recipe_ingredient_is_in_catalog(ranker: RecipeRanker) -> None:
    assert len(ranker.recipes) >= 60
    for r in ranker.recipes:
        for ing in r.ingredients:
            assert ing in STAPLES or normalize(ing) in CATALOG, (r.name, ing)


def test_time_urgency_monotonic() -> None:
    vals = [time_urgency(d) for d in range(-2, 15)]
    assert vals[0] == vals[1] == vals[2] == 1.0
    assert all(a >= b for a, b in zip(vals, vals[1:], strict=False))
    assert status_for(-1) == "expired" and status_for(0) == "use today" and status_for(20) == "fine"


def test_waste_model_quality_and_direction(model: WasteModel) -> None:
    assert model.metrics["roc_auc"] > 0.8
    assert model.metrics["brier"] < model.metrics["brier_baseline"]
    rows = pd.DataFrame(
        {
            "category": ["leafy", "grain"],
            "storage": ["fridge", "pantry"],
            "days_since_purchase": [6, 6],
            "household_size": [2, 2],
        }
    )
    p_leafy, p_grain = model.predict_proba(rows)
    assert p_leafy > 0.4 > 0.2 > p_grain


def test_waste_data_is_deterministic() -> None:
    pd.testing.assert_frame_equal(generate_waste_events(200, seed=3), generate_waste_events(200, seed=3))


def test_prioritize_orders_by_urgency_and_puts_expired_last(model: WasteModel) -> None:
    items = enrich([raw("rice", 300), raw("spinach", 1), raw("milk", 6), raw("lettuce", -2)], TODAY, 2, model)
    order = [i.name for i in prioritize(items)]
    assert order[0] == "spinach"
    assert order[-1] == "lettuce"
    assert order.index("milk") < order.index("rice")


def test_enrich_defaults_when_expiry_missing(model: WasteModel) -> None:
    (it,) = enrich([RawItem("milk")], TODAY, 2, model)
    assert it.days_left == 12 and it.storage == "fridge"
    (it2,) = enrich([RawItem("mystery goo", quantity=2)], TODAY, 2, model)
    assert it2.canonical is None and it2.category == "other"


def test_ranker_prefers_recipes_using_expiring_items(model: WasteModel, ranker: RecipeRanker) -> None:
    pantry = [raw("spinach", 1), raw("egg", 20, 6), raw("butter", 20), raw("pasta", 300), raw("tomato", 20)]
    ranked = ranker.rank(enrich(pantry, TODAY, 2, model), limit=3)
    assert ranked[0].recipe.name == "Spinach and Egg Scramble"
    assert ranked[0].missing == []
    assert ranked[0].waste_kg > 0 and ranked[0].waste_value > 0


def test_ranker_never_uses_expired_items(model: WasteModel, ranker: RecipeRanker) -> None:
    pantry = [raw("spinach", -1), raw("egg", -1), raw("butter", -1)]
    assert ranker.rank(enrich(pantry, TODAY, 2, model)) == []


def test_score_formula_penalises_missing(model: WasteModel, ranker: RecipeRanker) -> None:
    pantry = [raw("mushroom", 1), raw("spinach", 1), raw("egg", 2, 4), raw("cream", 2), raw("pasta", 200)]
    ranked = ranker.rank(enrich(pantry, TODAY, 2, model), limit=20)
    assert any(r.missing for r in ranked)
    for r in ranked:
        expected = sum(u.urgency for u in r.used) - MISSING_PENALTY * len(r.missing) + TFIDF_WEIGHT * r.cosine
        assert abs(r.score - expected) < 1e-3
    assert [r.score for r in ranked] == sorted((r.score for r in ranked), reverse=True)


def test_plan_consumes_stock_and_never_repeats(model: WasteModel, ranker: RecipeRanker) -> None:
    names = [("spinach", 2, 1), ("egg", 10, 6), ("milk", 3, 1), ("bread", 1, 1), ("mushroom", 2, 1),
             ("pasta", 300, 1), ("tomato", 4, 4), ("cheddar", 20, 1), ("onion", 10, 3), ("potato", 15, 5)]  # fmt: skip
    pantry = [raw(n, d, q) for n, d, q in names]
    plan = plan_week(pantry, ranker, model, TODAY, 2, 7)
    assert len(plan.days) == 7
    picks = [d.pick.recipe.id for d in plan.days if d.pick]
    assert len(picks) == len(set(picks)) >= 3
    assert plan.waste_kg > 0 and plan.waste_value > 0
    assert pantry[0].quantity == 1.0  # input is not mutated


def test_plan_with_empty_matches_skips_days(model: WasteModel, ranker: RecipeRanker) -> None:
    plan = plan_week([raw("mystery goo", 3)], ranker, model, TODAY)
    assert all(d.pick is None for d in plan.days)
    assert plan.waste_kg == 0
