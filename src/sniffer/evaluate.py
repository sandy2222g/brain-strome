"""Score the detector against the synthetic ground truth (merchant kind labels)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sniffer.detect import detect
from sniffer.io import parse_csv


def evaluate(path: Path) -> dict[str, Any]:
    text = path.read_text()
    truth = {r["merchant"] for r in csv.DictReader(text.splitlines()) if r["kind"] in {"subscription", "bill"}}
    found = {r.merchant for r in detect(parse_csv(text))}
    tp = len(truth & found)
    precision = tp / len(found) if found else 0.0
    recall = tp / len(truth) if truth else 0.0
    return {
        "detect_precision": round(precision, 3),
        "detect_recall": round(recall, 3),
        "missed": sorted(truth - found),
        "false_alarms": sorted(found - truth),
    }
