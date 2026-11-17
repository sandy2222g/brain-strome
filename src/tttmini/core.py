"""Tic-tac-toe with minimax and alpha-beta pruning. Board is a 9-character string of 'X', 'O' and '.'."""
from __future__ import annotations

from functools import cache

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


class GameError(ValueError):
    """Raised for invalid boards or moves."""


def winner(b: str) -> str | None:
    for x, y, z in LINES:
        if b[x] != "." and b[x] == b[y] == b[z]:
            return b[x]
    return None


def turn(b: str) -> str:
    return "X" if b.count("X") == b.count("O") else "O"


def validate(b: str) -> None:
    if len(b) != 9 or set(b) - set("XO."):
        raise GameError("board must be 9 characters of X, O or .")
    if not 0 <= b.count("X") - b.count("O") <= 1:
        raise GameError("impossible board: X moves first and players alternate")


def moves(b: str) -> list[int]:
    return [i for i, c in enumerate(b) if c == "."]


def play(b: str, i: int) -> str:
    if i not in moves(b) or winner(b) is not None:
        raise GameError("illegal move")
    p = turn(b)
    return b[:i] + p + b[i + 1:]


def minimax(b: str, counter: list[int] | None = None) -> int:
    """Value for X: +1 X wins, 0 draw, -1 O wins, under perfect play. Plain search, no pruning."""
    if counter is not None:
        counter[0] += 1
    w = winner(b)
    if w:
        return 1 if w == "X" else -1
    ms = moves(b)
    if not ms:
        return 0
    vals = [minimax(play(b, m), counter) for m in ms]
    return max(vals) if turn(b) == "X" else min(vals)


def alphabeta(b: str, alpha: int = -2, beta: int = 2, counter: list[int] | None = None) -> int:
    if counter is not None:
        counter[0] += 1
    w = winner(b)
    if w:
        return 1 if w == "X" else -1
    ms = moves(b)
    if not ms:
        return 0
    if turn(b) == "X":
        best = -2
        for m in ms:
            best = max(best, alphabeta(play(b, m), alpha, beta, counter))
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best
    best = 2
    for m in ms:
        best = min(best, alphabeta(play(b, m), alpha, beta, counter))
        beta = min(beta, best)
        if alpha >= beta:
            break
    return best


@cache
def value(b: str) -> int:
    return minimax(b)


def best_move(b: str) -> int:
    """Best square; ties go to the lowest index. Prefers faster wins and slower losses via depth-aware scoring."""
    validate(b)
    if winner(b) or not moves(b):
        raise GameError("game is over")
    sign = 1 if turn(b) == "X" else -1

    def score(m: int) -> tuple[int, int]:
        nb = play(b, m)
        v = value(nb) * sign
        # among equal outcomes: win sooner (more empties left is better), lose later (fewer is better)
        return (v, len(moves(nb)) * v)

    return max(moves(b), key=lambda m: (score(m), -m))


def count_nodes(b: str = ".........") -> dict[str, int]:
    plain, pruned = [0], [0]
    v1 = minimax(b, plain)
    v2 = alphabeta(b, counter=pruned)
    if v1 != v2:
        raise GameError("pruning changed the answer")
    return {"value": v1, "plain": plain[0], "pruned": pruned[0]}


def reachable_games() -> dict[str, int]:
    """Count every distinct board reachable in legal play, and every complete game."""
    seen = {"........."}
    games = 0

    def walk(b: str) -> None:
        nonlocal games
        seen.add(b)
        if winner(b) or not moves(b):
            games += 1
            return
        for m in moves(b):
            walk(play(b, m))
    walk(".........")
    return {"positions": len(seen), "games": games}
