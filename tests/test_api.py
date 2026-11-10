from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_index_page(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "Rent Check" in r.text


def test_metrics(client: TestClient) -> None:
    m = client.get("/metrics").json()
    assert {"mae", "mape_pct", "interval_coverage", "n_test"} <= set(m)


def test_districts(client: TestClient) -> None:
    rows = client.get("/districts").json()["districts"]
    assert len(rows) == 8 and rows[0]["median_per_m2"] >= rows[-1]["median_per_m2"]


def test_sample_then_estimate(client: TestClient) -> None:
    sample = client.get("/sample").json()
    r = client.post("/estimate", json=sample)
    assert r.status_code == 200
    body = r.json()
    rng = body["range"]
    assert rng["p10"] <= rng["p50"] <= rng["p90"]
    assert body["verdict"]["key"] == "above"
    assert body["breakdown"]["drivers"]
    assert "Comparable flats" in body["negotiation"]


def test_estimate_rejects_unknown_district(client: TestClient) -> None:
    bad = {**client.get("/sample").json(), "district": "Atlantis"}
    r = client.post("/estimate", json=bad)
    assert r.status_code == 422
    assert "unknown district" in r.text


def test_estimate_rejects_out_of_range(client: TestClient) -> None:
    bad = {**client.get("/sample").json(), "size_m2": 3}
    assert client.post("/estimate", json=bad).status_code == 422


def test_estimate_requires_rent(client: TestClient) -> None:
    body = client.get("/sample").json()
    del body["rent"]
    assert client.post("/estimate", json=body).status_code == 422


def test_alternatives_endpoint(client: TestClient) -> None:
    body = {**client.get("/sample").json(), "rent": 1600}
    alts = client.post("/alternatives", json=body).json()["alternatives"]
    assert alts and all(a["rent"] < 1600 for a in alts)
