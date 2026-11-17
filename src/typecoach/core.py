"""Typing analysis: edit-distance alignment, WPM, weak keys and drills."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data"
Op = tuple[str, str, str]  # (kind, expected, got); kind in match/sub/miss/extra


class TypingError(ValueError):
    """Invalid input."""


def load_sessions(path: Path = ROOT / "sessions.json") -> list[dict[str, object]]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def load_words(path: Path = ROOT / "words.txt") -> list[str]:
    return path.read_text().split()


def align(target: str, typed: str) -> list[Op]:
    """Minimum-edit alignment (Levenshtein with traceback)."""
    n, m = len(target), len(typed)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (target[i - 1] != typed[j - 1]))
    ops: list[Op] = []
    i, j = n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (target[i - 1] != typed[j - 1]):
            ops.append(("match" if target[i - 1] == typed[j - 1] else "sub", target[i - 1], typed[j - 1]))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            ops.append(("miss", target[i - 1], ""))
            i -= 1
        else:
            ops.append(("extra", "", typed[j - 1]))
            j -= 1
    return ops[::-1]


def naive_errors(target: str, typed: str) -> int:
    """Position-by-position comparison: one dropped letter makes everything after it 'wrong'."""
    return sum(a != b for a, b in zip(target, typed, strict=False)) + abs(len(target) - len(typed))


def analyse(target: str, typed: str, seconds: float) -> dict[str, object]:
    if not target or not typed:
        raise TypingError("target and typed text must not be empty")
    if seconds <= 0:
        raise TypingError("seconds must be positive")
    ops = align(target, typed)
    errors = sum(o[0] != "match" for o in ops)
    minutes = seconds / 60
    gross = len(typed) / 5 / minutes
    net = max(0.0, (len(typed) / 5 - errors) / minutes)
    seen: Counter[str] = Counter()
    missed: Counter[str] = Counter()
    for kind, exp, _ in ops:
        if exp and exp != " ":
            seen[exp] += 1
            missed[exp] += kind in ("sub", "miss")
    conf = Counter((e, g) for k, e, g in ops if k == "sub")
    return {"errors": errors, "gross_wpm": round(gross, 1), "net_wpm": round(net, 1),
            "accuracy": round(max(0.0, 1 - errors / len(target)), 3),
            "seen": dict(seen), "missed": dict(missed),
            "confusions": [[e, g, n] for (e, g), n in conf.most_common(5)],
            "ops": [list(o) for o in ops]}


def weak_keys(results: list[dict[str, object]], min_seen: int = 4, top: int = 5) -> list[dict[str, object]]:
    seen: Counter[str] = Counter()
    missed: Counter[str] = Counter()
    for r in results:
        seen.update(r["seen"])  # type: ignore[arg-type]
        missed.update(r["missed"])  # type: ignore[arg-type]
    rows = [{"key": k, "attempts": seen[k], "misses": missed[k], "miss_rate": round(missed[k] / seen[k], 3)}
            for k in seen if seen[k] >= min_seen and missed[k]]
    return sorted(rows, key=lambda r: (-r["miss_rate"], -r["misses"], r["key"]))[:top]  # type: ignore[operator]


def drill(weak: list[str], words: list[str], n: int = 8) -> list[str]:
    """Words that contain the most weak letters (counted with repeats), ties by shorter word."""
    if not weak:
        raise TypingError("no weak keys to drill")
    def score(w: str) -> int:
        return sum(w.count(k) for k in weak)
    ranked = sorted((w for w in words if score(w)), key=lambda w: (-score(w), len(w), w))
    return ranked[:n]


def evaluate() -> dict[str, object]:
    sessions = load_sessions()
    rows = []
    for s in sessions:
        a = analyse(str(s["target"]), str(s["typed"]), float(s["seconds"]))  # type: ignore[arg-type]
        rows.append({"id": s["id"], "true_errors": s["true_errors"], "aligned": a["errors"],
                     "naive": naive_errors(str(s["target"]), str(s["typed"])),
                     "net_wpm": a["net_wpm"], "accuracy": a["accuracy"]})
    gap = lambda k: sum(abs(r[k] - r["true_errors"]) for r in rows) / len(rows)  # noqa: E731
    return {"sessions": rows, "aligned_gap": round(gap("aligned"), 2), "naive_gap": round(gap("naive"), 2)}
