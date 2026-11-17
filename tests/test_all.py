import pytest
from fastapi.testclient import TestClient

from gradeneed.api import app
from gradeneed.core import GradeError, analyse, category_average, load, naive_mean

D = load()
CATS, BANDS = D["categories"], D["bands"]
c = TestClient(app)


def cat(name: str, weight: float, scores: list[float], drop: int = 0) -> dict[str, object]:
    return {"name": name, "weight": weight, "drop_lowest": drop, "scores": scores}


def test_drop_lowest():
    assert category_average([95, 88, 40, 92, 90], 1) == 91.25
    assert category_average([70, 85, 55, 90, 60, 80], 2) == 81.25
    assert category_average([50], 3) == 50  # never drops the last score
    assert category_average([], 1) is None


def test_sample_by_hand():
    r = analyse(CATS, BANDS)
    # 91.25*.20 + 81.25*.15 + 78*.25 + 92*.15 = 63.7375
    assert r["points_earned"] == 63.74 and r["weight_done"] == 75
    assert r["needed"]["B"] == {"needed": 65.05, "status": "possible"}
    assert r["needed"]["C"]["needed"] == 25.05


def test_status_flags():
    r = analyse(CATS, BANDS)["needed"]
    assert r["A"]["status"] == "impossible" and r["A"]["needed"] > 100
    assert r["D"] == {"needed": 0, "status": "secured"}


def test_needed_score_really_reaches_the_band():
    r = analyse(CATS, BANDS)
    need = r["needed"]["B"]["needed"]
    final = [*CATS[:4], cat("Final exam", 25, [need])]
    assert analyse(final, BANDS)["points_earned"] == pytest.approx(80, abs=0.01)


def test_everything_graded():
    cats = [cat("a", 60, [90]), cat("b", 40, [70])]
    r = analyse(cats, {"A": 90, "B": 80})
    assert r["needed"]["A"] == {"needed": None, "status": "missed"}
    assert r["needed"]["B"]["status"] == "secured"


def test_naive_mean_ignores_weights():
    assert naive_mean(CATS) == 78.08
    assert analyse(CATS, BANDS)["standing"] == 84.98
    assert naive_mean([cat("x", 100, [])]) is None


def test_validation():
    with pytest.raises(GradeError):
        analyse([cat("a", 50, [90])], BANDS)  # weights do not add to 100
    with pytest.raises(GradeError):
        analyse([cat("a", 100, [120])], BANDS)
    with pytest.raises(GradeError):
        analyse([], BANDS)
    with pytest.raises(GradeError):
        analyse([cat("a", 100, [90], -1)], BANDS)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/analyse", json={"bands": BANDS, "categories": CATS}).json()
    assert r["needed"]["B"]["needed"] == 65.05 and r["naive_mean"] == 78.08
    assert c.get("/").status_code == 200
    assert c.post("/analyse", json={"bands": BANDS, "categories": [cat("a", 50, [1])]}).status_code == 422
