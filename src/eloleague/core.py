"""Elo ratings from match results, compared with a plain win-rate ranking."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
START, K = 1000.0, 24.0
Match = tuple[str, str]  # (winner, loser)


class LeagueError(ValueError):
    """Invalid input."""


def load_matches(path: Path = DATA / "matches.csv") -> list[Match]:
    with path.open() as fh:
        return [(r["winner"], r["loser"]) for r in csv.DictReader(fh)]


def load_truth(path: Path = DATA / "truth.json") -> dict[str, float]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def expected(ra: float, rb: float) -> float:
    """Probability that a player rated ra beats one rated rb."""
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400))


def rate(matches: list[Match], k: float = K) -> tuple[dict[str, float], dict[str, list[float]]]:
    """Process matches in order; returns final ratings and each player's rating history."""
    if not matches:
        raise LeagueError("need at least one match")
    ratings: dict[str, float] = defaultdict(lambda: START)
    history: dict[str, list[float]] = defaultdict(lambda: [START])
    for w, lo in matches:
        if w == lo:
            raise LeagueError("a player cannot play themselves")
        e = expected(ratings[w], ratings[lo])
        ratings[w] += k * (1 - e)
        ratings[lo] -= k * (1 - e)
        history[w].append(ratings[w])
        history[lo].append(ratings[lo])
    return dict(ratings), dict(history)


def win_rates(matches: list[Match]) -> dict[str, float]:
    wins: dict[str, int] = defaultdict(int)
    games: dict[str, int] = defaultdict(int)
    for w, lo in matches:
        wins[w] += 1
        games[w] += 1
        games[lo] += 1
    return {p: wins[p] / games[p] for p in games}


def ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for t in range(i, j + 1):
            out[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(xs: list[float], ys: list[float]) -> float:
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    return cov / (vx * vy) ** 0.5 if vx and vy else 0.0


def evaluate(holdout: int = 60) -> dict[str, object]:
    ms = load_matches()
    truth = load_truth()
    train, test = ms[:-holdout], ms[-holdout:]
    elo, _ = rate(train)
    wr = win_rates(train)
    players = sorted(truth)
    tv = [truth[p] for p in players]
    rho_elo = spearman([elo.get(p, START) for p in players], tv)
    rho_wr = spearman([wr.get(p, 0.5) for p in players], tv)
    elo_ok = wr_ok = 0.0
    brier = 0.0
    for w, lo in test:
        elo_ok += elo.get(w, START) > elo.get(lo, START)
        a, b = wr.get(w, 0.5), wr.get(lo, 0.5)
        wr_ok += 1.0 if a > b else 0.5 if a == b else 0.0
        brier += (1 - expected(elo.get(w, START), elo.get(lo, START))) ** 2
    n = len(test)
    return {"matches": len(ms), "holdout": n, "rank_corr_elo": round(rho_elo, 3), "rank_corr_winrate": round(rho_wr, 3),
            "acc_elo": round(elo_ok / n, 3), "acc_winrate": round(wr_ok / n, 3), "brier_elo": round(brier / n, 3)}


def leaderboard() -> list[dict[str, object]]:
    ms = load_matches()
    elo, hist = rate(ms)
    wr = win_rates(ms)
    games: dict[str, int] = defaultdict(int)
    for w, lo in ms:
        games[w] += 1
        games[lo] += 1
    rows = [{"player": p, "rating": round(r, 1), "win_rate": round(wr[p], 3), "games": games[p],
             "history": [round(h, 1) for h in hist[p]]} for p, r in elo.items()]
    return sorted(rows, key=lambda r: (-r["rating"], r["player"]))  # type: ignore[operator]


def predict(a: str, b: str) -> dict[str, object]:
    elo, _ = rate(load_matches())
    if a not in elo or b not in elo or a == b:
        raise LeagueError("choose two different known players")
    return {"a": a, "b": b, "p_a": round(expected(elo[a], elo[b]), 3), "rating_a": round(elo[a], 1),
            "rating_b": round(elo[b], 1)}
