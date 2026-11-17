import pytest
from fastapi.testclient import TestClient

from gdlab.api import app
from gdlab.core import GDError, closed_form, descend, experiment, make_data, mse

c = TestClient(app)
XS, YS = make_data()
W0, B0 = closed_form(XS, YS)


def test_data_and_closed_form_recover_the_hidden_line():
    assert len(XS) == len(YS) == 120 and make_data() == (XS, YS)
    assert W0 == pytest.approx(0.85, abs=0.1) and B0 == pytest.approx(1.5, abs=0.4)
    assert mse(XS, YS, W0, B0) < mse(XS, YS, W0 + 0.05, B0) and mse(XS, YS, W0, B0) < mse(XS, YS, W0, B0 + 0.2)


def test_closed_form_exact_on_a_perfect_line():
    w, b = closed_form([1.0, 2.0, 3.0], [3.0, 5.0, 7.0])
    assert (round(w, 9), round(b, 9)) == (2.0, 1.0)
    with pytest.raises(GDError):
        closed_form([2.0, 2.0], [1.0, 3.0])


def test_scaled_descent_reaches_the_exact_answer():
    r = descend(XS, YS, 0.1, 400, scale=True)
    assert not r.diverged and r.w == pytest.approx(W0, abs=1e-3) and r.b == pytest.approx(B0, abs=1e-2)


def test_loss_never_rises_with_a_safe_learning_rate():
    r = descend(XS, YS, 0.1, 200, scale=True)
    assert all(b <= a + 1e-12 for a, b in zip(r.losses, r.losses[1:], strict=False))


def test_too_large_a_rate_diverges():
    assert descend(XS, YS, 1.2, 400, scale=True).diverged
    assert descend(XS, YS, 0.03, 400, scale=False).diverged  # fine for scaled data, explosive for raw kilometres


def test_scaling_makes_it_faster_and_allows_bigger_steps():
    fast = descend(XS, YS, 0.1, 400, scale=True)
    slow = descend(XS, YS, 0.01, 400, scale=False)
    assert fast.steps_to_1pct is not None and fast.steps_to_1pct < 40
    assert slow.steps_to_1pct is None  # still not within 1% after 400 steps


def test_tiny_rate_is_stable_but_slow():
    r = descend(XS, YS, 0.0005, 400, scale=True)
    assert not r.diverged and r.losses[-1] > 10 * mse(XS, YS, W0, B0)


def test_experiment_table_shape_and_validation():
    rows = experiment(XS, YS, [0.01, 0.1])
    assert len(rows) == 4 and {r["scaled"] for r in rows} == {False, True}
    for bad in [(0, 100), (-1, 100), (0.1, 0), (0.1, 9999)]:
        with pytest.raises(GDError):
            descend(XS, YS, *bad)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    d = c.get("/data").json()
    assert len(d["x"]) == 120 and abs(d["best"]["w"] - 0.85) < 0.1
    r = c.get("/descend", params={"lr": 0.1, "scale": True}).json()
    assert not r["diverged"] and abs(r["w"] - d["best"]["w"]) < 1e-3 and r["steps_to_1pct"] < 40
    assert c.get("/descend", params={"lr": 1.2, "scale": True}).json()["diverged"]
    assert c.get("/descend", params={"lr": -1}).status_code == 422
    assert len(c.get("/experiment").json()["rows"]) == 14 and c.get("/").status_code == 200
