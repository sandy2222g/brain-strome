"""Dominant colour palette from an image via k-means++ (written from scratch) vs uniform binning."""

from __future__ import annotations

import io
import random
from collections import Counter
from pathlib import Path

from PIL import Image, UnidentifiedImageError

SAMPLE = Path(__file__).resolve().parents[2] / "static" / "sample.png"
Pixel = tuple[int, int, int]
MAX_SIDE = 64  # downscale so a request costs a few thousand pixels, whatever the upload size
MAX_BYTES = 5_000_000


class PaletteError(ValueError):
    """Raised for unreadable images or bad parameters."""


def pixels_from_bytes(data: bytes) -> list[Pixel]:
    if len(data) > MAX_BYTES:
        raise PaletteError("image larger than 5 MB")
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except (UnidentifiedImageError, OSError) as err:
        raise PaletteError("not a readable image") from err
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    return list(img.getdata())


def dist2(a: Pixel | tuple[float, ...], b: Pixel | tuple[float, ...]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b, strict=True))


def _init(px: list[Pixel], k: int, rng: random.Random) -> list[tuple[float, ...]]:
    """k-means++: each new centre is picked with probability proportional to squared distance."""
    centres: list[tuple[float, ...]] = [tuple(float(v) for v in rng.choice(px))]
    while len(centres) < k:
        d = [min(dist2(p, c) for c in centres) for p in px]
        if sum(d) == 0:
            break
        pick = rng.choices(range(len(px)), weights=d)[0]
        centres.append(tuple(float(v) for v in px[pick]))
    return centres


def kmeans(px: list[Pixel], k: int, seed: int = 0, iters: int = 40) -> list[tuple[float, ...]]:
    if not 1 <= k <= 12:
        raise PaletteError("k must be between 1 and 12")
    if not px:
        raise PaletteError("empty image")
    rng = random.Random(seed)
    centres = _init(px, min(k, len(set(px))), rng)
    for _ in range(iters):
        groups: list[list[Pixel]] = [[] for _ in centres]
        for p in px:
            groups[min(range(len(centres)), key=lambda i: dist2(p, centres[i]))].append(p)
        new = [
            tuple(sum(p[ch] for p in g) / len(g) for ch in range(3)) if g else c
            for g, c in zip(groups, centres, strict=True)
        ]
        if new == centres:
            break
        centres = new
    return centres


def uniform_bins(px: list[Pixel], k: int, levels: int = 4) -> list[tuple[float, ...]]:
    """Baseline: cut each channel into `levels` equal ranges and average the k most common cells."""
    if not 1 <= k <= 12:
        raise PaletteError("k must be between 1 and 12")
    step = 256 // levels
    cells: dict[tuple[int, int, int], list[Pixel]] = {}
    for p in px:
        cells.setdefault((p[0] // step, p[1] // step, p[2] // step), []).append(p)
    top = Counter({key: len(v) for key, v in cells.items()}).most_common(k)
    return [tuple(sum(p[ch] for p in cells[key]) / len(cells[key]) for ch in range(3)) for key, _ in top]


def mse(px: list[Pixel], centres: list[tuple[float, ...]]) -> float:
    """Mean squared colour error when every pixel is replaced by its nearest palette colour."""
    return sum(min(dist2(p, c) for c in centres) for p in px) / len(px)


def summarise(px: list[Pixel], centres: list[tuple[float, ...]]) -> list[dict[str, object]]:
    counts = Counter(min(range(len(centres)), key=lambda i: dist2(p, centres[i])) for p in px)
    rows = []
    for i, c in enumerate(centres):
        r, g, b = (round(v) for v in c)
        rows.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": [r, g, b], "share": round(counts[i] / len(px), 4)})
    return sorted(rows, key=lambda r: -float(r["share"]))  # type: ignore[arg-type]


def extract(px: list[Pixel], k: int, seed: int = 0) -> dict[str, object]:
    km, base = kmeans(px, k, seed), uniform_bins(px, k)
    return {
        "k": k,
        "pixels": len(px),
        "palette": summarise(px, km),
        "mse_kmeans": round(mse(px, km), 1),
        "baseline_palette": summarise(px, base),
        "mse_baseline": round(mse(px, base), 1),
    }
