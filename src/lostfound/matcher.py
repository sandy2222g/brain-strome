"""Train and run the matcher: TF-IDF similarity + attribute features -> logistic regression."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from lostfound.features import FEATURE_NAMES, Report, explain, pair_features, to_matrix
from lostfound.text import parse

BRANDS = frozenset(
    ["Norvik", "Alder", "Kestrel", "Brightline", "Tamsin", "Orbyt", "Quillon", "Haverly", "Zenmark", "Pico"]
)


@dataclass
class Candidate:
    found_id: str
    score: float
    description: str
    place: str
    date: str
    reasons: list[str]


def _report(row: pd.Series | dict[str, Any]) -> Report:
    return Report(date.fromisoformat(str(row["date"])), str(row["place"]), parse(str(row["description"]), BRANDS))


class Matcher:
    def __init__(self) -> None:
        self.tfidf = TfidfVectorizer(ngram_range=(1, 2))
        self.scaler = StandardScaler()
        self.clf = LogisticRegression(max_iter=2000, C=2.0)
        self.threshold = 0.5
        self.metrics: dict[str, Any] = {}

    # ---- scoring -------------------------------------------------------
    def _scores(self, lost: Report, found_reports: list[Report]) -> np.ndarray:
        sims = cosine_similarity(
            self.tfidf.transform([lost.attrs.tokens]), self.tfidf.transform([f.attrs.tokens for f in found_reports])
        )[0]
        feats = to_matrix([pair_features(lost, f, float(s)) for f, s in zip(found_reports, sims, strict=True)])
        return np.asarray(self.clf.predict_proba(self.scaler.transform(feats))[:, 1])

    def match(self, lost_row: dict[str, Any], found: pd.DataFrame, k: int = 5) -> list[Candidate]:
        if found.empty:
            return []
        lost = _report(lost_row)
        reports = [_report(r) for r in found.to_dict("records")]
        scores = self._scores(lost, reports)
        order = np.argsort(-scores)[:k]
        out = []
        for i in order:
            row = found.iloc[int(i)]
            out.append(
                Candidate(
                    str(row["id"]),
                    round(float(scores[i]), 4),
                    str(row["description"]),
                    str(row["place"]),
                    str(row["date"]),
                    explain(lost, reports[int(i)]),
                )
            )
        return out

    def is_confident(self, score: float) -> bool:
        return score >= self.threshold

    # ---- training ------------------------------------------------------
    def fit(self, found: pd.DataFrame, lost: pd.DataFrame, seed: int = 0) -> dict[str, Any]:
        rng = random.Random(seed)
        ids = sorted(lost["id"])
        rng.shuffle(ids)
        cut = int(len(ids) * 0.65)
        train_ids, test_ids = set(ids[:cut]), set(ids[cut:])
        train, test = lost[lost["id"].isin(train_ids)], lost[lost["id"].isin(test_ids)]
        self.tfidf.fit(list(found["description"].map(lambda d: parse(d, BRANDS).tokens)))
        f_reports = [_report(r) for r in found.to_dict("records")]
        f_index = {str(i): n for n, i in enumerate(found["id"])}

        x_rows, y = [], []
        for r in train.to_dict("records"):
            lost_rep = _report(r)
            sims = cosine_similarity(
                self.tfidf.transform([lost_rep.attrs.tokens]), self.tfidf.transform([f.attrs.tokens for f in f_reports])
            )[0]
            true = f_index.get(str(r["match_id"]))
            negatives = [n for n in range(len(f_reports)) if n != true]
            hard = sorted(negatives, key=lambda n: -sims[n])[:12]  # the most confusable wrong items
            picks = ([true] if true is not None else []) + hard + rng.sample(negatives, 8)
            for n in picks:
                x_rows.append(pair_features(lost_rep, f_reports[n], float(sims[n])))
                y.append(int(n == true))
        x = to_matrix(x_rows)
        self.scaler.fit(x)
        self.clf.fit(self.scaler.transform(x), np.asarray(y))

        self.threshold = self._tune_threshold(train, found, f_reports, f_index)
        self.metrics = self._evaluate(test, found, f_reports, f_index)
        self.metrics["threshold"] = round(self.threshold, 3)
        self.metrics["feature_weights"] = {
            n: round(float(w), 3) for n, w in zip(FEATURE_NAMES, self.clf.coef_[0], strict=True)
        }
        return self.metrics

    def _rank(self, row: dict[str, Any], f_reports: list[Report]) -> np.ndarray:
        return self._scores(_report(row), f_reports)

    def _tune_threshold(
        self, lost: pd.DataFrame, found: pd.DataFrame, f_reports: list[Report], f_index: dict[str, int]
    ) -> float:
        """Pick the score cut-off with the best F1 for declaring 'this is the owner's item'."""
        top: list[tuple[float, bool]] = []
        for r in lost.to_dict("records"):
            s = self._rank(r, f_reports)
            best = int(np.argmax(s))
            top.append((float(s[best]), f_index.get(str(r["match_id"])) == best))
        best_t, best_f1 = 0.5, -1.0
        for t in np.linspace(0.1, 0.95, 35):
            tp = sum(1 for s, ok in top if s >= t and ok)
            fp = sum(1 for s, ok in top if s >= t and not ok)
            fn = sum(1 for s, ok in top if s < t and ok)
            denom = 2 * tp + fp + fn
            f1 = 2 * tp / denom if denom else 0.0
            if f1 > best_f1:
                best_t, best_f1 = float(t), f1
        return best_t

    def _evaluate(
        self, lost: pd.DataFrame, found: pd.DataFrame, f_reports: list[Report], f_index: dict[str, int]
    ) -> dict[str, Any]:
        at1 = at3 = n_pos = tfidf1 = 0
        declared = correct = no_match = rejected = 0
        for r in lost.to_dict("records"):
            s = self._rank(r, f_reports)
            order = np.argsort(-s)
            true = f_index.get(str(r["match_id"]))
            lost_rep = _report(r)
            sims = cosine_similarity(
                self.tfidf.transform([lost_rep.attrs.tokens]), self.tfidf.transform([f.attrs.tokens for f in f_reports])
            )[0]
            if true is None:
                no_match += 1
                rejected += int(s[order[0]] < self.threshold)
                continue
            n_pos += 1
            at1 += int(order[0] == true)
            at3 += int(true in order[:3])
            tfidf1 += int(int(np.argmax(sims)) == true)
            if s[order[0]] >= self.threshold:
                declared += 1
                correct += int(order[0] == true)
        wrong_declared = no_match - rejected
        return {
            "n_test_reports": int(len(lost)),
            "with_match": n_pos,
            "recall_at_1": round(at1 / n_pos, 3),
            "recall_at_3": round(at3 / n_pos, 3),
            "baseline_text_only_recall_at_1": round(tfidf1 / n_pos, 3),
            "no_match_rejected": round(rejected / no_match, 3) if no_match else None,
            "precision_when_confident": round(correct / (declared + wrong_declared), 3)
            if declared + wrong_declared
            else None,
        }

    # ---- persistence ---------------------------------------------------
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> Matcher:
        obj = joblib.load(path)
        assert isinstance(obj, cls)
        return obj
