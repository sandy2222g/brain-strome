"""Regenerate data/sample_town.json from the seeded generator."""

import json
from pathlib import Path

from busroutes.instance import generate, instance_to_dict

if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "sample_town.json"
    out.write_text(json.dumps(instance_to_dict(generate()), indent=1) + "\n")
    print("wrote", out)
