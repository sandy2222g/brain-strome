"""Countdown numbers game: reach a target using +, -, x and exact division on some given numbers (each used once)."""
from __future__ import annotations

import random
from itertools import combinations


class CountdownError(ValueError):
    """Raised for invalid puzzles."""


def solve(numbers: list[int], target: int) -> dict[str, object]:
    """Exhaustive search over all ways of combining pairs. Returns the closest reachable value and one expression."""
    if not 2 <= len(numbers) <= 6 or any(n < 1 or n > 100 for n in numbers):
        raise CountdownError("give 2 to 6 numbers, each between 1 and 100")
    if not 1 <= target <= 999:
        raise CountdownError("target must be between 1 and 999")
    best: tuple[int, str] = (10**9, "")
    nodes = 0
    seen: set[tuple[tuple[int, ...], ...]] = set()

    def consider(val: int, expr: str) -> None:
        nonlocal best
        gap, best_gap = abs(val - target), abs(best[0] - target)
        if gap < best_gap or (gap == best_gap and len(expr) < len(best[1])):
            best = (val, expr)

    def go(items: list[tuple[int, str]]) -> None:
        nonlocal nodes
        key = (tuple(sorted(v for v, _ in items)),)
        if key in seen:
            return
        seen.add(key)
        nodes += 1
        for v, e in items:
            consider(v, e)
        for (i, (a, ea)), (j, (b, eb)) in combinations(enumerate(items), 2):
            rest = [it for k, it in enumerate(items) if k not in (i, j)]
            hi, lo = ((a, ea), (b, eb)) if a >= b else ((b, eb), (a, ea))
            opts = [(hi[0] + lo[0], f"({hi[1]} + {lo[1]})"), (hi[0] * lo[0], f"({hi[1]} x {lo[1]})")]
            if hi[0] > lo[0]:
                opts.append((hi[0] - lo[0], f"({hi[1]} - {lo[1]})"))
            if lo[0] > 0 and hi[0] % lo[0] == 0 and lo[0] != 1:
                opts.append((hi[0] // lo[0], f"({hi[1]} / {lo[1]})"))
            for val, expr in opts:
                go([*rest, (val, expr)])

    go([(n, str(n)) for n in numbers])
    value, expr = best
    return {
        "value": value, "expression": expr, "exact": value == target, "distance": abs(value - target), "states": nodes,
    }


def evaluate(expr: str) -> int:
    """Safely evaluate an expression produced by `solve` (digits, + - x / and brackets only)."""
    if not expr or set(expr) - set("0123456789+-x/() "):
        raise CountdownError("unexpected characters in expression")
    return int(eval(expr.replace("x", "*"), {"__builtins__": {}}, {}))  # noqa: S307 - input is whitelisted above


def random_puzzle(seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    large = rng.sample([25, 50, 75, 100], rng.randint(0, 2))
    small = rng.sample(list(range(1, 11)) * 2, 6 - len(large))
    return {"numbers": sorted(large + small, reverse=True), "target": rng.randint(101, 999)}


def solvable_share(trials: int = 40) -> float:
    """Fraction of random 6-number puzzles for which the target is hit exactly."""
    hits = 0
    for s in range(trials):
        p = random_puzzle(s)
        hits += bool(solve(p["numbers"], p["target"])["exact"])  # type: ignore[arg-type]
    return hits / trials
