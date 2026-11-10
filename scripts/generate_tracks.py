"""Generate a fictional music library (invented titles and artists; features are synthetic).

Writes data/tracks.csv. Run: python scripts/generate_tracks.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 29
N = 200
GENRES = {  # genre -> (tempo mean, energy mean, valence mean, acoustic mean)
    "ambient": (78, 0.22, 0.45, 0.80),
    "folk": (98, 0.38, 0.58, 0.85),
    "soul": (92, 0.50, 0.65, 0.40),
    "indie": (118, 0.62, 0.55, 0.30),
    "house": (124, 0.78, 0.68, 0.05),
    "pop": (112, 0.70, 0.75, 0.15),
    "rock": (136, 0.85, 0.50, 0.10),
    "drum and bass": (172, 0.92, 0.45, 0.03),
}
WORDS_A = [
    "Neon",
    "Quiet",
    "Paper",
    "Golden",
    "Velvet",
    "Hollow",
    "Silver",
    "Wild",
    "Slow",
    "Electric",
    "Crimson",
    "Lunar",
    "Salt",
    "Amber",
    "Glass",
]
WORDS_B = [
    "Harbour",
    "Orchard",
    "Signal",
    "Garden",
    "Engine",
    "Weather",
    "Lantern",
    "River",
    "Static",
    "Parade",
    "Ember",
    "Tide",
    "Compass",
    "Motel",
    "Meadow",
]
ARTISTS = [
    "The Marlows",
    "Ivy & Oak",
    "June Parade",
    "Night Orchard",
    "Kestrel Club",
    "Soft Engines",
    "Odessa Lane",
    "Blue Tarmac",
    "Pale Harbor",
    "Mira Voss",
    "Tomo Hale",
    "Sunday Static",
    "Lark Theory",
    "Ferris Wheel",
    "Cold Frames",
    "Dune Radio",
    "Nell Archer",
    "The Quiet Fires",
]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def main() -> None:
    rng = random.Random(SEED)
    rows, seen = [], set()
    while len(rows) < N:
        genre = rng.choice(list(GENRES))
        tempo_m, en_m, val_m, ac_m = GENRES[genre]
        title = f"{rng.choice(WORDS_A)} {rng.choice(WORDS_B)}"
        if title in seen:
            continue
        seen.add(title)
        energy = clip(rng.gauss(en_m, 0.09))
        rows.append(
            {
                "id": f"T{len(rows):03d}",
                "title": title,
                "artist": rng.choice(ARTISTS),
                "genre": genre,
                "tempo": round(max(55, rng.gauss(tempo_m, 7)), 1),
                "energy": round(energy, 3),
                "valence": round(clip(rng.gauss(val_m, 0.15)), 3),
                "danceability": round(clip(rng.gauss(0.3 + 0.6 * energy, 0.1)), 3),
                "acousticness": round(clip(rng.gauss(ac_m, 0.1)), 3),
                "duration_s": int(clip(rng.gauss(215, 40), 120, 360) // 1),
                "key": rng.randrange(12),
                "mode": rng.choice([0, 1]),
            }
        )
    out = Path(__file__).resolve().parents[1] / "data" / "tracks.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} tracks to {out}")


if __name__ == "__main__":
    main()
