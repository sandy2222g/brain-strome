import random

import pytest
from fastapi.testclient import TestClient

from sudokucoach.api import app
from sudokucoach.core import (
    SudokuError,
    consistent,
    count_solutions,
    find_hint,
    fmt,
    full_grid,
    generate,
    parse,
    rate,
    solve,
)

c = TestClient(app)
KNOWN = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"  # classic example


def test_parse_accepts_dots_and_rejects_bad_input():
    assert parse(KNOWN.replace("0", ".")) == parse(KNOWN)
    with pytest.raises(SudokuError):
        parse("123")
    with pytest.raises(SudokuError):
        parse("55" + "0" * 79)  # two fives in one row


def test_solver_solves_the_classic_example_correctly():
    sol = solve(parse(KNOWN))
    assert sol is not None and 0 not in sol and consistent(sol)
    assert fmt(sol).startswith("534678912672195348198342567")
    assert all(a == b for a, b in zip(parse(KNOWN), sol, strict=True) if a)


def test_unsolvable_grid_is_detected():
    g = parse("0" * 81)
    g[0:8] = [1, 2, 3, 4, 5, 6, 7, 8]
    g[17] = 9  # row 1 needs a 9 in column 9 but column 9 already has it in row 2
    assert solve(g) is None and count_solutions(g[:]) == 0


def test_empty_grid_has_many_solutions_capped_at_limit():
    assert count_solutions([0] * 81, limit=2) == 2


def test_full_grids_are_valid_and_random():
    a, b = full_grid(random.Random(1)), full_grid(random.Random(2))
    assert consistent(a) and 0 not in a and a != b


def test_generated_puzzles_are_unique_and_have_requested_clues():
    for seed in range(5):
        g = generate(seed, 34)
        assert 81 - g.count(0) == 34 and count_solutions(g[:]) == 1


def test_generation_is_deterministic():
    assert generate(7, 36) == generate(7, 36)


def test_generate_rejects_impossible_clue_counts():
    with pytest.raises(SudokuError):
        generate(1, 10)


def test_hint_move_is_always_correct():
    for seed in range(8):
        g = generate(seed, 36)
        sol = solve(g[:])
        h = find_hint(g)
        if h:
            assert sol[h.cell] == h.digit and g[h.cell] == 0


def test_hints_alone_finish_easy_puzzles_and_stall_on_hard_ones():
    easy = generate(0, 45)
    assert rate(easy) == "easy"
    work = easy[:]
    while 0 in work:
        h = find_hint(work)
        assert h is not None
        work[h.cell] = h.digit
    assert consistent(work)
    hard = next(generate(s, 30) for s in range(40) if rate(generate(s, 30)) == "hard")
    work = hard[:]
    while (h := find_hint(work)) is not None:
        work[h.cell] = h.digit
    assert 0 in work  # logical hints stall with blanks left: a guess is needed


def test_ratings_are_ordered_by_technique_needed():
    ratings = {rate(generate(s, 30)) for s in range(25)}
    assert {"medium", "hard"} <= ratings


def test_api_flow():
    p = c.get("/puzzle", params={"seed": 3, "clues": 36}).json()
    assert p["clues"] == 36 and p["difficulty"] in {"easy", "medium", "hard"}
    s = c.post("/solve", json={"grid": p["grid"]}).json()
    assert s["solvable"] and s["unique"] and "0" not in s["solution"]
    h = c.post("/hint", json={"grid": p["grid"]}).json()
    if h["hint"]:
        assert s["solution"][h["hint"]["cell"]] == str(h["hint"]["digit"])
    assert c.post("/check", json={"grid": s["solution"]}).json()["complete"] is True
    assert c.post("/hint", json={"grid": s["solution"]}).json()["done"] is True
    assert c.get("/").status_code == 200 and c.get("/health").json() == {"status": "ok"}


def test_api_validation():
    assert c.post("/solve", json={"grid": "1" * 81}).status_code == 422
    assert c.post("/hint", json={"grid": "short"}).status_code == 422
    assert c.get("/puzzle", params={"clues": 5}).status_code == 422
