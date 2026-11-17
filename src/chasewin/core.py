"""Exact win probability of a limited-overs run chase via dynamic programming (invented per-ball model)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "presets.json"
RUNS = ("dot", "1", "2", "3", "4", "6")
RUN_VALUE = {"dot": 0, "1": 1, "2": 2, "3": 3, "4": 4, "6": 6}
MAX_BALLS = 300
MAX_NEED = 300


class ChaseError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def check_probs(p: dict[str, float]) -> None:
    keys = {*RUNS, "wicket", "extra"}
    if set(p) != keys or any(v < 0 for v in p.values()) or abs(sum(p.values()) - 1) > 1e-6:
        raise ChaseError("probabilities must cover dot,1,2,3,4,6,wicket,extra and sum to 1")


def _need(target: int, runs: int, wickets: int, balls_left: int) -> int:
    if target < 1 or runs < 0 or not 0 <= wickets <= 10 or balls_left < 0:
        raise ChaseError("target must be >= 1, runs >= 0, 0 <= wickets <= 10 and balls_left >= 0")
    if balls_left > MAX_BALLS:
        raise ChaseError(f"at most {MAX_BALLS} balls left")
    need = target - runs
    if need > MAX_NEED:
        raise ChaseError(f"at most {MAX_NEED} runs needed")
    return need


def win_probability(p: dict[str, float], target: int, runs: int, wickets: int, balls_left: int) -> float:
    """P(chasing side reaches `target` before running out of balls or wickets).

    f(b, w, n) = sum_r p_r f(b-1, w, n-r) + p_wkt f(b-1, w+1, n) + p_extra f(b, w, n-1)
    where n is runs still needed, b balls left, w wickets lost. An extra (wide / no-ball) scores one run and does
    not use a ball, which is why the n-1 term stays on the same ball layer.
    """
    check_probs(p)
    need = _need(target, runs, wickets, balls_left)
    if need <= 0:
        return 1.0
    if wickets >= 10 or balls_left == 0:
        return 0.0
    moves = [(RUN_VALUE[k], p[k]) for k in RUNS]
    pw, px = p["wicket"], p["extra"]
    prev = [[1.0] + [0.0] * need for _ in range(11)]  # b = 0: only n = 0 is a win
    for _ in range(balls_left):
        cur = [[1.0] + [0.0] * need for _ in range(11)]
        for w in range(10):
            row, wk = cur[w], prev[w + 1]
            same = prev[w]
            for n in range(1, need + 1):
                v = pw * wk[n] + px * row[max(n - 1, 0)]
                for r, pr in moves:
                    v += pr * same[max(n - r, 0)]
                row[n] = v
        # wickets == 10: all out, cannot win while n > 0 (already 0.0 in the initial rows)
        prev = cur
    return prev[wickets][need]


def simulate(
    p: dict[str, float], target: int, runs: int, wickets: int, balls_left: int, n: int, seed: int = 0
) -> float:
    """Monte Carlo estimate of the same probability, used to cross-check the DP."""
    check_probs(p)
    rng = random.Random(seed)
    labels = [*RUNS, "wicket", "extra"]
    weights = [p[k] for k in labels]
    wins = 0
    for _ in range(n):
        r, w, b = runs, wickets, balls_left
        while r < target and w < 10 and b > 0:
            o = rng.choices(labels, weights)[0]
            if o == "wicket":
                w += 1
                b -= 1
            elif o == "extra":
                r += 1
            else:
                r += RUN_VALUE[o]
                b -= 1
        wins += r >= target
    return wins / n


def run_rate_baseline(target: int, runs: int, balls_left: int, balls_faced: int) -> dict[str, float | str]:
    """Baseline: compare the current run rate with the required run rate, ignoring wickets."""
    need = target - runs
    rrr = need * 6 / balls_left if balls_left else float("inf")
    crr = runs * 6 / balls_faced if balls_faced else 0.0
    verdict = "ahead" if crr >= rrr else "behind"
    return {"required_rate": round(rrr, 2), "current_rate": round(crr, 2), "verdict": verdict}


def analyse(
    preset: str, target: int, runs: int, wickets: int, balls_left: int, total_balls: int = 120
) -> dict[str, Any]:
    presets = load()["presets"]
    if preset not in presets:
        raise ChaseError(f"unknown preset: {preset}")
    prob = win_probability(presets[preset], target, runs, wickets, balls_left)
    faced = max(total_balls - balls_left, 0)
    return {
        "win_probability": round(prob, 4),
        "baseline": run_rate_baseline(target, runs, balls_left, faced),
        "by_preset": {k: round(win_probability(v, target, runs, wickets, balls_left), 4) for k, v in presets.items()},
    }
