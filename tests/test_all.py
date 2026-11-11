import numpy as np
import pytest
from fastapi.testclient import TestClient

from digitpad.api import app, state
from digitpad.core import DigitError, accuracy, centre, fit, shift, shifted_accuracy, split, validate

XTR, XTE, YTR, YTE = split()
CLF = fit(XTR, YTR, True)
c = TestClient(app)


def test_split_is_stratified_and_disjoint_in_size():
    assert len(XTR) + len(XTE) == 1797 and set(np.unique(YTE)) == set(range(10))


def test_centre_moves_a_corner_blob_to_the_middle():
    img = np.zeros((8, 8))
    img[0:2, 0:2] = 16
    out = centre(img)
    ys, xs = np.nonzero(out)
    assert abs(ys.mean() - 3.5) <= 0.6 and abs(xs.mean() - 3.5) <= 0.6 and out.sum() == img.sum()


def test_centre_keeps_blank_images_blank():
    assert centre(np.zeros((8, 8))).sum() == 0


def test_shift_loses_only_pixels_pushed_off_the_edge():
    img = np.ones((8, 8))
    assert shift(img, 1, 0).sum() == 56


def test_accuracy_is_high_on_clean_test_set():
    assert accuracy(CLF, XTE, YTE) > 0.95


def test_centring_is_what_makes_it_robust_to_shifts():
    plain = fit(XTR, YTR, False)
    assert shifted_accuracy(CLF, XTE, YTE) > shifted_accuracy(plain, XTE, YTE) + 0.3


def test_probabilities_sum_to_one():
    p = CLF.proba(XTE[0])
    assert p.shape == (10,) and abs(p.sum() - 1) < 1e-6


def test_validate_rejects_bad_drawings():
    with pytest.raises(DigitError):
        validate([0.0] * 10)
    with pytest.raises(DigitError):
        validate([0.0] * 64)
    with pytest.raises(DigitError):
        validate([17.0] * 64)
    assert validate([1.0] * 64).shape == (8, 8)


def test_api_predict_matches_model_on_a_sample():
    s = state()
    pixels = [float(v) for v in s["x_test"][0].ravel()]
    r = c.post("/predict", json={"pixels": pixels}).json()
    assert r["digit"] == int(s["clf"].predict(s["x_test"][:1])[0]) and abs(sum(r["probabilities"]) - 1) < 0.01


def test_api_samples_and_metrics():
    sm = c.get("/samples").json()
    assert [d["label"] for d in sm] == list(range(10))
    m = c.get("/metrics").json()
    assert (
        m["accuracy"] > 0.95
        and len(m["confusion"]) == 10
        and m["shifted_accuracy"] > m["shifted_accuracy_without_centring"]
    )
    assert c.get("/health").json() == {"status": "ok"} and c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/predict", json={"pixels": [0.0] * 64}).status_code == 422
    assert c.post("/predict", json={"pixels": [0.0] * 3}).status_code == 422
