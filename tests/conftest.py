from __future__ import annotations

from datetime import date

from meetfair.core import Person

DAY = date(2026, 11, 16)  # a Monday, no DST change that week in the zones used below


def team(*zones: str) -> list[Person]:
    return [Person(f"P{i}", z) for i, z in enumerate(zones)]
