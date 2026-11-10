"""Recipe loading and expiry-weighted ranking (TF-IDF overlap + urgency of used items - missing penalty)."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pantry.catalog import CATALOG, STAPLES, normalize
from pantry.urgency import PantryItem

MISSING_PENALTY = 0.35
TFIDF_WEIGHT = 0.5
AT_RISK_DAYS = 3  # items with this many days left (or fewer) count as "saved from the bin" when used


@dataclass(frozen=True)
class Recipe:
    id: int
    name: str
    minutes: int
    servings: int
    ingredients: tuple[str, ...]
    steps: str


@dataclass
class Used:
    idx: int
    name: str
    canonical: str
    kg: float
    urgency: float
    days_left: int
    at_risk: bool


@dataclass
class ScoredRecipe:
    recipe: Recipe
    score: float
    cosine: float
    used: list[Used] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def waste_kg(self) -> float:
        return round(sum(u.kg for u in self.used if u.at_risk), 3)

    @property
    def waste_value(self) -> float:
        return round(sum(u.kg * CATALOG[normalize(u.canonical)].price_per_kg for u in self.used if u.at_risk), 2)


def load_recipes(path: Path) -> list[Recipe]:
    out: list[Recipe] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ings = tuple(i.strip() for i in row["ingredients"].split(";") if i.strip())
            minutes, servings = int(row["minutes"]), int(row["servings"])
            out.append(Recipe(int(row["id"]), row["name"], minutes, servings, ings, row["steps"]))
    return out


def _split(doc: str) -> list[str]:
    return doc.split(";")


class RecipeRanker:
    def __init__(self, recipes: list[Recipe]) -> None:
        self.recipes = recipes
        self.vec = TfidfVectorizer(analyzer=_split, lowercase=False)
        self.matrix = self.vec.fit_transform([";".join(r.ingredients) for r in recipes])

    def rank(self, items: list[PantryItem], limit: int = 5, exclude: set[int] | None = None) -> list[ScoredRecipe]:
        """Best recipes first. Expired and unknown items are never used; score must be positive to be listed."""
        by_name: dict[str, PantryItem] = {}
        for it in sorted(items, key=lambda i: (i.days_left, -i.urgency)):
            if it.canonical and it.days_left >= 0 and it.kg > 0:
                by_name.setdefault(it.canonical, it)
        if not by_name:
            return []
        cos = cosine_similarity(self.vec.transform([";".join(by_name)]), self.matrix)[0]
        results: list[ScoredRecipe] = []
        for recipe, c in zip(self.recipes, cos, strict=True):
            if exclude and recipe.id in exclude:
                continue
            used: list[Used] = []
            missing: list[str] = []
            for ing in recipe.ingredients:
                if ing in STAPLES:
                    continue
                it = by_name.get(ing)
                if it is None:
                    missing.append(ing)
                    continue
                need = CATALOG[normalize(ing)].portion_kg
                used.append(
                    Used(it.idx, it.name, ing, round(min(need, it.kg), 4), it.urgency, it.days_left,
                         it.days_left <= AT_RISK_DAYS)
                )  # fmt: skip
            if not used:
                continue
            score = sum(u.urgency for u in used) - MISSING_PENALTY * len(missing) + TFIDF_WEIGHT * float(c)
            if score > 0:
                results.append(ScoredRecipe(recipe, round(score, 4), round(float(c), 4), used, missing))
        results.sort(key=lambda r: (-r.score, r.recipe.id))
        return results[:limit]
