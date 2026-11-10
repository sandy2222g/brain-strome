"""Generate synthetic lost-property data for a fictional campus (no real people or items).

Writes data/found.csv (items handed in) and data/lost.csv (reports from owners). About 65% of
lost reports have a true match in found.csv (column `match_id`); the rest do not, so the
matcher must also learn to say "no match". Run: python scripts/generate_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 21
N_FOUND = 320
N_LOST = 240
BASE = date(2026, 9, 1)

PLACES = [
    "main gate",
    "library",
    "cafeteria",
    "gym",
    "lab block",
    "lecture hall",
    "bus stop",
    "sports field",
    "dorm lobby",
    "car park",
]
ITEMS: dict[str, list[str]] = {
    "phone": ["phone", "mobile", "smartphone", "cellphone"],
    "wallet": ["wallet", "billfold", "purse"],
    "keys": ["keys", "key ring", "keychain"],
    "backpack": ["backpack", "rucksack", "school bag"],
    "umbrella": ["umbrella", "brolly"],
    "laptop": ["laptop", "notebook computer"],
    "glasses": ["glasses", "spectacles", "eyeglasses"],
    "bottle": ["water bottle", "flask", "drink bottle"],
    "jacket": ["jacket", "coat", "hoodie"],
    "headphones": ["headphones", "earphones", "earbuds"],
    "book": ["textbook", "book", "notebook"],
    "watch": ["watch", "wristwatch"],
    "scarf": ["scarf", "muffler"],
    "charger": ["charger", "power adapter", "charging cable"],
}
COLORS: dict[str, list[str]] = {
    "black": ["black", "jet black", "charcoal"],
    "blue": ["blue", "navy", "dark blue", "sky blue"],
    "red": ["red", "maroon", "crimson"],
    "green": ["green", "olive", "dark green"],
    "white": ["white", "cream", "off-white"],
    "grey": ["grey", "gray", "silver"],
    "brown": ["brown", "tan", "chocolate"],
    "yellow": ["yellow", "mustard"],
    "pink": ["pink", "rose"],
}
BRANDS = ["Norvik", "Alder", "Kestrel", "Brightline", "Tamsin", "Orbyt", "Quillon", "Haverly", "Zenmark", "Pico"]
EXTRAS = [
    "with a cracked corner",
    "with a sticker on it",
    "in a plastic cover",
    "slightly scratched",
    "with a small tear",
    "with a name tag",
    "with a blue lanyard",
    "very worn",
    "almost new",
    "with a keyring attached",
    "",
]


def describe(rng: random.Random, item: str, color: str, brand: str | None, extra: str, found: bool) -> str:
    noun = rng.choice(ITEMS[item])
    col = rng.choice(COLORS[color])
    parts = [f"{col} {noun}"]
    if brand and rng.random() < 0.7:
        parts.insert(0, brand)
    if extra and rng.random() < 0.8:
        parts.append(extra)
    prefix = rng.choice(["Found a", "Handed in a", "Picked up a"] if found else ["Lost my", "Missing:", "I lost a"])
    return f"{prefix} {' '.join(parts)}".replace("Found a Alder", "Found an Alder").strip()


def main() -> None:
    rng = random.Random(SEED)
    found, lost = [], []
    truth = []
    for i in range(N_FOUND):
        item = rng.choice(list(ITEMS))
        color = rng.choice(list(COLORS))
        brand = rng.choice(BRANDS) if rng.random() < 0.6 else None
        extra = rng.choice(EXTRAS)
        place = rng.choice(PLACES)
        day = BASE + timedelta(days=rng.randint(0, 40))
        found.append(
            {
                "id": f"F{i:04d}",
                "date": day.isoformat(),
                "place": place,
                "description": describe(rng, item, color, brand, extra, True),
            }
        )
        truth.append((item, color, brand, extra, place, day))
    for j in range(N_LOST):
        if rng.random() < 0.65:
            k = rng.randrange(N_FOUND)
            item, color, brand, extra, place, day = truth[k]
            lost_day = day - timedelta(days=rng.randint(0, 5))
            if rng.random() < 0.4:
                place = rng.choice(PLACES)
            mid = found[k]["id"]
        else:
            item, color = rng.choice(list(ITEMS)), rng.choice(list(COLORS))
            brand = rng.choice(BRANDS) if rng.random() < 0.6 else None
            extra, place = rng.choice(EXTRAS), rng.choice(PLACES)
            lost_day = BASE + timedelta(days=rng.randint(0, 40))
            mid = ""
        lost.append(
            {
                "id": f"L{j:04d}",
                "date": lost_day.isoformat(),
                "place": place,
                "description": describe(rng, item, color, brand, extra, False),
                "match_id": mid,
            }
        )
    root = Path(__file__).resolve().parents[1] / "data"
    root.mkdir(exist_ok=True)
    for name, rows in (("found", found), ("lost", lost)):
        with (root / f"{name}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    matched = sum(1 for r in lost if r["match_id"])
    print(f"wrote {len(found)} found items and {len(lost)} lost reports ({matched} with a match)")


if __name__ == "__main__":
    main()
