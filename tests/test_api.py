from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from carbon.api import app

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def sample(client: TestClient) -> dict[str, Any]:
    return client.get("/sample").json()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "model_loaded": True}


def test_index_page(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "Household Carbon Coach" in r.text


def test_factors_endpoint(client: TestClient) -> None:
    body = client.get("/factors").json()
    assert body["count"] == len(body["factors"]) >= 30
    assert "not certified" in body["disclaimer"]


def test_sample_is_already_calculated(sample: dict[str, Any]) -> None:
    fp = sample["footprint"]
    assert 10 < fp["total_t"] < 20
    assert fp["uses_estimates"] and len(fp["filled"]) == 4
    assert abs(sum(c["t"] for c in fp["categories"]) - fp["total_t"]) < 0.01


def test_footprint_response(client: TestClient, sample: dict[str, Any]) -> None:
    fp = client.post("/footprint", json={"answers": sample["answers"]}).json()
    assert len(fp["categories"]) == 7
    assert 0 <= fp["peers"]["percentile"] <= 100
    assert fp["estimate"]["low_t"] <= fp["estimate"]["tonnes"] <= fp["estimate"]["high_t"]
    assert fp["per_person_t"] == pytest.approx(fp["total_t"] / 3, abs=0.01)


def test_footprint_with_every_answer_has_no_fills(client: TestClient, sample: dict[str, Any]) -> None:
    answers = dict(sample["answers"], **{k: 100 for k in sample["answers"] if sample["answers"][k] is None})
    fp = client.post("/footprint", json={"answers": answers}).json()
    assert fp["uses_estimates"] is False and fp["filled"] == []


def test_footprint_validation_error(client: TestClient, sample: dict[str, Any]) -> None:
    assert client.post("/footprint", json={"answers": dict(sample["answers"], household_size=0)}).status_code == 422
    assert client.post("/footprint", json={"answers": dict(sample["answers"], diet="carnivore")}).status_code == 422
    assert client.post("/footprint", json={}).status_code == 422


def test_levers_endpoint(client: TestClient, sample: dict[str, Any]) -> None:
    body = client.post("/levers", json={"answers": sample["answers"]}).json()
    scores = [lv["impact_per_effort"] for lv in body["levers"]]
    assert scores == sorted(scores, reverse=True) and len(scores) >= 6
    assert all(lv["saved_t"] <= body["baseline_t"] for lv in body["levers"])


def test_plan_endpoint(client: TestClient, sample: dict[str, Any]) -> None:
    body = client.post("/plan", json={"answers": sample["answers"], "lever_ids": ["green_tariff", "flight_cut"]}).json()
    assert body["suggested"] is False and body["saved_t"] > 0
    assert body["after_t"] == pytest.approx(body["baseline_t"] - body["saved_t"], abs=0.002)
    suggested = client.post("/plan", json={"answers": sample["answers"], "lever_ids": []}).json()
    assert suggested["suggested"] is True and len(suggested["lever_ids"]) == 3


def test_plan_errors(client: TestClient, sample: dict[str, Any]) -> None:
    bad = client.post("/plan", json={"answers": sample["answers"], "lever_ids": ["teleport"]})
    assert bad.status_code == 422 and "unknown" in bad.json()["detail"]
    many = ["thermostat_down", "green_tariff", "flight_cut", "heat_pump"]
    assert client.post("/plan", json={"answers": sample["answers"], "lever_ids": many}).status_code == 422


def test_metrics_endpoint(client: TestClient) -> None:
    body = client.get("/metrics").json()
    assert body["footprint_r2"] > 0.85 and "band_coverage" in body
