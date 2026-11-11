import json
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clubpick.api import app
from clubpick.core import VoteError, borda, condorcet_winner, pairwise, plurality, schulze, tally

S = json.loads(Path("data/ballots.json").read_text())
BOOKS = S["books"]
BALLOTS = [b["ranking"] for b in S["ballots"]]
c = TestClient(app)


def test_plurality_counts_first_choices():
    assert sum(plurality(BOOKS, BALLOTS).values()) == len(BALLOTS)


def test_borda_total_is_fixed():
    n = len(BOOKS)
    assert sum(borda(BOOKS, BALLOTS).values()) == len(BALLOTS) * n * (n - 1) // 2


def test_pairwise_is_complementary():
    d = pairwise(BOOKS, BALLOTS)
    assert all(d[(a, b)] + d[(b, a)] == len(BALLOTS) for (a, b) in d)


def test_schulze_picks_condorcet_winner_when_it_exists():
    rng = random.Random(2)
    books = list("abcd")
    for _ in range(100):
        ballots = [rng.sample(books, 4) for _ in range(rng.randint(3, 9))]
        cw = condorcet_winner(books, ballots)
        if cw:
            assert schulze(books, ballots)[0][0] == cw


def test_condorcet_cycle_still_resolves():
    books = ["a", "b", "c"]
    ballots = [["a", "b", "c"], ["b", "c", "a"], ["c", "a", "b"]]
    assert condorcet_winner(books, ballots) is None
    order, _ = schulze(books, ballots)
    assert sorted(order) == books


def test_unanimous_ballots():
    books = ["a", "b", "c"]
    assert schulze(books, [["b", "a", "c"]] * 3)[0] == ["b", "a", "c"]


def test_sample_plurality_and_schulze_can_disagree():
    t = tally(BOOKS, BALLOTS)
    assert t["winner"] == t["condorcet_winner"] == "A Map of Small Rooms"
    assert t["plurality_winner"] == "The Quiet Orchard"


def test_order_independent_of_ballot_order():
    shuffled = BALLOTS[:]
    random.Random(1).shuffle(shuffled)
    assert schulze(BOOKS, shuffled)[0] == schulze(BOOKS, BALLOTS)[0]


def test_validation():
    with pytest.raises(VoteError):
        tally(["a"], [["a"]])
    with pytest.raises(VoteError):
        tally(["a", "b"], [])
    with pytest.raises(VoteError):
        tally(["a", "b"], [["a", "a"]])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/tally", json={"books": BOOKS, "ballots": S["ballots"]}).json()
    assert r["winner"] in BOOKS
    assert c.get("/").status_code == 200


def test_api_errors():
    bad = {"books": ["a", "b"], "ballots": [{"voter": "x", "ranking": ["a", "a"]}]}
    assert c.post("/tally", json=bad).status_code == 422
