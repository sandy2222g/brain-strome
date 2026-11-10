from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from plantparent.care import MAX_MULT, MIN_MULT, Plant, classify, schedule, update_multiplier
from plantparent.model import IntervalModel, season_for

TODAY = date(2026, 6, 10)


def plant(
    name: str = "P",
    species: str = "Monstera",
    pot: float = 15,
    material: str = "plastic",
    ago: int = 5,
    mult: float = 1.0,
) -> Plant:
    return Plant(name, species, pot, material, TODAY - timedelta(days=ago), mult)


def one(model: IntervalModel, species: pd.DataFrame, p: Plant, **kw: object) -> dict:  # type: ignore[type-arg]
    return schedule([p], species, model, TODAY, **kw)["items"][0]  # type: ignore[arg-type]


def test_model_beats_species_only_baseline(model: IntervalModel) -> None:
    m = model.metrics
    assert m["test_mae_days"] < m["baseline_mae_days_species_only"] / 2
    assert 0.05 < m["p80_relative_error"] < 0.4


@pytest.mark.parametrize(
    ("month", "north", "south"),
    [(1, "winter", "summer"), (4, "spring", "autumn"), (7, "summer", "winter"), (10, "autumn", "spring")],
)
def test_season_for(month: int, north: str, south: str) -> None:
    assert season_for(month) == north and season_for(month, "south") == south


def test_terracotta_dries_faster_than_ceramic(model: IntervalModel, species: pd.DataFrame) -> None:
    t = one(model, species, plant(material="terracotta"))
    c = one(model, species, plant(material="ceramic"))
    assert t["interval_days"] < c["interval_days"]


def test_bigger_pot_and_winter_stretch_the_interval(model: IntervalModel, species: pd.DataFrame) -> None:
    small = one(model, species, plant(pot=10))["interval_days"]
    big = one(model, species, plant(pot=30))["interval_days"]
    assert big > small
    winter = schedule([plant()], species, model, date(2026, 1, 10))["items"][0]["interval_days"]
    assert winter > one(model, species, plant())["interval_days"]


def test_cactus_like_species_wait_longer_than_ferns(model: IntervalModel, species: pd.DataFrame) -> None:
    assert (
        one(model, species, plant(species="ZZ plant"))["interval_days"]
        > 2 * one(model, species, plant(species="Boston fern"))["interval_days"]
    )


def test_status_and_due_dates(model: IntervalModel, species: pd.DataFrame) -> None:
    overdue = one(model, species, plant(species="Boston fern", ago=20))
    assert overdue["status"] == "overdue" and overdue["days_until_due"] < 0
    fresh = one(model, species, plant(ago=0))
    assert fresh["status"] == "ok" and fresh["days_until_due"] > 2


@pytest.mark.parametrize(("days", "status"), [(-3, "overdue"), (0, "today"), (1, "soon"), (2, "soon"), (3, "ok")])
def test_classify(days: int, status: str) -> None:
    assert classify(days) == status


def test_multiplier_learning_and_clamping() -> None:
    assert update_multiplier(1.0, "dry") < 1.0 < update_multiplier(1.0, "wet")
    assert update_multiplier(1.0, "ok") == 1.0
    assert update_multiplier(MIN_MULT, "dry") == MIN_MULT and update_multiplier(MAX_MULT, "wet") == MAX_MULT
    with pytest.raises(ValueError):
        update_multiplier(1.0, "soggy")


def test_multiplier_changes_the_schedule(model: IntervalModel, species: pd.DataFrame) -> None:
    base = one(model, species, plant())["interval_days"]
    assert one(model, species, plant(mult=1.5))["interval_days"] == pytest.approx(base * 1.5, abs=0.1)


def test_repeated_dry_checks_converge_downwards() -> None:
    m = 1.0
    for _ in range(10):
        m = update_multiplier(m, "dry")
    assert m == MIN_MULT


def test_calendar_repeats_and_lists_water_today(model: IntervalModel, species: pd.DataFrame) -> None:
    res = schedule([plant(species="Basil (kitchen)", ago=10)], species, model, TODAY, horizon_days=30)
    assert res["water_today"] == ["P"]
    assert len(res["calendar"]) >= 5 and all(date.fromisoformat(d) >= TODAY for d in res["calendar"])


def test_pet_warning(model: IntervalModel, species: pd.DataFrame) -> None:
    res = schedule([plant(species="Monstera"), plant("S", species="Spider plant")], species, model, TODAY, pets=True)
    assert res["pet_warnings"] == ["P"]
    assert schedule([plant()], species, model, TODAY, pets=False)["pet_warnings"] == []


def test_unknown_species_raises(model: IntervalModel, species: pd.DataFrame) -> None:
    with pytest.raises(KeyError):
        schedule([plant(species="Triffid")], species, model, TODAY)
