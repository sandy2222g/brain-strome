"""Rule-based parser for short event sentences: date words, clock times and durations."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "examples.json"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_RE = "|".join(MONTHS)


class ParseError(ValueError):
    """Raised when a sentence has nothing to parse."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _time(text: str) -> tuple[str | None, str]:
    for word, hhmm in (("noon", "12:00"), ("midnight", "00:00")):
        if re.search(rf"\b{word}\b", text):
            return hhmm, re.sub(rf"\b(at )?{word}\b", " ", text)
    m = re.search(r"\b(?:at )?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if not 1 <= h <= 12 or mi > 59:
            raise ParseError(f"bad time {m.group(0)!r}")
        h = h % 12 + (12 if ap == "pm" else 0)
        return f"{h:02d}:{mi:02d}", text.replace(m.group(0), " ")
    m = re.search(r"\b(?:at )?([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}", text.replace(m.group(0), " ")
    return None, text


def _duration(text: str) -> tuple[int | None, str]:
    m = re.search(r"\bfor (\d+(?:\.\d+)?) (hours?|hrs?|minutes?|mins?)\b", text)
    if not m:
        return None, text
    n = float(m.group(1))
    minutes = round(n * 60) if m.group(2).startswith("h") else round(n)
    return minutes, text.replace(m.group(0), " ")


def _span(m: re.Match[str]) -> int:
    """Days in 'in N days' or 'in N weeks'."""
    return int(m.group(1)) * (7 if m.group(2).startswith("w") else 1)


def _date(text: str, today: date) -> tuple[date | None, str]:
    rules: list[tuple[str, Any]] = [
        (r"\bday after tomorrow\b", lambda m: today + timedelta(days=2)),
        (r"\btomorrow\b", lambda m: today + timedelta(days=1)),
        (r"\btoday\b", lambda m: today),
        (r"\bin (\d+) (day|days|week|weeks)\b", lambda m: today + timedelta(days=_span(m))),
        (r"\b(\d{4})-(\d{2})-(\d{2})\b", lambda m: date(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    ]
    for pattern, make in rules:
        m = re.search(pattern, text)
        if m:
            try:
                return make(m), text.replace(m.group(0), " ")
            except ValueError as err:
                raise ParseError(f"bad date {m.group(0)!r}") from err
    m = re.search(rf"\b(?:on )?({MONTH_RE})[a-z]* (\d{{1,2}})\b|\b(?:on )?(\d{{1,2}}) ({MONTH_RE})[a-z]*\b", text)
    if m:
        mon, day = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        try:
            d = date(today.year, MONTHS.index(mon) + 1, int(day))
        except ValueError as err:
            raise ParseError(f"bad date {m.group(0)!r}") from err
        return (d if d >= today else d.replace(year=today.year + 1)), text.replace(m.group(0), " ")
    m = re.search(rf"\b(next )?({'|'.join(WEEKDAYS)})\b", text)
    if m:
        ahead = (WEEKDAYS.index(m.group(2)) - today.weekday()) % 7 or 7
        if m.group(1):  # "next monday" means the one in the following week, never this week
            ahead = ahead if ahead > 7 - today.weekday() - 1 else ahead + 7
        return today + timedelta(days=ahead), text.replace(m.group(0), " ")
    return None, text


def parse(sentence: str, today: date) -> dict[str, Any]:
    """Pull out date, time and duration; what is left is the title."""
    if not sentence.strip():
        raise ParseError("empty sentence")
    text = sentence.lower()
    minutes, text = _duration(text)
    clock, text = _time(text)
    when, text = _date(text, today)
    title = re.sub(r"\b(on|at|for)\b\s*$", "", re.sub(r"\s+", " ", text).strip()).strip(" ,.-")
    original = {w.lower(): w for w in sentence.split()}
    title = " ".join(original.get(w, w) for w in title.split()) or "Untitled"
    return {
        "title": title[:1].upper() + title[1:],
        "date": when.isoformat() if when else None,
        "time": clock,
        "duration_min": minutes,
        "weekday": WEEKDAYS[when.weekday()].capitalize() if when else None,
        "complete": bool(when and clock),
    }
