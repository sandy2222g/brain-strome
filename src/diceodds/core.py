"""Exact dice probabilities (Fractions) with keep/drop rules, plus a Monte Carlo cross-check."""

from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from fractions import Fraction
from itertools import combinations_with_replacement
from pathlib import Path

PRESETS = Path(__file__).resolve().parents[2] / "data" / "presets.json"
PATTERN = re.compile(r"^(\d+)d(\d+)(?:(kh|kl|dh|dl)(\d+))?([+-]\d+)?$")
MAX_MULTISETS = 200_000


class DiceError(ValueError):
    """Invalid expression."""


class Spec:
    def __init__(self, n: int, sides: int, rule: str | None, m: int, mod: int) -> None:
        self.n, self.sides, self.rule, self.m, self.mod = n, sides, rule, m, mod

    def keep(self, rolls: list[int]) -> int:
        s = sorted(rolls)
        if self.rule == "kh":
            return sum(s[len(s) - self.m :])
        if self.rule == "kl":
            return sum(s[: self.m])
        if self.rule == "dh":
            return sum(s[: len(s) - self.m])
        if self.rule == "dl":
            return sum(s[self.m :])
        return sum(s)


def parse(expr: str) -> Spec:
    m = PATTERN.match(expr.strip().lower().replace(" ", ""))
    if not m:
        raise DiceError("use NdS with optional kh/kl/dh/dl count and +/- modifier, e.g. 4d6dl1+2")
    n, sides = int(m.group(1)), int(m.group(2))
    rule, cnt = m.group(3), int(m.group(4) or 0)
    if not 1 <= n <= 20 or not 2 <= sides <= 100:
        raise DiceError("dice count must be 1..20 and sides 2..100")
    if rule and not 1 <= cnt <= n - (1 if rule[0] == "d" else 0):
        raise DiceError("keep/drop count must leave at least one die")
    return Spec(n, sides, rule, cnt, int(m.group(5) or 0))


def distribution(expr: str) -> dict[int, Fraction]:
    sp = parse(expr)
    if sp.rule is None:  # plain sum: convolve one die at a time
        dist: dict[int, Fraction] = {0: Fraction(1)}
        die = Fraction(1, sp.sides)
        for _ in range(sp.n):
            nxt: dict[int, Fraction] = {}
            for v, p in dist.items():
                for f in range(1, sp.sides + 1):
                    nxt[v + f] = nxt.get(v + f, Fraction(0)) + p * die
            dist = nxt
        return {v + sp.mod: p for v, p in sorted(dist.items())}
    if math.comb(sp.sides + sp.n - 1, sp.n) > MAX_MULTISETS:
        raise DiceError("too many dice for keep/drop rules")
    total = sp.sides**sp.n
    fact = math.factorial(sp.n)
    acc: Counter[int] = Counter()
    for combo in combinations_with_replacement(range(1, sp.sides + 1), sp.n):
        ways = fact
        for c in Counter(combo).values():
            ways //= math.factorial(c)
        acc[sp.keep(list(combo)) + sp.mod] += ways
    return {v: Fraction(w, total) for v, w in sorted(acc.items())}


def stats(dist: dict[int, Fraction]) -> tuple[float, float]:
    mean = sum(v * p for v, p in dist.items())
    var = sum((v - mean) ** 2 * p for v, p in dist.items())
    return float(mean), math.sqrt(float(var))


def at_least(dist: dict[int, Fraction], target: int) -> Fraction:
    return sum((p for v, p in dist.items() if v >= target), Fraction(0))


def monte_carlo(expr: str, trials: int = 100_000, seed: int = 7) -> dict[int, float]:
    sp = parse(expr)
    rng = random.Random(seed)
    counts: Counter[int] = Counter()
    for _ in range(trials):
        counts[sp.keep([rng.randint(1, sp.sides) for _ in range(sp.n)]) + sp.mod] += 1
    return {v: c / trials for v, c in sorted(counts.items())}


def analyse(expr: str, target: int | None = None, trials: int = 50_000) -> dict[str, object]:
    dist = distribution(expr)
    mean, sd = stats(dist)
    mc = monte_carlo(expr, trials)
    diff = max(abs(float(dist.get(v, 0)) - mc.get(v, 0.0)) for v in set(dist) | set(mc))
    out: dict[str, object] = {
        "expr": expr, "mean": round(mean, 2), "sd": round(sd, 2),
        "pmf": [{"value": v, "p": float(p), "exact": f"{p.numerator}/{p.denominator}"} for v, p in dist.items()],
        "mc_max_diff": round(diff, 4), "trials": trials}
    if target is not None:
        p = at_least(dist, target)
        out.update({"target": target, "p_at_least": float(p), "p_exact": f"{p.numerator}/{p.denominator}"})
    return out


def presets() -> list[dict[str, object]]:
    return json.loads(PRESETS.read_text())  # type: ignore[no-any-return]
