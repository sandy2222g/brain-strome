"""Handwritten-digit classifier on the 8x8 UCI optical-digits set bundled with scikit-learn.

Dataset: "Optical Recognition of Handwritten Digits" (E. Alpaydin, C. Kaynak), UCI Machine Learning
Repository, distributed with scikit-learn under the BSD licence. Pixel values run 0-16.

Drawn digits are first *centred* by their centre of mass, because users rarely paint the digit in the
exact middle of the grid and the classifier is sensitive to shifts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

SIZE = 8


class DigitError(ValueError):
    """Invalid drawing."""


def centre(img: np.ndarray) -> np.ndarray:
    """Shift an 8x8 image so its centre of mass sits as close to the middle as whole pixels allow."""
    total = img.sum()
    if total <= 0:
        return img
    ys, xs = np.indices(img.shape)
    cy, cx = (ys * img).sum() / total, (xs * img).sum() / total
    dy, dx = int(round(3.5 - cy)), int(round(3.5 - cx))
    out = np.zeros_like(img)
    for y in range(SIZE):
        for x in range(SIZE):
            ny, nx = y + dy, x + dx
            if 0 <= ny < SIZE and 0 <= nx < SIZE:
                out[ny, nx] = img[y, x]
    return out


def validate(pixels: list[float]) -> np.ndarray:
    if len(pixels) != SIZE * SIZE:
        raise DigitError(f"need {SIZE * SIZE} pixel values")
    a = np.asarray(pixels, dtype=float)
    if a.min() < 0 or a.max() > 16:
        raise DigitError("pixel values must be between 0 and 16")
    if a.sum() == 0:
        raise DigitError("the drawing is empty")
    return a.reshape(SIZE, SIZE)


@dataclass
class Classifier:
    scaler: StandardScaler
    model: CalibratedClassifierCV
    use_centre: bool = True

    def _prep(self, imgs: np.ndarray) -> np.ndarray:
        flat = np.array([centre(i) if self.use_centre else i for i in imgs]).reshape(len(imgs), -1)
        return self.scaler.transform(flat)

    def proba(self, img: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(self._prep(img[None]))[0]

    def predict(self, imgs: np.ndarray) -> np.ndarray:
        return self.model.predict(self._prep(imgs))


def split(seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    d = load_digits()
    return train_test_split(d.images, d.target, test_size=0.25, random_state=seed, stratify=d.target)


def fit(x_train: np.ndarray, y_train: np.ndarray, use_centre: bool = True) -> Classifier:
    imgs = np.array([centre(i) if use_centre else i for i in x_train]).reshape(len(x_train), -1)
    scaler = StandardScaler().fit(imgs)
    model = CalibratedClassifierCV(SVC(C=10, gamma="scale"), method="sigmoid", cv=3, ensemble=False).fit(
        scaler.transform(imgs), y_train
    )
    return Classifier(scaler, model, use_centre)


def shift(img: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.zeros_like(img)
    for y in range(SIZE):
        for x in range(SIZE):
            ny, nx = y + dy, x + dx
            if 0 <= ny < SIZE and 0 <= nx < SIZE:
                out[ny, nx] = img[y, x]
    return out


def accuracy(clf: Classifier, x: np.ndarray, y: np.ndarray) -> float:
    return float((clf.predict(x) == y).mean())


def shifted_accuracy(clf: Classifier, x: np.ndarray, y: np.ndarray, dy: int = 1, dx: int = 1) -> float:
    return accuracy(clf, np.array([shift(i, dy, dx) for i in x]), y)


def baseline_logreg(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, y_test: np.ndarray) -> float:
    lr = LogisticRegression(max_iter=2000).fit(x_train.reshape(len(x_train), -1), y_train)
    return float((lr.predict(x_test.reshape(len(x_test), -1)) == y_test).mean())


def confusion(clf: Classifier, x: np.ndarray, y: np.ndarray) -> list[list[int]]:
    return confusion_matrix(y, clf.predict(x), labels=list(range(10))).tolist()
