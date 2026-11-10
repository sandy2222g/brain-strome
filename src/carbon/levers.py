"""What-if levers. Each lever rewrites the answers; the saving is the calculator's difference, so it can
never exceed the categories the lever touches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from carbon.calculator import calculate
from carbon.factors import Factors
from carbon.schema import Answers

Apply = Callable[[Answers], Answers | None]


@dataclass(frozen=True)
class Lever:
    id: str
    title: str
    description: str
    category: str
    affects: tuple[str, ...]
    effort: int  # 1 (a minute) to 5 (a project)
    cost_note: str
    payback_note: str
    apply: Apply


@dataclass(frozen=True)
class LeverResult:
    id: str
    title: str
    description: str
    category: str
    saved_t: float
    saved_pct: float
    effort: int
    impact_per_effort: float
    cost_note: str
    payback_note: str


def _thermostat_down(a: Answers) -> Answers | None:
    return a.model_copy(update={"thermostat_c": a.thermostat_c - 1}) if a.thermostat_c > 16 else None


def _green_tariff(a: Answers) -> Answers | None:
    return None if a.green_tariff else a.model_copy(update={"green_tariff": True})


def _heat_pump(a: Answers) -> Answers | None:
    return None if a.heating == "heat_pump" else a.model_copy(update={"heating": "heat_pump"})


def _insulation_up(a: Answers) -> Answers | None:
    step = {"poor": "average", "average": "good"}.get(a.insulation)
    return a.model_copy(update={"insulation": step}) if step else None


def _meat_free(a: Answers) -> Answers | None:
    if a.diet in ("vegetarian", "vegan") or a.meat_free_days > 5:
        return None
    return a.model_copy(update={"meat_free_days": a.meat_free_days + 2})


def _car_to_bus(a: Answers) -> Answers | None:
    if not a.car_km_week or a.car_km_week <= 0 or a.transit_km_week is None:
        return None
    moved = a.car_km_week * 0.2
    return a.model_copy(update={"car_km_week": a.car_km_week - moved, "transit_km_week": a.transit_km_week + moved})


def _electric_car(a: Answers) -> Answers | None:
    if a.car_type == "ev" or not a.car_km_week:
        return None
    return a.model_copy(update={"car_type": "ev"})


def _one_fewer_flight(a: Answers) -> Answers | None:
    if a.flights_long >= 1:
        return a.model_copy(update={"flights_long": a.flights_long - 1})
    if a.flights_short >= 1:
        return a.model_copy(update={"flights_short": a.flights_short - 1})
    return None


def _fewer_clothes(a: Answers) -> Answers | None:
    if a.clothes_items_year is None or a.clothes_items_year < 4:
        return None
    return a.model_copy(update={"clothes_items_year": a.clothes_items_year * 2 / 3})


def _spend_less(a: Answers) -> Answers | None:
    step = {"high": "average", "average": "low"}.get(a.shopping_level)
    return a.model_copy(update={"shopping_level": step}) if step else None


def _recycle_more(a: Answers) -> Answers | None:
    return None if a.recycling == "most" else a.model_copy(update={"recycling": "most"})


LEVERS: tuple[Lever, ...] = (
    Lever(
        "thermostat_down",
        "Turn the heating down 1 degree",
        "Set the thermostat one degree lower.",
        "heating",
        ("heating",),
        1,
        "Free.",
        "Lowers bills straight away.",
        _thermostat_down,
    ),
    Lever(
        "green_tariff",
        "Switch to a green electricity tariff",
        "Move your supply to a renewable tariff.",
        "electricity",
        ("electricity", "heating"),
        1,
        "Often close to a standard tariff price.",
        "No upfront cost; compare tariffs first.",
        _green_tariff,
    ),
    Lever(
        "recycle_more",
        "Recycle most of your waste",
        "Sort more of your waste for recycling.",
        "waste",
        ("waste",),
        2,
        "Free.",
        "No payback needed; saves a little on bin fees in some areas.",
        _recycle_more,
    ),
    Lever(
        "meat_free_2",
        "Eat meat-free two more days a week",
        "Two extra meat-free days each week.",
        "food",
        ("food",),
        2,
        "Usually lowers the food bill.",
        "Saves money from the first week.",
        _meat_free,
    ),
    Lever(
        "car_to_bus",
        "Move 20% of car km to the bus",
        "Take the bus for one trip in five.",
        "travel",
        ("travel",),
        2,
        "Fares are usually below fuel and parking for the same trips.",
        "Saves money from the first month.",
        _car_to_bus,
    ),
    Lever(
        "fewer_clothes",
        "Buy a third fewer new clothes",
        "Buy two items instead of three.",
        "shopping",
        ("shopping",),
        2,
        "Saves what you would have spent.",
        "Saves money straight away.",
        _fewer_clothes,
    ),
    Lever(
        "flight_cut",
        "Skip one flight a year",
        "Drop one return flight, long-haul first.",
        "flights",
        ("flights",),
        3,
        "Saves the fare.",
        "Saves money straight away.",
        _one_fewer_flight,
    ),
    Lever(
        "spend_less",
        "Buy fewer new things",
        "Step your general spending on goods down one level.",
        "shopping",
        ("shopping",),
        3,
        "Saves what you would have spent.",
        "Saves money straight away.",
        _spend_less,
    ),
    Lever(
        "insulation_up",
        "Improve home insulation one level",
        "Loft, wall or draught-proofing work.",
        "heating",
        ("heating",),
        4,
        "Medium to high upfront cost; grants exist in some places.",
        "Often 5 to 15 years through lower bills.",
        _insulation_up,
    ),
    Lever(
        "heat_pump",
        "Switch to a heat pump",
        "Replace your boiler or heater with an air-source heat pump.",
        "heating",
        ("heating",),
        5,
        "High upfront cost; grants vary by country.",
        "Often 8 to 15 years, depending on energy prices.",
        _heat_pump,
    ),
    Lever(
        "electric_car",
        "Switch to an electric car",
        "Replace your car with an electric one.",
        "travel",
        ("travel",),
        5,
        "Higher purchase price, lower running cost.",
        "Depends on how far you drive; heavy drivers recover it sooner.",
        _electric_car,
    ),
)
BY_ID: dict[str, Lever] = {lv.id: lv for lv in LEVERS}


def saving_kg(lever: Lever, a: Answers, factors: Factors | None = None) -> float | None:
    """Kilograms saved a year by applying this lever alone, or None if it does not apply."""
    changed = lever.apply(a)
    if changed is None:
        return None
    return calculate(a, factors).total_kg - calculate(changed, factors).total_kg


def rank_levers(a: Answers, factors: Factors | None = None) -> list[LeverResult]:
    """Applicable levers with a real saving, ordered by tonnes saved per unit of effort."""
    total_kg = calculate(a, factors).total_kg
    out: list[LeverResult] = []
    for lv in LEVERS:
        kg = saving_kg(lv, a, factors)
        if kg is None or kg < 5:
            continue
        out.append(
            LeverResult(
                id=lv.id,
                title=lv.title,
                description=lv.description,
                category=lv.category,
                saved_t=round(kg / 1000, 3),
                saved_pct=round(100 * kg / total_kg, 1) if total_kg else 0.0,
                effort=lv.effort,
                impact_per_effort=round(kg / 1000 / lv.effort, 3),
                cost_note=lv.cost_note,
                payback_note=lv.payback_note,
            )
        )
    out.sort(key=lambda r: (-r.impact_per_effort, r.effort, r.id))
    return out
