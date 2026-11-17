"""Rate limiters (fixed window, sliding window log, token bucket) driven by simulated time."""
from __future__ import annotations

import random
from collections import deque
from typing import Protocol


class RateError(ValueError):
    """Raised for invalid parameters."""


class Limiter(Protocol):
    def allow(self, t: float) -> bool: ...


class FixedWindow:
    """At most `limit` requests per aligned window. Cheap, but allows 2x bursts at a window edge."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit, self.window = limit, window
        self.start, self.count = 0.0, 0

    def allow(self, t: float) -> bool:
        w = (t // self.window) * self.window
        if w != self.start:
            self.start, self.count = w, 0
        if self.count < self.limit:
            self.count += 1
            return True
        return False


class SlidingLog:
    """At most `limit` requests in ANY window-length span. Exact, but stores every timestamp."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit, self.window = limit, window
        self.log: deque[float] = deque()

    def allow(self, t: float) -> bool:
        while self.log and self.log[0] <= t - self.window:
            self.log.popleft()
        if len(self.log) < self.limit:
            self.log.append(t)
            return True
        return False


class TokenBucket:
    """Refills `limit/window` tokens per second up to `limit`: allows short bursts, enforces the average."""

    def __init__(self, limit: int, window: float) -> None:
        self.capacity, self.rate = float(limit), limit / window
        self.tokens, self.last = float(limit), 0.0

    def allow(self, t: float) -> bool:
        self.tokens = min(self.capacity, self.tokens + (t - self.last) * self.rate)
        self.last = t
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


ALGORITHMS = {"fixed_window": FixedWindow, "sliding_log": SlidingLog, "token_bucket": TokenBucket}


def make(name: str, limit: int, window: float) -> Limiter:
    if name not in ALGORITHMS:
        raise RateError(f"unknown algorithm {name!r}; choose from {sorted(ALGORITHMS)}")
    if limit < 1 or window <= 0:
        raise RateError("limit must be >= 1 and window > 0")
    return ALGORITHMS[name](limit, window)


def traffic(kind: str, seconds: int = 60, seed: int = 0) -> list[float]:
    """Synthetic request times: 'steady' ~5/s, 'bursty' = spikes, 'edge' = bursts straddling window edges."""
    rng = random.Random(seed)
    if kind == "steady":
        return sorted(rng.uniform(0, seconds) for _ in range(5 * seconds))
    if kind == "bursty":
        out: list[float] = []
        for s in range(0, seconds, 10):
            centre = s + rng.uniform(1, 9)
            out += [centre + rng.uniform(0, 0.5) for _ in range(40)]
            out += [rng.uniform(s, s + 10) for _ in range(10)]
        return sorted(t for t in out if t < seconds)
    if kind == "edge":
        out = []
        for s in range(10, seconds, 10):  # burst just before and just after each 10 s boundary
            out += [s - rng.uniform(0.01, 0.4) for _ in range(10)]
            out += [s + rng.uniform(0.01, 0.4) for _ in range(10)]
        return sorted(out)
    raise RateError(f"unknown traffic {kind!r}; choose steady, bursty or edge")


def simulate(name: str, times: list[float], limit: int, window: float) -> list[bool]:
    lim = make(name, limit, window)
    return [lim.allow(t) for t in times]


def worst_span(times: list[float], allowed: list[bool], window: float) -> int:
    """Largest number of ALLOWED requests inside any span of `window` seconds."""
    ok = [t for t, a in zip(times, allowed, strict=True) if a]
    best, lo = 0, 0
    for hi, t in enumerate(ok):
        while ok[lo] <= t - window:
            lo += 1
        best = max(best, hi - lo + 1)
    return best


def compare(kind: str, limit: int = 10, window: float = 10.0, seed: int = 0) -> list[dict[str, object]]:
    times = traffic(kind, 60, seed)
    rows = []
    for name in ALGORITHMS:
        allowed = simulate(name, times, limit, window)
        rows.append({
            "algorithm": name, "requests": len(times), "allowed": sum(allowed),
            "worst_span": worst_span(times, allowed, window), "limit": limit,
        })
    return rows
