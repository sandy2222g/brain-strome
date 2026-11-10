"""Train the model from the bundled synthetic survey and write models/carbon.joblib + models/metrics.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

from carbon.model import CarbonModel, load_dataset
from carbon.synth import DATA_PATH, ROOT, generate

MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "carbon.joblib"))


def train(data_path: Path = DATA_PATH, model_path: Path = MODEL_PATH) -> CarbonModel:
    if not data_path.exists():
        generate().to_csv(data_path, index=False)
    model = CarbonModel().fit(load_dataset(data_path))
    model.save(model_path)
    (model_path.parent / "metrics.json").write_text(json.dumps(model.metrics, indent=2), encoding="utf-8")
    return model


def main() -> None:
    model = train()
    print(json.dumps(model.metrics, indent=2))


if __name__ == "__main__":
    main()
