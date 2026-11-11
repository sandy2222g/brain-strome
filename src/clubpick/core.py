"""Rank-aggregation voting: plurality, Borda and the Schulze (Condorcet-consistent) method."""

from __future__ import annotations


class VoteError(ValueError):
    """Invalid ballots."""


def check(books: list[str], ballots: list[list[str]]) -> None:
    if len(books) < 2 or len(set(books)) != len(books):
        raise VoteError("need at least 2 distinct books")
    if not ballots:
        raise VoteError("need at least one ballot")
    for b in ballots:
        if sorted(b) != sorted(books):
            raise VoteError("every ballot must rank every book exactly once")


def plurality(books: list[str], ballots: list[list[str]]) -> dict[str, int]:
    check(books, ballots)
    t = dict.fromkeys(books, 0)
    for b in ballots:
        t[b[0]] += 1
    return t


def borda(books: list[str], ballots: list[list[str]]) -> dict[str, int]:
    check(books, ballots)
    n = len(books)
    t = dict.fromkeys(books, 0)
    for b in ballots:
        for i, x in enumerate(b):
            t[x] += n - 1 - i
    return t


def pairwise(books: list[str], ballots: list[list[str]]) -> dict[tuple[str, str], int]:
    """d[(a, b)] = number of voters who rank a above b."""
    check(books, ballots)
    d = {(a, b): 0 for a in books for b in books if a != b}
    for bal in ballots:
        pos = {x: i for i, x in enumerate(bal)}
        for a in books:
            for b in books:
                if a != b and pos[a] < pos[b]:
                    d[(a, b)] += 1
    return d


def schulze(books: list[str], ballots: list[list[str]]) -> tuple[list[str], dict[tuple[str, str], int]]:
    """Schulze ranking: strongest-path strengths via Floyd-Warshall; ties broken by Borda then name."""
    d = pairwise(books, ballots)
    p = {k: (v if v > d[(k[1], k[0])] else 0) for k, v in d.items()}
    for i in books:
        for j in books:
            if i == j:
                continue
            for k in books:
                if i != k and j != k:
                    p[(j, k)] = max(p[(j, k)], min(p[(j, i)], p[(i, k)]))
    wins = {a: sum(1 for b in books if a != b and p[(a, b)] > p[(b, a)]) for a in books}
    bd = borda(books, ballots)
    order = sorted(books, key=lambda a: (-wins[a], -bd[a], a))
    return order, p


def condorcet_winner(books: list[str], ballots: list[list[str]]) -> str | None:
    d = pairwise(books, ballots)
    for a in books:
        if all(d[(a, b)] > d[(b, a)] for b in books if b != a):
            return a
    return None


def tally(books: list[str], ballots: list[list[str]]) -> dict[str, object]:
    order, _ = schulze(books, ballots)
    return {
        "winner": order[0],
        "schulze_order": order,
        "plurality": plurality(books, ballots),
        "borda": borda(books, ballots),
        "condorcet_winner": condorcet_winner(books, ballots),
        "plurality_winner": max(plurality(books, ballots).items(), key=lambda kv: (kv[1], kv[0]))[0],
    }
