"""Parse five-field cron expressions, describe them in English and find upcoming run times."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[2] / "data" / "examples.json"
MACROS = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *", "@weekly": "0 0 * * 0",
          "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *"}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SEARCH_DAYS = 366 * 8  # long enough for a leap-day schedule


class CronError(ValueError):
    """Invalid cron expression."""


@dataclass(frozen=True)
class Field:
    values: frozenset[int]
    star: bool
    text: str


def parse_field(text: str, lo: int, hi: int, names: list[str] | None, name: str, first_name: int) -> Field:
    values: set[int] = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, s = part.split("/", 1)
            if not s.isdigit() or int(s) < 1:
                raise CronError(f"{name}: step must be a positive number, got '{s}'")
            step = int(s)
        if part == "*":
            a, b = lo, hi
        elif "-" in part:
            x, y = part.split("-", 1)
            a, b = num(x, lo, hi, names, name, first_name), num(y, lo, hi, names, name, first_name)
            if a > b:
                raise CronError(f"{name}: range {part} runs backwards")
        else:
            a = num(part, lo, hi, names, name, first_name)
            b = hi if step > 1 else a  # "5/15" means from 5 onwards
        values.update(range(a, b + 1, step))
    return Field(frozenset(values), text in ("*", "?"), text)


def num(tok: str, lo: int, hi: int, names: list[str] | None, name: str, first_name: int) -> int:
    t = tok.upper()
    if names and t in names:
        return names.index(t) + first_name
    if not t.isdigit():
        raise CronError(f"{name}: '{tok}' is not a number or name")
    v = int(t)
    if name == "day of week" and v == 7:
        v = 0
    if not lo <= v <= hi:
        raise CronError(f"{name}: {v} is outside {lo}-{hi}")
    return v


@dataclass(frozen=True)
class Cron:
    minute: Field
    hour: Field
    dom: Field
    month: Field
    dow: Field
    source: str


def parse(expr: str) -> Cron:
    e = MACROS.get(expr.strip().lower(), expr).split()
    if len(e) != 5:
        raise CronError("expected 5 fields: minute hour day-of-month month day-of-week")
    return Cron(parse_field(e[0], 0, 59, None, "minute", 0), parse_field(e[1], 0, 23, None, "hour", 0),
                parse_field(e[2], 1, 31, None, "day of month", 1),
                parse_field(e[3], 1, 12, MONTHS, "month", 1),
                parse_field(e[4], 0, 7, DAYS, "day of week", 0), expr.strip())


def day_matches(c: Cron, d: datetime) -> bool:
    if d.month not in c.month.values:
        return False
    dom_ok, dow_ok = d.day in c.dom.values, (d.isoweekday() % 7) in c.dow.values
    dom_any, dow_any = c.dom.text == "*", c.dow.text == "*"
    if dom_any and dow_any:
        return True
    if dom_any:
        return dow_ok
    if dow_any:
        return dom_ok
    return dom_ok or dow_ok  # both restricted: classic cron runs when either matches


def next_runs(expr: str, after: datetime, n: int = 5) -> list[datetime]:
    if not 1 <= n <= 20:
        raise CronError("n must be within 1..20")
    c = parse(expr)
    out: list[datetime] = []
    day = after.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(SEARCH_DAYS):
        if day_matches(c, day):
            for h in sorted(c.hour.values):
                for m in sorted(c.minute.values):
                    t = day.replace(hour=h, minute=m)
                    if t > after:
                        out.append(t)
                        if len(out) == n:
                            return out
        day += timedelta(days=1)
    return out  # e.g. 31 Feb never happens


def join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def runs_of(vals: list[int]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for v in vals:
        if out and out[-1][1] == v - 1:
            out[-1] = (out[-1][0], v)
        else:
            out.append((v, v))
    return out


def describe_list(vals: list[int], label: dict[int, str] | None = None) -> str:
    f = (lambda v: label[v]) if label else str
    parts = [f(a) if a == b else f"{f(a)} through {f(b)}" if b > a + 1 else f"{f(a)} and {f(b)}"
             for a, b in runs_of(vals)]
    return join(parts)


def explain(expr: str) -> str:
    c = parse(expr)
    mins, hrs = sorted(c.minute.values), sorted(c.hour.values)
    if c.minute.text == "*" and c.hour.text == "*":
        when = "Every minute"
    elif c.minute.text.startswith("*/") and c.hour.text == "*":
        when = f"Every {c.minute.text[2:]} minutes"
    elif len(mins) == 1 and c.hour.text == "*":
        when = f"At minute {mins[0]} of every hour"
    elif len(mins) == 1 and c.hour.text.startswith("*/"):
        when = f"At minute {mins[0]} past every {c.hour.text[2:]} hours"
    elif len(mins) == 1 and len(hrs) == 1:
        when = f"At {hrs[0]:02d}:{mins[0]:02d}"
    elif len(mins) == 1:
        when = "At " + join([f"{h:02d}:{mins[0]:02d}" for h in hrs])
    elif c.minute.text.startswith("*/") and c.hour.text != "*":
        when = f"Every {c.minute.text[2:]} minutes, during hours {describe_list(hrs)}"
    elif c.hour.text == "*":
        when = f"At minutes {describe_list(mins)} of every hour"
    else:
        when = f"At minutes {describe_list(mins)} past hours {describe_list(hrs)}"
    days = sorted(c.dom.values)
    dom = f" on day{'s' if len(days) > 1 else ''} {describe_list(days)} of the month" if c.dom.text != "*" else ""
    dow = (" on " + describe_list(sorted(c.dow.values), dict(enumerate(DAY_NAMES)))) if c.dow.text != "*" else ""
    if c.dom.text != "*" and c.dow.text != "*":
        dow = " or" + dow
    mon = (" in " + describe_list(sorted(c.month.values), {i + 1: n for i, n in enumerate(MONTH_NAMES)})
           ) if c.month.text != "*" else ""
    every = " every day" if c.dom.text == c.dow.text == c.month.text == "*" and "Every" not in when else ""
    return when + every + dom + dow + mon


def examples() -> list[dict[str, str]]:
    return json.loads(EXAMPLES.read_text())  # type: ignore[no-any-return]
