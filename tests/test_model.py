from __future__ import annotations

import pytest

from buddies.model import BuddyError, Student, count_blocking, helps, match, pair_score, shared_slots
from conftest import mk


def test_helps_needs_strong_helper_and_weak_learner() -> None:
    a = mk("A", {"Calculus": 5, "Physics": 3})
    b = mk("B", {"Calculus": 1, "Physics": 1})
    assert helps(a, b) == [("Calculus", 4)]
    assert helps(b, a) == []


def test_score_is_symmetric_and_bounded(cohort: list[Student]) -> None:
    for a in cohort[:8]:
        for b in cohort[8:16]:
            assert pair_score(a, b) == pair_score(b, a)
            assert 0 <= pair_score(a, b) <= 10.5


def test_complementary_pair_beats_identical_skills() -> None:
    slots = ("Mon morning", "Tue evening")
    comp = pair_score(mk("A", {"Calculus": 5, "Physics": 1}, slots), mk("B", {"Calculus": 1, "Physics": 5}, slots))
    same = pair_score(mk("A", {"Calculus": 5, "Physics": 5}, slots), mk("B", {"Calculus": 5, "Physics": 5}, slots))
    assert comp > same


def test_no_shared_time_lowers_score() -> None:
    skills_a, skills_b = {"Calculus": 5}, {"Calculus": 0}
    together = pair_score(mk("A", skills_a, ("Mon morning",)), mk("B", skills_b, ("Mon morning",)))
    apart = pair_score(mk("A", skills_a, ("Mon morning",)), mk("B", skills_b, ("Tue evening",)))
    assert together > apart and shared_slots(mk("A", {}, ("x",)), mk("B", {}, ("y",))) == []


def test_matching_covers_everyone_once(cohort: list[Student]) -> None:
    r = match(cohort, seed=1)
    names = [n for p in r.pairs for n in p.members]
    assert sorted(names) == sorted(s.name for s in cohort) and all(len(p.members) == 2 for p in r.pairs)


def test_beats_random_and_is_nearly_stable(cohort: list[Student]) -> None:
    r = match(cohort, seed=1)
    assert r.total_score > r.random_baseline * 1.3
    assert r.blocking_pairs <= 3


def test_deterministic_for_a_seed(cohort: list[Student]) -> None:
    a, b = match(cohort, seed=2), match(cohort, seed=2)
    assert [p.members for p in a.pairs] == [p.members for p in b.pairs]


def test_odd_cohort_makes_one_trio(cohort: list[Student]) -> None:
    r = match(cohort[:-1], seed=1)
    sizes = sorted(len(p.members) for p in r.pairs)
    assert sizes.count(3) == 1 and sum(sizes) == len(cohort) - 1
    assert any("joins as a third member" in x for p in r.pairs for x in p.reasons)


def test_explanations_name_who_helps_whom() -> None:
    r = match([mk("Ana", {"Calculus": 5}, ("Mon morning",)), mk("Ben", {"Calculus": 0}, ("Mon morning",))])
    assert r.pairs[0].helps == ["Ana can help Ben with Calculus"]
    assert any("shared free slot" in x for x in r.pairs[0].reasons)


def test_blocking_pairs_counts_unstable_matchings() -> None:
    scores = [[0, 9, 1, 1], [9, 0, 1, 1], [1, 1, 0, 9], [1, 1, 9, 0]]
    assert count_blocking([(0, 1), (2, 3)], scores, 4) == 0
    assert count_blocking([(0, 2), (1, 3)], scores, 4) >= 1


@pytest.mark.parametrize(
    "students",
    [[mk("A")], [mk("A"), mk("A")], [mk("A", {"Calculus": 9}), mk("B")]],
)
def test_validation(students: list[Student]) -> None:
    with pytest.raises(BuddyError):
        match(students)
