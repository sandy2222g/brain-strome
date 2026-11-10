"""CLI: python -m lostfound.train"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lostfound.matcher import Matcher

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, default=ROOT / "models" / "matcher.joblib")
    args = ap.parse_args(argv)
    m = Matcher()
    metrics = m.fit(pd.read_csv(args.data / "found.csv"), pd.read_csv(args.data / "lost.csv"))
    m.save(args.out)
    print(json.dumps({k: v for k, v in metrics.items() if k != "feature_weights"}))


if __name__ == "__main__":
    main()
