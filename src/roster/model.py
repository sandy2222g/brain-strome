"""Input data (validated with pydantic) and the compiled, index-based instance the solver works on."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Kind = Literal["morning", "afternoon", "evening", "night"]
KIND_ORDER: tuple[str, ...] = ("morning", "afternoon", "evening", "night")
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
OFF = -1  # grid value meaning "not working"


class Staff(BaseModel):
    id: str = Field(min_length=1, max_length=24)
    name: str = Field(min_length=1, max_length=60)
    skills: list[str] = Field(default_factory=list, max_length=12)
    contract_hours: int = Field(ge=0, le=60, description="Contracted hours per 7 days")
    leave: list[int] = Field(default_factory=list, description="Day indices that are unavailable (hard)")
    days_off_requests: list[int] = Field(default_factory=list, description="Day indices they would like off (soft)")
    preferred_shifts: list[Kind] = Field(default_factory=list)
    avoid_shifts: list[Kind] = Field(default_factory=list)
    max_consecutive_days: int = Field(default=5, ge=1, le=14)


class ShiftTemplate(BaseModel):
    kind: Kind
    start_hour: int = Field(ge=0, le=23)
    hours: int = Field(ge=1, le=12)
    headcount: int = Field(ge=0, le=20, description="People needed Monday-Friday")
    weekend_headcount: int | None = Field(default=None, ge=0, le=20)
    required_skills: dict[str, int] = Field(default_factory=dict, description="Minimum people holding each skill")


class Override(BaseModel):
    """Change the headcount of one shift on one day, for example when extra cover is needed."""

    day: int = Field(ge=0, le=27)
    kind: Kind
    headcount: int = Field(ge=0, le=20)


class Rules(BaseModel):
    min_rest_hours: int = Field(default=11, ge=0, le=24)
    max_consecutive_days: int = Field(default=6, ge=1, le=14)
    max_weekly_hours: int = Field(default=48, ge=8, le=80)


class Problem(BaseModel):
    name: str = "Roster"
    days: int = Field(default=7, ge=1, le=28)
    start_weekday: int = Field(default=0, ge=0, le=6, description="0 = Monday")
    staff: list[Staff] = Field(min_length=1, max_length=40)
    templates: list[ShiftTemplate] = Field(min_length=1, max_length=4)
    rules: Rules = Field(default_factory=Rules)
    overrides: list[Override] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def _check(self) -> Problem:
        ids = [s.id for s in self.staff]
        if len(set(ids)) != len(ids):
            raise ValueError("staff ids must be unique")
        kinds = [t.kind for t in self.templates]
        if len(set(kinds)) != len(kinds):
            raise ValueError("each shift kind may appear only once in templates")
        for s in self.staff:
            for d in [*s.leave, *s.days_off_requests]:
                if not 0 <= d < self.days:
                    raise ValueError(f"{s.id}: day {d} is outside the {self.days}-day period")
        for o in self.overrides:
            if o.day >= self.days:
                raise ValueError(f"override day {o.day} is outside the {self.days}-day period")
            if o.kind not in kinds:
                raise ValueError(f"override kind {o.kind} has no template")
        return self


class Assignment(BaseModel):
    staff_id: str
    day: int = Field(ge=0, le=27)
    kind: Kind


@dataclass
class Instance:
    """Index-based view of a Problem. Grid values are template indices, or OFF."""

    problem: Problem
    P: int
    D: int
    K: int
    kinds: list[str]
    start: list[int]
    hours: list[int]
    rest_conflict: list[list[bool]]  # [k_today][k_tomorrow]
    weekend: list[bool]
    need: list[list[int]]  # [d][k]
    skill_need: list[list[dict[str, int]]]  # [d][k]
    skills: list[frozenset[str]]
    leave: list[frozenset[int]]
    off_req: list[frozenset[int]]
    preferred: list[frozenset[int]]
    avoid: list[frozenset[int]]
    target: list[float]  # contracted hours scaled to the period
    max_consec: list[int]
    weeks: int
    staff_index: dict[str, int] = field(default_factory=dict)

    def label(self, d: int) -> str:
        return DAY_NAMES[(self.problem.start_weekday + d) % 7]

    def slot_text(self, d: int, k: int) -> str:
        week = f" (week {d // 7 + 1})" if self.D > 7 else ""
        return f"{self.label(d)}{week} {self.kinds[k]}"


def compile_problem(problem: Problem) -> Instance:
    templates = sorted(problem.templates, key=lambda t: KIND_ORDER.index(t.kind))
    kinds = [t.kind for t in templates]
    K, D, P = len(templates), problem.days, len(problem.staff)
    start = [t.start_hour for t in templates]
    hours = [t.hours for t in templates]
    mr = problem.rules.min_rest_hours
    rest_conflict = [[(start[b] + 24) - (start[a] + hours[a]) < mr for b in range(K)] for a in range(K)]
    weekend = [(problem.start_weekday + d) % 7 >= 5 for d in range(D)]
    need = [[0] * K for _ in range(D)]
    skill_need: list[list[dict[str, int]]] = [[{} for _ in range(K)] for _ in range(D)]
    for d in range(D):
        for k, t in enumerate(templates):
            n = t.headcount if not weekend[d] or t.weekend_headcount is None else t.weekend_headcount
            need[d][k] = n
    for o in problem.overrides:
        need[o.day][kinds.index(o.kind)] = o.headcount
    for d in range(D):
        for k, t in enumerate(templates):
            skill_need[d][k] = {s: min(c, need[d][k]) for s, c in t.required_skills.items() if c > 0 and need[d][k] > 0}
    idx = {s.id: i for i, s in enumerate(problem.staff)}

    def kind_set(vals: list[str]) -> frozenset[int]:
        return frozenset(kinds.index(v) for v in vals if v in kinds)

    return Instance(
        problem=problem,
        P=P,
        D=D,
        K=K,
        kinds=kinds,
        start=start,
        hours=hours,
        rest_conflict=rest_conflict,
        weekend=weekend,
        need=need,
        skill_need=skill_need,
        skills=[frozenset(s.skills) for s in problem.staff],
        leave=[frozenset(s.leave) for s in problem.staff],
        off_req=[frozenset(s.days_off_requests) for s in problem.staff],
        preferred=[kind_set(s.preferred_shifts) for s in problem.staff],
        avoid=[kind_set(s.avoid_shifts) for s in problem.staff],
        target=[s.contract_hours * D / 7 for s in problem.staff],
        max_consec=[min(s.max_consecutive_days, problem.rules.max_consecutive_days) for s in problem.staff],
        weeks=(D + 6) // 7,
        staff_index=idx,
    )


Grid = list[list[int]]


def new_grid(inst: Instance) -> Grid:
    return [[OFF] * inst.D for _ in range(inst.P)]


def grid_to_assignments(inst: Instance, grid: Grid) -> list[Assignment]:
    out = []
    for d in range(inst.D):
        for p in range(inst.P):
            if grid[p][d] != OFF:
                out.append(Assignment(staff_id=inst.problem.staff[p].id, day=d, kind=inst.kinds[grid[p][d]]))  # type: ignore[arg-type]
    return out


def assignments_to_grid(inst: Instance, assignments: list[Assignment]) -> tuple[Grid, list[tuple[int, int]]]:
    """Return the grid and a list of (person, day) pairs that were given more than one shift."""
    grid = new_grid(inst)
    doubles: list[tuple[int, int]] = []
    for a in assignments:
        if a.staff_id not in inst.staff_index:
            raise ValueError(f"unknown staff id {a.staff_id}")
        if a.day >= inst.D:
            raise ValueError(f"day {a.day} is outside the period")
        if a.kind not in inst.kinds:
            raise ValueError(f"no template for {a.kind}")
        p = inst.staff_index[a.staff_id]
        if grid[p][a.day] != OFF:
            doubles.append((p, a.day))
            continue
        grid[p][a.day] = inst.kinds.index(a.kind)
    return grid, doubles
