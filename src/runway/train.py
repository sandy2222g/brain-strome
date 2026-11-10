"""CLI: python -m runway.train"""
from __future__ import annotations

import argparse
from pathlib import Path

from runway.predictor import ScoreModel, load_dataset

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "study_sessions.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "models" / "score.joblib")
    args = ap.parse_args(argv)
    model = ScoreModel()
    m = model.fit(load_dataset(args.data))
    model.save(args.out)
    print(f"MAE {m['test_mae']} (baseline {m['baseline_mae']}), R2 {m['test_r2']}")


if __name__ == "__main__":
    main()
