"""Huffman coding from scratch: tree, code table, exact round trip, and size comparisons."""

from __future__ import annotations

import heapq
import json
import math
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples.json"
MAX_CHARS = 20_000


class CodingError(ValueError):
    """Invalid input."""


@dataclass
class Node:
    weight: int
    char: str | None = None
    left: Node | None = None
    right: Node | None = None


def build_tree(text: str) -> Node:
    if not text:
        raise CodingError("text must not be empty")
    if len(text) > MAX_CHARS:
        raise CodingError(f"text is limited to {MAX_CHARS} characters")
    heap: list[tuple[int, int, Node]] = []
    for i, (ch, n) in enumerate(sorted(Counter(text).items())):  # sorted: deterministic ties
        heap.append((n, i, Node(n, ch)))
    heapq.heapify(heap)
    uid = len(heap)
    while len(heap) > 1:
        w1, _, a = heapq.heappop(heap)
        w2, _, b = heapq.heappop(heap)
        heapq.heappush(heap, (w1 + w2, uid, Node(w1 + w2, None, a, b)))
        uid += 1
    return heap[0][2]


def code_table(root: Node) -> dict[str, str]:
    if root.char is not None:  # a single distinct symbol still needs one bit
        return {root.char: "0"}
    table: dict[str, str] = {}
    stack = [(root, "")]
    while stack:
        node, prefix = stack.pop()
        if node.char is not None:
            table[node.char] = prefix
        else:
            assert node.left and node.right
            stack.append((node.right, prefix + "1"))
            stack.append((node.left, prefix + "0"))
    return table


def encode(text: str, table: dict[str, str]) -> str:
    return "".join(table[c] for c in text)


def decode(bits: str, table: dict[str, str]) -> str:
    """Decode with the code table alone (prefix-free, so greedy matching is exact)."""
    rev = {v: k for k, v in table.items()}
    out, cur = [], ""
    for b in bits:
        if b not in "01":
            raise CodingError("bits must contain only 0 and 1")
        cur += b
        if cur in rev:
            out.append(rev[cur])
            cur = ""
    if cur:
        raise CodingError("bit string ends in the middle of a symbol")
    return "".join(out)


def entropy(text: str) -> float:
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in Counter(text).values())


def shrink(text: str) -> dict[str, object]:
    root = build_tree(text)
    table = code_table(root)
    bits = encode(text, table)
    raw = len(text.encode()) * 8
    header = sum(len(c.encode()) * 8 + 8 for c in table)  # symbol bytes + one length byte each (canonical table)
    total = len(bits) + header
    z = len(zlib.compress(text.encode(), 9)) * 8
    avg = len(bits) / len(text)
    return {"chars": len(text), "symbols": len(table), "raw_bits": raw, "payload_bits": len(bits),
            "header_bits": header, "total_bits": total, "ratio": round(total / raw, 3),
            "payload_ratio": round(len(bits) / raw, 3), "zlib_ratio": round(z / raw, 3),
            "avg_code_len": round(avg, 3), "entropy": round(entropy(text), 3),
            "table": dict(sorted(table.items(), key=lambda kv: (len(kv[1]), kv[1]))), "bits": bits}


def samples() -> list[dict[str, str]]:
    return json.loads(SAMPLES.read_text())  # type: ignore[no-any-return]


def evaluate() -> list[dict[str, object]]:
    out = []
    for s in samples():
        r = shrink(s["text"])
        assert decode(str(r["bits"]), r["table"]) == s["text"]  # type: ignore[arg-type]
        out.append({k: r[k] for k in ("symbols", "ratio", "payload_ratio", "zlib_ratio", "avg_code_len", "entropy")}
                   | {"name": s["name"], "chars": r["chars"]})
    return out
