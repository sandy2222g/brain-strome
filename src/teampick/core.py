"""Exhaustive search for the fairest equal-size split, honouring pair rules."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "players.json"
MAX_PLAYERS = 16


class TeamError(ValueError):
    """Raised for invalid players or impossible rules."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _validate(players: list[dict[str, Any]]) -> None:
    if len(players) < 2 or len(players) % 2:
        raise TeamError("need an even number of players, at least 2")
    if len(players) > MAX_PLAYERS:
        raise TeamError(f"at most {MAX_PLAYERS} players")
    names = [p["name"] for p in players]
    if len(set(names)) != len(names):
        raise TeamError("player names must be unique")
    if any(not 1 <= int(p["skill"]) <= 10 for p in players):
        raise TeamError("skill must be between 1 and 10")


def _ok(team: set[str], apart: list[list[str]], together: list[list[str]]) -> bool:
    if any(a in team and b in team for a, b in apart):
        return False
    return all((a in team) == (b in team) for a, b in together)


def split(
    players: list[dict[str, Any]], apart: list[list[str]] | None = None, together: list[list[str]] | None = None
) -> dict[str, Any]:
    """Equal-size teams with the smallest total-skill gap; ties go to the lexicographically first team A."""
    _validate(players)
    apart, together = apart or [], together or []
    names = sorted(p["name"] for p in players)
    skill = {p["name"]: int(p["skill"]) for p in players}
    for pair in apart + together:
        if any(n not in skill for n in pair):
            raise TeamError(f"unknown player in rule {pair}")
    half, first, best = len(names) // 2, names[0], None
    for combo in combinations(names, half):
        if first not in combo:
            continue  # team A always holds the first name; avoids mirrored duplicates
        a = set(combo)
        b = set(names) - a
        if not (_ok(a, apart, together) and _ok(b, apart, together)):
            continue
        gap = abs(sum(skill[n] for n in a) - sum(skill[n] for n in b))
        key = (gap, combo)
        if best is None or key < best[0]:
            best = (key, a, b)
    if best is None:
        raise TeamError("no split satisfies the rules")
    return _out(sorted(best[1]), sorted(best[2]), skill)


def _out(a: list[str], b: list[str], skill: dict[str, int]) -> dict[str, Any]:
    sa, sb = sum(skill[n] for n in a), sum(skill[n] for n in b)
    return {"team_a": a, "team_b": b, "skill_a": sa, "skill_b": sb, "gap": abs(sa - sb)}


def top_two_picks(players: list[dict[str, Any]]) -> dict[str, Any]:
    """Baseline: two captains pick in turn, best remaining player first (A, B, A, B, ...)."""
    _validate(players)
    ranked = sorted(players, key=lambda p: (-int(p["skill"]), p["name"]))
    a = [p["name"] for p in ranked[0::2]]
    b = [p["name"] for p in ranked[1::2]]
    skill = {p["name"]: int(p["skill"]) for p in players}
    return _out(sorted(a), sorted(b), skill)


def broken_rules(result: dict[str, Any], apart: list[list[str]], together: list[list[str]]) -> list[str]:
    a = set(result["team_a"])
    out = [f"{x} and {y} are on the same team" for x, y in apart if (x in a) == (y in a)]
    out += [f"{x} and {y} are on different teams" for x, y in together if (x in a) != (y in a)]
    return out
