"""CLI: train the models and write artifacts. Usage: python -m triage.train"""
from __future__ import annotations

import argparse
from pathlib import Path

from triage.model import TriageModel, load_dataset

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train the ticket triage model")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "tickets.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "models" / "triage.joblib")
    args = parser.parse_args(argv)
    model = TriageModel()
    metrics = model.fit(load_dataset(args.data))
    model.save(args.out)
    print(
        f"category acc={metrics['category_accuracy']} f1={metrics['category_macro_f1']} | "
        f"priority acc={metrics['priority_accuracy']} f1={metrics['priority_macro_f1']}"
    )
    print(f"saved model to {args.out}")


if __name__ == "__main__":
    main()
