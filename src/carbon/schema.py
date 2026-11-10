"""Questionnaire answers: one validated model shared by the calculator, levers, plan and API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Heating = Literal["gas", "oil", "electric", "heat_pump", "district", "wood"]
Insulation = Literal["poor", "average", "good"]
CommuteMode = Literal["car", "bus_rail", "mixed", "bike_walk"]
CarType = Literal["petrol", "diesel", "hybrid", "ev"]
Diet = Literal["meat_heavy", "average", "low_meat", "vegetarian", "vegan"]
Shopping = Literal["low", "average", "high"]
Recycling = Literal["none", "some", "most"]

# Detailed answers a household may skip; the model fills them in from the quick answers.
DETAILED_FIELDS: tuple[str, ...] = (
    "electricity_kwh_month",
    "car_km_week",
    "transit_km_week",
    "clothes_items_year",
    "waste_kg_week",
)

FIELD_LABELS: dict[str, tuple[str, str]] = {
    "electricity_kwh_month": ("Electricity use", "kWh a month"),
    "car_km_week": ("Car distance", "km a week"),
    "transit_km_week": ("Bus and rail distance", "km a week"),
    "clothes_items_year": ("New clothes", "items a year"),
    "waste_kg_week": ("Household waste", "kg a week"),
}


class Answers(BaseModel):
    """The questionnaire. Fields in DETAILED_FIELDS are optional; everything else has a quick answer."""

    household_size: int = Field(ge=1, le=12)
    home_size_m2: float = Field(ge=15, le=600)
    heating: Heating
    insulation: Insulation = "average"
    thermostat_c: float = Field(default=20, ge=14, le=26)
    electricity_kwh_month: float | None = Field(default=None, ge=0, le=5000)
    green_tariff: bool = False
    commute_mode: CommuteMode
    car_km_week: float | None = Field(default=None, ge=0, le=3000)
    car_type: CarType = "petrol"
    transit_km_week: float | None = Field(default=None, ge=0, le=3000)
    flights_short: float = Field(default=0, ge=0, le=60)
    flights_long: float = Field(default=0, ge=0, le=30)
    diet: Diet
    meat_free_days: int = Field(default=0, ge=0, le=7)
    shopping_level: Shopping = "average"
    clothes_items_year: float | None = Field(default=None, ge=0, le=400)
    recycling: Recycling = "some"
    waste_kg_week: float | None = Field(default=None, ge=0, le=300)

    def missing(self) -> list[str]:
        return [name for name in DETAILED_FIELDS if getattr(self, name) is None]
