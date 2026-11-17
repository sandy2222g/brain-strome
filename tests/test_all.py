import random

import pytest
from fastapi.testclient import TestClient

from townbridge.api import app
from townbridge.core import Town, TownError, best_new_roads, brute_bridges, closure, components, load_town, tarjan

c = TestClient(app)
T = load_town()


def random_town(rng: random.Random) -> Town:
    n = rng.randint(2, 9)
    names = [f"p{i}" for i in range(n)]
    roads = {tuple(sorted(rng.sample(names, 2))) for _ in range(rng.randint(0, 11))}
    return Town({p: (0.0, 0.0) for p in names}, sorted(roads))


def brute_cut_points(town: Town) -> list[str]:
    base = len(components(town.adjacency()))
    out = []
    for p in town.places:
        rest = Town({k: v for k, v in town.places.items() if k != p}, [r for r in town.roads if p not in r])
        if len(components(rest.adjacency())) > base - (1 if not town.adjacency()[p] else 0):
            out.append(p)
    return sorted(out)


def test_town_data():
    assert len(T.places) == 15 and len(T.roads) == 18 and len(components(T.adjacency())) == 1


def test_known_bridges_and_junctions():
    b, cut = tarjan(T.adjacency())
    assert len(b) == 6 and ("Park", "Station") in b and ("Harbour", "Lighthouse") in b
    assert "Station" in cut and "Library" not in cut  # the cycle around Library has no single point of failure


def test_tarjan_matches_brute_force_on_the_town():
    assert tarjan(T.adjacency())[0] == brute_bridges(T)


def test_tarjan_matches_brute_force_on_random_graphs():
    rng = random.Random(9)
    for _ in range(400):
        t = random_town(rng)
        b, cut = tarjan(t.adjacency())
        assert b == brute_bridges(t)
        assert cut == brute_cut_points(t)


def test_closing_a_bridge_splits_closing_a_cycle_road_does_not():
    assert len(closure(T, ("Park", "Station"))) == 2
    assert len(closure(T, ("Market", "Library"))) == 1
    sizes = sorted(len(p) for p in closure(T, ("Harbour", "Lighthouse")))
    assert sizes == [1, 14]


def test_best_new_road_connects_the_far_ends():
    top = best_new_roads(T)[0]
    assert top["bridges_left"] == 1 and top["fixed"] == 5 and set(top["road"]) == {"Hill", "Lighthouse"}  # type: ignore[arg-type]


def test_validation():
    with pytest.raises(TownError):
        closure(T, ("Market", "Castle"))


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    d = c.get("/town").json()
    assert len(d["bridges"]) == 6 and "Station" in d["junctions"] and d["suggestions"][0]["fixed"] == 5
    r = c.get("/close", params={"a": "Church", "b": "Castle"}).json()
    assert r["split"] and sorted(len(p) for p in r["pieces"]) == [1, 14]
    assert c.get("/close", params={"a": "Market", "b": "Library"}).json()["split"] is False
    assert c.get("/close", params={"a": "x", "b": "y"}).status_code == 404 and c.get("/").status_code == 200
