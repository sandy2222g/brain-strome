import itertools
import random

import pytest
from fastapi.testclient import TestClient

from couponstack.api import app
from couponstack.core import CouponError, best, best_single_percent, cents, compare, load, total_with, valid

D = load()
S, SH, CP = D["subtotal"], D["shipping"], D["coupons"]
c = TestClient(app)


def cp(code, kind, value, min_spend=0, group=None, max_off=None):
    return {
        "code": code, "kind": kind, "value": value, "min_spend": min_spend, "group": group or code, "max_off": max_off,
    }


def test_sample_by_hand():
    r = best(S, SH, CP)
    # 120 -> -24 (20%, capped at 25) = 96 -> -14.40 = 81.60 -> -6.53 (8%) = 75.07 -> -5 = 70.07, shipping free
    assert r["total"] == 70.07 and r["saved"] == 57.93
    assert set(r["coupons"]) == {"SAVE20", "WELCOME15", "LOYAL8", "FIVEOFF", "FREESHIP"}


def test_one_coupon_per_group_and_min_spend_respected():
    r = best(S, SH, CP)
    assert "TENOFF75" not in r["coupons"]  # shares group "site" with SAVE20, which is worth more
    assert "BIGSPEND" not in r["coupons"]  # needs 200 spend
    rich = [c_ for c_ in CP if c_["code"] in {"SAVE20", "TENOFF75"}]
    assert not valid(tuple(rich), cents(S))


def test_cap_applies():
    assert total_with(40000, 0, [{**cp("A", "percent", 50, max_off=30), "max_off_c": 3000}])["total_c"] == 37000


def test_no_valid_coupon_means_no_saving():
    r = best(10, 4, [cp("BIG", "fixed", 5, min_spend=50)])
    assert r["coupons"] == [] and r["total"] == 14 and r["saved"] == 0


def test_never_below_zero_and_free_shipping_counts():
    assert best(3, 5, [cp("X", "fixed", 10)])["total"] == 5
    assert best(3, 5, [cp("X", "fixed", 10), cp("S", "shipping", 0)])["total"] == 0


def test_optimal_against_random_valid_combos():
    rng = random.Random(2)
    top = best(S, SH, CP)["total"]
    items = [{**x, "max_off_c": cents(x["max_off"]) if x.get("max_off") else None} for x in CP]
    for _ in range(300):
        combo = tuple(rng.sample(items, rng.randint(1, 4)))
        if valid(combo, cents(S)):
            assert total_with(cents(S), cents(SH), list(combo))["total_c"] / 100 >= top


def test_best_beats_baseline():
    r = compare(S, SH, CP)
    assert r["baseline"]["total"] == 104.0 and r["extra_saved"] == 33.93
    assert best_single_percent(S, SH, [cp("F", "fixed", 5)])["coupons"] == []


def test_validation():
    with pytest.raises(CouponError):
        best(-1, 0, [])
    with pytest.raises(CouponError):
        best(10, 0, [cp("A", "bogus", 1)])
    with pytest.raises(CouponError):
        best(10, 0, [cp("A", "percent", 150)])
    with pytest.raises(CouponError):
        best(10, 0, [cp("A", "fixed", 1), cp("A", "fixed", 2)])
    with pytest.raises(CouponError):
        best(10, 0, [cp(f"C{i}", "fixed", 1) for i in range(15)])
    assert len(list(itertools.combinations(range(14), 7))) > 3000


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/choose", json={"subtotal": S, "shipping": SH, "coupons": CP}).json()
    assert r["best"]["total"] == 70.07
    assert c.get("/").status_code == 200
    assert c.post("/choose", json={"subtotal": -5, "shipping": 0, "coupons": []}).status_code == 422
