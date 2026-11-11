"""Round-robin league schedule with balanced home and away games.

`circle_schedule` uses the circle method (one team fixed, the rest rotate) and alternates home and away so that a
team plays at home and away as evenly as possible. A "break" is a team playing home (or away) twice in a row; for n
teams (n even) the minimum possible is n - 2, and this schedule reaches it. With an odd number of teams one team
sits out each round (a bye). The baseline pairs teams in list order and always makes the team listed first the
home side.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "league.json"
MAX_TEAMS = 24
BYE = "BYE"

Round = list[tuple[str, str]]  # (home, away)


class LeagueError(ValueError):
    """Invalid league."""


@dataclass(frozen=True)
class League:
    name: str
    teams: tuple[str, ...]


def build(name: str, teams: list[str]) -> League:
    if not 2 <= len(teams) <= MAX_TEAMS:
        raise LeagueError(f"between 2 and {MAX_TEAMS} teams")
    if len({t.strip() for t in teams}) != len(teams) or any(not t.strip() for t in teams) or BYE in teams:
        raise LeagueError("team names must be unique, non-empty and not 'BYE'")
    return League(name, tuple(teams))


def load(path: Path = DATA) -> League:
    raw = json.loads(path.read_text())
    return build(raw["name"], raw["teams"])


def _slots(league: League) -> list[str]:
    return [*league.teams, BYE] if len(league.teams) % 2 else list(league.teams)


def naive_schedule(league: League) -> list[Round]:
    """Baseline: circle-method pairings, but the lower-listed team is always at home."""
    slots = _slots(league)
    n = len(slots)
    rounds: list[Round] = []
    for r in range(n - 1):
        pairs = [(n - 1, r)]
        pairs += [((r + k) % (n - 1), (r - k) % (n - 1)) for k in range(1, n // 2)]
        rounds.append([(slots[min(a, b)], slots[max(a, b)]) for a, b in pairs])
    return [[g for g in rd if BYE not in g] for rd in rounds]


def circle_schedule(league: League) -> list[Round]:
    slots = _slots(league)
    n = len(slots)
    m = n - 1
    rounds: list[Round] = []
    for r in range(m):
        pairs = [(n - 1, r) if r % 2 == 0 else (r, n - 1)]
        for k in range(1, n // 2):
            a, b = (r + k) % m, (r - k) % m
            pairs.append((a, b) if k % 2 == 0 else (b, a))
        rounds.append([(slots[h], slots[a]) for h, a in pairs])
    return [[g for g in rd if BYE not in g] for rd in rounds]


def count_breaks(rounds: list[Round]) -> int:
    last: dict[str, str] = {}
    breaks = 0
    for rd in rounds:
        cur: dict[str, str] = {}
        for home, away in rd:
            cur[home], cur[away] = "H", "A"
        breaks += sum(1 for t, side in cur.items() if last.get(t) == side)
        last = cur
    return breaks


def home_counts(rounds: list[Round]) -> dict[str, int]:
    out: dict[str, int] = {}
    for rd in rounds:
        for home, away in rd:
            out[home] = out.get(home, 0) + 1
            out.setdefault(away, 0)
    return out
