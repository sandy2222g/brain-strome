from __future__ import annotations

from pathlib import Path

import pytest

from arcmix.library import Track, load_tracks

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def tracks() -> list[Track]:
    return load_tracks(ROOT / "data" / "tracks.csv")


def mk(
    id_: str,
    energy: float = 0.5,
    tempo: float = 100,
    key: int = 0,
    mode: int = 1,
    artist: str = "A",
    valence: float = 0.5,
    dur: int = 200,
) -> Track:
    return Track(id_, id_, artist, "pop", tempo, energy, valence, 0.5, 0.5, dur, key, mode, "Uplift")
