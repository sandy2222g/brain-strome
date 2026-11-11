"""Sudoku: parse, solve (MRV backtracking), count solutions, generate, rate and give logical hints.

A grid is a string of 81 characters, digits 1-9 and '0' or '.' for blanks, row by row.
Difficulty is the weakest technique that finishes the puzzle without guessing:
  easy   - naked singles only
  medium - needs hidden singles too
  hard   - needs guessing (backtracking)
"""

from __future__ import annotations

import random
from dataclasses import dataclass

ALL = 0b111111111
UNITS: list[list[int]] = (
    [[r * 9 + c for c in range(9)] for r in range(9)]
    + [[r * 9 + c for r in range(9)] for c in range(9)]
    + [[(br * 3 + r) * 9 + bc * 3 + c for r in range(3) for c in range(3)] for br in range(3) for bc in range(3)]
)
PEERS: list[set[int]] = [{p for u in UNITS if i in u for p in u if p != i} for i in range(81)]
UNIT_NAMES = (
    [f"row {i + 1}" for i in range(9)] + [f"column {i + 1}" for i in range(9)] + [f"box {i + 1}" for i in range(9)]
)


class SudokuError(ValueError):
    """Invalid grid."""


def parse(text: str) -> list[int]:
    s = text.replace(".", "0").replace("\n", "").replace(" ", "")
    if len(s) != 81 or not s.isdigit():
        raise SudokuError("a grid is 81 digits (0 or . for blanks)")
    g = [int(ch) for ch in s]
    if not consistent(g):
        raise SudokuError("the grid breaks the rules: a digit repeats in a row, column or box")
    return g


def fmt(g: list[int]) -> str:
    return "".join(str(v) for v in g)


def consistent(g: list[int]) -> bool:
    return all(len({g[i] for i in u if g[i]}) == sum(1 for i in u if g[i]) for u in UNITS)


def candidates(g: list[int]) -> list[int]:
    """Bitmask of allowed digits for each cell (0 for filled cells)."""
    out = []
    for i, v in enumerate(g):
        if v:
            out.append(0)
        else:
            used = 0
            for p in PEERS[i]:
                if g[p]:
                    used |= 1 << (g[p] - 1)
            out.append(ALL & ~used)
    return out


def solve(g: list[int], rng: random.Random | None = None) -> list[int] | None:
    """Backtracking with minimum-remaining-values; returns a solution or None."""
    cand = candidates(g)
    best, best_n = -1, 10
    for i, v in enumerate(g):
        if not v:
            n = bin(cand[i]).count("1")
            if n == 0:
                return None
            if n < best_n:
                best, best_n = i, n
    if best < 0:
        return g[:]
    digits = [d for d in range(1, 10) if cand[best] >> (d - 1) & 1]
    if rng:
        rng.shuffle(digits)
    for d in digits:
        g[best] = d
        sol = solve(g, rng)
        if sol is not None:
            g[best] = 0
            return sol
    g[best] = 0
    return None


def count_solutions(g: list[int], limit: int = 2) -> int:
    cand = candidates(g)
    best, best_n = -1, 10
    for i, v in enumerate(g):
        if not v:
            n = bin(cand[i]).count("1")
            if n == 0:
                return 0
            if n < best_n:
                best, best_n = i, n
    if best < 0:
        return 1
    total = 0
    for d in range(1, 10):
        if cand[best] >> (d - 1) & 1:
            g[best] = d
            total += count_solutions(g, limit - total)
            g[best] = 0
            if total >= limit:
                break
    return total


@dataclass(frozen=True)
class Hint:
    cell: int
    digit: int
    technique: str
    reason: str


def cell_name(i: int) -> str:
    return f"row {i // 9 + 1}, column {i % 9 + 1}"


def find_hint(g: list[int]) -> Hint | None:
    """Next logical move: a naked single, else a hidden single. None means a guess is needed."""
    cand = candidates(g)
    for i, v in enumerate(g):
        if not v and bin(cand[i]).count("1") == 1:
            d = cand[i].bit_length()
            return Hint(
                i,
                d,
                "naked single",
                f"{cell_name(i)} can only be {d}: every other digit already appears in its row, column or box",
            )
    for u, name in zip(UNITS, UNIT_NAMES, strict=True):
        for d in range(1, 10):
            spots = [i for i in u if not g[i] and cand[i] >> (d - 1) & 1]
            if len(spots) == 1 and d not in {g[i] for i in u}:
                return Hint(
                    spots[0], d, "hidden single", f"in {name}, {d} fits in only one cell: {cell_name(spots[0])}"
                )
    return None


def rate(g: list[int]) -> str:
    """Easy / medium / hard by the weakest technique that solves the puzzle (see module docstring)."""
    work, used_hidden = g[:], False
    while 0 in work:
        h = find_hint(work)
        if h is None:
            return "hard"
        used_hidden = used_hidden or h.technique == "hidden single"
        work[h.cell] = h.digit
    return "medium" if used_hidden else "easy"


def full_grid(rng: random.Random) -> list[int]:
    sol = solve([0] * 81, rng)
    assert sol is not None
    return sol


def generate(seed: int, clues: int = 32) -> list[int]:
    """Remove digits from a random solved grid while the solution stays unique, until `clues` remain."""
    if not 17 <= clues <= 81:
        raise SudokuError("clues must be between 17 and 81")
    rng = random.Random(seed)
    g = full_grid(rng)
    order = list(range(81))
    rng.shuffle(order)
    left = 81
    for i in order:
        if left <= clues:
            break
        keep = g[i]
        g[i] = 0
        if count_solutions(g[:], 2) != 1:
            g[i] = keep
        else:
            left -= 1
    return g
