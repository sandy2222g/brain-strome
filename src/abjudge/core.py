"""A/B test statistics from scratch: z-test, confidence interval, sample size and a peeking simulation."""
from __future__ import annotations

import math
import random
from statistics import NormalDist

N = NormalDist()


class ABError(ValueError):
    """Raised for invalid inputs."""


def _check(conv: int, n: int) -> None:
    if n < 1 or not 0 <= conv <= n:
        raise ABError("need 0 <= conversions <= visitors and visitors >= 1")


def analyse(conv_a: int, n_a: int, conv_b: int, n_b: int, alpha: float = 0.05) -> dict[str, float | bool | str]:
    """Two-sided two-proportion z-test with pooled variance, plus an unpooled confidence interval for the lift."""
    _check(conv_a, n_a)
    _check(conv_b, n_b)
    if not 0 < alpha < 1:
        raise ABError("alpha must be between 0 and 1")
    pa, pb = conv_a / n_a, conv_b / n_b
    pool = (conv_a + conv_b) / (n_a + n_b)
    se0 = math.sqrt(pool * (1 - pool) * (1 / n_a + 1 / n_b))
    z = (pb - pa) / se0 if se0 > 0 else 0.0
    p = 2 * (1 - N.cdf(abs(z)))
    se = math.sqrt(pa * (1 - pa) / n_a + pb * (1 - pb) / n_b)
    zc = N.inv_cdf(1 - alpha / 2)
    diff = pb - pa
    return {
        "rate_a": round(pa, 4), "rate_b": round(pb, 4), "diff": round(diff, 4),
        "z": round(z, 3), "p_value": round(p, 4),
        "ci_low": round(diff - zc * se, 4), "ci_high": round(diff + zc * se, 4),
        "significant": p < alpha,
        "verdict": "B is different from A" if p < alpha else "No reliable difference yet",
    }


def sample_size(base_rate: float, min_lift: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Visitors needed PER VARIANT to detect an absolute lift `min_lift` over `base_rate`."""
    if not 0 < base_rate < 1 or min_lift <= 0 or base_rate + min_lift >= 1:
        raise ABError("need 0 < base_rate, min_lift > 0 and base_rate + min_lift < 1")
    p1, p2 = base_rate, base_rate + min_lift
    za, zb = N.inv_cdf(1 - alpha / 2), N.inv_cdf(power)
    pbar = (p1 + p2) / 2
    num = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(num / min_lift**2)


def false_positive_rate(
    peeks: int, n_per_peek: int = 200, rate: float = 0.10, trials: int = 1500, seed: int = 0
) -> float:
    """Both variants are IDENTICAL. How often does a test checked `peeks` times still declare a winner?"""
    if peeks < 1:
        raise ABError("peeks must be at least 1")
    rng = random.Random(seed)
    wrong = 0
    for _ in range(trials):
        ca = cb = na = nb = 0
        hit = False
        for _ in range(peeks):
            ca += sum(rng.random() < rate for _ in range(n_per_peek))
            cb += sum(rng.random() < rate for _ in range(n_per_peek))
            na += n_per_peek
            nb += n_per_peek
            if analyse(ca, na, cb, nb)["significant"]:
                hit = True
                break
        wrong += hit
    return wrong / trials
