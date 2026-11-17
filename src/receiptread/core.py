"""Parse receipt text into items and totals, and flag arithmetic that does not add up."""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "receipts.json"
MONEY = re.compile(r"\$?[0-9OolI]+[.,][0-9OolI]{2}(?![0-9A-Za-z])")
TOTAL_WORDS = [("subtotal", "subtotal"), ("sub total", "subtotal"), ("tax", "tax"), ("vat", "tax"),
               ("tip", "tip"), ("gratuity", "tip"), ("amount due", "total"), ("total", "total")]


class ReceiptError(ValueError):
    """Invalid input."""


def to_cents(token: str) -> int:
    """'$1O,5O' -> 1050. Letters that OCR confuses with digits are repaired inside the amount only."""
    t = token.lstrip("$").translate(str.maketrans("OolI", "0011")).replace(",", ".")
    whole, frac = t.split(".")
    return int(whole) * 100 + int(frac)


def parse_item(line: str) -> dict[str, object] | None:
    ms = list(MONEY.finditer(line))
    if not ms:
        return None
    total = ms[-1]
    head = line[: total.start()]
    qty = 1
    at = re.search(r"(\d+)\s*@\s*" + MONEY.pattern + r"\s*$", head)
    if at:
        qty, head = int(at.group(1)), head[: at.start()]
    else:
        lead = re.match(r"^\s*(\d+)\s*[xX]\s+", head)
        if lead:
            qty, head = int(lead.group(1)), head[lead.end():]
    name = re.sub(r"[\s.\-_*]+$", "", head).strip()
    if not name or not re.search(r"[A-Za-z]", name):
        return None
    return {"name": name, "qty": qty, "total_cents": to_cents(total.group(0))}


def parse(text: str) -> dict[str, object]:
    if not text.strip():
        raise ReceiptError("receipt text must not be empty")
    items: list[dict[str, object]] = []
    totals: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        ms = list(MONEY.finditer(line))
        if not ms:
            continue
        kind = next((k for w, k in TOTAL_WORDS if low.startswith(w)), None)
        if kind:
            totals[kind] = to_cents(ms[-1].group(0))
        else:
            it = parse_item(line)
            if it:
                items.append(it)
    return {"items": items, "totals": {"subtotal": totals.get("subtotal"), "tax": totals.get("tax", 0),
                                      "tip": totals.get("tip", 0), "total": totals.get("total")},
            "issues": check(items, totals)}


def check(items: list[dict[str, object]], totals: dict[str, int]) -> list[str]:
    issues: list[str] = []
    item_sum = sum(int(i["total_cents"]) for i in items)  # type: ignore[call-overload]
    sub = totals.get("subtotal")
    if sub is not None and item_sum != sub:
        issues.append("items_sum_mismatch")
    base = sub if sub is not None else item_sum
    if "total" in totals and base + totals.get("tax", 0) + totals.get("tip", 0) != totals["total"]:
        issues.append("total_mismatch")
    return issues


def load(path: Path = DATA) -> list[dict[str, object]]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


NAIVE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z ]*?)\s+(?P<p>\d+\.\d{2})$")


def naive_items(text: str) -> list[dict[str, object]]:
    """Baseline: 'words then a dotted price at end of line', skipping all total lines."""
    out = []
    for line in text.splitlines():
        m = NAIVE.match(line.strip())
        if m and not any(line.lower().strip().startswith(w) for w, _ in TOTAL_WORDS):
            out.append({"name": m["name"], "qty": 1, "total_cents": to_cents(m["p"])})
    return out


def evaluate() -> dict[str, object]:
    rs = load()
    expected = sum(len(r["items"]) for r in rs)  # type: ignore[arg-type]
    ours = base = issue_ok = 0
    for r in rs:
        want = {(i["name"], i["qty"], i["total_cents"]) for i in r["items"]}  # type: ignore[attr-defined]
        got = {(i["name"], i["qty"], i["total_cents"]) for i in parse(str(r["text"]))["items"]}  # type: ignore[attr-defined]
        nb = {(i["name"], i["qty"], i["total_cents"]) for i in naive_items(str(r["text"]))}
        ours += len(want & got)
        base += len(want & nb)
        issue_ok += parse(str(r["text"]))["issues"] == r["issues"]
    return {"receipts": len(rs), "items": expected, "parser_accuracy": round(ours / expected, 3),
            "baseline_accuracy": round(base / expected, 3), "issue_detection": f"{issue_ok}/{len(rs)}"}
