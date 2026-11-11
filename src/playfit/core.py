"""Fill a fixed trip length with songs: subset-sum DP for the most music that fits without running over.

Durations are whole seconds. Among selections with the same total, fewer songs wins, then earlier list order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "songs.json"
MAX_SONGS = 200


class PlaylistError(ValueError):
    """Invalid songs or target."""


@dataclass(frozen=True)
class Song:
    title: str
    seconds: int


def build(songs: list[dict], target_minutes: int) -> tuple[list[Song], int]:  # type: ignore[type-arg]
    if not 1 <= len(songs) <= MAX_SONGS or not 1 <= target_minutes <= 600:
        raise PlaylistError("1-200 songs and a target of 1-600 minutes")
    out = [Song(str(s["title"]), int(s["seconds"])) for s in songs]
    if any(not 30 <= s.seconds <= 1800 for s in out):
        raise PlaylistError("song lengths must be 30-1800 seconds")
    return out, target_minutes * 60


def best_fit(songs: list[Song], target: int) -> list[Song]:
    """Songs (in original order) whose total length is as close to `target` as possible without exceeding it."""
    best: list[tuple[int, ...] | None] = [None] * (target + 1)
    best[0] = ()
    for i, s in enumerate(songs):
        for t in range(target, s.seconds - 1, -1):
            prev = best[t - s.seconds]
            if prev is not None:
                cand = (*prev, i)
                cur = best[t]
                if cur is None or len(cand) < len(cur):
                    best[t] = cand
    total = max(t for t in range(target + 1) if best[t] is not None)
    return [songs[i] for i in best[total] or ()]


def in_order(songs: list[Song], target: int) -> list[Song]:
    """Baseline: play the list top to bottom until the next song would run over."""
    out: list[Song] = []
    used = 0
    for s in songs:
        if used + s.seconds > target:
            break
        out.append(s)
        used += s.seconds
    return out


def total(songs: list[Song]) -> int:
    return sum(s.seconds for s in songs)


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
