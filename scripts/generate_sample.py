"""Build data/sample_party.json: 48 fictional guests for a demo wedding (no real people)."""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 3
FIRST = [
    "Maya",
    "Noor",
    "Leo",
    "Iris",
    "Omar",
    "Tessa",
    "Jonas",
    "Priya",
    "Felix",
    "Amara",
    "Hugo",
    "Lena",
    "Tariq",
    "Sofia",
    "Mateo",
    "Elin",
    "Kofi",
    "Nina",
    "Arjun",
    "Clara",
    "Idris",
    "Mila",
    "Rafael",
    "Yuki",
    "Ines",
    "Dario",
    "Hana",
    "Pavel",
    "Zara",
    "Bruno",
    "Leila",
    "Oskar",
    "Talia",
    "Emeka",
    "Vera",
    "Anton",
    "Sana",
    "Milo",
    "Rhea",
    "Casper",
    "Dina",
    "Ravi",
    "Greta",
    "Samir",
    "Alma",
    "Joel",
    "Nadia",
    "Theo",
]
GROUPS = [("Bride's family", 10), ("Groom's family", 10), ("College friends", 12), ("Work", 8), ("Neighbours", 8)]


def main() -> None:
    rng = random.Random(SEED)
    names = FIRST[:]
    rng.shuffle(names)
    guests, i = [], 0
    by_group: dict[str, list[str]] = {}
    for group, n in GROUPS:
        by_group[group] = []
        for _ in range(n):
            guests.append({"name": names[i], "group": group})
            by_group[group].append(names[i])
            i += 1
    together = [
        [by_group["Bride's family"][0], by_group["Bride's family"][1], by_group["Bride's family"][2]],
        [by_group["Groom's family"][0], by_group["Groom's family"][1]],
        [by_group["College friends"][0], by_group["College friends"][1]],
        [by_group["Work"][0], by_group["Work"][1]],
    ]
    likes = [
        [by_group["College friends"][3], by_group["Work"][2]],
        [by_group["Neighbours"][0], by_group["Bride's family"][5]],
        [by_group["Groom's family"][4], by_group["College friends"][5]],
        [by_group["Work"][4], by_group["Neighbours"][2]],
    ]
    dislikes = [
        [by_group["Bride's family"][3], by_group["Groom's family"][3]],
        [by_group["Work"][5], by_group["College friends"][6]],
    ]
    apart = [
        [by_group["Bride's family"][4], by_group["Groom's family"][5]],
        [by_group["Neighbours"][3], by_group["Work"][6]],
    ]
    out = {
        "table_size": 8,
        "guests": guests,
        "together": together,
        "likes": likes,
        "dislikes": dislikes,
        "apart": apart,
    }
    path = Path(__file__).resolve().parents[1] / "data" / "sample_party.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {len(guests)} guests to {path}")


if __name__ == "__main__":
    main()
