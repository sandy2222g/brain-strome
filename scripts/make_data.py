"""Generate data/items.json: an invented 22-item flat move. Typical weights and volumes, jittered by seed 1."""

import json
import random
from pathlib import Path

BASE = [
    ("Hardback books", 14, 18), ("Paperbacks", 8, 24), ("Dinner plates", 9, 12), ("Pots and pans", 7, 30),
    ("Winter duvet", 3, 55), ("Pillows", 2, 40), ("Towels", 4, 28), ("Board games", 6, 35),
    ("Vinyl records", 15, 14), ("Toolbox", 12, 16), ("Shoes", 5, 32), ("Coats", 4, 50),
    ("Cookbooks", 9, 14), ("Glasses (wrapped)", 6, 14), ("Lamp and shades", 3, 38),
    ("Kettle and toaster", 4, 22), ("Photo albums", 8, 20), ("Desk files", 11, 18),
    ("Bedding set", 3, 30), ("Cushions", 2, 45), ("Laptop and cables", 5, 10), ("Speaker", 9, 20),
]  # fmt: skip


def main() -> None:
    r = random.Random(1)
    items = [
        {"name": n, "kg": round(k * r.uniform(0.85, 1.15), 1), "litres": round(li * r.uniform(0.85, 1.15), 1)}
        for n, k, li in BASE
    ]
    r.shuffle(items)
    out = {"source": "Invented household items; weights and volumes are typical values with random jitter. MIT.",
           "box_kg": 20, "box_litres": 60, "items": items}  # fmt: skip
    Path(__file__).resolve().parents[1].joinpath("data", "items.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
