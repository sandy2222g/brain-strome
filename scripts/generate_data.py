"""Generate a synthetic 14-month bank statement (fictional merchants, no real person).

Writes data/transactions.csv (with ground-truth labels used only for evaluation) and
data/merchants.csv (merchant -> category, used to train the category classifier).
Run: python scripts/generate_data.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 5
END = date(2026, 10, 31)
START = date(2025, 9, 1)
CITIES = ["LONDON", "LEEDS", "BRISTOL", "DUBLIN", "CORK"]

# (name, category, kind). kind: subscription | bill | other
MERCHANTS: list[tuple[str, str, str]] = [
    ("STREAMBOX", "streaming", "subscription"), ("TUNENEST", "music", "subscription"),
    ("FITPASS GYM", "fitness", "subscription"), ("CLOUDVAULT", "software", "subscription"),
    ("NEWSDAILY", "news", "subscription"), ("GAMELOOP", "gaming", "subscription"),
    ("MEALBOX", "food", "subscription"), ("DOMAINSHOP", "software", "subscription"),
    ("SHIELDVPN", "software", "subscription"), ("POWERGRID ENERGY", "utilities", "bill"),
    ("HOMEKEY RENTALS", "housing", "bill"), ("SAFENEST INSURANCE", "insurance", "bill"),
    ("FRESHMART", "groceries", "other"), ("BEANCART COFFEE", "coffee", "other"),
    ("QUICKFUEL", "transport", "other"), ("PIZZA HARBOUR", "dining", "other"),
    ("HEALTHPLUS PHARMACY", "health", "other"), ("PAGETURN BOOKS", "shopping", "other"),
    # extra names only used to train the category classifier
    ("FILMFLIX PLUS", "streaming", "subscription"), ("SOUNDWAVE MUSIC", "music", "subscription"),
    ("IRONWORKS FITNESS", "fitness", "subscription"), ("DOCSTORE CLOUD", "software", "subscription"),
    ("DAILY HERALD", "news", "subscription"), ("PLAYZONE GAMES", "gaming", "subscription"),
    ("GREENCRATE MEALS", "food", "subscription"), ("CITY WATER", "utilities", "bill"),
    ("AQUAPOWER GAS", "utilities", "bill"), ("LANDLORD PROPERTY", "housing", "bill"),
    ("CARESURE INSURANCE", "insurance", "bill"), ("MARKET GROCER", "groceries", "other"),
    ("ROAST COFFEE HOUSE", "coffee", "other"), ("METRO TRANSIT", "transport", "other"),
    ("NOODLE BAR", "dining", "other"), ("WELLCARE CHEMIST", "health", "other"),
    ("CORNER BOOKSHOP", "shopping", "other"), ("SERIES STREAM TV", "streaming", "subscription"),
    ("BEATS RADIO", "music", "subscription"), ("YOGA STUDIO PASS", "fitness", "subscription"),
]


PREFIXES = [
    "BLUE", "NOVA", "PRIME", "METRO", "SUN", "PEAK", "ZEN", "BRIGHT", "SWIFT", "OAK", "RIVER", "URBAN", "LUMA", "ATLAS",
]
KEYWORDS: dict[str, tuple[str, list[str]]] = {
    "streaming": ("subscription", ["FLIX", "STREAM TV", "CINEMA PLUS", "WATCHLY", "SHOWTIME"]),
    "music": ("subscription", ["MUSIC", "TUNES", "RADIO", "SOUNDS", "BEATS"]),
    "fitness": ("subscription", ["GYM", "FITNESS", "YOGA", "CLIMBING CLUB", "SWIM CLUB"]),
    "software": ("subscription", ["CLOUD", "VPN", "APPS", "DOMAINS", "SOFTWARE"]),
    "news": ("subscription", ["NEWS", "TIMES", "HERALD", "DAILY", "MAGAZINE"]),
    "gaming": ("subscription", ["GAMES", "PLAY", "ARCADE", "ESPORTS", "PLAYPASS"]),
    "food": ("subscription", ["MEALBOX", "FOOD BOX", "RECIPE KIT", "FRESH CRATE", "SNACK BOX"]),
    "utilities": ("bill", ["ENERGY", "WATER", "GAS", "BROADBAND", "ELECTRIC"]),
    "housing": ("bill", ["RENTALS", "PROPERTY", "LETTINGS", "HOMES", "ESTATES"]),
    "insurance": ("bill", ["INSURANCE", "ASSURANCE", "COVER", "INSURE", "PROTECT"]),
    "groceries": ("other", ["MARKET", "GROCER", "SUPERMART", "FOODS", "FRESHMART"]),
    "coffee": ("other", ["COFFEE", "ROASTERS", "CAFE", "ESPRESSO", "COFFEE CART"]),
    "transport": ("other", ["FUEL", "TRANSIT", "TAXI", "PARKING", "RAIL"]),
    "dining": ("other", ["PIZZA", "NOODLES", "GRILL", "BISTRO", "KEBAB"]),
    "health": ("other", ["PHARMACY", "CHEMIST", "DENTAL", "OPTICIANS", "CLINIC"]),
    "shopping": ("other", ["BOOKS", "OUTLET", "HARDWARE", "GADGETS", "STORE"]),
}


def extra_merchants(rng: random.Random) -> list[tuple[str, str, str]]:
    """Invented names (prefix + category keyword) so the classifier sees enough variety."""
    out = []
    for cat, (kind, words) in KEYWORDS.items():
        for w in words:
            for pre in rng.sample(PREFIXES, 3):
                out.append((f"{pre} {w}", cat, kind))
    return out


def m_day(m: date, k: int) -> date:
    return m + timedelta(days=k)


def months(start: date, end: date) -> list[date]:
    out, d = [], date(start.year, start.month, 1)
    while d <= end:
        out.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def descr(rng: random.Random, name: str) -> str:
    ref = rng.randint(1000, 9999)
    style = rng.choice(["star", "pos", "card"])
    if style == "star":
        return f"{name}*{ref} {rng.choice(CITIES)}"
    if style == "pos":
        return f"POS {rng.randint(100, 999)} {name}"
    return f"CARD PAYMENT TO {name} {ref}"


def build(rng: random.Random) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []

    def add(d: date, name: str, amount: float, kind: str) -> None:
        if START <= d <= END:
            rows.append({"date": d.isoformat(), "description": descr(rng, name), "amount": round(-amount, 2),
                         "merchant": name, "kind": kind})

    ms = months(START, END)
    for i, m in enumerate(ms):
        rows.append({"date": m_day(m, 0).isoformat(), "description": "ACME PAYROLL", "amount": 2500.0,
                     "merchant": "ACME PAYROLL", "kind": "income"})
        add(m_day(m, 0), "HOMEKEY RENTALS", 900.0, "bill")
        add(m_day(m, rng.randint(2, 4)), "STREAMBOX", 12.99 if i < 9 else 15.99, "subscription")
        add(m_day(m, rng.randint(8, 10)), "TUNENEST", 9.99, "subscription")
        add(m_day(m, 14), "FITPASS GYM", 29.0, "subscription")
        add(m_day(m, rng.randint(17, 19)), "CLOUDVAULT", 2.99, "subscription")
        add(m_day(m, 21), "NEWSDAILY", 11.0 if i < 7 else 12.5, "subscription")
        if i < 8:
            add(m_day(m, 23), "GAMELOOP", 7.99, "subscription")  # cancelled after 8 months
        add(m_day(m, 25), "POWERGRID ENERGY", round(rng.uniform(58, 66), 2), "bill")
        add(m_day(m, 26), "SAFENEST INSURANCE", 34.2, "bill")
        for _ in range(rng.randint(6, 9)):
            add(m_day(m, rng.randint(0, 27)), "FRESHMART", round(rng.uniform(8, 85), 2), "other")
        for _ in range(rng.randint(6, 12)):
            add(m_day(m, rng.randint(0, 27)), "BEANCART COFFEE", round(rng.uniform(2.8, 5.2), 2), "other")
        for _ in range(rng.randint(2, 4)):
            add(m_day(m, rng.randint(0, 27)), rng.choice(["QUICKFUEL", "PIZZA HARBOUR"]),
                round(rng.uniform(9, 55), 2), "other")
        if rng.random() < 0.5:
            add(m_day(m, rng.randint(0, 27)), "HEALTHPLUS PHARMACY", round(rng.uniform(6, 30), 2), "other")
        if rng.random() < 0.35:
            add(m_day(m, rng.randint(0, 27)), "PAGETURN BOOKS", round(rng.uniform(8, 40), 2), "other")
    d = START + timedelta(days=3)
    while d <= END:  # weekly meal kit
        add(d + timedelta(days=rng.choice([0, 0, 1])), "MEALBOX", 24.5, "subscription")
        d += timedelta(days=7)
    for q in range(5):  # quarterly VPN
        add(START + timedelta(days=12 + 91 * q), "SHIELDVPN", 29.97, "subscription")
    add(date(2025, 9, 20), "DOMAINSHOP", 14.0, "subscription")  # yearly, seen twice
    add(date(2026, 9, 20), "DOMAINSHOP", 14.0, "subscription")
    rows.sort(key=lambda r: str(r["date"]))
    return rows


def main() -> None:
    rng = random.Random(SEED)
    root = Path(__file__).resolve().parents[1] / "data"
    root.mkdir(exist_ok=True)
    rows = [r for r in build(rng) if str(r["date"]) <= END.isoformat()]
    with (root / "transactions.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "description", "amount", "merchant", "kind"])
        w.writeheader()
        w.writerows(rows)
    with (root / "merchants.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["merchant", "category", "kind"])
        w.writerows(MERCHANTS + extra_merchants(random.Random(SEED + 1)))
    print(f"wrote {len(rows)} transactions and {len(MERCHANTS)} merchants to {root}")


if __name__ == "__main__":
    main()
