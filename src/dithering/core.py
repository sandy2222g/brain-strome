"""Turn grey images into pure black and white, four ways, and measure how well each one looks right."""
from __future__ import annotations

import math

Image = list[list[float]]  # rows of brightness in 0..1
Bits = list[list[int]]  # rows of 0 (black) or 1 (white)
SIZE = 96
BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
METHODS = ("threshold", "ordered", "floyd-steinberg", "atkinson")


class DitherError(ValueError):
    pass


def images() -> dict[str, Image]:
    """Three synthetic test pictures, generated in code so no files are needed."""
    n = SIZE
    ramp = [[x / (n - 1) for x in range(n)] for _ in range(n)]
    sphere: Image = []
    for y in range(n):
        row = []
        for x in range(n):
            dx, dy = (x - n * 0.4) / (n * 0.38), (y - n * 0.4) / (n * 0.38)
            r2 = dx * dx + dy * dy
            row.append(max(0.0, min(1.0, math.sqrt(1 - r2) * 0.9 + 0.08)) if r2 < 1 else 0.12 + 0.1 * y / n)
        sphere.append(row)
    waves = [[0.5 + 0.35 * math.sin(x / 7) * math.cos(y / 9) + 0.1 * math.sin((x + y) / 4) for x in range(n)]
             for y in range(n)]
    return {"ramp": ramp, "sphere": sphere, "waves": [[max(0.0, min(1.0, v)) for v in r] for r in waves]}


def threshold(img: Image) -> Bits:
    return [[int(v >= 0.5) for v in row] for row in img]


def ordered(img: Image) -> Bits:
    return [[int(v > (BAYER4[y % 4][x % 4] + 0.5) / 16) for x, v in enumerate(row)] for y, row in enumerate(img)]


def _diffuse(img: Image, taps: list[tuple[int, int, float]]) -> Bits:
    """Push each pixel's rounding error onto neighbours that are not yet decided."""
    h, w = len(img), len(img[0])
    buf = [row[:] for row in img]
    out = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            old = buf[y][x]
            new = 1 if old >= 0.5 else 0
            out[y][x] = new
            err = old - new
            for dx, dy, f in taps:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    buf[ny][nx] += err * f
    return out


def floyd_steinberg(img: Image) -> Bits:
    return _diffuse(img, [(1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)])


def atkinson(img: Image) -> Bits:
    """Spreads only 6/8 of the error: crisper, higher contrast, loses some shadow and highlight detail."""
    return _diffuse(img, [(1, 0, 1 / 8), (2, 0, 1 / 8), (-1, 1, 1 / 8), (0, 1, 1 / 8), (1, 1, 1 / 8), (0, 2, 1 / 8)])


def dither(img: Image, method: str) -> Bits:
    fn = {"threshold": threshold, "ordered": ordered, "floyd-steinberg": floyd_steinberg, "atkinson": atkinson}
    if method not in fn:
        raise DitherError(f"method must be one of {', '.join(METHODS)}")
    return fn[method](img)


def blur_error(img: Image, bits: Bits, k: int = 5) -> float:
    """Mean gap between k x k window averages, every window position: how different the two look from far away.
    k = 5 on purpose: a window of 4 would line up with the 4 x 4 Bayer tile and flatter that method."""
    h, w = len(img), len(img[0])
    tot, cnt = 0.0, 0
    for y in range(h - k + 1):
        for x in range(w - k + 1):
            a = sum(img[y + j][x + i] for j in range(k) for i in range(k)) / (k * k)
            b = sum(bits[y + j][x + i] for j in range(k) for i in range(k)) / (k * k)
            tot += abs(a - b)
            cnt += 1
    return tot / cnt


def brightness_gap(img: Image, bits: Bits) -> float:
    n = len(img) * len(img[0])
    return abs(sum(map(sum, img)) - sum(map(sum, bits))) / n


def compare(img: Image) -> list[dict[str, float | str]]:
    out = []
    for m in METHODS:
        b = dither(img, m)
        out.append({"method": m, "blur_error": round(blur_error(img, b), 4),
                    "brightness_gap": round(brightness_gap(img, b), 4)})
    return out
