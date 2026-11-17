"""Next birthday, days left and age being reached, for a list of people."""

from __future__ import annotations

import calendar
import json
from datetime import date
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "birthdays.json"


class BirthdayError(ValueError):
    """Raised for invalid dates or people."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def parse(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as err:
        raise BirthdayError(f"bad date {s!r}, use YYYY-MM-DD") from err


def occurrence(born: date, year: int) -> date:
    """The birthday in `year`; a 29 Feb birthday falls on 28 Feb in non-leap years."""
    if born.month == 2 and born.day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, born.month, born.day)


def next_birthday(born: date, today: date) -> date:
    """First birthday on or after today (a birthday today counts as 0 days away)."""
    if born > today:
        raise BirthdayError("born date is in the future")
    this = occurrence(born, today.year)
    return this if this >= today else occurrence(born, today.year + 1)


def upcoming(people: list[dict[str, str]], today: date) -> list[dict[str, Any]]:
    rows = []
    for p in people:
        born = parse(p["born"])
        nxt = next_birthday(born, today)
        rows.append(
            {"name": p["name"], "date": nxt.isoformat(), "days": (nxt - today).days, "turning": nxt.year - born.year}
        )
    rows.sort(key=lambda r: (r["days"], r["name"]))
    return rows


def calendar_order(people: list[dict[str, str]]) -> list[str]:
    """Baseline: January-to-December list, which ignores what day it is today."""
    return [p["name"] for p in sorted(people, key=lambda p: (parse(p["born"]).month, parse(p["born"]).day, p["name"]))]
