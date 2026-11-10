"""Transparent calculator: emission factor x activity, one small function per category."""

from __future__ import annotations

from dataclasses import dataclass

from carbon.factors import Factors, default_factors
from carbon.schema import Answers

CATEGORIES: tuple[str, ...] = ("heating", "electricity", "travel", "flights", "food", "shopping", "waste")
LABELS: dict[str, str] = {
    "heating": "Home heating",
    "electricity": "Electricity",
    "travel": "Getting around",
    "flights": "Flights",
    "food": "Food",
    "shopping": "Shopping",
    "waste": "Waste",
}
WEEKS = 52
FUEL_KEYS = {
    "gas": "heat_gas_kg_per_kwh",
    "oil": "heat_oil_kg_per_kwh",
    "district": "heat_district_kg_per_kwh",
    "wood": "heat_wood_kg_per_kwh",
}


class MissingAnswerError(ValueError):
    """Raised when a detailed answer is still empty; fill it first (see CarbonModel.fill)."""


@dataclass(frozen=True)
class Footprint:
    by_category_kg: dict[str, float]

    @property
    def total_kg(self) -> float:
        return sum(self.by_category_kg.values())

    @property
    def total_t(self) -> float:
        return self.total_kg / 1000


def electricity_factor(a: Answers, f: Factors) -> float:
    return f.get("green_tariff_kg_per_kwh" if a.green_tariff else "grid_kg_per_kwh")


def heat_demand_kwh(a: Answers, f: Factors) -> float:
    per_m2 = f.get(f"heat_demand_{a.insulation}_kwh_per_m2")
    delta = a.thermostat_c - f.get("heat_ref_setpoint_c")
    return a.home_size_m2 * per_m2 * (1 + f.get("heat_setpoint_change_per_degc") * delta)


def heating_kg(a: Answers, f: Factors) -> float:
    demand = heat_demand_kwh(a, f)
    if a.heating == "electric":
        return demand * electricity_factor(a, f)
    if a.heating == "heat_pump":
        return demand / f.get("heat_pump_cop") * electricity_factor(a, f)
    return demand * f.get(FUEL_KEYS[a.heating])


def electricity_kg(a: Answers, f: Factors) -> float:
    assert a.electricity_kwh_month is not None
    return a.electricity_kwh_month * 12 * electricity_factor(a, f)


def travel_kg(a: Answers, f: Factors) -> float:
    assert a.car_km_week is not None and a.transit_km_week is not None
    car_km = a.car_km_week * WEEKS
    if a.car_type == "ev":
        car = car_km * f.get("car_ev_kwh_per_km") * electricity_factor(a, f)
    else:
        car = car_km * f.get(f"car_{a.car_type}_kg_per_km")
    return car + a.transit_km_week * WEEKS * f.get("transit_kg_per_km")


def flights_kg(a: Answers, f: Factors) -> float:
    return a.flights_short * f.get("flight_short_kg_each") + a.flights_long * f.get("flight_long_kg_each")


def food_kg_per_person(a: Answers, f: Factors) -> float:
    """Diet factor, reduced linearly toward vegetarian for each meat-free day (vegetarian and vegan are unaffected)."""
    base = f.get(f"food_{a.diet}_kg_per_person")
    if a.diet in ("vegetarian", "vegan"):
        return base
    veg = f.get("food_vegetarian_kg_per_person")
    return base - (a.meat_free_days / 7) * (base - veg)


def food_kg(a: Answers, f: Factors) -> float:
    return food_kg_per_person(a, f) * a.household_size


def shopping_kg(a: Answers, f: Factors) -> float:
    assert a.clothes_items_year is not None
    goods = f.get(f"shopping_{a.shopping_level}_kg_per_person") * a.household_size
    return goods + a.clothes_items_year * f.get("clothes_kg_per_item")


def waste_kg(a: Answers, f: Factors) -> float:
    assert a.waste_kg_week is not None
    share = f.get(f"recycling_share_{a.recycling}")
    per_kg = (1 - share) * f.get("waste_residual_kg_per_kg") + share * f.get("waste_recycled_kg_per_kg")
    return a.waste_kg_week * WEEKS * per_kg


def calculate(a: Answers, factors: Factors | None = None) -> Footprint:
    """Yearly footprint in kg CO2e by category. All detailed answers must be present."""
    missing = a.missing()
    if missing:
        raise MissingAnswerError(f"missing answers: {', '.join(missing)}")
    f = factors or default_factors()
    return Footprint(
        {
            "heating": heating_kg(a, f),
            "electricity": electricity_kg(a, f),
            "travel": travel_kg(a, f),
            "flights": flights_kg(a, f),
            "food": food_kg(a, f),
            "shopping": shopping_kg(a, f),
            "waste": waste_kg(a, f),
        }
    )


def typical_answers(size: int) -> Answers:
    """The synthetic 'typical household' of a given size, used as the benchmark."""
    return Answers(
        household_size=size,
        home_size_m2=40 + 25 * size,
        heating="gas",
        insulation="average",
        thermostat_c=20,
        electricity_kwh_month=80 + 60 * size,
        commute_mode="car",
        car_km_week=80 + 40 * size,
        car_type="petrol",
        transit_km_week=20 + 10 * size,
        flights_short=round(0.35 * size, 2),
        flights_long=round(0.1 * size, 2),
        diet="average",
        shopping_level="average",
        clothes_items_year=8 * size,
        recycling="some",
        waste_kg_week=4.5 * size,
    )
