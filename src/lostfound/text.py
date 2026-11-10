"""Turn free-text item descriptions into attributes (category, colour, brand, extras)."""

from __future__ import annotations

import re
from dataclasses import dataclass

ITEM_WORDS: dict[str, list[str]] = {
    "phone": ["phone", "mobile", "smartphone", "cellphone"],
    "wallet": ["wallet", "billfold", "purse"],
    "keys": ["keys", "key ring", "keychain", "key"],
    "backpack": ["backpack", "rucksack", "school bag", "bag"],
    "umbrella": ["umbrella", "brolly"],
    "laptop": ["laptop", "notebook computer"],
    "glasses": ["glasses", "spectacles", "eyeglasses"],
    "bottle": ["water bottle", "flask", "drink bottle", "bottle"],
    "jacket": ["jacket", "coat", "hoodie"],
    "headphones": ["headphones", "earphones", "earbuds"],
    "book": ["textbook", "book", "notebook"],
    "watch": ["watch", "wristwatch"],
    "scarf": ["scarf", "muffler"],
    "charger": ["charger", "power adapter", "charging cable", "cable"],
}
COLOR_WORDS: dict[str, list[str]] = {
    "black": ["black", "jet black", "charcoal"],
    "blue": ["blue", "navy", "dark blue", "sky blue"],
    "red": ["red", "maroon", "crimson"],
    "green": ["green", "olive", "dark green"],
    "white": ["white", "cream", "off-white"],
    "grey": ["grey", "gray", "silver"],
    "brown": ["brown", "tan", "chocolate"],
    "yellow": ["yellow", "mustard"],
    "pink": ["pink", "rose"],
}
EXTRA_WORDS = [
    "cracked",
    "sticker",
    "plastic cover",
    "scratched",
    "tear",
    "name tag",
    "lanyard",
    "keyring",
    "worn",
    "new",
]
STOP = {
    "found",
    "lost",
    "my",
    "a",
    "an",
    "the",
    "i",
    "handed",
    "in",
    "picked",
    "up",
    "missing",
    "with",
    "on",
    "it",
    "of",
    "and",
}


def _phrase_map(words: dict[str, list[str]]) -> list[tuple[str, str]]:
    pairs = [(w, canon) for canon, ws in words.items() for w in ws]
    return sorted(pairs, key=lambda p: -len(p[0]))  # longest phrase first


_ITEM_PAIRS = _phrase_map(ITEM_WORDS)
_COLOR_PAIRS = _phrase_map(COLOR_WORDS)


def _find(text: str, pairs: list[tuple[str, str]]) -> str | None:
    for phrase, canon in pairs:
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            return canon
    return None


@dataclass(frozen=True)
class Attributes:
    category: str | None
    color: str | None
    brand: str | None
    extras: frozenset[str]
    tokens: str  # normalised text used for TF-IDF


def parse(description: str, brands: frozenset[str]) -> Attributes:
    text = description.lower()
    category = _find(text, _ITEM_PAIRS)
    color = _find(text, _COLOR_PAIRS)
    brand = next((b for b in brands if re.search(rf"\b{re.escape(b.lower())}\b", text)), None)
    extras = frozenset(e for e in EXTRA_WORDS if e in text)
    norm = text
    for phrase, canon in _ITEM_PAIRS + _COLOR_PAIRS:  # collapse synonyms to canonical words
        norm = re.sub(rf"\b{re.escape(phrase)}\b", canon.replace(" ", "_"), norm)
    tokens = " ".join(t for t in re.findall(r"[a-z_]+", norm) if t not in STOP)
    return Attributes(category, color, brand, extras, tokens)
