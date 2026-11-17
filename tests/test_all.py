import pytest
from fastapi.testclient import TestClient

from dithering.api import app
from dithering.core import (
    BAYER4,
    METHODS,
    DitherError,
    atkinson,
    blur_error,
    brightness_gap,
    compare,
    dither,
    floyd_steinberg,
    images,
    ordered,
    threshold,
)

c = TestClient(app)
IM = images()


def test_images_are_valid_grey():
    assert set(IM) == {"ramp", "sphere", "waves"}
    for img in IM.values():
        assert len(img) == 96 and all(len(r) == 96 and all(0 <= v <= 1 for v in r) for r in img)


def test_outputs_are_pure_black_and_white_and_same_size():
    for m in METHODS:
        b = dither(IM["sphere"], m)
        assert len(b) == 96 and all(len(r) == 96 and set(r) <= {0, 1} for r in b)


def test_threshold_and_flat_greys():
    assert threshold([[0.49, 0.5]]) == [[0, 1]]
    flat = [[0.5] * 8 for _ in range(8)]
    assert sum(map(sum, floyd_steinberg(flat))) in range(30, 35)  # about half the pixels white
    assert sum(map(sum, [[1] * 8] * 8)) == 64 and not any(map(any, floyd_steinberg([[0.0] * 8] * 8)))
    assert all(all(r) for r in floyd_steinberg([[1.0] * 8] * 8))


def test_bayer_matrix_is_a_permutation():
    assert sorted(v for r in BAYER4 for v in r) == list(range(16))
    assert sum(map(sum, ordered([[0.5] * 4] * 4))) == 8


def test_error_diffusion_preserves_overall_brightness():
    for img in IM.values():
        assert brightness_gap(img, floyd_steinberg(img)) < 0.01
    assert brightness_gap(IM["sphere"], threshold(IM["sphere"])) > 0.03  # plain threshold shifts overall brightness


def test_floyd_steinberg_is_best_when_measured_fairly():
    for name, img in IM.items():
        e = {r["method"]: r["blur_error"] for r in compare(img)}
        assert e["floyd-steinberg"] == min(e.values()), name
        assert e["threshold"] > 4 * e["floyd-steinberg"], name


def test_measure_choice_can_flatter_a_method():
    ramp = IM["ramp"]  # a window the same size as the Bayer tile makes ordered dithering look better than it is
    assert blur_error(ramp, ordered(ramp), 4) < blur_error(ramp, floyd_steinberg(ramp), 4)
    assert blur_error(ramp, ordered(ramp), 5) > blur_error(ramp, floyd_steinberg(ramp), 5)


def test_atkinson_is_more_contrasty():
    assert blur_error(IM["sphere"], atkinson(IM["sphere"])) > blur_error(IM["sphere"], floyd_steinberg(IM["sphere"]))


def test_unknown_method():
    with pytest.raises(DitherError):
        dither(IM["ramp"], "nope")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/dither", params={"image": "ramp", "method": "ordered"}).json()
    assert len(r["bits"]) == 96 and set(r["bits"][0]) <= {"0", "1"} and len(r["table"]) == 4
    assert c.get("/dither", params={"method": "x"}).status_code == 422
    assert c.get("/dither", params={"image": "x"}).status_code == 404
    assert len(c.get("/images").json()["methods"]) == 4 and c.get("/").status_code == 200
