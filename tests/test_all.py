import json
from pathlib import Path

from fastapi.testclient import TestClient

from dedupe.api import app
from dedupe.core import (
    Contact,
    UnionFind,
    evaluate,
    find_duplicates,
    merge,
    name_score,
    norm_name,
    norm_phone,
    pair_score,
)

D = json.loads(Path("data/contacts.json").read_text())["contacts"]
CS = [Contact(c["id"], c["name"], c["phone"], c["email"]) for c in D]
TRUTH = {c["id"]: c["group"] for c in D}
c = TestClient(app)


def test_norm_name_handles_formats_and_nicknames():
    assert norm_name("GARCIA, Maria") == "maria garcia"
    assert norm_name("Jim Smith") == "james smith"
    assert norm_name("  Wei   Chen ") == "wei chen"


def test_norm_phone_formats_agree():
    assert norm_phone("(555) 123 4567") == norm_phone("555-123-4567") == norm_phone("+1 555.123.4567")


def test_initial_matches_full_surname():
    assert name_score("maria garcia", "maria g") >= 0.9


def test_shared_phone_is_decisive_but_different_people_stay_apart():
    a = Contact(1, "Maria Garcia", "555-111-2222", "a@x.com")
    b = Contact(2, "Mria Garcia", "(555) 111 2222", "b@x.com")
    other = Contact(3, "Liam Murphy", "555-999-0000", "l@x.com")
    assert pair_score(a, b) >= 0.8 and pair_score(a, other) < 0.8


def test_union_find_transitivity():
    uf = UnionFind(4)
    uf.union(0, 1)
    uf.union(1, 2)
    assert uf.find(0) == uf.find(2) != uf.find(3)


def test_sample_precision_and_recall_floor():
    m = evaluate(TRUTH, find_duplicates(CS, 0.8))
    assert m["precision"] >= 0.9 and m["recall"] >= 0.8


def test_stricter_threshold_never_lowers_precision_on_sample():
    p = [evaluate(TRUTH, find_duplicates(CS, t))["precision"] for t in (0.7, 0.8, 0.9)]
    assert p == sorted(p)


def test_clusters_are_disjoint_and_multi_member():
    cl = find_duplicates(CS, 0.8)
    flat = [i for g in cl for i in g]
    assert len(flat) == len(set(flat)) and all(len(g) > 1 for g in cl)


def test_merge_keeps_best_fields():
    m = merge([Contact(5, "Maria G.", "", "M@X.com"), Contact(2, "Maria Garcia", "555-1", "")])
    assert m.name == "Maria Garcia" and m.phone == "555-1" and m.email == "m@x.com" and m.id == 2


def test_evaluate_edge_cases():
    assert evaluate({1: 0, 2: 1}, []) == {"precision": 1.0, "recall": 1.0, "pairs_true": 0, "pairs_found": 0}


def test_api_roundtrip_and_eval():
    body = c.get("/sample").json()
    r = c.post("/dedupe", json=body).json()
    assert r["after_merge"] < r["total"] and r["evaluation"]["precision"] > 0.9
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/").status_code == 200


def test_api_without_labels_has_no_evaluation():
    body = {"contacts": [{"id": 1, "name": "Ana Lopez"}, {"id": 2, "name": "Ana Lopez"}, {"id": 3, "name": "Bo Chen"}]}
    r = c.post("/dedupe", json=body).json()
    assert "evaluation" not in r
    assert [x["ids"] for x in r["clusters"]] == [[1, 2]] and r["after_merge"] == 2


def test_api_validation():
    assert c.post("/dedupe", json={"contacts": [], "threshold": 0.1}).status_code == 422
