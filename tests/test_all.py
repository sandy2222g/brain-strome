import pytest
from fastapi.testclient import TestClient

from plainwords.api import SAMPLE, app
from plainwords.core import (
    TextError,
    find_swaps,
    is_passive,
    label,
    load_swaps,
    review,
    score,
    sentences,
    syllables,
    words,
)

c = TestClient(app)


@pytest.mark.parametrize(
    ("word", "n"),
    [("cat", 1), ("make", 1), ("table", 2), ("created", 3), ("people", 2), ("beautiful", 3), ("hundred", 2), ("a", 1)],
)
def test_syllables_known_words(word, n):
    got = syllables(word)
    assert abs(got - n) <= 1  # heuristic: within one syllable


def test_syllables_simple_exact_cases():
    assert [syllables(w) for w in ("cat", "make", "table", "banana")] == [1, 1, 2, 3]
    assert syllables("123") == 0


def test_sentences_and_words_split():
    t = "Hello there. How are you?\nFine!"
    assert sentences(t) == ["Hello there.", "How are you?", "Fine!"]
    assert words("Don't stop, ok?") == ["Don't", "stop", "ok"]


def test_easy_text_scores_easier_than_legal_text():
    easy = score("The cat sat on the mat. It was warm.")
    hard = score(
        "Notwithstanding the aforementioned stipulations, the administrative representatives deliberated extensively."
    )
    assert easy.reading_ease > hard.reading_ease and easy.grade < hard.grade


def test_score_rejects_empty():
    with pytest.raises(TextError):
        score("   ...  ")


def test_label_bands():
    assert label(95) == "very easy" and label(65) == "plain" and label(10) == "very hard"


def test_swaps_found_case_insensitively_with_longest_phrase_first():
    s = find_swaps("Prior to this, we will Utilize it in order to win.", load_swaps())
    pairs = {(x["found"].lower(), x["use"]) for x in s}
    assert ("prior to", "before") in pairs and ("utilize", "use") in pairs and ("in order to", "to") in pairs


def test_swap_does_not_match_inside_words():
    assert find_swaps("The terminator is additionally funny.", load_swaps()) == []


def test_passive_detection():
    assert is_passive("The form was completed by the tenant.")
    assert is_passive("Charges will be applied.")
    assert not is_passive("The tenant completed the form.")
    assert not is_passive("We need a hundred beds.")


def test_review_counts_and_flags_long_sentence():
    r = review(SAMPLE)
    assert r["counts"]["long"] == 1 and r["counts"]["swaps"] >= 5 and r["counts"]["passive"] >= 1
    assert r["label"] in {"fairly hard", "hard", "very hard"}


def test_simple_text_has_no_flags():
    r = review("Put the bins out on Tuesday. We empty them early.")
    assert r["counts"] == {"long": 0, "passive": 0, "swaps": 0} and r["label"] in {"very easy", "easy"}


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    t = c.get("/sample").json()["text"]
    r = c.post("/review", json={"text": t}).json()
    assert r["scores"]["words"] > 40 and c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/review", json={"text": ""}).status_code == 422
    assert c.post("/review", json={"text": "..."}).status_code == 422
