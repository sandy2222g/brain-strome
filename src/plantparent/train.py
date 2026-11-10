"""CLI: python -m plantparent.train"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from plantparent.model import IntervalModel

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "observations.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "models" / "interval.joblib")
    args = ap.parse_args(argv)
    m = IntervalModel()
    metrics = m.fit(pd.read_csv(args.data))
    m.save(args.out)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
