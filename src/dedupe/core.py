"""Find duplicate contacts: normalise, block, score pairs, cluster with union-find."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations

NICKNAMES = {"jim": "james", "jimmy": "james", "mari": "maria", "tom": "tomas", "will": "liam", "noe": "noah"}


@dataclass(frozen=True)
class Contact:
    id: int
    name: str
    phone: str
    email: str


def norm_name(raw: str) -> str:
    s = raw.strip().lower()
    if "," in s:  # "SMITH, James" -> "james smith"
        last, first = (x.strip() for x in s.split(",", 1))
        s = f"{first} {last}"
    parts = [NICKNAMES.get(p.strip("."), p.strip(".")) for p in re.split(r"\s+", s) if p]
    return " ".join(parts)


def norm_phone(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    return d[-10:] if len(d) >= 10 else d


def norm_email(raw: str) -> str:
    return raw.strip().lower()


def name_score(a: str, b: str) -> float:
    """Similarity of normalised names; an initial in place of a full name still matches."""
    pa, pb = a.split(), b.split()
    if len(pa) == 2 and len(pb) == 2 and pa[0] == pb[0] and (len(pa[1]) == 1 or len(pb[1]) == 1):
        if pa[1][0] == pb[1][0]:
            return 0.9
    return SequenceMatcher(None, a, b).ratio()


def pair_score(a: Contact, b: Contact) -> float:
    """0-1 evidence: shared phone or email is decisive, otherwise fuzzy name similarity."""
    pa, pb = norm_phone(a.phone), norm_phone(b.phone)
    ea, eb = norm_email(a.email), norm_email(b.email)
    ns = name_score(norm_name(a.name), norm_name(b.name))
    contact_match = (pa and pa == pb) or (ea and ea == eb)
    return min(1.0, ns * 0.5 + 0.5) if contact_match else ns * 0.8


def blocks(contacts: list[Contact]) -> dict[str, list[int]]:
    """Cheap keys so we only compare plausible pairs instead of all n^2."""
    out: dict[str, list[int]] = defaultdict(list)
    for c in contacts:
        n = norm_name(c.name).split()
        if n:
            out["last:" + n[-1][:3]].append(c.id)
            out["first:" + n[0][:3]].append(c.id)
        if norm_phone(c.phone):
            out["ph:" + norm_phone(c.phone)].append(c.id)
        if norm_email(c.email):
            out["em:" + norm_email(c.email)].append(c.id)
    return out


class UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        self.p[self.find(a)] = self.find(b)


def find_duplicates(contacts: list[Contact], threshold: float = 0.8) -> list[list[int]]:
    """Clusters of ids (size > 1) judged to be the same person."""
    by_id = {c.id: c for c in contacts}
    index = {c.id: i for i, c in enumerate(contacts)}
    uf = UnionFind(len(contacts))
    seen: set[tuple[int, int]] = set()
    for ids in blocks(contacts).values():
        for a, b in combinations(sorted(ids), 2):
            if (a, b) in seen:
                continue
            seen.add((a, b))
            if pair_score(by_id[a], by_id[b]) >= threshold:
                uf.union(index[a], index[b])
    groups: dict[int, list[int]] = defaultdict(list)
    for c in contacts:
        groups[uf.find(index[c.id])].append(c.id)
    return sorted(sorted(g) for g in groups.values() if len(g) > 1)


def merge(cluster: list[Contact]) -> Contact:
    """Keep the longest name, first phone and first email seen in the cluster."""
    name = max((c.name for c in cluster), key=lambda n: (len(norm_name(n)), n))
    phone = next((c.phone for c in cluster if c.phone), "")
    email = next((c.email.lower() for c in cluster if c.email), "")
    return Contact(min(c.id for c in cluster), name, phone, email)


def evaluate(truth: dict[int, int], clusters: list[list[int]]) -> dict[str, float]:
    """Pairwise precision/recall of predicted clusters vs ground-truth group labels."""
    pred = {frozenset(p) for c in clusters for p in combinations(c, 2)}
    by_group: dict[int, list[int]] = defaultdict(list)
    for i, g in truth.items():
        by_group[g].append(i)
    real = {frozenset(p) for ids in by_group.values() for p in combinations(ids, 2)}
    tp = len(pred & real)
    prec = tp / len(pred) if pred else 1.0
    rec = tp / len(real) if real else 1.0
    return {"precision": round(prec, 3), "recall": round(rec, 3), "pairs_true": len(real), "pairs_found": len(pred)}
