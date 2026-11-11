import pytest
from fastapi.testclient import TestClient

from capsule.api import app
from capsule.core import (
    CapsuleError,
    Garment,
    best_capsule,
    lightest_first,
    load,
    outfits,
    pack_in_order,
    validate,
    weight,
)

LIMIT, ITEMS = load()
ORDER = pack_in_order(LIMIT, ITEMS)
LIGHT = lightest_first(LIMIT, ITEMS)
BEST = best_capsule(LIMIT, ITEMS)
c = TestClient(app)


def test_outfit_counting_by_hand():
    tee = Garment("tee", "top", "neutral", 100)
    jeans = Garment("jeans", "bottom", "neutral", 100)
    shoes = Garment("shoes", "shoes", "neutral", 100)
    # neutral pieces work in both styles: (1*1*1) smart + (1*1*1) casual
    assert outfits([tee, jeans, shoes]) == 2
    coat = Garment("coat", "layer", "neutral", 100)
    assert outfits([tee, jeans, shoes, coat]) == 4  # layer doubles each style's outfits
    assert outfits([tee, jeans]) == 0  # no shoes, no outfit


def test_every_method_respects_the_weight_limit_and_uses_real_items():
    names = {i.name for i in ITEMS}
    for chosen in (ORDER, LIGHT, BEST):
        assert weight(chosen) <= LIMIT and {g.name for g in chosen} <= names


def test_best_beats_both_baselines_on_the_sample():
    assert (outfits(ORDER), outfits(LIGHT), outfits(BEST)) == (0, 12, 24)


def test_best_is_optimal_against_random_subsets():
    import random

    r = random.Random(0)
    for _ in range(300):
        pick = [g for g in ITEMS if r.random() < 0.5]
        if weight(pick) <= LIMIT:
            assert outfits(pick) <= outfits(BEST)


def test_a_bigger_limit_never_reduces_the_best_count():
    assert outfits(best_capsule(LIMIT + 800, ITEMS)) >= outfits(BEST)


def test_validation():
    with pytest.raises(CapsuleError):
        validate(0, ITEMS)
    with pytest.raises(CapsuleError):
        validate(1000, [])
    with pytest.raises(CapsuleError):
        validate(1000, [Garment("x", "hat", "smart", 10)])
    with pytest.raises(CapsuleError):
        validate(1000, [Garment("x", "top", "smart", 10), Garment("x", "top", "smart", 10)])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/capsule", json={"limit_g": body["limit_g"], "items": body["items"]}).json()
    assert r["best"]["outfits"] == 24 and r["in_order"]["outfits"] == 0 and r["best"]["grams"] <= LIMIT
    assert c.get("/").status_code == 200


def test_api_validation():
    bad = {"limit_g": 1000, "items": [{"name": "x", "kind": "hat", "style": "smart", "g": 10}]}
    assert c.post("/capsule", json=bad).status_code == 422
