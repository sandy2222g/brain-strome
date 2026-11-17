"""Myers' O(ND) diff, written from scratch, with line and word views."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
TOKEN = re.compile(r"\s+|\w+|[^\w\s]")


@dataclass(frozen=True)
class Op:
    kind: str  # "eq", "del" or "add"
    text: str


def myers(a: list[str], b: list[str]) -> list[Op]:
    """Shortest edit script from a to b (equal items kept, extra ones deleted or added)."""
    n, m = len(a), len(b)
    mx = n + m
    v = {1: 0}
    trace: list[dict[int, int]] = []
    for d in range(mx + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x, y = x + 1, y + 1
            v[k] = x
            if x >= n and y >= m:
                return _backtrack(a, b, trace, d)
    raise AssertionError("unreachable")  # pragma: no cover


def _backtrack(a: list[str], b: list[str], trace: list[dict[int, int]], d_end: int) -> list[Op]:
    x, y = len(a), len(b)
    out: list[Op] = []
    for d in range(d_end, -1, -1):
        if d == 0:  # only the leading run of equal items is left
            while x > 0 and y > 0:
                x, y = x - 1, y - 1
                out.append(Op("eq", a[x]))
            break
        v = trace[d]
        k = x - y
        pk = k + 1 if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)) else k - 1
        px = v.get(pk, 0)
        py = px - pk
        while x > px and y > py:  # walk back along the diagonal of equal items
            x, y = x - 1, y - 1
            out.append(Op("eq", a[x]))
        if x == px:
            y -= 1
            out.append(Op("add", b[y]))
        else:
            x -= 1
            out.append(Op("del", a[x]))
    return out[::-1]


def lcs_distance(a: list[str], b: list[str]) -> int:
    """Baseline: edit distance (adds + deletes) from the textbook O(nm) table."""
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = prev[j - 1] if a[i - 1] == b[j - 1] else min(prev[j], cur[j - 1]) + 1
        prev = cur
    return prev[-1]


def apply(ops: list[Op]) -> tuple[list[str], list[str]]:
    """Rebuild the two inputs from an edit script (used to prove the diff is lossless)."""
    a = [o.text for o in ops if o.kind != "add"]
    b = [o.text for o in ops if o.kind != "del"]
    return a, b


def distance(ops: list[Op]) -> int:
    return sum(o.kind != "eq" for o in ops)


def diff_lines(a: str, b: str) -> list[Op]:
    return myers(a.splitlines(), b.splitlines())


def tokens(s: str) -> list[str]:
    return TOKEN.findall(s)


def diff_words(a: str, b: str) -> list[Op]:
    return myers(tokens(a), tokens(b))


def pair_changes(ops: list[Op]) -> list[dict[str, object]]:
    """Group a line diff into rows; a deleted line followed by an added one becomes one changed row
    with a word-level diff inside."""
    rows: list[dict[str, object]] = []
    i = 0
    while i < len(ops):
        o = ops[i]
        if o.kind == "eq":
            rows.append({"kind": "eq", "text": o.text})
            i += 1
            continue
        dels: list[str] = []
        adds: list[str] = []
        while i < len(ops) and ops[i].kind != "eq":
            (dels if ops[i].kind == "del" else adds).append(ops[i].text)
            i += 1
        for j in range(max(len(dels), len(adds))):
            d = dels[j] if j < len(dels) else None
            a = adds[j] if j < len(adds) else None
            if d is not None and a is not None:
                rows.append({"kind": "chg", "old": d, "new": a,
                             "words": [{"kind": w.kind, "text": w.text} for w in diff_words(d, a)]})
            elif d is not None:
                rows.append({"kind": "del", "text": d})
            else:
                rows.append({"kind": "add", "text": a})
    return rows


def samples() -> dict[str, str]:
    return {"a": (DATA / "a.txt").read_text(), "b": (DATA / "b.txt").read_text()}
