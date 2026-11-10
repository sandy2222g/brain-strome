"""Training, evaluation and inference for the ticket triage models."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

PRIORITY_ORDER = ["low", "medium", "high", "urgent"]
# Target first-response time (hours) per priority; a simple, explainable SLA table.
SLA_HOURS = {"low": 72, "medium": 24, "high": 8, "urgent": 1}


def build_text(subject: str, body: str) -> str:
    """Combine subject and body; the subject is repeated to up-weight it."""
    return f"{subject} {subject} {body}".strip()


def _pipeline() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=5.0)),
        ]
    )


@dataclass
class Prediction:
    category: str
    category_confidence: float
    priority: str
    priority_confidence: float
    sla_hours: int
    top_terms: list[str]


class TriageModel:
    """Two independent TF-IDF + logistic regression classifiers (category, priority)."""

    def __init__(self) -> None:
        self.category_pipe: Pipeline = _pipeline()
        self.priority_pipe: Pipeline = _pipeline()
        self.metrics: dict[str, object] = {}

    # ---- training -------------------------------------------------------
    def fit(self, df: pd.DataFrame, test_size: float = 0.2, seed: int = 42) -> dict[str, object]:
        texts = [build_text(s, b) for s, b in zip(df["subject"], df["body"], strict=True)]
        x_train, x_test, c_train, c_test, p_train, p_test = train_test_split(
            texts, df["category"], df["priority"], test_size=test_size, random_state=seed,
            stratify=df["category"],
        )
        self.category_pipe.fit(x_train, c_train)
        self.priority_pipe.fit(x_train, p_train)
        c_pred = self.category_pipe.predict(x_test)
        p_pred = self.priority_pipe.predict(x_test)
        self.metrics = {
            "n_train": len(x_train),
            "n_test": len(x_test),
            "category_accuracy": round(float(accuracy_score(c_test, c_pred)), 4),
            "category_macro_f1": round(float(f1_score(c_test, c_pred, average="macro")), 4),
            "priority_accuracy": round(float(accuracy_score(p_test, p_pred)), 4),
            "priority_macro_f1": round(float(f1_score(p_test, p_pred, average="macro")), 4),
            "category_report": classification_report(c_test, c_pred, output_dict=True, zero_division=0),
            "priority_report": classification_report(p_test, p_pred, output_dict=True, zero_division=0),
        }
        return self.metrics

    # ---- inference ------------------------------------------------------
    def predict(self, subject: str, body: str) -> Prediction:
        return self.predict_batch([(subject, body)])[0]

    def predict_batch(self, items: list[tuple[str, str]]) -> list[Prediction]:
        texts = [build_text(s, b) for s, b in items]
        c_proba = self.category_pipe.predict_proba(texts)
        p_proba = self.priority_pipe.predict_proba(texts)
        c_classes = self.category_pipe.classes_
        p_classes = self.priority_pipe.classes_
        out: list[Prediction] = []
        for i, text in enumerate(texts):
            ci = int(np.argmax(c_proba[i]))
            pi = int(np.argmax(p_proba[i]))
            priority = str(p_classes[pi])
            out.append(
                Prediction(
                    category=str(c_classes[ci]),
                    category_confidence=round(float(c_proba[i][ci]), 4),
                    priority=priority,
                    priority_confidence=round(float(p_proba[i][pi]), 4),
                    sla_hours=SLA_HOURS[priority],
                    top_terms=self._top_terms(text, ci),
                )
            )
        return out

    def _top_terms(self, text: str, class_index: int, k: int = 5) -> list[str]:
        """Explain a category prediction: terms in the text with the largest contribution."""
        tfidf: TfidfVectorizer = self.category_pipe.named_steps["tfidf"]
        clf: LogisticRegression = self.category_pipe.named_steps["clf"]
        vec = tfidf.transform([text])
        if vec.nnz == 0:
            return []
        names = tfidf.get_feature_names_out()
        coefs = clf.coef_[class_index] if clf.coef_.shape[0] > 1 else clf.coef_[0]
        idx = vec.indices
        contrib = vec.data * coefs[idx]
        order = np.argsort(-contrib)[:k]
        return [str(names[idx[j]]) for j in order if contrib[j] > 0]

    # ---- persistence ----------------------------------------------------
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"category": self.category_pipe, "priority": self.priority_pipe, "metrics": self.metrics}, path
        )
        path.with_suffix(".metrics.json").write_text(json.dumps(self.metrics, indent=2))

    @classmethod
    def load(cls, path: Path) -> TriageModel:
        blob = joblib.load(path)
        model = cls()
        model.category_pipe = blob["category"]
        model.priority_pipe = blob["priority"]
        model.metrics = blob["metrics"]
        return model


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).dropna(subset=["subject", "body", "category", "priority"])
    unknown = set(df["priority"]) - set(PRIORITY_ORDER)
    if unknown:
        raise ValueError(f"unknown priority labels: {sorted(unknown)}")
    return df
