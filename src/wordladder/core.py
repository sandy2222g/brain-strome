"""Word ladders: shortest chains of one-letter changes, via BFS."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "words.txt"


class LadderError(ValueError):
    pass


@dataclass(frozen=True)
class Result:
    path: list[str]
    explored: int  # words taken off the queue: the work done


def load_words(path: Path = DATA) -> set[str]:
    return {w.strip().lower() for w in path.read_text().split() if w.strip().isalpha()}


def buckets(words: set[str]) -> dict[str, list[str]]:
    """Group words by pattern with one letter wildcarded: 'cat' -> '*at', 'c*t', 'ca*'."""
    out: dict[str, list[str]] = defaultdict(list)
    for w in sorted(words):
        for i in range(len(w)):
            out[w[:i] + "*" + w[i + 1:]].append(w)
    return out


def neighbours(word: str, b: dict[str, list[str]]) -> list[str]:
    seen: list[str] = []
    for i in range(len(word)):
        for n in b.get(word[:i] + "*" + word[i + 1:], []):
            if n != word and n not in seen:
                seen.append(n)
    return seen


def check(a: str, z: str, words: set[str]) -> tuple[str, str]:
    a, z = a.strip().lower(), z.strip().lower()
    if len(a) != len(z):
        raise LadderError("both words must have the same length")
    for w in (a, z):
        if w not in words:
            raise LadderError(f"'{w}' is not in the word list")
    return a, z


def _walk(parent: dict[str, str | None], end: str) -> list[str]:
    out: list[str] = []
    cur: str | None = end
    while cur is not None:
        out.append(cur)
        cur = parent[cur]
    return out[::-1]


def bfs(a: str, z: str, words: set[str]) -> Result | None:
    """Plain breadth-first search from a until z is reached."""
    a, z = check(a, z, words)
    b = buckets(words)
    parent: dict[str, str | None] = {a: None}
    q = deque([a])
    explored = 0
    while q:
        cur = q.popleft()
        explored += 1
        if cur == z:
            return Result(_walk(parent, z), explored)
        for n in neighbours(cur, b):
            if n not in parent:
                parent[n] = cur
                q.append(n)
    return None


def bidirectional(a: str, z: str, words: set[str]) -> Result | None:
    """Search from both ends, always growing the smaller frontier, until they meet."""
    a, z = check(a, z, words)
    if a == z:
        return Result([a], 1)
    b = buckets(words)
    pa: dict[str, str | None] = {a: None}
    pz: dict[str, str | None] = {z: None}
    fa, fz = [a], [z]
    explored = 0
    while fa and fz:
        forward = len(fa) <= len(fz)
        front, mine, other = (fa, pa, pz) if forward else (fz, pz, pa)
        nxt: list[str] = []
        for cur in front:
            explored += 1
            for n in neighbours(cur, b):
                if n in other:  # the two searches touch
                    mine[n] = cur
                    left = _walk(pa, n)
                    right = _walk(pz, n)[::-1]
                    return Result(left + right[1:], explored)
                if n not in mine:
                    mine[n] = cur
                    nxt.append(n)
        if forward:
            fa = nxt
        else:
            fz = nxt
    return None


def valid(path: list[str], words: set[str]) -> bool:
    """Every word is real and each step changes exactly one letter."""
    if not path or any(w not in words for w in path):
        return False
    return all(len(x) == len(y) and sum(p != q for p, q in zip(x, y, strict=True)) == 1
               for x, y in zip(path, path[1:], strict=False))


def examples() -> list[dict[str, str]]:
    return [{"from": "cold", "to": "warm"}, {"from": "cat", "to": "dog"}, {"from": "bake", "to": "mind"},
            {"from": "hit", "to": "sun"}, {"from": "gold", "to": "mint"}]
