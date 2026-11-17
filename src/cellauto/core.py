"""Two tiny universes: 256 one-dimensional 'elementary' automata, and Conway's Game of Life."""
from __future__ import annotations

import zlib

Cell = tuple[int, int]

PATTERNS: dict[str, list[Cell]] = {
    "block": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "blinker": [(0, 0), (1, 0), (2, 0)],
    "toad": [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1)],
    "beacon": [(0, 0), (1, 0), (0, 1), (3, 2), (2, 3), (3, 3)],
    "glider": [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)],
    "lwss": [(1, 0), (4, 0), (0, 1), (0, 2), (4, 2), (0, 3), (1, 3), (2, 3), (3, 3)],
    "r-pentomino": [(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)],
}


class AutomataError(ValueError):
    pass


def rule_row(rule: int, row: list[int]) -> list[int]:
    """One step of an elementary automaton on a ring: each cell looks at itself and its two neighbours."""
    n = len(row)
    return [(rule >> (row[(i - 1) % n] * 4 + row[i] * 2 + row[(i + 1) % n])) & 1 for i in range(n)]


def run_rule(rule: int, steps: int, width: int = 101) -> list[list[int]]:
    if not 0 <= rule <= 255 or not 1 <= steps <= 400 or not 3 <= width <= 401 or width % 2 == 0:
        raise AutomataError("rule 0-255, steps 1-400, odd width 3-401")
    row = [0] * width
    row[width // 2] = 1
    rows = [row]
    for _ in range(steps - 1):
        row = rule_row(rule, row)
        rows.append(row)
    return rows


def complexity(rows: list[list[int]]) -> float:
    """How well the picture compresses: near 0 for dull patterns, higher for rich or random ones."""
    data = bytes(v for r in rows for v in r)
    return round(len(zlib.compress(data, 9)) / len(data), 4)


def rule_table(steps: int = 100, width: int = 201) -> list[dict[str, float]]:
    out = []
    for r in range(256):
        rows = run_rule(r, steps, width)
        density = round(sum(map(sum, rows)) / (steps * width), 3)
        out.append({"rule": r, "density": density, "complexity": complexity(rows)})
    return out


def life_step(cells: set[Cell]) -> set[Cell]:
    """Conway's Game of Life on an unbounded grid: live cells survive with 2-3 neighbours, dead ones are born with 3."""
    counts: dict[Cell, int] = {}
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    c = (x + dx, y + dy)
                    counts[c] = counts.get(c, 0) + 1
    return {c for c, n in counts.items() if n == 3 or (n == 2 and c in cells)}


def normalise(cells: set[Cell]) -> frozenset[Cell]:
    if not cells:
        return frozenset()
    mx, my = min(x for x, _ in cells), min(y for _, y in cells)
    return frozenset((x - mx, y - my) for x, y in cells)


def classify(name: str, max_gens: int = 60) -> dict[str, object]:
    """Run a pattern until its shape repeats: still life, oscillator (period) or spaceship (period and move)."""
    if name not in PATTERNS:
        raise AutomataError(f"pattern must be one of {', '.join(PATTERNS)}")
    cells = set(PATTERNS[name])
    seen: dict[frozenset[Cell], tuple[int, tuple[int, int]]] = {}
    for gen in range(max_gens + 1):
        shape = normalise(cells)
        corner = (min(x for x, _ in cells), min(y for _, y in cells)) if cells else (0, 0)
        if shape in seen:
            g0, c0 = seen[shape]
            period, move = gen - g0, (corner[0] - c0[0], corner[1] - c0[1])
            kind = "still life" if period == 1 else ("oscillator" if move == (0, 0) else "spaceship")
            return {"pattern": name, "kind": kind, "period": period, "move": list(move), "population": len(cells)}
        seen[shape] = (gen, corner)
        cells = life_step(cells)
    return {"pattern": name, "kind": "no repeat", "period": None, "move": None, "population": len(cells)}


def life_run(name: str, gens: int) -> list[list[Cell]]:
    if name not in PATTERNS or not 0 <= gens <= 2000:
        raise AutomataError("unknown pattern, or gens outside 0-2000")
    cells = set(PATTERNS[name])
    out = [sorted(cells)]
    for _ in range(gens):
        cells = life_step(cells)
        out.append(sorted(cells))
    return out


def population_curve(name: str, gens: int) -> list[int]:
    return [len(c) for c in life_run(name, gens)]
