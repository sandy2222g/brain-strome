from __future__ import annotations

import pytest

from carbon.calculator import (
    CATEGORIES,
    MissingAnswerError,
    calculate,
    typical_answers,
)
from carbon.factors import DISCLAIMER, default_factors
from conftest import make_answers


def kg(category: str, **overrides: object) -> float:
    return calculate(make_answers(**overrides)).by_category_kg[category]


def test_heating_gas_by_hand() -> None:
    # 100 m2 x 90 kWh/m2 = 9000 kWh of heat x 0.23
    assert kg("heating") == pytest.approx(2070.0)


def test_heating_thermostat_one_degree_up() -> None:
    # demand x (1 + 0.07) = 9630 kWh x 0.23
    assert kg("heating", thermostat_c=21) == pytest.approx(2214.9)


def test_heat_pump_and_electric_heating() -> None:
    assert kg("heating", heating="heat_pump") == pytest.approx(9000 / 3 * 0.20)
    assert kg("heating", heating="electric") == pytest.approx(9000 * 0.20)
    assert kg("heating", heating="heat_pump", green_tariff=True) == pytest.approx(9000 / 3 * 0.03)


def test_electricity_and_green_tariff() -> None:
    assert kg("electricity") == pytest.approx(300 * 12 * 0.20)
    assert kg("electricity", green_tariff=True) == pytest.approx(300 * 12 * 0.03)


def test_travel_petrol_and_ev() -> None:
    assert kg("travel") == pytest.approx(100 * 52 * 0.17 + 50 * 52 * 0.07)
    assert kg("travel", car_type="ev") == pytest.approx(100 * 52 * 0.18 * 0.20 + 182.0)


def test_flights() -> None:
    assert kg("flights") == pytest.approx(2 * 250 + 1 * 1500)


def test_food_and_meat_free_days() -> None:
    assert kg("food") == pytest.approx(2 * 1600)
    assert kg("food", meat_free_days=2) == pytest.approx(2 * (1600 - 2 / 7 * 500))
    assert kg("food", diet="vegetarian", meat_free_days=3) == pytest.approx(2 * 1100)


def test_shopping() -> None:
    assert kg("shopping") == pytest.approx(2 * 800 + 10 * 15)


def test_waste_with_recycling_share() -> None:
    # 10 kg x 52 x (0.65 x 0.45 + 0.35 x 0.05)
    assert kg("waste") == pytest.approx(161.2)
    assert kg("waste", recycling="none") == pytest.approx(520 * 0.45)


def test_total_is_sum_of_categories() -> None:
    fp = calculate(make_answers())
    assert fp.total_kg == pytest.approx(10967.2)
    assert fp.total_t == pytest.approx(10.9672)
    assert set(fp.by_category_kg) == set(CATEGORIES)


def test_more_flights_means_more_co2e() -> None:
    totals = [calculate(make_answers(flights_short=n)).total_kg for n in range(6)]
    assert totals == sorted(totals) and len(set(totals)) == 6


def test_monotonic_in_car_distance_and_home_size() -> None:
    assert calculate(make_answers(car_km_week=200)).total_kg > calculate(make_answers(car_km_week=100)).total_kg
    assert calculate(make_answers(home_size_m2=150)).total_kg > calculate(make_answers()).total_kg


def test_missing_answers_raise() -> None:
    with pytest.raises(MissingAnswerError, match="electricity_kwh_month"):
        calculate(make_answers(electricity_kwh_month=None))


def test_validation_rejects_bad_values() -> None:
    with pytest.raises(ValueError):
        make_answers(household_size=0)
    with pytest.raises(ValueError):
        make_answers(heating="coal")
    with pytest.raises(ValueError):
        make_answers(flights_short=-1)


def test_factors_table_is_labelled_illustrative() -> None:
    f = default_factors()
    assert len(f.rows) >= 30
    assert "illustrative" in DISCLAIMER.lower() and "not certified" in DISCLAIMER.lower()
    assert all(r.note.startswith(("ILLUSTRATIVE", "Assumption", "Reference")) for r in f.rows)
    with pytest.raises(KeyError):
        f.get("nope")


def test_typical_household_scales_with_size() -> None:
    small, large = (calculate(typical_answers(n)).total_t for n in (1, 4))
    assert 0 < small < large
