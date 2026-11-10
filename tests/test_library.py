from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from arcmix.library import MOOD_NAMES, Track, assign_moods, key_distance, load_tracks, wheel_position
from conftest import mk


def test_wheel_position_relative_keys_match() -> None:
    assert wheel_position(0, 1) == wheel_position(9, 0)  # C major and A minor
    assert wheel_position(7, 1) == (wheel_position(0, 1) + 1) % 12  # G is one step from C


def test_key_distance_properties() -> None:
    c, g, fs = mk("c", key=0), mk("g", key=7), mk("fs", key=6)
    assert key_distance(c, c) == 0 and key_distance(c, mk("am", key=9, mode=0)) == 0
    assert key_distance(c, g) == pytest.approx(1 / 6)
    assert key_distance(c, fs) == 1.0 and key_distance(c, fs) == key_distance(fs, c)


def test_library_loads_and_moods_are_ordered_by_energy(tracks: list[Track]) -> None:
    assert len(tracks) == 200 and {t.mood for t in tracks} == set(MOOD_NAMES)
    mean = {m: sum(t.energy for t in tracks if t.mood == m) / sum(t.mood == m for t in tracks) for m in MOOD_NAMES}
    assert mean["Calm"] < mean["Mellow groove"] < mean["Uplift"] < mean["Full throttle"]


def test_mood_assignment_is_deterministic() -> None:
    df = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "tracks.csv")
    assert assign_moods(df) == assign_moods(df)


def test_missing_columns_rejected(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    p.write_text("id,title\nT1,x\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_tracks(p)
