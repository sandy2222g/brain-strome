"""Regenerate the committed synthetic waste-event sample in data/ (recipes.csv is hand-written)."""
from __future__ import annotations

from pathlib import Path

from pantry.waste_model import generate_waste_events

DATA = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    DATA.mkdir(exist_ok=True)
    generate_waste_events(6000, seed=0).to_csv(DATA / "waste_events.csv", index=False)
    print("wrote", DATA / "waste_events.csv")


if __name__ == "__main__":
    main()
