"""Read transactions from CSV (columns: date, description, amount)."""
from __future__ import annotations

import csv
import io
from datetime import date

from sniffer.detect import Txn


class StatementError(ValueError):
    """Raised for unreadable statements; the message is safe to show to users."""


def parse_csv(text: str, max_rows: int = 20000) -> list[Txn]:
    reader = csv.DictReader(io.StringIO(text))
    cols = {c.strip().lower() for c in (reader.fieldnames or [])}
    missing = {"date", "description", "amount"} - cols
    if missing:
        raise StatementError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    out: list[Txn] = []
    for n, row in enumerate(reader, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        try:
            out.append(Txn(date.fromisoformat(row["date"]), row["description"], float(row["amount"])))
        except ValueError as exc:
            raise StatementError(f"row {n}: bad date or amount") from exc
        if len(out) > max_rows:
            raise StatementError(f"more than {max_rows} rows")
    if not out:
        raise StatementError("CSV has no rows")
    return out
