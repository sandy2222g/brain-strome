"""CLI: python -m sniffer.train  (trains the category model and writes metrics)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from sniffer.categorize import CategoryModel
from sniffer.evaluate import evaluate

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, default=ROOT / "models" / "category.joblib")
    args = ap.parse_args(argv)
    model = CategoryModel()
    model.fit(pd.read_csv(args.data / "merchants.csv"))
    model.save(args.out)
    result = {**model.metrics, **evaluate(args.data / "transactions.csv")}
    args.out.with_suffix(".metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
