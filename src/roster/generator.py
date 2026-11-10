"""Seeded synthetic data for a small fictional clinic. Every name and number is invented (CC0)."""

from __future__ import annotations

import random

from .model import Problem

# (id, name, skills, contract hours per week, max consecutive days)
STAFF: list[tuple[str, str, list[str], int, int]] = [
    ("amara", "Amara Osei", ["nurse", "first-aid", "keyholder"], 40, 5),
    ("bram", "Bram Keller", ["nurse", "first-aid"], 40, 5),
    ("chen", "Chen Wei", ["front-desk", "keyholder"], 40, 5),
    ("dalia", "Dalia Haddad", ["nurse", "first-aid"], 32, 4),
    ("emil", "Emil Novak", ["front-desk", "first-aid"], 40, 5),
    ("farah", "Farah Qureshi", ["nurse", "first-aid", "keyholder"], 36, 5),
    ("gus", "Gus Lindqvist", ["front-desk"], 32, 5),
    ("hana", "Hana Mori", ["nurse", "first-aid"], 32, 5),
    ("ivo", "Ivo Petrov", ["front-desk", "keyholder", "first-aid"], 24, 4),
    ("jun", "Jun Park", ["first-aid"], 24, 3),
    ("kofi", "Kofi Mensah", ["front-desk"], 20, 3),
    ("lena", "Lena Brandt", ["nurse", "first-aid"], 16, 3),
]

TEMPLATES = [
    {
        "kind": "morning",
        "start_hour": 7,
        "hours": 8,
        "headcount": 3,
        "weekend_headcount": 2,
        "required_skills": {"front-desk": 1, "nurse": 1, "keyholder": 1},
    },
    {
        "kind": "afternoon",
        "start_hour": 12,
        "hours": 8,
        "headcount": 1,
        "weekend_headcount": 1,
        "required_skills": {"nurse": 1},
    },
    {
        "kind": "evening",
        "start_hour": 15,
        "hours": 8,
        "headcount": 1,
        "weekend_headcount": 1,
        "required_skills": {"first-aid": 1},
    },
    {
        "kind": "night",
        "start_hour": 23,
        "hours": 8,
        "headcount": 1,
        "weekend_headcount": 1,
        "required_skills": {"nurse": 1},
    },
]

KINDS = ["morning", "afternoon", "evening", "night"]


def generate(seed: int = 2024, weeks: int = 1) -> Problem:
    """Build a clinic problem. Same seed, same data."""
    rng = random.Random(seed)
    days = 7 * weeks
    # Two short leave blocks per week, never two people from the same block on the same day.
    leave_days: dict[str, set[int]] = {row[0]: set() for row in STAFF}
    for w in range(weeks):
        for sid in rng.sample([row[0] for row in STAFF], 2):
            start = 7 * w + rng.randrange(0, 5)
            leave_days[sid].update(range(start, min(days, start + rng.choice([2, 3]))))
    staff = []
    for sid, name, skills, hours, mc in STAFF:
        pref = rng.sample(KINDS, rng.choice([0, 1, 1, 2]))
        avoid = [k for k in KINDS if k not in pref and rng.random() < 0.2][:1]
        leave = sorted(leave_days[sid])
        free = [d for d in range(days) if d not in leave]
        wants = sorted(rng.sample(free, min(len(free), rng.choice([0, 1, 1, 2]) * weeks)))
        staff.append(
            {
                "id": sid,
                "name": name,
                "skills": skills,
                "contract_hours": hours,
                "leave": leave,
                "days_off_requests": wants,
                "preferred_shifts": pref,
                "avoid_shifts": avoid,
                "max_consecutive_days": mc,
            }
        )
    return Problem.model_validate(
        {
            "name": "Harbour Lane Clinic" if weeks == 1 else f"Harbour Lane Clinic, {weeks} weeks",
            "days": days,
            "start_weekday": 0,
            "staff": staff,
            "templates": TEMPLATES,
            "rules": {"min_rest_hours": 11, "max_consecutive_days": 6, "max_weekly_hours": 48},
            "overrides": [],
        }
    )
