"""Track library, mood clusters and harmonic-key distance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

MOOD_FEATURES = ["tempo", "energy", "valence", "danceability", "acousticness"]
MOOD_NAMES = ["Calm", "Mellow groove", "Uplift", "Full throttle"]


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    artist: str
    genre: str
    tempo: float
    energy: float
    valence: float
    danceability: float
    acousticness: float
    duration_s: int
    key: int
    mode: int  # 1 major, 0 minor
    mood: str = ""


def wheel_position(key: int, mode: int) -> int:
    """Position on the circle of fifths; a minor key shares the position of its relative major."""
    major_key = key if mode == 1 else (key + 3) % 12
    return (major_key * 7) % 12


def key_distance(a: Track, b: Track) -> float:
    """0 = same or relative key, 1 = opposite side of the circle of fifths."""
    d = abs(wheel_position(a.key, a.mode) - wheel_position(b.key, b.mode))
    return min(d, 12 - d) / 6.0


def assign_moods(df: pd.DataFrame, seed: int = 0) -> list[str]:
    """Cluster tracks into four moods with KMeans; name clusters by rising mean energy."""
    x = StandardScaler().fit_transform(df[MOOD_FEATURES])
    km = KMeans(n_clusters=len(MOOD_NAMES), n_init=10, random_state=seed).fit(x)
    order = df.assign(c=km.labels_).groupby("c")["energy"].mean().sort_values().index.tolist()
    names = {int(c): MOOD_NAMES[rank] for rank, c in enumerate(order)}
    return [names[int(c)] for c in km.labels_]


def load_tracks(path: Path) -> list[Track]:
    df = pd.read_csv(path)
    missing = {"id", "title", "artist", "genre", "duration_s", "key", "mode", *MOOD_FEATURES} - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    moods = assign_moods(df)
    return [Track(**{**row, "mood": moods[i]}) for i, row in enumerate(df.to_dict("records"))]
