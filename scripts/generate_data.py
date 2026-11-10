"""Generate the species catalogue and synthetic watering observations.

The catalogue holds general, illustrative care values (not horticultural advice). The observations
simulate how many days a pot stays moist, using a simple drying model plus noise, so the
regression has something to learn. Run: python scripts/generate_data.py
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

SEED = 13
# name, light, base days between waterings (15 cm plastic pot, medium light, spring), pet_safe, tip
SPECIES = [
    ("Snake plant", "low", 18, False, "Let the soil dry fully; rot is the main risk."),
    ("Monstera", "medium", 8, False, "Water when the top 5 cm are dry."),
    ("Pothos", "low", 9, False, "Forgiving; leaves droop when thirsty."),
    ("Peace lily", "low", 6, False, "Droops dramatically when dry and recovers fast."),
    ("Spider plant", "medium", 7, True, "Brown tips often mean fluoride or dry air."),
    ("Rubber plant", "bright", 10, False, "Wipe leaves; water when top 3 cm are dry."),
    ("ZZ plant", "low", 21, False, "Stores water in rhizomes; err on the dry side."),
    ("Fiddle leaf fig", "bright", 8, False, "Dislikes drafts and moving."),
    ("Aloe vera", "bright", 16, False, "Soak, then dry out completely."),
    ("Jade plant", "bright", 17, False, "Wrinkled leaves mean it is thirsty."),
    ("Boston fern", "medium", 4, True, "Keep soil evenly moist, mist in dry air."),
    ("Calathea", "medium", 5, True, "Prefers soft water; curls when dry."),
    ("Philodendron", "medium", 8, False, "Water when the top 4 cm are dry."),
    ("Chinese money plant", "bright", 9, True, "Rotate weekly for even growth."),
    ("Parlor palm", "low", 7, True, "Keep lightly moist, never soggy."),
    ("Cast iron plant", "low", 12, True, "Nearly indestructible; avoid overwatering."),
    ("Prayer plant", "medium", 5, True, "Leaves fold at night; likes humidity."),
    ("Dracaena", "medium", 11, False, "Sensitive to salts in tap water."),
    ("String of pearls", "bright", 15, False, "Water sparingly; pearls shrivel when dry."),
    ("Orchid (Phalaenopsis)", "medium", 8, True, "Water the roots, not the crown."),
    ("Hoya", "bright", 12, True, "Let dry between waterings; flowers on old stems."),
    ("Succulent mix", "bright", 14, True, "Bright light and fast-draining soil."),
    ("Basil (kitchen)", "bright", 3, True, "Pinch flowers; likes moist soil."),
    ("Mint (kitchen)", "medium", 3, False, "Thirsty; keep in its own pot."),
]
MATERIAL = {"terracotta": 0.75, "plastic": 1.0, "ceramic": 1.1}
LIGHT = {"low": 1.35, "medium": 1.0, "bright": 0.8}
SEASON = {"winter": 1.5, "spring": 1.0, "summer": 0.85, "autumn": 1.2}


def interval(base: float, pot: float, material: str, light: str, season: str, temp: float, humidity: float) -> float:
    return (
        base
        * (pot / 15) ** 0.6
        * MATERIAL[material]
        * LIGHT[light]
        * SEASON[season]
        * math.exp(-(temp - 20) * 0.03)
        * (1 + (humidity - 50) / 300)
    )


def main() -> None:
    rng = random.Random(SEED)
    root = Path(__file__).resolve().parents[1] / "data"
    root.mkdir(exist_ok=True)
    with (root / "species.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["species", "light", "base_days", "pet_safe", "tip"])
        for name, light, base, pet, tip in SPECIES:
            w.writerow([name, light, base, int(pet), tip])
    rows = []
    for _ in range(4000):
        name, _light, base, _pet, _tip = rng.choice(SPECIES)
        pot = rng.choice([8, 10, 12, 14, 15, 17, 20, 24, 30])
        material = rng.choice(list(MATERIAL))
        light = rng.choice(list(LIGHT))
        season = rng.choice(list(SEASON))
        temp = round(rng.gauss(21, 3), 1)
        humidity = round(min(80, max(20, rng.gauss(45, 12))), 1)
        days = interval(base, pot, material, light, season, temp, humidity) * math.exp(rng.gauss(0, 0.12))
        rows.append([name, base, pot, material, light, season, temp, humidity, round(days, 1)])
    with (root / "observations.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["species", "base_days", "pot_cm", "material", "light", "season", "temp_c", "humidity", "days_until_dry"]
        )
        w.writerows(rows)
    print(f"wrote {len(SPECIES)} species and {len(rows)} observations to {root}")


if __name__ == "__main__":
    main()
