import pytest
from fastapi.testclient import TestClient

from receiptread.api import app
from receiptread.core import ReceiptError, check, evaluate, load, naive_items, parse, parse_item, to_cents

c = TestClient(app)


def test_to_cents_repairs_ocr_confusions():
    assert to_cents("12.50") == 1250
    assert to_cents("$1O,5O") == 1050
    assert to_cents("l.lI") == 111  # l and I read as 1


def test_item_formats():
    assert parse_item("Latte               4.50") == {"name": "Latte", "qty": 1, "total_cents": 450}
    assert parse_item("2 x Latte ...... $9.00") == {"name": "Latte", "qty": 2, "total_cents": 900}
    assert parse_item("Latte        3@4.50  13.50") == {"name": "Latte", "qty": 3, "total_cents": 1350}
    assert parse_item("Latte                4,5O")["total_cents"] == 450  # type: ignore[index]


def test_non_items_are_skipped():
    assert parse_item("CORNER CAFE") is None
    assert parse_item("12.50") is None  # a price with no name
    r = parse("CORNER CAFE\n2026-03-14 12:44\nTHANK YOU\nTea 2.00\n")
    assert len(r["items"]) == 1  # type: ignore[arg-type]


def test_totals_keywords_and_order():
    r = parse("Tea 2.00\nCake 3.00\nSUBTOTAL 5.00\nVAT 20% 1.00\nGratuity 0.50\nAmount due 6.50\n")
    assert r["totals"] == {"subtotal": 500, "tax": 100, "tip": 50, "total": 650} and r["issues"] == []


def test_arithmetic_checks_by_hand():
    items = [{"name": "a", "qty": 1, "total_cents": 500}, {"name": "b", "qty": 1, "total_cents": 250}]
    assert check(items, {"subtotal": 750, "tax": 60, "total": 810}) == []
    assert check(items, {"subtotal": 700, "tax": 56, "total": 756}) == ["items_sum_mismatch"]
    assert check(items, {"subtotal": 750, "tax": 60, "total": 800}) == ["total_mismatch"]
    assert check(items, {"total": 750}) == []  # no subtotal: fall back to the item sum


def test_beats_naive_baseline_on_sample_receipts():
    e = evaluate()
    assert e["items"] == 47 and e["parser_accuracy"] == 1.0 and e["baseline_accuracy"] == 0.404
    assert e["issue_detection"] == "8/8"
    assert len(naive_items(load()[0]["text"])) <= len(parse(load()[0]["text"])["items"])  # type: ignore[arg-type]


def test_validation():
    with pytest.raises(ReceiptError):
        parse("   \n")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    s = c.get("/samples").json()["samples"]
    assert len(s) == 8
    r = c.post("/parse", json={"text": s[6]["text"]}).json()
    assert r["issues"] == ["total_mismatch"] and len(r["items"]) >= 4
    assert c.post("/parse", json={"text": ""}).status_code == 422
    assert c.get("/evaluation").json()["parser_accuracy"] == 1.0 and c.get("/").status_code == 200
