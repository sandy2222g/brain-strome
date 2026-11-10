from __future__ import annotations

from itertools import combinations

import pytest

from conftest import it
from packlist.optimizer import GRAM_STEP, Item, PackError, Trip, _greedy, _solve, adjust, consumables, optimise


def brute(items: list[Item], budget: int) -> float:
    best = 0.0
    for r in range(len(items) + 1):
        for combo in combinations(items, r):
            groups = [i.group for i in combo if i.group]
            if len(groups) != len(set(groups)) or sum(-(-i.weight_g // GRAM_STEP) * GRAM_STEP for i in combo) > budget:
                continue
            best = max(best, sum(i.utility for i in combo))
    return best


def test_dp_matches_brute_force_on_small_cases() -> None:
    items = [
        it("a", 300, 5),
        it("b", 400, 7),
        it("c", 500, 8),
        it("d", 200, 3, "g"),
        it("e", 250, 4, "g"),
        it("f", 100, 1),
    ]
    for budget in (300, 600, 900, 1200, 1750):
        assert _solve(items, budget)[0] == pytest.approx(brute(items, budget))


def test_dp_beats_greedy_when_ratio_misleads() -> None:
    items = [it("a", 600, 6.5), it("b", 500, 5.0), it("c", 500, 5.0)]
    best, _ = _solve(items, 1000)
    assert best == 10.0 and _greedy(items, 1000) == 6.5  # greedy takes the best ratio first and strands the budget


def test_never_two_items_from_one_group() -> None:
    _, picked = _solve([it("t1", 500, 9, "shelter"), it("t2", 400, 8, "shelter"), it("x", 100, 1)], 2000)
    assert sum(i.group == "shelter" for i in picked) == 1


def test_weight_limit_respected(gear: list[Item]) -> None:
    for trip in (Trip(), Trip(days=4, limit_kg=11), Trip(days=1, limit_kg=4)):
        p = optimise(gear, trip)
        assert p.feasible and p.total_g <= p.limit_g and p.total_g == p.gear_g + p.food_g + p.water_g


def test_more_weight_never_lowers_utility(gear: list[Item]) -> None:
    us = [optimise(gear, Trip(days=2, limit_kg=k)).utility for k in (6, 8, 10, 14)]
    assert us == sorted(us)


def test_cold_trip_requires_insulation_and_warm_bag(gear: list[Item]) -> None:
    ids = {i.id for i in optimise(gear, Trip(days=2, min_temp_c=-8, limit_kg=16)).chosen}
    assert {"puffy", "gloves", "bag4"} <= ids and "bag1" not in ids


def test_rain_jacket_required_when_rain_likely(gear: list[Item]) -> None:
    assert "jacketrain" in {i.id for i in optimise(gear, Trip(rain_chance=0.6)).chosen}
    dry = {i.id for i in optimise(gear, Trip(rain_chance=0.0, limit_kg=5, days=1)).chosen}
    assert "pantsrain" not in dry


def test_bugs_and_sun_change_the_pack(gear: list[Item]) -> None:
    with_bugs = {i.id for i in optimise(gear, Trip(bugs=True)).chosen}
    assert "bugspray" in with_bugs
    no_sun = {i.id for i in optimise(gear, Trip(sun=False, limit_kg=6)).chosen}
    assert "sunglasses" not in no_sun


def test_day_hike_drops_overnight_kit(gear: list[Item]) -> None:
    ids = {i.id for i in optimise(gear, Trip(days=1, limit_kg=6)).chosen}
    assert not ids & {"tent", "tarp", "bivy", "pad", "bag3"}


def test_food_scales_with_days_and_water_with_heat() -> None:
    assert consumables(Trip(days=4))[0] == 2 * consumables(Trip(days=2))[0]
    assert consumables(Trip(min_temp_c=20, sun=True))[1] > consumables(Trip(min_temp_c=5))[1]


def test_infeasible_when_limit_too_low(gear: list[Item]) -> None:
    p = optimise(gear, Trip(days=14, limit_kg=3))
    assert not p.feasible and p.notes


def test_adjust_scales_utilities(gear: list[Item]) -> None:
    hot = {i.id: i for i in adjust(gear, Trip(min_temp_c=25))}
    cold = {i.id: i for i in adjust(gear, Trip(min_temp_c=-10))}
    assert hot["puffy"].utility < cold["puffy"].utility and cold["puffy"].required


@pytest.mark.parametrize(
    "bad", [dict(days=0), dict(people=0), dict(rain_chance=2), dict(limit_kg=1), dict(min_temp_c=-50)]
)
def test_validation(gear: list[Item], bad: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(PackError):
        optimise(gear, Trip(**bad))
