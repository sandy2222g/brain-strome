import pytest
from fastapi.testclient import TestClient

from kmeanslab.api import app
from kmeanslab.core import KMeansError, blobs, compare_inits, dist2, elbow, kmeans

c = TestClient(app)
CENTRES = [(2.0, 2.0), (8.0, 3.0), (5.0, 8.0), (9.0, 9.0)]


def test_recovers_the_true_centres():
    pts = blobs(80, seed=3)
    r = kmeans(pts, 4, "pp", seed=1)
    for true in CENTRES:
        assert min(dist2(true, c) for c in r["centres"]) < 0.1  # within about 0.3 units


def test_hand_worked_two_point_case():
    r = kmeans([(0.0, 0.0), (0.0, 2.0), (10.0, 0.0), (10.0, 2.0)], 2, "pp", seed=0)
    assert sorted(r["centres"]) == [(0.0, 1.0), (10.0, 1.0)] and r["inertia"] == pytest.approx(4.0)


def test_inertia_never_increases_with_more_clusters():
    e = elbow(blobs(40, seed=2), 6)
    assert all(a >= b - 1e-9 for a, b in zip(e, e[1:], strict=False))


def test_elbow_is_at_the_true_k():
    e = elbow(blobs(60, seed=1), 8)
    drops = [e[i] - e[i + 1] for i in range(len(e) - 1)]
    assert drops[2] > 5 * drops[3]  # going 3 -> 4 clusters helps hugely; 4 -> 5 barely


def test_kmeans_plus_plus_is_more_reliable_than_random_init():
    r = compare_inits(blobs(60, seed=1), 4, 60)
    assert r["pp"]["bad_runs_pct"] < r["random"]["bad_runs_pct"]
    assert r["pp"]["mean_inertia"] <= r["random"]["mean_inertia"]


def test_deterministic_and_validation():
    pts = blobs(20, seed=5)
    assert kmeans(pts, 3, "pp", 7) == kmeans(pts, 3, "pp", 7)
    for bad in [(0, "pp"), (999, "pp"), (3, "magic")]:
        with pytest.raises(KMeansError):
            kmeans(pts, *bad)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/cluster", params={"k": 4}).json()
    assert len(j["points"]) == 240 and len(j["centres"]) == 4
    assert c.get("/cluster", params={"init": "x"}).status_code == 422
    assert c.get("/cluster", params={"k": 0}).status_code == 422
    s = c.get("/summary").json()
    assert len(s["elbow"]) == 8 and set(s["inits"]) == {"random", "pp"} and c.get("/").status_code == 200
