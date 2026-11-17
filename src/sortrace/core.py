"""Five sorting algorithms, instrumented to count comparisons and record frames for animation."""
from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

KINDS = ["random", "sorted", "reversed", "few-unique", "nearly-sorted"]
ALGOS = ["bubble", "insertion", "merge", "quick", "heap"]


class SortError(ValueError):
    pass


@dataclass
class Tracker:
    a: list[int]
    comparisons: int = 0
    writes: int = 0
    frames: list[tuple[int, list[int]]] = field(default_factory=list)  # (comparisons so far, array snapshot)

    def less(self, x: int, y: int) -> bool:
        self.comparisons += 1
        return x < y

    def snap(self) -> None:
        self.frames.append((self.comparisons, self.a[:]))

    def swap(self, i: int, j: int) -> None:
        self.a[i], self.a[j] = self.a[j], self.a[i]
        self.writes += 2
        self.snap()


def bubble(t: Tracker) -> None:
    n = len(t.a)
    for end in range(n - 1, 0, -1):
        swapped = False
        for i in range(end):
            if t.less(t.a[i + 1], t.a[i]):
                t.swap(i, i + 1)
                swapped = True
        if not swapped:
            break


def insertion(t: Tracker) -> None:
    for i in range(1, len(t.a)):
        j = i
        while j > 0 and t.less(t.a[j], t.a[j - 1]):
            t.swap(j, j - 1)
            j -= 1


def merge(t: Tracker) -> None:
    def go(lo: int, hi: int) -> None:
        if hi - lo < 2:
            return
        mid = (lo + hi) // 2
        go(lo, mid)
        go(mid, hi)
        left, right, out = t.a[lo:mid], t.a[mid:hi], []
        i = j = 0
        while i < len(left) and j < len(right):
            if t.less(right[j], left[i]):  # strict: equal items keep their order, so the sort is stable
                out.append(right[j])
                j += 1
            else:
                out.append(left[i])
                i += 1
        out += left[i:] + right[j:]
        t.a[lo:hi] = out
        t.writes += len(out)
        t.snap()

    go(0, len(t.a))


def quick(t: Tracker) -> None:
    """Last element as pivot (Lomuto): simple, and slow on already-sorted input on purpose."""
    stack = [(0, len(t.a) - 1)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        pivot, p = t.a[hi], lo
        for i in range(lo, hi):
            if t.less(t.a[i], pivot):
                if i != p:
                    t.swap(i, p)
                p += 1
        if p != hi:
            t.swap(p, hi)
        stack += [(lo, p - 1), (p + 1, hi)]


def heap(t: Tracker) -> None:
    n = len(t.a)

    def sift(root: int, size: int) -> None:
        while (child := 2 * root + 1) < size:
            if child + 1 < size and t.less(t.a[child], t.a[child + 1]):
                child += 1
            if not t.less(t.a[root], t.a[child]):
                return
            t.swap(root, child)
            root = child

    for r in range(n // 2 - 1, -1, -1):
        sift(r, n)
    for end in range(n - 1, 0, -1):
        t.swap(0, end)
        sift(0, end)


FUNCS: dict[str, Callable[[Tracker], None]] = {"bubble": bubble, "insertion": insertion, "merge": merge,
                                                "quick": quick, "heap": heap}


def make_input(kind: str, n: int, seed: int = 1) -> list[int]:
    if kind not in KINDS or not 2 <= n <= 2000:
        raise SortError(f"kind must be one of {', '.join(KINDS)} and n between 2 and 2000")
    rng = random.Random(seed)
    base = list(range(n))
    if kind == "sorted":
        return base
    if kind == "reversed":
        return base[::-1]
    if kind == "few-unique":
        return [rng.randint(0, 4) for _ in range(n)]
    if kind == "nearly-sorted":
        for _ in range(max(1, n // 20)):
            i, j = rng.randrange(n), rng.randrange(n)
            base[i], base[j] = base[j], base[i]
        return base
    rng.shuffle(base)
    return base


def run(algo: str, data: list[int], keep_frames: bool = True) -> Tracker:
    if algo not in FUNCS:
        raise SortError(f"algorithm must be one of {', '.join(ALGOS)}")
    t = Tracker(data[:])
    if keep_frames:
        t.snap()
    FUNCS[algo](t)
    if keep_frames:
        t.snap()
    return t


def thin(frames: list[tuple[int, list[int]]], limit: int = 120) -> list[tuple[int, list[int]]]:
    if len(frames) <= limit:
        return frames
    step = len(frames) / (limit - 1)
    out = [frames[int(i * step)] for i in range(limit - 1)]
    return out + [frames[-1]]


def table(n: int = 200) -> dict[str, dict[str, int]]:
    """Comparisons for every algorithm on every kind of input."""
    return {k: {a: run(a, make_input(k, n), keep_frames=False).comparisons for a in ALGOS} for k in KINDS}
