import pytest
from fastapi.testclient import TestClient

from notesum.api import app
from notesum.core import (
    NotesError,
    action_items,
    evaluate,
    lead_k,
    load,
    precision,
    sentences,
    similarity_matrix,
    summarise,
    textrank,
)

M = load()["meetings"]
c = TestClient(app)


def test_sentence_split():
    assert sentences("One. Two! Three? Four") == ["One.", "Two!", "Three?", "Four"]
    with pytest.raises(NotesError):
        sentences("   ")


def test_similarity_is_symmetric_and_bounded():
    sim = similarity_matrix(sentences(M[0]["text"]))
    n = len(sim)
    assert all(sim[i][j] == sim[j][i] and 0 <= sim[i][j] <= 1.0001 for i in range(n) for j in range(n))
    assert all(sim[i][i] == 0 for i in range(n))


def test_textrank_star_graph_by_hand():
    # node 0 is connected to 1, 2, 3 with equal weight: it must rank first, the leaves tie
    sim = [[0, 1, 1, 1], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]
    s = textrank(sim)
    assert s[0] > s[1] and s[1] == pytest.approx(s[2]) == pytest.approx(s[3])
    assert sum(s) == pytest.approx(1.0, abs=1e-6)
    # (1 - d) / n = 0.0375; leaf = 0.0375 + 0.85 * centre / 3 ; centre = 0.0375 + 0.85 * 3 * leaf
    assert s[0] == pytest.approx(0.4797, abs=0.001)  # solving the two equations: 0.13313 / 0.2775


def test_summary_keeps_original_order_and_size():
    r = summarise(M[1]["text"], 3)
    assert r["indices"] == sorted(r["indices"]) and len(r["summary"]) == 3
    assert len(summarise("Only one sentence here.", 5)["summary"]) == 1


def test_beats_lead_baseline_on_average():
    e = evaluate()
    assert e["textrank_precision"] == 0.417 and e["lead_precision"] == 0.333
    assert e["textrank_precision"] > e["lead_precision"]
    assert precision([0, 1], [1, 2]) == 0.5
    assert lead_k(M[0]["text"], 2) == [0, 1]


def test_action_items():
    a = action_items(M[0]["text"])
    assert a[0] == {"owner": "Marcus", "task": "prepare the new design mockups", "due": "Friday"}
    assert [x["owner"] for x in a] == ["Marcus", "Lena"]
    assert action_items(M[2]["text"])[0]["due"] == "next Thursday"
    assert [x["owner"] for x in action_items(M[3]["text"])] == ["Ben", "Aisha"]  # no false hit
    assert action_items("Nothing is assigned here.") == []


def test_validation():
    with pytest.raises(NotesError):
        summarise("Some text.", 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/summarise", json={"text": M[2]["text"], "k": 3}).json()
    assert len(r["summary"]) == 3 and r["actions"][0]["owner"] == "Jamal" and len(r["sentences"]) == 9
    assert c.get("/metrics").json()["meetings"] == 4
    assert c.post("/summarise", json={"text": "  ", "k": 3}).status_code == 422
    assert c.post("/summarise", json={"text": "Hi.", "k": 0}).status_code == 422
    assert c.get("/").status_code == 200
