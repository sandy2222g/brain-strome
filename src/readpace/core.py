"""Plan reading a book by a deadline, skipping chosen rest weekdays and already-read pages.

Pages per reading day = ceil(pages left / reading days). Pages are spread so no day differs from
another by more than one page. The naive plan divides by all calendar days and so skips rest days
only by accident (it falls short unless you also read on rest days).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "book.json"


class PlanError(ValueError):
    """Invalid book or dates."""


@dataclass(frozen=True)
class Book:
    title: str
    pages: int
    pages_read: int
    start: date
    deadline: date
    rest_weekdays: frozenset[int]  # Monday=0


def build(raw: dict) -> Book:  # type: ignore[type-arg]
    try:
        b = Book(
            str(raw["title"]),
            int(raw["pages"]),
            int(raw.get("pages_read", 0)),
            date.fromisoformat(raw["start"]),
            date.fromisoformat(raw["deadline"]),
            frozenset(int(d) for d in raw.get("rest_weekdays", [])),
        )
    except (KeyError, ValueError, TypeError) as err:
        raise PlanError("need title, pages, start and deadline (ISO dates)") from err
    if not 1 <= b.pages <= 20000 or not 0 <= b.pages_read < b.pages:
        raise PlanError("pages 1-20000 and pages_read below pages")
    if b.deadline < b.start or (b.deadline - b.start).days > 730:
        raise PlanError("deadline must be within two years after the start")
    if any(not 0 <= d <= 6 for d in b.rest_weekdays) or len(b.rest_weekdays) > 6:
        raise PlanError("rest weekdays are 0-5 distinct values from 0 (Mon) to 6 (Sun)")
    return b


def reading_days(b: Book) -> list[date]:
    days = [b.start + timedelta(n) for n in range((b.deadline - b.start).days + 1)]
    return [d for d in days if d.weekday() not in b.rest_weekdays]


def plan(b: Book) -> list[tuple[date, int]]:
    days = reading_days(b)
    if not days:
        raise PlanError("no reading days before the deadline")
    left = b.pages - b.pages_read
    base, extra = divmod(left, len(days))
    return [(d, base + (1 if i < extra else 0)) for i, d in enumerate(days)]


def naive_pages_per_day(b: Book) -> int:
    return math.ceil((b.pages - b.pages_read) / ((b.deadline - b.start).days + 1))


def naive_total(b: Book) -> int:
    """Pages actually read if you follow the naive daily target but skip rest days."""
    return naive_pages_per_day(b) * len(reading_days(b))


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
