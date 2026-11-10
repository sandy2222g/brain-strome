"""Generate a fictional cohort for the demo (no real students). Run: python scripts/generate_students.py"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 17
SUBJECTS = ["Calculus", "Statistics", "Programming", "Physics", "Chemistry", "Academic writing"]
NAMES = [
    "Aiko",
    "Bruno",
    "Chloe",
    "Dev",
    "Esme",
    "Farid",
    "Gia",
    "Hector",
    "Ines",
    "Jamal",
    "Kira",
    "Leo",
    "Mina",
    "Niko",
    "Olu",
    "Pia",
    "Quentin",
    "Rosa",
    "Sven",
    "Tala",
    "Uma",
    "Viktor",
    "Wren",
    "Xavi",
    "Yara",
    "Zane",
    "Amal",
    "Boris",
]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PARTS = ["morning", "afternoon", "evening"]


def main() -> None:
    rng = random.Random(SEED)
    students = []
    for name in NAMES:
        skills = {s: rng.randint(0, 5) for s in SUBJECTS}
        slots = [f"{d} {p}" for d in DAYS for p in PARTS if rng.random() < 0.35]
        students.append(
            {
                "name": name,
                "skills": skills,
                "slots": slots,
                "style": rng.choice(["quiet", "chatty"]),
                "goal": rng.choice(["exam", "ongoing"]),
            }
        )
    out = Path(__file__).resolve().parents[1] / "data" / "students.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"subjects": SUBJECTS, "students": students}, indent=1))
    print(f"wrote {len(students)} students to {out}")


if __name__ == "__main__":
    main()
