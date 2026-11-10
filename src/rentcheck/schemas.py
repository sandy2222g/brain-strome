"""Request validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from rentcheck.config import DISTRICTS, FEATURES


class ListingIn(BaseModel):
    district: str
    bedrooms: int = Field(ge=0, le=6)
    bathrooms: int = Field(ge=1, le=4)
    size_m2: float = Field(ge=15, le=250)
    floor: int = Field(ge=0, le=40)
    furnished: bool = False
    balcony: bool = False
    lift: bool = False
    building_age: int = Field(ge=0, le=200)
    dist_centre_km: float = Field(ge=0, le=30)
    dist_metro_km: float = Field(ge=0, le=15)
    pets_allowed: bool = False
    rent: float = Field(gt=0, le=50000, description="Monthly rent you are asked to pay")

    @field_validator("district")
    @classmethod
    def _known_district(cls, v: str) -> str:
        if v not in DISTRICTS:
            raise ValueError(f"unknown district; choose one of: {', '.join(DISTRICTS)}")
        return v

    def features(self) -> dict[str, Any]:
        d = self.model_dump()
        return {k: (int(d[k]) if isinstance(d[k], bool) else d[k]) for k in FEATURES}
