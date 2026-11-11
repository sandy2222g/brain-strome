"""Secret Santa draw: a random assignment with no self-gifts, no excluded pairs and no repeats.

Modelled as a bipartite perfect matching (givers to receivers) found with Kuhn's augmenting-path
algorithm over a randomly shuffled adjacency list, so any valid draw is reachable and infeasible
groups are detected instead of looping forever.
"""

from __future__ import annotations

import random


class DrawError(ValueError):
    """The group cannot be drawn under the given rules."""


def allowed(
    names: list[str], exclusions: list[tuple[str, str]], last_year: dict[str, str] | None = None
) -> dict[str, list[str]]:
    if len(names) < 3 or len(set(names)) != len(names):
        raise DrawError("need at least 3 distinct names")
    bad = {frozenset(p) for p in exclusions}
    for p in bad:
        if len(p) != 2 or not p <= set(names):
            raise DrawError("exclusions must pair two different people in the group")
    last = last_year or {}
    return {g: [r for r in names if r != g and frozenset((g, r)) not in bad and last.get(g) != r] for g in names}


def draw(
    names: list[str],
    exclusions: list[tuple[str, str]] | None = None,
    last_year: dict[str, str] | None = None,
    seed: int | None = None,
) -> dict[str, str]:
    """Return {giver: receiver}. Raises DrawError if no valid draw exists."""
    adj = allowed(names, exclusions or [], last_year)
    rng = random.Random(seed)
    order = list(names)
    rng.shuffle(order)
    for g in adj:
        rng.shuffle(adj[g])
    owner: dict[str, str] = {}

    def augment(g: str, seen: set[str]) -> bool:
        for r in adj[g]:
            if r in seen:
                continue
            seen.add(r)
            if r not in owner or augment(owner[r], seen):
                owner[r] = g
                return True
        return False

    for g in order:
        if not augment(g, set()):
            raise DrawError(f"no valid draw exists (stuck on {g}); relax exclusions or last year's pairs")
    return {g: r for r, g in owner.items()}


def is_valid(
    result: dict[str, str],
    names: list[str],
    exclusions: list[tuple[str, str]] | None = None,
    last_year: dict[str, str] | None = None,
) -> bool:
    adj = allowed(names, exclusions or [], last_year)
    return (
        set(result) == set(names)
        and sorted(result.values()) == sorted(names)
        and all(r in adj[g] for g, r in result.items())
    )


def count_draws(
    names: list[str], exclusions: list[tuple[str, str]] | None = None, last_year: dict[str, str] | None = None
) -> int:
    """Number of valid draws (permanent of the allowed matrix) by DP over receiver subsets; n <= 14."""
    if len(names) > 14:
        raise DrawError("counting supports up to 14 people")
    adj = allowed(names, exclusions or [], last_year)
    idx = {n: i for i, n in enumerate(names)}
    ways = {0: 1}
    for g in names:
        nxt: dict[int, int] = {}
        for mask, w in ways.items():
            for r in adj[g]:
                b = 1 << idx[r]
                if not mask & b:
                    nxt[mask | b] = nxt.get(mask | b, 0) + w
        ways = nxt
    return ways.get((1 << len(names)) - 1, 0)
