"""Meeting-slot scoring across time zones.

Each person has working hours and a sleep window. A local hour costs 0 inside working hours and grows
quadratically outside them; sleep hours are effectively forbidden. A slot's cost for a person is the
worst hour the meeting touches. Slots are ranked by a blend of total pain and the worst individual pain,
so nobody carries a disastrous time just because the average looks fine. For recurring meetings, a
rotation picks a different good slot each week so that cumulative pain is balanced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SLEEP_MIN = 50.0  # any pain at or above this means the meeting lands in someone's sleep
SLEEP_PER_HOUR = 12.0  # extra pain per hour deeper into the sleep window
STEP_MIN = 30


class MeetingError(ValueError):
    """Bad request; message is safe to show."""


@dataclass(frozen=True)
class Person:
    name: str
    tz: str
    work_start: float = 9.0
    work_end: float = 17.0
    sleep_start: float = 22.5
    sleep_end: float = 6.5

    def zone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise MeetingError(f"unknown time zone: {self.tz}") from exc


@dataclass
class PersonSlot:
    name: str
    local_start: str
    local_end: str
    local_day: str
    pain: float
    note: str


@dataclass
class Slot:
    start_utc: datetime
    total_pain: float
    worst_pain: float
    score: float
    people: list[PersonSlot] = field(default_factory=list)
    sleepers: int = 0


def hour_cost(p: Person, hour: float) -> float:
    """Pain of a meeting at a local hour (0-24)."""
    in_sleep = hour >= p.sleep_start or hour < p.sleep_end
    if in_sleep:
        length = (24 - p.sleep_start) + p.sleep_end
        into = hour - p.sleep_start if hour >= p.sleep_start else hour + 24 - p.sleep_start
        return round(SLEEP_MIN + SLEEP_PER_HOUR * min(into, length - into), 3)
    if p.work_start <= hour < p.work_end:
        return 0.0
    gap = p.work_start - hour if hour < p.work_start else hour - p.work_end
    return round(gap * gap, 3)


def _local(p: Person, start_utc: datetime) -> datetime:
    return start_utc.astimezone(p.zone())


def slot_pain(p: Person, start_utc: datetime, duration_min: int) -> float:
    """Worst hour touched by the meeting, sampled every 15 minutes (so DST and day wrap are respected)."""
    worst = 0.0
    for off in range(0, duration_min + 1, 15):
        t = _local(p, start_utc + timedelta(minutes=off))
        worst = max(worst, hour_cost(p, t.hour + t.minute / 60))
    return worst


def _note(pain: float) -> str:
    if pain >= SLEEP_MIN:
        return "during sleep"
    if pain == 0:
        return "working hours"
    return "outside working hours"


def score_slot(people: list[Person], start_utc: datetime, duration_min: int, lam: float = 1.0) -> Slot:
    parts, pains = [], []
    for p in people:
        pain = slot_pain(p, start_utc, duration_min)
        pains.append(pain)
        s = _local(p, start_utc)
        e = _local(p, start_utc + timedelta(minutes=duration_min))
        parts.append(
            PersonSlot(p.name, s.strftime("%H:%M"), e.strftime("%H:%M"), s.strftime("%a %d %b"), pain, _note(pain))
        )
    total, worst = sum(pains), max(pains)
    return Slot(start_utc, total, worst, total + lam * worst, parts, sum(1 for x in pains if x >= SLEEP_MIN))


def validate(people: list[Person], duration_min: int) -> None:
    if len(people) < 2:
        raise MeetingError("add at least two people")
    if len({p.name for p in people}) != len(people):
        raise MeetingError("names must be unique")
    if not 15 <= duration_min <= 180 or duration_min % 15:
        raise MeetingError("duration must be 15 to 180 minutes in 15-minute steps")
    for p in people:
        p.zone()
        if not 0 <= p.work_start < p.work_end <= 24:
            raise MeetingError(f"{p.name}: working hours must satisfy 0 <= start < end <= 24")


def candidate_slots(people: list[Person], day: date, duration_min: int = 60, lam: float = 1.0) -> list[Slot]:
    """Every start time (30-minute steps) on a UTC day, best first."""
    validate(people, duration_min)
    base = datetime(day.year, day.month, day.day, tzinfo=UTC)
    slots = [score_slot(people, base + timedelta(minutes=m), duration_min, lam) for m in range(0, 24 * 60, STEP_MIN)]
    return sorted(slots, key=lambda s: (s.score, s.start_utc))


def best_slots(people: list[Person], day: date, duration_min: int = 60, n: int = 5, lam: float = 1.0) -> list[Slot]:
    return candidate_slots(people, day, duration_min, lam)[:n]


@dataclass
class Rotation:
    weeks: list[Slot]
    cumulative: dict[str, float]
    fixed_cumulative: dict[str, float]
    spread: float
    fixed_spread: float
    max_pain_rotation: float
    max_pain_fixed: float


def rotation(
    people: list[Person], start: date, weeks: int, duration_min: int = 60, lam: float = 1.0, pool_size: int = 14
) -> Rotation:
    """Pick a slot per week so that cumulative pain stays balanced; compare with always using the single best slot."""
    validate(people, duration_min)
    if not 2 <= weeks <= 52:
        raise MeetingError("weeks must be between 2 and 52")
    names = [p.name for p in people]
    cum = {n: 0.0 for n in names}
    fixed = {n: 0.0 for n in names}
    chosen: list[Slot] = []
    for w in range(weeks):
        day = start + timedelta(weeks=w)
        cands = candidate_slots(people, day, duration_min, lam)
        pool = [c for c in cands[:pool_size] if c.sleepers == 0] or cands[:pool_size]
        best_fixed = cands[0]
        for ps in best_fixed.people:
            fixed[ps.name] += ps.pain

        def after(c: Slot) -> tuple[float, float, float]:
            new = {ps.name: cum[ps.name] + ps.pain for ps in c.people}
            return (max(new.values()), sum(new.values()), c.score)

        pick = min(pool, key=after)
        for ps in pick.people:
            cum[ps.name] += ps.pain
        chosen.append(pick)

    def spread(d: dict[str, float]) -> float:
        return round(max(d.values()) - min(d.values()), 2)

    return Rotation(
        chosen,
        {k: round(v, 2) for k, v in cum.items()},
        {k: round(v, 2) for k, v in fixed.items()},
        spread(cum),
        spread(fixed),
        round(max(cum.values()), 2),
        round(max(fixed.values()), 2),
    )
