from __future__ import annotations

from datetime import date, timedelta

import pytest

from conftest import ROOT, monthly
from sniffer.detect import Txn, detect
from sniffer.evaluate import evaluate
from sniffer.io import StatementError, parse_csv
from sniffer.normalize import merchant_key

START = date(2026, 1, 5)


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("POS 927 STREAMBOX", "STREAMBOX"),
        ("FITPASS GYM*4821 LEEDS", "FITPASS GYM"),
        ("CARD PAYMENT TO MEALBOX 1234", "MEALBOX"),
        ("1234 5678", "1234 5678"),
    ],
)
def test_merchant_key(raw: str, key: str) -> None:
    assert merchant_key(raw) == key


def test_detects_monthly_subscription() -> None:
    res = detect(monthly("STREAMBOX*1 LONDON", 9.99, START, 6))
    assert len(res) == 1
    r = res[0]
    assert (r.merchant, r.cadence, r.charges) == ("STREAMBOX", "monthly", 6)
    assert r.annual_cost == pytest.approx(9.99 * 365 / 30, abs=0.05)
    assert r.active and r.confidence > 0.9


def test_ignores_irregular_spend() -> None:
    gaps = [1, 9, 2, 14, 3, 20, 5]
    d, txns = START, []
    for i, g in enumerate(gaps):
        d += timedelta(days=g)
        txns.append(Txn(d, "FRESHMART", -(10 + 7 * i)))
    assert detect(txns) == []


def test_regular_but_variable_amounts_are_not_subscriptions() -> None:
    amounts = [5, 40, 12, 90, 7, 33]
    txns = [Txn(START + timedelta(days=30 * i), "CORNER SHOP", -a) for i, a in enumerate(amounts)]
    assert detect(txns) == []


def test_price_hike_detected_with_annual_cost() -> None:
    txns = monthly("STREAMBOX", 12.99, START, 5) + monthly("STREAMBOX", 15.99, START + timedelta(days=150), 3)
    r = detect(txns)[0]
    assert len(r.hikes) == 1 and (r.hikes[0].old, r.hikes[0].new) == (12.99, 15.99)
    assert r.annual_hike_cost == pytest.approx(3.0 * 365 / 30, abs=0.1)


def test_noise_in_a_utility_bill_is_not_a_hike() -> None:
    amounts = [60, 66, 58, 64, 61, 65]
    txns = [Txn(START + timedelta(days=30 * i), "POWERGRID", -a) for i, a in enumerate(amounts)]
    r = detect(txns)
    assert r and r[0].hikes == []


def test_weekly_quarterly_and_yearly_cadences() -> None:
    weekly = monthly("MEALBOX", 24.5, START, 8, step=7)
    quarterly = monthly("SHIELDVPN", 29.97, START, 4, step=91)
    yearly = monthly("DOMAINSHOP", 14.0, START, 2, step=365)
    cad = {r.merchant: r.cadence for r in detect(weekly + quarterly + yearly)}
    assert cad == {"MEALBOX": "weekly", "SHIELDVPN": "quarterly", "DOMAINSHOP": "yearly"}


def test_cancelled_subscription_is_inactive() -> None:
    txns = monthly("GAMELOOP", 7.99, START, 4) + [Txn(START + timedelta(days=400), "OTHER", -1.0)]
    r = next(x for x in detect(txns) if x.merchant == "GAMELOOP")
    assert not r.active


def test_income_and_empty_input() -> None:
    assert detect([]) == []
    assert detect([Txn(START, "PAYROLL", 2500.0), Txn(START + timedelta(days=30), "PAYROLL", 2500.0)]) == []


def test_next_expected_date() -> None:
    r = detect(monthly("TUNENEST", 9.99, START, 4))[0]
    assert r.next_expected == (START + timedelta(days=90 + 30)).isoformat()


def test_detector_scores_on_synthetic_statement() -> None:
    res = evaluate(ROOT / "data" / "transactions.csv")
    assert res["detect_precision"] >= 0.9 and res["detect_recall"] >= 0.9, res


def test_parse_csv_errors() -> None:
    with pytest.raises(StatementError, match="missing columns"):
        parse_csv("date,amount\n2026-01-01,5\n")
    with pytest.raises(StatementError, match="bad date"):
        parse_csv("date,description,amount\nyesterday,X,5\n")
    with pytest.raises(StatementError, match="no rows"):
        parse_csv("date,description,amount\n")
