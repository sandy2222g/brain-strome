import pytest
from fastapi.testclient import TestClient

from prlab.api import app
from prlab.core import TOWN, RankError, damping_sweep, indegree_ranking, pagerank, pagerank_exact, ranking

c = TestClient(app)


def test_scores_sum_to_one():
    assert sum(pagerank(TOWN).values()) == pytest.approx(1.0, abs=1e-9)


def test_matches_a_direct_linear_solve():
    a, b = pagerank(TOWN), pagerank_exact(TOWN)
    assert all(a[k] == pytest.approx(b[k], abs=1e-9) for k in a)


def test_two_page_hand_example():
    # A -> B, B -> A: perfectly symmetric
    r = pagerank({"a": ["b"], "b": ["a"]})
    assert r["a"] == pytest.approx(0.5) and r["b"] == pytest.approx(0.5)
    # a -> b only; b is dangling: b ranks higher, and the exact solver agrees
    g = {"a": ["b"], "b": []}
    assert pagerank(g)["b"] > pagerank(g)["a"]
    assert pagerank(g)["b"] == pytest.approx(pagerank_exact(g)["b"], abs=1e-9)


def test_damping_zero_gives_uniform_scores():
    r = pagerank(TOWN, 0.0)
    assert max(r.values()) == pytest.approx(min(r.values())) == pytest.approx(1 / len(r))


def test_town_hall_wins_and_gazette_with_no_inbound_links_is_last_tier():
    r = ranking(TOWN)
    assert r[0][0] == "town-hall"
    scores = dict(r)
    assert scores["gazette"] == pytest.approx(0.15 / 11, abs=1e-6)  # nothing links to it: only the random-jump share


def test_rank_is_not_just_counting_links():
    scores, deg = dict(ranking(TOWN)), dict(indegree_ranking(TOWN))
    # the clinic has 1 link in (from the town hall); the sports club has 3. The town hall's endorsement is worth more.
    assert deg["clinic"] == 1 and deg["sports-club"] == 3
    assert scores["clinic"] > scores["sports-club"]
    assert [p for p, _ in ranking(TOWN)] != [p for p, _ in indegree_ranking(TOWN)]


def test_sweep_and_validation():
    s = damping_sweep(TOWN, [0.0, 0.85])
    assert len(s["town-hall"]) == 2 and s["town-hall"][1] > s["town-hall"][0]
    for bad in (1.0, -0.1):
        with pytest.raises(RankError):
            pagerank(TOWN, bad)
    with pytest.raises(RankError):
        pagerank({})


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/town").json()
    assert j["pagerank"][0]["page"] == "town-hall" and len(j["pagerank"]) == 11
    r = c.post("/rank", json={"links": {"x": ["y"], "y": ["x"]}}).json()
    assert r["pagerank"][0]["score"] == 0.5
    assert c.post("/rank", json={"links": {}}).status_code == 422
    assert c.get("/town", params={"damping": 1}).status_code == 422 and c.get("/").status_code == 200
