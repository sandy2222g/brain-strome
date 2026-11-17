"""Huffman coding from scratch: build the tree, encode, decode, and measure against entropy and zlib."""
from __future__ import annotations

import heapq
import math
import zlib
from collections import Counter
from dataclasses import dataclass


class HuffmanError(ValueError):
    """Raised for invalid input."""


@dataclass(order=True)
class _Node:
    weight: int
    order: int
    sym: str | None = None
    left: _Node | None = None
    right: _Node | None = None


def build_codes(text: str) -> dict[str, str]:
    if not text:
        raise HuffmanError("text must not be empty")
    freq = Counter(text)
    if len(freq) == 1:
        return {next(iter(freq)): "0"}
    heap = [_Node(w, i, s) for i, (s, w) in enumerate(sorted(freq.items()))]
    heapq.heapify(heap)
    n = len(heap)
    while len(heap) > 1:
        a, b = heapq.heappop(heap), heapq.heappop(heap)
        heapq.heappush(heap, _Node(a.weight + b.weight, n, None, a, b))
        n += 1
    codes: dict[str, str] = {}

    def walk(node: _Node, prefix: str) -> None:
        if node.sym is not None:
            codes[node.sym] = prefix
            return
        assert node.left and node.right
        walk(node.left, prefix + "0")
        walk(node.right, prefix + "1")

    walk(heap[0], "")
    return codes


def encode(text: str, codes: dict[str, str]) -> str:
    return "".join(codes[c] for c in text)


def decode(bits: str, codes: dict[str, str]) -> str:
    rev = {v: k for k, v in codes.items()}
    out, cur = [], ""
    for b in bits:
        cur += b
        if cur in rev:
            out.append(rev[cur])
            cur = ""
    if cur:
        raise HuffmanError("bit string ends in the middle of a code")
    return "".join(out)


def entropy_bits(text: str) -> float:
    """Shannon lower bound for coding each character independently, in bits per character."""
    freq = Counter(text)
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in freq.values())


def analyse(text: str) -> dict[str, object]:
    codes = build_codes(text)
    bits = encode(text, codes)
    # table cost: one byte per symbol plus one byte per code length (a simple canonical-style header)
    header = 2 * len(codes)
    huff_bytes = math.ceil(len(bits) / 8) + header
    return {
        "chars": len(text),
        "original_bytes": len(text.encode()),
        "huffman_bytes": huff_bytes,
        "zlib_bytes": len(zlib.compress(text.encode(), 9)),
        "bits_per_char": round(len(bits) / len(text), 3),
        "entropy": round(entropy_bits(text), 3),
        "codes": dict(sorted(codes.items(), key=lambda kv: (len(kv[1]), kv[0]))),
    }
