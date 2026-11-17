import math

import pytest
from fastapi.testclient import TestClient

from faqsearch.api import app
from faqsearch.core import Index, SearchError, evaluate, load, overlap_search, stem, tokens

D = load()
c = TestClient(app)


def test_tokens_and_stem():
    assert stem("renewing") == "renew" and stem("books") == "book" and stem("gym") == "gym"
    assert tokens("How do I renew the books?") == ["renew", "book"]


def test_idf_by_hand():
    faqs = [{"id": 1, "q": "apple pie", "a": "baked"}, {"id": 2, "q": "apple tart", "a": "sweet"}]
    idx = Index(faqs)
    # "apple" is in both documents: log(3/3)+1 = 1; "pie" in one: log(3/2)+1
    assert idx.idf["apple"] == pytest.approx(1.0)
    assert idx.idf["pie"] == pytest.approx(math.log(1.5) + 1)
    assert idx.search("pie")[0]["id"] == 1 and idx.search("tart")[0]["id"] == 2


def test_scores_are_cosines():
    idx = Index(D["faqs"])
    r = idx.search("renew library book", 3)
    assert r[0]["id"] == 1 and all(0 < x["score"] <= 1 for x in r)
    assert r == sorted(r, key=lambda x: -x["score"])


def test_obvious_questions():
    idx = Index(D["faqs"])
    assert idx.search("pay fees monthly")[0]["id"] == 9
    assert idx.search("forgot my email password")[0]["id"] == 3
    assert idx.search("permit to park my car")[0]["id"] == 16


def test_beats_word_overlap_baseline():
    m = evaluate()
    assert m["queries"] == 32 and m["tfidf_top1"] >= 0.9
    assert m["tfidf_top1"] > m["overlap_top1"] and m["tfidf_mrr"] > m["overlap_mrr"]
    assert overlap_search(D["faqs"], "xyzzy") == []


def test_validation():
    with pytest.raises(SearchError):
        Index([])
    with pytest.raises(SearchError):
        Index(D["faqs"]).search("the of and")
    with pytest.raises(SearchError):
        Index(D["faqs"]).search("zzzz qqqq")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/search", json={"query": "where do I print"}).json()
    assert r["results"][0]["id"] == 2
    assert c.get("/metrics").json()["queries"] == 32
    assert c.post("/search", json={"query": "the"}).status_code == 422
    assert c.get("/").status_code == 200
