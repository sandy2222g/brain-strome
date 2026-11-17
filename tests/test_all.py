import random

import pytest
from fastapi.testclient import TestClient

from hashlab.api import app
from hashlab.core import HashError, make, measure, theory

c = TestClient(app)
KINDS = ("chaining", "linear", "double")


@pytest.mark.parametrize("kind", KINDS)
def test_behaves_like_a_set(kind):
    rng = random.Random(4)
    t, ref = make(kind, 101), set()
    for _ in range(80):
        k = rng.randrange(1000)
        t.insert(k)
        ref.add(k)
    assert all(t.contains(k) for k in ref)
    assert not any(t.contains(k) for k in range(1000, 1100))
    assert t.n == len(ref)


def test_duplicate_insert_does_not_grow():
    t = make("linear", 11)
    t.insert(5)
    t.insert(5)
    assert t.n == 1


def test_full_open_table_raises():
    t = make("double", 5)
    for k in range(5):
        t.insert(k)
    with pytest.raises(HashError):
        t.insert(99)
    assert t.contains(3)


def test_theory_formulas():
    assert theory("chaining", 0.5) == 1.5 and theory("double", 0.5) == 2.0
    assert theory("linear", 0.5) == pytest.approx(2.5)  # 0.5 * (1 + 1/0.25) = 2.5
    assert theory("linear", 0.9) > 50 > theory("double", 0.9) == pytest.approx(10)


def test_measurements_agree_with_theory():
    for kind in KINDS:
        for a in (0.5, 0.8):
            m, th = measure(kind, a, 1009, 12), theory(kind, a)
            assert abs(m - th) / th < 0.2, (kind, a, m, th)


def test_linear_probing_degrades_much_faster_than_double_hashing():
    lin, dbl = measure("linear", 0.9, 1009, 8), measure("double", 0.9, 1009, 8)
    assert lin > 3 * dbl


def test_validation():
    for bad in (("nope", 11), ("linear", 2)):
        with pytest.raises(HashError):
            make(*bad)
    with pytest.raises(HashError):
        measure("linear", 1.0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/curves").json()
    assert j["loads"][0] == 0.1 and set(j["curves"]) == set(KINDS) and c.get("/").status_code == 200
