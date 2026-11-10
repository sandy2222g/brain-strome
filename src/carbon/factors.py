"""Emission factors: a small CSV table of ILLUSTRATIVE values, loaded once and looked up by key."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACTORS_PATH = Path(os.environ.get("FACTORS_PATH", ROOT / "data" / "emission_factors.csv"))

DISCLAIMER = (
    "Illustrative, rounded from publicly available factor sets such as UK DESNZ and US EPA. "
    "These are not certified or exact values; use them to compare choices, not to report emissions."
)


@dataclass(frozen=True)
class Factor:
    key: str
    category: str
    value: float
    unit: str
    note: str


class Factors:
    """Lookup table over the factor rows."""

    def __init__(self, rows: list[Factor]) -> None:
        self.rows = rows
        self._by_key = {r.key: r for r in rows}

    def get(self, key: str) -> float:
        try:
            return self._by_key[key].value
        except KeyError:
            raise KeyError(f"unknown emission factor: {key}") from None


def load_factors(path: Path | None = None) -> Factors:
    with open(path or FACTORS_PATH, newline="", encoding="utf-8") as fh:
        rows = [Factor(r["key"], r["category"], float(r["value"]), r["unit"], r["note"]) for r in csv.DictReader(fh)]
    return Factors(rows)


@lru_cache(maxsize=1)
def default_factors() -> Factors:
    return load_factors()
