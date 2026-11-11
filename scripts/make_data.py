"""Generate data/sales.csv and data/truth.json: 12 weeks of invented bake-sale prices and units sold.

Demand is constant-elasticity, q = a * p^e, with log-normal noise (seed 7). The truth file is used only by tests
and the README to check the fitted curve; the app itself never reads it.
"""

import csv
import json
import math
import random
from pathlib import Path

ITEMS = {  # name: (unit cost, a, elasticity)
    "Brownie": (0.60, 600.0, -1.8),
    "Sourdough loaf": (1.80, 900.0, -1.3),
    "Cupcake": (0.50, 500.0, -2.4),
    "Cookie": (0.25, 300.0, -1.6),
    "Millionaire shortbread": (0.90, 200.0, -1.2),
}
MULTIPLES = [1.3, 1.6, 1.9, 2.2, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0]  # price as a multiple of unit cost


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "data"
    rng = random.Random(7)
    with (root / "sales.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "price", "units", "unit_cost"])
        for name, (cost, a, e) in ITEMS.items():
            for m in MULTIPLES:
                price = round(cost * m, 2)
                units = max(1, round(a * price**e * math.exp(rng.gauss(0, 0.12))))
                w.writerow([name, price, units, cost])
    truth = {n: {"unit_cost": c, "a": a, "elasticity": e} for n, (c, a, e) in ITEMS.items()}
    (root / "truth.json").write_text(json.dumps(truth, indent=1))


if __name__ == "__main__":
    main()
