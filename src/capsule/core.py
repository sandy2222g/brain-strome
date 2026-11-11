"""Choose which clothes go in a carry-on so the most outfits are possible under a weight limit.

An outfit is one top, one bottom and one pair of shoes that share a style (smart or casual); items with style
"neutral" go with both. A layer (jacket, jumper) is optional and multiplies the outfits by (1 + layers that
match the style). Outfits are counted per style, so a neutral top worn with smart trousers is a different outfit
from the same top worn with casual ones.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "wardrobe.json"
KINDS = ("top", "bottom", "shoes", "layer")
STYLES = ("smart", "casual", "neutral")
MAX_ITEMS = 20


class CapsuleError(ValueError):
    """Invalid wardrobe."""


@dataclass(frozen=True)
class Garment:
    name: str
    kind: str
    style: str
    g: int


def load(path: Path = DATA) -> tuple[int, list[Garment]]:
    raw = json.loads(path.read_text())
    return raw["limit_g"], [Garment(i["name"], i["kind"], i["style"], i["g"]) for i in raw["items"]]


def validate(limit_g: int, items: list[Garment]) -> None:
    if limit_g <= 0:
        raise CapsuleError("weight limit must be positive")
    if not items:
        raise CapsuleError("empty wardrobe")
    if len(items) > MAX_ITEMS:
        raise CapsuleError(f"at most {MAX_ITEMS} items")
    if len({i.name for i in items}) != len(items):
        raise CapsuleError("item names must be unique")
    for i in items:
        if i.kind not in KINDS or i.style not in STYLES or i.g <= 0:
            raise CapsuleError(f"invalid item '{i.name}'")


def outfits(chosen: list[Garment]) -> int:
    total = 0
    for style in ("smart", "casual"):
        pick = {k: sum(1 for g in chosen if g.kind == k and g.style in (style, "neutral")) for k in KINDS}
        total += pick["top"] * pick["bottom"] * pick["shoes"] * (1 + pick["layer"])
    return total


def weight(chosen: list[Garment]) -> int:
    return sum(g.g for g in chosen)


def pack_in_order(limit_g: int, items: list[Garment]) -> list[Garment]:
    """Baseline: pack in the order listed (your favourites first) and skip what no longer fits."""
    validate(limit_g, items)
    out: list[Garment] = []
    for g in items:
        if weight(out) + g.g <= limit_g:
            out.append(g)
    return out


def lightest_first(limit_g: int, items: list[Garment]) -> list[Garment]:
    """Heuristic: take the lightest garments first. Packs a lot, but ignores which pieces go together."""
    validate(limit_g, items)
    out: list[Garment] = []
    for g in sorted(items, key=lambda x: x.g):
        if weight(out) + g.g <= limit_g:
            out.append(g)
    return out


def best_capsule(limit_g: int, items: list[Garment]) -> list[Garment]:
    """Exact: try every subset (at most 2^20) and keep the one with the most outfits, lightest on ties."""
    validate(limit_g, items)
    n = len(items)
    best: tuple[int, int, int] = (-1, 0, 0)
    for mask in range(1 << n):
        chosen = [items[k] for k in range(n) if mask >> k & 1]
        w = weight(chosen)
        if w > limit_g:
            continue
        o = outfits(chosen)
        if (o, -w) > (best[0], -best[1]):
            best = (o, w, mask)
    return [items[k] for k in range(n) if best[2] >> k & 1]
