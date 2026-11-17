import pytest
from fastapi.testclient import TestClient

from tttmini.api import app
from tttmini.core import (
    GameError,
    alphabeta,
    best_move,
    count_nodes,
    minimax,
    play,
    reachable_games,
    turn,
    validate,
    winner,
)

c = TestClient(app)


def test_empty_board_is_a_draw_with_perfect_play():
    assert minimax(".........") == 0


def test_known_game_counts():
    r = reachable_games()
    assert r["games"] == 255168  # well-known number of complete tic-tac-toe games
    assert r["positions"] == 5478  # distinct legal positions including the empty board


def test_alphabeta_always_agrees_with_minimax_but_searches_less():
    n = count_nodes()
    assert n["value"] == 0 and n["plain"] == 549946 and n["pruned"] < n["plain"] / 3
    boards = ["X........", "XO.......", "XOX.O....", "X...O...X"]
    assert all(alphabeta(b) == minimax(b) for b in boards)


def test_takes_a_win_and_blocks_a_loss():
    assert best_move("XX.OO....") == 2  # X wins now rather than blocking
    assert best_move("XX..O....") == 2  # O to move must block the top row


def test_computer_never_loses_against_any_human_strategy():
    # enumerate every possible human reply sequence when the computer plays O
    def humans(b: str) -> bool:
        if winner(b):
            return winner(b) != "X"
        if "." not in b:
            return True
        if turn(b) == "X":
            return all(humans(play(b, m)) for m in [i for i, ch in enumerate(b) if ch == "."])
        return humans(play(b, best_move(b)))

    assert humans(".........")  # the human (X) can never win


def test_computer_as_x_also_never_loses():
    def humans(b: str) -> bool:
        if winner(b):
            return winner(b) != "O"
        if "." not in b:
            return True
        if turn(b) == "O":
            return all(humans(play(b, m)) for m in [i for i, ch in enumerate(b) if ch == "."])
        return humans(play(b, best_move(b)))

    assert humans(".........")


def test_prefers_the_fastest_win():
    # X can win immediately at 2; a slower route also wins, but the immediate one must be chosen
    assert best_move("XX.O.O...") == 2


def test_validation():
    for bad in ["XX.......", "XO", "abcdefghi", "OOO......"]:
        with pytest.raises(GameError):
            validate(bad)
    with pytest.raises(GameError):
        play("X........", 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/move", params={"board": "X........"}).json()
    assert j["move"] == 4 and j["board"] == "X...O...."  # the only non-losing reply to a corner opening
    assert c.get("/move", params={"board": "XXXOO...."}).json()["done"] is True
    assert c.get("/move", params={"board": "OOOOOOOOO"}).status_code == 422
    assert c.get("/stats").json()["plain"] == 549946 and c.get("/").status_code == 200
