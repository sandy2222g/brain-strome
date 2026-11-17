import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from palettex.api import app
from palettex.core import SAMPLE, PaletteError, dist2, extract, kmeans, mse, pixels_from_bytes, uniform_bins

c = TestClient(app)


def png(colours: list[tuple[int, int, int]], size: int = 8) -> bytes:
    img = Image.new("RGB", (size * len(colours), size))
    for i, col in enumerate(colours):
        img.paste(col, (i * size, 0, (i + 1) * size, size))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_recovers_flat_colours_exactly():
    px = pixels_from_bytes(png([(255, 0, 0), (0, 255, 0), (0, 0, 255)]))
    centres = kmeans(px, 3)
    assert sorted(tuple(round(v) for v in c_) for c_ in centres) == [(0, 0, 255), (0, 255, 0), (255, 0, 0)]
    assert mse(px, centres) == 0


def test_shares_add_up_and_sorted():
    r = extract(pixels_from_bytes(SAMPLE.read_bytes()), 5)
    shares = [p["share"] for p in r["palette"]]
    assert shares == sorted(shares, reverse=True) and sum(shares) == pytest.approx(1.0, abs=0.01)
    assert all(p["hex"].startswith("#") and len(p["hex"]) == 7 for p in r["palette"])


def test_kmeans_beats_uniform_binning_on_sample():
    r = extract(pixels_from_bytes(SAMPLE.read_bytes()), 5)
    assert r["mse_kmeans"] == 200.5 and r["mse_baseline"] == 465.1


def test_more_colours_never_hurt():
    px = pixels_from_bytes(SAMPLE.read_bytes())
    errs = [mse(px, kmeans(px, k)) for k in (2, 4, 8)]
    assert errs[0] > errs[1] > errs[2]


def test_deterministic():
    px = pixels_from_bytes(SAMPLE.read_bytes())
    assert kmeans(px, 4, seed=1) == kmeans(px, 4, seed=1)


def test_fewer_distinct_colours_than_k():
    px = pixels_from_bytes(png([(10, 10, 10), (200, 200, 200)]))
    assert len(kmeans(px, 6)) == 2
    assert dist2((1, 2, 3), (1, 2, 3)) == 0


def test_validation():
    for bad in (b"not an image", b""):
        with pytest.raises(PaletteError):
            pixels_from_bytes(bad)
    with pytest.raises(PaletteError):
        pixels_from_bytes(b"x" * 5_000_001)
    px = pixels_from_bytes(png([(1, 1, 1)]))
    for k in (0, 13):
        with pytest.raises(PaletteError):
            kmeans(px, k)
        with pytest.raises(PaletteError):
            uniform_bins(px, k)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/palette", data={"k": "4"}).json()  # no file: bundled sample
    assert len(r["palette"]) == 4 and r["mse_kmeans"] < r["mse_baseline"]
    up = c.post("/palette", data={"k": "2"}, files={"file": ("a.png", png([(255, 0, 0), (0, 0, 255)]), "image/png")})
    assert up.status_code == 200 and {p["hex"] for p in up.json()["palette"]} == {"#ff0000", "#0000ff"}
    assert c.post("/palette", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 422
    assert c.post("/palette", data={"k": "99"}).status_code == 422
    assert c.get("/").status_code == 200
