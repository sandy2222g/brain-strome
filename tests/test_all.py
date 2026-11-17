import random

import pytest
from fastapi.testclient import TestClient

from namemaker.api import app
from namemaker.core import MakerError, Model, best_order, evaluate, generate, load_names, split

c = TestClient(app)
N = load_names()


def test_data_and_split():
    assert len(N) > 100 and all(n == n.lower() for n in N)
    train, test = split(N)
    assert not set(map(N.index, train)) & set(map(N.index, test)) and len(train) + len(test) == len(N)


def test_probabilities_sum_to_one():
    m = Model(2).fit(N)
    total = sum(m.prob("wi", ch) for ch in m.vocab)
    assert 0.9 < total <= 1.0  # one slot is kept for unseen symbols


def test_context_helps_up_to_a_point():
    scores = {r["order"]: r["bits"] for r in evaluate(N)}
    assert scores[1] < scores[0] and scores[2] < scores[1]  # context beats no context
    assert scores[4] > scores[2]  # too much context overfits a small dataset
    assert best_order(N) == 2


def test_smoothing_keeps_unseen_text_finite():
    m = Model(2).fit(N)
    assert m.bits_per_char(["zzzxqj"]) < 20


def test_sampling_is_reproducible_and_follows_the_prefix():
    m = Model(2).fit(N)
    assert m.sample(random.Random(5)) == m.sample(random.Random(5))
    assert m.sample(random.Random(1), "wil").startswith("wil")


def test_generated_names_are_new_and_well_formed():
    b = generate(N, 2, 20, seed=4)
    assert len(b.names) == 20 and len(set(b.names)) == 20
    known = set(N)
    assert all(n.lower() not in known and 4 <= len(n) <= 14 for n in b.names)
    assert generate(N, 2, 5, seed=4).names == generate(N, 2, 5, seed=4).names


def test_validation():
    for n, prefix in [(0, ""), (51, ""), (5, "toolongprefix"), (5, "a1")]:
        with pytest.raises(MakerError):
            generate(N, 2, n, 0, prefix)
    with pytest.raises(MakerError):
        Model(-1)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    s = c.get("/scores").json()
    assert s["best"] == 2 and len(s["scores"]) == 5
    r = c.get("/generate", params={"n": 5, "seed": 2}).json()
    assert len(r["names"]) == 5 and r["order"] == 2
    assert c.get("/generate", params={"order": 9}).status_code == 422
    assert c.get("/generate", params={"n": 99}).status_code == 422 and c.get("/").status_code == 200
