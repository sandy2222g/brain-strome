import pytest
from fastapi.testclient import TestClient

from wordladder.api import app
from wordladder.core import LadderError, bfs, bidirectional, buckets, examples, load_words, neighbours, valid

c = TestClient(app)
W = load_words()


def test_word_list_is_clean():
    assert len(W) > 300 and all(w.isalpha() and w == w.lower() and len(w) in (3, 4) for w in W)


def test_neighbours_differ_by_one_letter():
    n = neighbours("cat", buckets(W))
    assert "cot" in n and "cut" in n and "cat" not in n
    assert all(sum(a != b for a, b in zip("cat", x, strict=True)) == 1 for x in n)


def test_known_ladder_length():
    r = bfs("cat", "dog", W)
    assert r and len(r.path) == 4 and r.path[0] == "cat" and r.path[-1] == "dog" and valid(r.path, W)


def test_bidirectional_matches_plain_length_everywhere():
    pairs = [(e["from"], e["to"]) for e in examples()] + [("bat", "pen"), ("bake", "hint"), ("ban", "fox")]
    for a, z in pairs:
        if a not in W or z not in W:
            continue
        p, f = bfs(a, z, W), bidirectional(a, z, W)
        assert (p is None) == (f is None)
        if p and f:
            assert len(p.path) == len(f.path) and valid(f.path, W)


def test_bidirectional_does_less_work():
    tot_p = tot_f = 0
    for e in examples():
        p, f = bfs(e["from"], e["to"], W), bidirectional(e["from"], e["to"], W)
        assert p and f
        tot_p += p.explored
        tot_f += f.explored
    assert tot_f * 3 < tot_p


def test_same_word_and_unreachable():
    assert bidirectional("cat", "cat", W).path == ["cat"]
    small = {"cat", "cot", "dog", "dig"}
    assert bfs("cat", "dog", small) is None and bidirectional("cat", "dog", small) is None


def test_validation():
    for a, z, msg in [("cat", "door", "same length"), ("cat", "zzz", "not in the word list")]:
        with pytest.raises(LadderError, match=msg):
            bfs(a, z, W)


def test_valid_rejects_bad_paths():
    assert not valid(["cat", "dog"], W) and not valid(["cat", "cxt"], W) and not valid([], W)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/ladder", params={"a": "cold", "z": "warm"}).json()
    assert r["found"] and r["steps"] == 4 and r["explored"] < r["plain_explored"]
    assert c.get("/ladder", params={"a": "cat", "z": "zzz"}).status_code == 422
    assert len(c.get("/examples").json()["examples"]) == 5 and c.get("/").status_code == 200
