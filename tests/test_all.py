import itertools
import random

import pytest
from fastapi.testclient import TestClient

from potluck.api import app
from potluck.core import PotluckError, first_come, load, match

D = load()
G, N = D["guests"], D["needs"]
c = TestClient(app)


def brute(guests, needs):
    slots = [cat for cat in sorted(needs) for _ in range(needs[cat])]
    n = max(len(guests), len(slots))
    best = 0
    for perm in itertools.permutations(range(n)):
        ok = sum(
            1 for gi, si in enumerate(perm) if gi < len(guests) and si < len(slots) and slots[si] in guests[gi]["can"]
        )
        best = max(best, ok)
    return best


def test_sample_fills_every_slot():
    r = match(G, N)
    assert r["filled"] == r["slots"] == 7 and r["missing"] == [] and r["unassigned_guests"] == []


def test_first_come_leaves_a_gap():
    r = first_come(G, N)
    assert r["filled"] == 6 and r["missing"] == ["Bread#1"] and r["unassigned_guests"] == ["Gia"]


def test_everyone_brings_something_they_offered():
    r = match(G, N)
    can = {g["name"]: g["can"] for g in G}
    for cat, names in r["assignment"].items():
        for n in names:
            assert cat in can[n]


def test_no_guest_used_twice():
    r = match(G, N)
    names = [n for lst in r["assignment"].values() for n in lst if n]
    assert len(names) == len(set(names))


def test_random_cases_match_brute_force():
    rng = random.Random(3)
    cats = ["A", "B", "C"]
    for _ in range(40):
        needs = {c_: rng.randint(1, 2) for c_ in cats}
        guests = [
            {"name": f"g{i}", "can": rng.sample(cats, rng.randint(1, 3))} for i in range(rng.randint(2, 6))
        ]
        assert match(guests, needs)["filled"] == brute(guests, needs)


def test_more_slots_than_guests_reports_missing():
    r = match([{"name": "solo", "can": ["Main"]}], {"Main": 2})
    assert r["filled"] == 1 and r["missing"] == ["Main#2"]


def test_validation():
    with pytest.raises(PotluckError):
        match([], N)
    with pytest.raises(PotluckError):
        match(G, {})
    with pytest.raises(PotluckError):
        match([{"name": "a", "can": ["Cake"]}], N)
    with pytest.raises(PotluckError):
        match([{"name": "a", "can": ["Main"]}, {"name": "a", "can": ["Main"]}], N)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/match", json={"needs": N, "guests": G}).json()
    assert r["best"]["filled"] == 7 and r["first_come"]["filled"] == 6
    assert c.get("/").status_code == 200
    assert c.post("/match", json={"needs": N, "guests": []}).status_code == 422
