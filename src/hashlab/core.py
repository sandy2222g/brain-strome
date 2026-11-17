"""Hash tables built from scratch: separate chaining, linear probing and double hashing, with probe counting."""
from __future__ import annotations

import random


class HashError(ValueError):
    """Raised for invalid use."""


def _h1(key: int, m: int) -> int:
    return (key * 2654435761) % (2**32) % m


def _h2(key: int, m: int) -> int:
    return 1 + (key * 40503) % (m - 1)


class Chaining:
    def __init__(self, m: int) -> None:
        self.m, self.n = m, 0
        self.buckets: list[list[int]] = [[] for _ in range(m)]

    def insert(self, key: int) -> int:
        b = self.buckets[_h1(key, self.m)]
        probes = len(b) + 1
        if key not in b:
            b.append(key)
            self.n += 1
        return probes

    def find(self, key: int) -> int:
        b = self.buckets[_h1(key, self.m)]
        return (b.index(key) + 1) if key in b else len(b) + 1

    def contains(self, key: int) -> bool:
        return key in self.buckets[_h1(key, self.m)]


class OpenAddressing:
    """Open addressing: 'linear' steps by 1, 'double' steps by a second hash (m should be prime)."""

    def __init__(self, m: int, scheme: str) -> None:
        if scheme not in ("linear", "double"):
            raise HashError("scheme must be 'linear' or 'double'")
        self.m, self.scheme, self.n = m, scheme, 0
        self.slots: list[int | None] = [None] * m

    def _step(self, key: int) -> int:
        return 1 if self.scheme == "linear" else _h2(key, self.m)

    def insert(self, key: int) -> int:
        if self.n >= self.m and not self.contains(key):
            raise HashError("table is full")
        i, step = _h1(key, self.m), self._step(key)
        for probes in range(1, self.m + 1):
            if self.slots[i] is None:
                self.slots[i] = key
                self.n += 1
                return probes
            if self.slots[i] == key:
                return probes
            i = (i + step) % self.m
        raise HashError("no free slot found")

    def find(self, key: int) -> int:
        i, step = _h1(key, self.m), self._step(key)
        for probes in range(1, self.m + 1):
            if self.slots[i] is None or self.slots[i] == key:
                return probes
            i = (i + step) % self.m
        return self.m

    def contains(self, key: int) -> bool:
        i, step = _h1(key, self.m), self._step(key)
        for _ in range(self.m):
            if self.slots[i] is None:
                return False
            if self.slots[i] == key:
                return True
            i = (i + step) % self.m
        return False


def make(kind: str, m: int) -> Chaining | OpenAddressing:
    if m < 3:
        raise HashError("table size must be at least 3")
    if kind == "chaining":
        return Chaining(m)
    if kind in ("linear", "double"):
        return OpenAddressing(m, kind)
    raise HashError(f"unknown kind {kind!r}; choose chaining, linear or double")


def theory(kind: str, a: float) -> float:
    """Expected probes for an UNSUCCESSFUL search at load factor a (Knuth / CLRS)."""
    if kind == "chaining":
        return 1 + a
    if kind == "linear":
        return 0.5 * (1 + 1 / (1 - a) ** 2)
    if kind == "double":
        return 1 / (1 - a)
    raise HashError("unknown kind")


def measure(kind: str, load: float, m: int = 1009, trials: int = 8, seed: int = 0) -> float:
    """Average probes for searching keys NOT in the table, at the given load factor."""
    if not 0 < load < 1:
        raise HashError("load must be between 0 and 1")
    rng = random.Random(seed)
    total, count = 0, 0
    for _ in range(trials):
        t = make(kind, m)
        keys = rng.sample(range(10**7), int(load * m) + 400)
        for k in keys[: int(load * m)]:
            t.insert(k)
        for k in keys[int(load * m):]:
            total += t.find(k)
            count += 1
    return total / count


def curves(loads: list[float], m: int = 1009) -> dict[str, dict[str, list[float]]]:
    out: dict[str, dict[str, list[float]]] = {}
    for kind in ("chaining", "linear", "double"):
        out[kind] = {
            "measured": [round(measure(kind, a, m), 3) for a in loads],
            "theory": [round(theory(kind, a), 3) for a in loads],
        }
    return out
