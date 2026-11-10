"""CLI: python -m noshow.train"""
from __future__ import annotations

import argparse
from pathlib import Path

from noshow.model import NoShowModel, load_dataset

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Train the no-show model")
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "appointments.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "models" / "noshow.joblib")
    args = ap.parse_args(argv)
    model = NoShowModel()
    m = model.fit(load_dataset(args.data))
    model.save(args.out)
    print(f"selected={m['selected_model']} test_auc={m['test_auc']} brier={m['test_brier']} "
          f"(baseline {m['baseline_brier']})")


if __name__ == "__main__":
    main()
