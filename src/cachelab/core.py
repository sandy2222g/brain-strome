"""Cache eviction policies (FIFO, LRU, LFU) plus Belady's optimal policy as an upper bound."""
from __future__ import annotations

import random
from collections import Counter, OrderedDict, deque


class CacheError(ValueError):
    """Raised for invalid parameters."""


def fifo(trace: list[int], size: int) -> int:
    q: deque[int] = deque()
    members: set[int] = set()
    hits = 0
    for k in trace:
        if k in members:
            hits += 1
            continue
        if len(q) == size:
            members.discard(q.popleft())
        q.append(k)
        members.add(k)
    return hits


def lru(trace: list[int], size: int) -> int:
    od: OrderedDict[int, None] = OrderedDict()
    hits = 0
    for k in trace:
        if k in od:
            hits += 1
            od.move_to_end(k)
            continue
        if len(od) == size:
            od.popitem(last=False)
        od[k] = None
    return hits


def lfu(trace: list[int], size: int) -> int:
    """Evicts the least frequently used key (ties: least recently used)."""
    freq: Counter[int] = Counter()
    last: dict[int, int] = {}
    hits = 0
    for t, k in enumerate(trace):
        if k in freq:
            hits += 1
        elif len(freq) == size:
            victim = min(freq, key=lambda x: (freq[x], last[x]))
            del freq[victim], last[victim]
        freq[k] += 1
        last[k] = t
    return hits


def optimal(trace: list[int], size: int) -> int:
    """Belady: evict the key whose next use is furthest away. Needs the future, so it is only a bound."""
    nxt: list[int] = [0] * len(trace)
    seen: dict[int, int] = {}
    for i in range(len(trace) - 1, -1, -1):
        nxt[i] = seen.get(trace[i], len(trace) + 1)
        seen[trace[i]] = i
    cache: dict[int, int] = {}  # key -> index of next use
    hits = 0
    for i, k in enumerate(trace):
        if k in cache:
            hits += 1
        elif len(cache) == size:
            del cache[max(cache, key=lambda x: cache[x])]
        cache[k] = nxt[i]
    return hits


POLICIES = {"fifo": fifo, "lru": lru, "lfu": lfu, "optimal": optimal}


def make_trace(kind: str, n: int = 5000, keys: int = 200, seed: int = 0) -> list[int]:
    rng = random.Random(seed)
    if kind == "zipf":  # a few hot keys dominate, like popular pages
        weights = [1 / (r + 1) for r in range(keys)]
        return rng.choices(range(keys), weights, k=n)
    if kind == "uniform":
        return [rng.randrange(keys) for _ in range(n)]
    if kind == "scan":  # hot working set interrupted by one-off sweeps over many keys
        out: list[int] = []
        scan_key = 1000
        while len(out) < n:
            out += [rng.randrange(20) for _ in range(150)]
            out += list(range(scan_key, scan_key + 60))
            scan_key += 60
        return out[:n]
    raise CacheError(f"unknown trace {kind!r}; choose zipf, uniform or scan")


def compare(kind: str, size: int = 20, n: int = 5000, seed: int = 0) -> list[dict[str, object]]:
    if size < 1:
        raise CacheError("size must be at least 1")
    trace = make_trace(kind, n, seed=seed)
    return [{"policy": p, "hit_rate": round(fn(trace, size) / len(trace), 4)} for p, fn in POLICIES.items()]


def curve(kind: str, sizes: list[int], n: int = 5000, seed: int = 0) -> dict[str, list[float]]:
    trace = make_trace(kind, n, seed=seed)
    return {p: [round(fn(trace, s) / len(trace), 4) for s in sizes] for p, fn in POLICIES.items()}
