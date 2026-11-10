from __future__ import annotations

import pytest

from arcmix.builder import ARCS, PlaylistError, arc_at, build, transition_cost
from arcmix.library import Track
from conftest import mk


def test_arc_interpolation() -> None:
    pts = [(0.0, 0.2), (1.0, 0.8)]
    assert arc_at(pts, 0) == 0.2 and arc_at(pts, 1) == 0.8 and arc_at(pts, 0.5) == pytest.approx(0.5)
    assert arc_at(pts, -1) == 0.2 and arc_at(pts, 2) == 0.8


def test_transition_cost_orders_sensible_pairs() -> None:
    a = mk("a", tempo=100, key=0)
    smooth = mk("b", tempo=102, key=7)
    rough = mk("c", tempo=170, key=6, valence=0.1)
    assert transition_cost(a, smooth) < transition_cost(a, rough)
    assert transition_cost(a, mk("d", artist="A")) > transition_cost(a, mk("d", artist="Z"))


@pytest.mark.parametrize("arc", list(ARCS))
def test_playlist_length_no_repeats_and_beats_shuffle(tracks: list[Track], arc: str) -> None:
    p = build(tracks, ARCS[arc], minutes=40)
    ids = [s.track.id for s in p.steps]
    assert len(ids) == len(set(ids))
    assert abs(p.minutes - 40) <= 5
    assert p.arc_rmse < p.baseline_arc_rmse * 0.6
    assert p.mean_transition < p.baseline_mean_transition * 0.5


def test_follows_a_rising_arc(tracks: list[Track]) -> None:
    p = build(tracks, ARCS["Slow burn"], minutes=40)
    third = len(p.steps) // 3
    first = sum(s.track.energy for s in p.steps[:third]) / third
    last = sum(s.track.energy for s in p.steps[-third:]) / third
    assert last > first + 0.3


def test_deterministic_for_a_seed(tracks: list[Track]) -> None:
    a = build(tracks, ARCS["Steady focus"], 30, seed=3)
    b = build(tracks, ARCS["Steady focus"], 30, seed=3)
    assert [s.track.id for s in a.steps] == [s.track.id for s in b.steps]


def test_mood_filter_is_respected(tracks: list[Track]) -> None:
    p = build(tracks, ARCS["Steady focus"], 30, allowed_moods={"Calm", "Mellow groove"})
    assert {s.track.mood for s in p.steps} <= {"Calm", "Mellow groove"}


def test_avoids_same_artist_back_to_back_when_possible(tracks: list[Track]) -> None:
    p = build(tracks, ARCS["Warm-up, peak, cool-down"], 60)
    repeats = sum(a.track.artist == b.track.artist for a, b in zip(p.steps, p.steps[1:], strict=False))
    assert repeats <= 1


def test_tiny_library_errors(tracks: list[Track]) -> None:
    with pytest.raises(PlaylistError, match="not enough tracks"):
        build(tracks[:5], ARCS["Steady focus"], 60)


@pytest.mark.parametrize(
    ("arc", "minutes"), [([(0.0, 0.5)], 30), ([(0.0, 0.5), (1.0, 1.5)], 30), ([(0, 0.2), (1, 0.8)], 2)]
)
def test_validation(tracks: list[Track], arc: list[tuple[float, float]], minutes: float) -> None:
    with pytest.raises(PlaylistError):
        build(tracks, arc, minutes)
