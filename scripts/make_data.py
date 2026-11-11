"""Generate synthetic SMS messages (spam and ham) from templates; labels are known by construction."""

from __future__ import annotations

import csv
import random
from pathlib import Path

HAM = [
    "are you still coming to {place} at {time}",
    "can you pick up {food} on the way home",
    "running late, see you at {time}",
    "thanks for dinner last night, it was lovely",
    "did you finish the {work} yet",
    "happy birthday {name}! hope you have a great day",
    "mum says call her when you get a minute",
    "meeting moved to {time}, room {num}",
    "i left my keys at {place}, can you check",
    "great game today, same time next week",
    "don't forget {food} for the party",
    "the {work} is due on friday, want to study together",
]
SPAM = [
    "WINNER! you have won a {prize}, claim now at {url}",
    "free entry to win {prize}, text WIN to {num} now",
    "urgent: your account is suspended, verify at {url}",
    "congratulations, you are selected for a {prize}, call {num} now",
    "limited offer, get {pct}% off today only, click {url}",
    "you owe unpaid fees, pay now at {url} to avoid penalty",
    "claim your free {prize} today, reply YES to {num}",
    "final notice: parcel waiting, confirm delivery fee at {url}",
]
FILL = {
    "place": ["the cafe", "the gym", "the station", "your place", "the library"],
    "time": ["6pm", "7:30", "noon", "8 tonight", "9am"],
    "food": ["milk", "pizza", "bread", "eggs", "pasta"],
    "work": ["report", "homework", "slides", "essay", "project"],
    "name": ["Sam", "Priya", "Leo", "Maya", "Omar"],
    "num": ["4", "12", "80222", "63333", "5"],
    "prize": ["new phone", "holiday voucher", "cash prize", "gift card", "free tablet"],
    "url": ["bit.example/x7k", "prize-claim.example", "secure-login.example", "win.example/now"],
    "pct": ["50", "70", "90"],
}


def fill(t: str, rng: random.Random) -> str:
    out = t
    for k, vals in FILL.items():
        while "{" + k + "}" in out:
            out = out.replace("{" + k + "}", rng.choice(vals), 1)
    return out


def noisy(msg: str, rng: random.Random) -> str:
    words = msg.split()
    if rng.random() < 0.3 and len(words) > 3:
        words.insert(rng.randrange(len(words)), rng.choice(["ok", "so", "hey", "well", "btw", "lol", "now"]))
    return " ".join(words)


def make(n: int = 900, spam_rate: float = 0.25, seed: int = 21) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        if rng.random() < spam_rate:
            rows.append(("spam", noisy(fill(rng.choice(SPAM), rng), rng)))
        else:
            rows.append(("ham", noisy(fill(rng.choice(HAM), rng), rng)))
    return rows


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "messages.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["label", "text"])
        w.writerows(make())
    print("wrote", out)
