"""Build a clash-free timetable: required courses first, then the most credits, then the fewest campus days.

Each course has one or more sections (a section is a set of weekly meetings). A timetable takes at most one section
per course. Exact search: every course is skipped or taken in each of its sections, abandoning a branch as soon as
it clashes or exceeds the credit cap. Ranking: all required courses present, then credits, then fewer days on
campus, then fewer idle minutes between classes on the same day.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "catalog.json"
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
MAX_COURSES = 12

Meeting = tuple[str, int, int]  # day, start minute, end minute


class TimetableError(ValueError):
    """Invalid catalogue or no feasible timetable."""


@dataclass(frozen=True)
class Section:
    code: str
    meetings: tuple[Meeting, ...]


@dataclass(frozen=True)
class Course:
    name: str
    credits: int
    required: bool
    sections: tuple[Section, ...]


def _minutes(hhmm: str) -> int:
    try:
        h, m = hhmm.split(":")
        value = int(h) * 60 + int(m)
    except ValueError as err:
        raise TimetableError(f"bad time '{hhmm}'") from err
    if not 0 <= value <= 24 * 60:
        raise TimetableError(f"bad time '{hhmm}'")
    return value


def build_courses(raw: list[dict]) -> list[Course]:  # type: ignore[type-arg]
    if not raw or len(raw) > MAX_COURSES:
        raise TimetableError(f"between 1 and {MAX_COURSES} courses")
    courses = []
    for c in raw:
        sections = []
        for s in c["sections"]:
            meetings = []
            for day, start, end in s["meetings"]:
                a, b = _minutes(start), _minutes(end)
                if day not in DAYS or a >= b:
                    raise TimetableError(f"bad meeting {day} {start}-{end} in {s['code']}")
                meetings.append((day, a, b))
            sections.append(Section(s["code"], tuple(meetings)))
        if not sections or c["credits"] <= 0:
            raise TimetableError(f"course '{c['name']}' needs sections and positive credits")
        courses.append(Course(c["name"], c["credits"], bool(c.get("required", False)), tuple(sections)))
    if len({c.name for c in courses}) != len(courses):
        raise TimetableError("course names must be unique")
    return courses


def load(path: Path = DATA) -> tuple[int, list[Course]]:
    raw = json.loads(path.read_text())
    return raw["max_credits"], build_courses(raw["courses"])


def clashes(a: Section, b: Section) -> bool:
    return any(d1 == d2 and s1 < e2 and s2 < e1 for d1, s1, e1 in a.meetings for d2, s2, e2 in b.meetings)


def campus_days(chosen: list[Section]) -> int:
    return len({d for s in chosen for d, _, _ in s.meetings})


def idle_minutes(chosen: list[Section]) -> int:
    total = 0
    for day in DAYS:
        slots = sorted((a, b) for s in chosen for d, a, b in s.meetings if d == day)
        total += sum(max(0, nxt[0] - prev[1]) for prev, nxt in zip(slots, slots[1:], strict=False))
    return total


def credits_of(courses: list[Course], taken: dict[str, Section]) -> int:
    return sum(c.credits for c in courses if c.name in taken)


def register_in_order(max_credits: int, courses: list[Course]) -> dict[str, Section]:
    """Baseline: go down the catalogue, take each course's first section if it fits and does not clash."""
    taken: dict[str, Section] = {}
    used = 0
    for c in courses:
        sec = c.sections[0]
        if used + c.credits <= max_credits and all(not clashes(sec, t) for t in taken.values()):
            taken[c.name] = sec
            used += c.credits
    return taken


def best_timetable(max_credits: int, courses: list[Course]) -> dict[str, Section]:
    required = [c.name for c in courses if c.required]
    if sum(c.credits for c in courses if c.required) > max_credits:
        raise TimetableError("required courses exceed the credit cap")
    best: dict[str, Section] | None = None
    best_key: tuple[int, int, int, int] | None = None
    taken: dict[str, Section] = {}

    def go(i: int, used: int) -> None:
        nonlocal best, best_key
        if i == len(courses):
            if any(r not in taken for r in required):
                return
            chosen = list(taken.values())
            key = (-used, campus_days(chosen), idle_minutes(chosen), 0)
            if best_key is None or key < best_key:
                best, best_key = dict(taken), key
            return
        c = courses[i]
        for sec in c.sections:
            if used + c.credits <= max_credits and all(not clashes(sec, t) for t in taken.values()):
                taken[c.name] = sec
                go(i + 1, used + c.credits)
                del taken[c.name]
        if not c.required:
            go(i + 1, used)

    go(0, 0)
    if best is None:
        raise TimetableError("no clash-free timetable contains every required course")
    return best
