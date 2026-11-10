"""Write the committed sample data. Usage: python scripts/generate_sample.py (from the project root)."""

from __future__ import annotations

import json
from pathlib import Path

from roster.generator import generate

OUT = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for weeks, name in ((1, "sample_week.json"), (4, "sample_4weeks.json")):
        problem = generate(seed=2024, weeks=weeks)
        (OUT / name).write_text(json.dumps(problem.model_dump(), indent=2) + "\n")
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
