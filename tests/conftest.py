from __future__ import annotations

from pathlib import Path

import pytest

from packlist.optimizer import Item, load_gear

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def gear() -> list[Item]:
    return load_gear(ROOT / "data" / "gear.csv")


def it(id_: str, w: int, u: float, group: str = "") -> Item:
    return Item(id_, id_, "x", w, u, group, ())
