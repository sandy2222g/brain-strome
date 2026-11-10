"""Beam search for a playlist that follows a target energy arc.

Cost = how far each track's energy is from the arc at that moment
     + how rough each transition is (tempo jump, key clash, mood swing, same artist twice in a row).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from arcmix.library import Track, key_distance

ARCS: dict[str, list[tuple[float, float]]] = {
    "Warm-up, peak, cool-down": [(0.0, 0.25), (0.35, 0.6), (0.65, 0.92), (1.0, 0.25)],
    "Steady focus": [(0.0, 0.40), (1.0, 0.40)],
    "Slow burn": [(0.0, 0.20), (1.0, 0.90)],
    "Rollercoaster": [(0.0, 0.3), (0.2, 0.9), (0.4, 0.3), (0.6, 0.9), (0.8, 0.3), (1.0, 0.8)],
    "Wind down": [(0.0, 0.85), (1.0, 0.15)],
}
W_ARC, W_TEMPO, W_KEY, W_VAL, W_ARTIST = 6.0, 1.0, 0.8, 0.5, 1.5
TEMPO_SCALE = 40.0
MAX_MINUTES = 240
TOLERANCE_S = 60


class PlaylistError(ValueError):
    """Bad request; message is safe to show."""


def arc_at(points: list[tuple[float, float]], x: float) -> float:
    """Linear interpolation of the target energy at position x in [0, 1]."""
    pts = sorted(points)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y1
    return pts[-1][1]


def transition_cost(a: Track, b: Track) -> float:
    tempo = min(abs(a.tempo - b.tempo) / TEMPO_SCALE, 1.5)
    same_artist = W_ARTIST if a.artist == b.artist else 0.0
    return W_TEMPO * tempo + W_KEY * key_distance(a, b) + W_VAL * abs(a.valence - b.valence) + same_artist


@dataclass
class Step:
    track: Track
    target_energy: float
    transition: float
    tempo_delta: float
    key_distance: float


@dataclass
class Playlist:
    steps: list[Step]
    minutes: float
    arc_rmse: float
    mean_transition: float
    baseline_arc_rmse: float
    baseline_mean_transition: float


def _make_step(prev: Track | None, t: Track, target: float) -> Step:
    if prev is None:
        return Step(t, target, 0.0, 0.0, 0.0)
    return Step(t, target, transition_cost(prev, t), abs(prev.tempo - t.tempo), key_distance(prev, t))


def _target(points: list[tuple[float, float]], elapsed: float, total: float, duration: float) -> float:
    return arc_at(points, min(1.0, (elapsed + duration / 2) / total))


def build(
    tracks: list[Track],
    arc: list[tuple[float, float]],
    minutes: float = 45.0,
    allowed_moods: set[str] | None = None,
    beam: int = 12,
    branch: int = 10,
    seed: int = 0,
) -> Playlist:
    if not 5 <= minutes <= MAX_MINUTES:
        raise PlaylistError(f"minutes must be between 5 and {MAX_MINUTES}")
    if len(arc) < 2 or any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in arc):
        raise PlaylistError("an arc needs at least two points with positions and energy within [0, 1]")
    pool = [t for t in tracks if allowed_moods is None or t.mood in allowed_moods]
    total = minutes * 60.0
    if sum(t.duration_s for t in pool) < total:
        raise PlaylistError("not enough tracks in the chosen moods for that length")
    rng = random.Random(seed)
    beams: list[tuple[float, float, frozenset[str], list[Step]]] = [(0.0, 0.0, frozenset(), [])]
    done: list[tuple[float, list[Step]]] = []
    for _ in range(len(pool)):  # hard bound: a playlist can never be longer than the pool
        if not beams:
            break
        nxt: list[tuple[float, float, frozenset[str], list[Step]]] = []
        for cost, elapsed, ids, steps in beams:
            prev = steps[-1].track if steps else None
            cands = []
            for t in pool:
                if t.id in ids:
                    continue
                tgt = _target(arc, elapsed, total, t.duration_s)
                step = _make_step(prev, t, tgt)
                cands.append((W_ARC * (t.energy - tgt) ** 2 + step.transition + rng.random() * 1e-6, step))
            cands.sort(key=lambda x: x[0])
            for c, step in cands[:branch]:
                new_elapsed = elapsed + step.track.duration_s
                state = (cost + c, new_elapsed, ids | {step.track.id}, [*steps, step])
                if new_elapsed >= total - TOLERANCE_S:
                    done.append((state[0] / len(state[3]), state[3]))
                else:
                    nxt.append(state)
        nxt.sort(key=lambda s: s[0] / len(s[3]))
        beams = nxt[:beam]
        if len(done) >= beam * 3:
            break
    if not done:
        raise PlaylistError("could not fill the requested length")
    best = min(done, key=lambda d: d[0])[1]
    return _summarise(best, arc, total, pool, rng)


def _metrics(steps: list[Step]) -> tuple[float, float]:
    rmse = (sum((s.track.energy - s.target_energy) ** 2 for s in steps) / len(steps)) ** 0.5
    trans = [s.transition for s in steps[1:]]
    return rmse, (sum(trans) / len(trans) if trans else 0.0)


def _summarise(
    steps: list[Step], arc: list[tuple[float, float]], total: float, pool: list[Track], rng: random.Random
) -> Playlist:
    rmse, mean_tr = _metrics(steps)
    shuffled = pool[:]
    rng.shuffle(shuffled)  # baseline: no planning at all, same length
    base: list[Step] = []
    elapsed, prev = 0.0, None
    for t in shuffled:
        if elapsed >= total - TOLERANCE_S:
            break
        base.append(_make_step(prev, t, _target(arc, elapsed, total, t.duration_s)))
        elapsed += t.duration_s
        prev = t
    b_rmse, b_tr = _metrics(base)
    minutes = sum(s.track.duration_s for s in steps) / 60.0
    return Playlist(steps, round(minutes, 1), round(rmse, 4), round(mean_tr, 4), round(b_rmse, 4), round(b_tr, 4))
