"""Generate a synthetic support-ticket dataset (no real personal data).

Tickets are assembled from category-specific phrase templates plus shared
noise phrases, so the classifier has a realistic (non-trivial) task.
Run: python scripts/generate_data.py
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
N_PER_CATEGORY = 240

CATEGORIES: dict[str, dict[str, list[str]]] = {
    "billing": {
        "subjects": [
            "charged twice", "refund request", "invoice is wrong", "payment failed",
            "subscription renewal price", "cancel my plan billing", "unexpected charge",
        ],
        "bodies": [
            "I was charged twice for my monthly subscription and need a refund.",
            "The invoice shows the wrong amount compared to my plan price.",
            "My credit card payment keeps failing even though the card is valid.",
            "I see an unexpected charge on my statement from your company.",
            "Please send me a receipt for last month's payment.",
            "I cancelled but you still billed me this month.",
            "The discount code was not applied to my order total.",
        ],
    },
    "technical": {
        "subjects": [
            "app crashes on launch", "error 500 when saving", "cannot upload files",
            "sync is broken", "page loads forever", "bug in export", "login loop error",
        ],
        "bodies": [
            "The application crashes every time I open the dashboard.",
            "I get an error 500 whenever I try to save my project.",
            "File uploads hang at 90 percent and then time out.",
            "Data does not sync between my phone and the web app.",
            "The export to CSV produces an empty file with only headers.",
            "The page is extremely slow and sometimes shows a blank screen.",
            "After the last update the app freezes when I press the save button.",
        ],
    },
    "account": {
        "subjects": [
            "cannot reset password", "locked out of account", "change my email",
            "enable two factor", "delete my account", "update profile name", "no verification email",
        ],
        "bodies": [
            "I forgot my password and the reset email never arrives.",
            "My account is locked after several login attempts.",
            "I want to change the email address associated with my account.",
            "How do I enable two factor authentication for my profile?",
            "Please delete my account and all associated data.",
            "I did not receive the verification email after signing up.",
            "I need to update the display name on my profile.",
        ],
    },
    "shipping": {
        "subjects": [
            "order not delivered", "package damaged", "wrong item received",
            "tracking not updating", "delivery delayed", "change shipping address", "missing parcel",
        ],
        "bodies": [
            "My order was supposed to arrive last week and has not been delivered.",
            "The package arrived damaged and the product is broken.",
            "I received the wrong item, I ordered a blue one but got red.",
            "The tracking number has shown the same status for ten days.",
            "Can I change the delivery address before the parcel ships?",
            "The courier says the parcel was delivered but I never got it.",
            "One item is missing from my shipment.",
        ],
    },
    "feature_request": {
        "subjects": [
            "please add dark mode", "feature suggestion", "integration request",
            "would love bulk edit", "api rate limit increase idea", "idea for reports", "wishlist item",
        ],
        "bodies": [
            "It would be great if you added a dark mode option.",
            "Could you add an integration with our calendar tool?",
            "I suggest a bulk edit feature for managing many records at once.",
            "Please consider adding scheduled email reports.",
            "A keyboard shortcut for quick search would improve my workflow.",
            "Would it be possible to support exporting to PDF in the future?",
            "I would love custom dashboards with drag and drop widgets.",
        ],
    },
}

URGENT_PHRASES = [
    "this is urgent", "production is down", "we are losing customers", "need help immediately",
    "critical issue", "ASAP please", "business blocked",
]
HIGH_PHRASES = [
    "very frustrated", "still waiting for a reply", "third time contacting you", "important deadline tomorrow",
]
LOW_PHRASES = ["no rush", "whenever you have time", "just a small suggestion", "not urgent at all", "just curious"]
FILLER = ["Thanks.", "Regards.", "Hello team,", "Hi,", "Kind regards.", "Best,", "Thank you for your help."]


def make_ticket(rng: random.Random, category: str) -> dict[str, str]:
    spec = CATEGORIES[category]
    subject = rng.choice(spec["subjects"])
    parts = [rng.choice(FILLER[:3]), rng.choice(spec["bodies"])]
    if rng.random() < 0.5:
        parts.append(rng.choice(spec["bodies"]))
    roll = rng.random()
    # feature requests are rarely urgent; technical/billing/shipping more often
    if category == "feature_request":
        weights = (0.70, 0.25, 0.04, 0.01)
    elif category == "technical":
        weights = (0.15, 0.35, 0.25, 0.25)
    elif category == "billing":
        weights = (0.15, 0.45, 0.25, 0.15)
    else:
        weights = (0.30, 0.45, 0.17, 0.08)
    levels = ["low", "medium", "high", "urgent"]
    priority = rng.choices(levels, weights=weights)[0]
    if priority == "urgent":
        parts.append(rng.choice(URGENT_PHRASES))
    elif priority == "high":
        parts.append(rng.choice(HIGH_PHRASES))
    elif priority == "low":
        parts.append(rng.choice(LOW_PHRASES))
    elif roll < 0.3:
        parts.append(rng.choice(FILLER[3:]))
    # label noise: 3% of categories get swapped to a confusable one, to avoid a trivially perfect score
    label = category
    if rng.random() < 0.03:
        label = rng.choice([c for c in CATEGORIES if c != category])
    return {"subject": subject, "body": " ".join(parts), "category": label, "priority": priority}


def main() -> None:
    rng = random.Random(SEED)
    rows = [make_ticket(rng, c) for c in CATEGORIES for _ in range(N_PER_CATEGORY)]
    rng.shuffle(rows)
    out = Path(__file__).resolve().parents[1] / "data" / "tickets.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["subject", "body", "category", "priority"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} tickets to {out}")


if __name__ == "__main__":
    main()
