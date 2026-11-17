"""Exact pick-k-of-n odds (hypergeometric), expected value, and a seeded long-run simulation."""

from __future__ import annotations

import json
import math
import random
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path

GAMES = Path(__file__).resolve().parents[2] / "data" / "games.json"
MAX_DRAWS = 2_000_000


class OddsError(ValueError):
    """Invalid input."""


@dataclass(frozen=True)
class Game:
    name: str
    n: int
    k: int
    price: float
    prizes: dict[int, float]

    def __post_init__(self) -> None:
        if not 1 <= self.k < self.n <= 100 or self.price <= 0:
            raise OddsError("need 1 <= k < n <= 100 and a positive price")
        if any(not 1 <= m <= self.k or p < 0 for m, p in self.prizes.items()):
            raise OddsError("prize tiers must be within 1..k matches and non-negative")


def load_games(path: Path = GAMES) -> list[Game]:
    return [Game(g["name"], g["n"], g["k"], g["price"], {int(m): p for m, p in g["prizes"].items()})
            for g in json.loads(path.read_text())]


def p_matches(game: Game, m: int) -> float:
    """P(exactly m of your k numbers are among the k drawn out of n)."""
    return math.comb(game.k, m) * math.comb(game.n - game.k, game.k - m) / math.comb(game.n, game.k)


def tiers(game: Game) -> list[dict[str, float]]:
    return [{"matches": m, "prize": game.prizes.get(m, 0.0), "p": p_matches(game, m),
             "one_in": 1 / p_matches(game, m)} for m in range(game.k, -1, -1)]


def expected_value(game: Game) -> dict[str, float]:
    ret = sum(p_matches(game, m) * pr for m, pr in game.prizes.items())
    return {"return_per_ticket": ret, "net_per_ticket": ret - game.price, "payout_rate": ret / game.price,
            "p_any_prize": sum(p_matches(game, m) for m, pr in game.prizes.items() if pr > 0)}


def simulate(game: Game, tickets: int, trials: int = 1000, seed: int = 11) -> dict[str, object]:
    """Each trial buys `tickets` tickets; reports the spread of net winnings across trials."""
    if tickets < 1 or trials < 1 or tickets * trials > MAX_DRAWS:
        raise OddsError(f"tickets and trials must be positive with tickets x trials <= {MAX_DRAWS}")
    levels = list(range(game.k + 1))
    cdf: list[float] = []
    acc = 0.0
    for m in levels:
        acc += p_matches(game, m)
        cdf.append(acc)
    cdf[-1] = 1.0
    rng = random.Random(seed)
    nets: list[float] = []
    top = 0
    for _ in range(trials):
        won = 0.0
        for _ in range(tickets):
            m = levels[bisect_left(cdf, rng.random())]
            won += game.prizes.get(m, 0.0)
            top += m == game.k
        nets.append(won - tickets * game.price)
    nets.sort()
    q = lambda f: nets[min(trials - 1, int(f * trials))]  # noqa: E731
    return {"tickets": tickets, "trials": trials, "spent": round(tickets * game.price, 2),
            "mean_net": round(sum(nets) / trials, 2), "median_net": round(q(0.5), 2),
            "worst": round(nets[0], 2), "p10": round(q(0.1), 2), "p90": round(q(0.9), 2), "best": round(nets[-1], 2),
            "share_ahead": round(sum(n > 0 for n in nets) / trials, 3), "jackpots": top,
            "expected_net": round(tickets * expected_value(game)["net_per_ticket"], 2),
            "hist": histogram(nets)}


def histogram(nets: list[float], bins: int = 12) -> list[dict[str, float]]:
    lo, hi = nets[0], nets[-1]
    width = (hi - lo) / bins or 1.0
    counts = [0] * bins
    for n in nets:
        counts[min(bins - 1, int((n - lo) / width))] += 1
    return [{"from": round(lo + i * width, 2), "to": round(lo + (i + 1) * width, 2), "count": c}
            for i, c in enumerate(counts)]


def raffle(tickets_sold: int, mine: int, prize: float, price: float) -> dict[str, float]:
    if not 0 < mine <= tickets_sold or prize < 0 or price < 0:
        raise OddsError("need 0 < mine <= tickets_sold and non-negative money")
    p = mine / tickets_sold
    return {"p_win": p, "expected_prize": p * prize, "cost": mine * price, "net": p * prize - mine * price,
            "break_even_prize": mine * price / p}


def analyse(index: int, tickets: int) -> dict[str, object]:
    games = load_games()
    if not 0 <= index < len(games):
        raise OddsError("unknown game")
    g = games[index]
    return {"name": g.name, "n": g.n, "k": g.k, "price": g.price, "tiers": tiers(g), "ev": expected_value(g),
            "sim": simulate(g, tickets, min(1000, MAX_DRAWS // tickets))}
