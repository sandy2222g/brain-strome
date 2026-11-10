from __future__ import annotations

from fastapi.testclient import TestClient

from waitsim.api import app


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Waiting room console" in c.get("/").text
        sample = c.get("/sample").json()
        r = c.post("/simulate", json={**sample, "replications": 10}).json()
        assert r["summary"]["patients_per_day"] > 40 and "erlang_c_flat_peak" in r
        rec = c.post("/recommend", json={**sample, "replications": 10}).json()
        assert rec["recommended_servers"] >= 2 and rec["options"]
        e = c.get("/erlang", params={"arrivals_per_hour": 20, "mean_service_min": 12, "servers": 5}).json()
        assert e["stable"] and 6 < e["mean_wait_min"] < 7.5


def test_overload_flag_and_validation() -> None:
    with TestClient(app) as c:
        over = c.post("/simulate", json={"config": {"arrivals_per_hour": 40, "servers": 2}, "replications": 3}).json()
        assert over["peak_overloaded"] and over["erlang_c_flat_peak"]["mean_wait_min"] is None
        assert c.post("/simulate", json={"config": {"open_hour": 12, "close_hour": 8}}).status_code == 422
        assert c.post("/simulate", json={"config": {"hourly_profile": [1.0]}}).status_code == 422
        assert c.post("/simulate", json={"replications": 0}).status_code == 422
        assert c.get("/erlang", params={"arrivals_per_hour": 0, "mean_service_min": 5, "servers": 1}).status_code == 422


def test_trace_is_consistent() -> None:
    with TestClient(app) as c:
        t = c.post("/trace", json={"config": {"servers": 2, "arrivals_per_hour": 10}, "seed": 3}).json()
        assert t["patients"] and t["servers"] == 2
        for p in t["patients"]:
            assert p["arrive"] <= p["start"] < p["end"] and 0 <= p["server"] < 2
        by_server: dict[int, list[tuple[float, float]]] = {}
        for p in t["patients"]:
            by_server.setdefault(p["server"], []).append((p["start"], p["end"]))
        for spans in by_server.values():  # a server never serves two patients at once
            spans.sort()
            assert all(a[1] <= b[0] + 1e-6 for a, b in zip(spans, spans[1:], strict=False))
