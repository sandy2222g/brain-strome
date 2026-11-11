"""Choose which hall booking requests to accept so total fees are highest and no two bookings overlap.

This is weighted interval scheduling. `best_bookings` is the classic dynamic programme: sort requests by end time;
for each request either skip it or take it together with the best set that ends before it starts. Baselines:
first-come-first-served (accept each request in the order received if it fits) and the earliest-finish greedy,
which maximises the NUMBER of bookings rather than the fees.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "requests.json"
MAX_REQUESTS = 200


class BookingError(ValueError):
    """Invalid booking requests."""


@dataclass(frozen=True)
class Request:
    name: str
    start: int  # minutes from midnight
    end: int
    fee: float


def _minutes(hhmm: str) -> int:
    try:
        h, m = hhmm.split(":")
        value = int(h) * 60 + int(m)
    except ValueError as err:
        raise BookingError(f"bad time '{hhmm}'") from err
    if not 0 <= value <= 24 * 60:
        raise BookingError(f"bad time '{hhmm}'")
    return value


def build(raw: list[dict]) -> list[Request]:  # type: ignore[type-arg]
    if not 1 <= len(raw) <= MAX_REQUESTS:
        raise BookingError(f"between 1 and {MAX_REQUESTS} requests")
    out = [Request(r["name"], _minutes(r["start"]), _minutes(r["end"]), float(r["fee"])) for r in raw]
    if any(r.start >= r.end or r.fee < 0 for r in out):
        raise BookingError("each request needs start before end and a non-negative fee")
    if len({r.name for r in out}) != len(out):
        raise BookingError("request names must be unique")
    return out


def load(path: Path = DATA) -> list[Request]:
    return build(json.loads(path.read_text())["requests"])


def overlaps(a: Request, b: Request) -> bool:
    return a.start < b.end and b.start < a.end


def revenue(chosen: list[Request]) -> float:
    return sum(r.fee for r in chosen)


def hours(chosen: list[Request]) -> float:
    return sum(r.end - r.start for r in chosen) / 60


def first_come_first_served(requests: list[Request]) -> list[Request]:
    taken: list[Request] = []
    for r in requests:
        if all(not overlaps(r, t) for t in taken):
            taken.append(r)
    return taken


def earliest_finish(requests: list[Request]) -> list[Request]:
    taken: list[Request] = []
    for r in sorted(requests, key=lambda x: (x.end, x.start)):
        if all(not overlaps(r, t) for t in taken):
            taken.append(r)
    return taken


def best_bookings(requests: list[Request]) -> list[Request]:
    order = sorted(requests, key=lambda r: (r.end, r.start))
    ends = [r.end for r in order]
    best = [0.0] * (len(order) + 1)
    take = [False] * len(order)
    prev = [0] * len(order)
    for i, r in enumerate(order):
        prev[i] = bisect_right(ends, r.start, 0, i)  # requests before i that end by r.start
        with_r = r.fee + best[prev[i]]
        take[i] = with_r > best[i]
        best[i + 1] = with_r if take[i] else best[i]
    chosen: list[Request] = []
    i = len(order)
    while i > 0:
        if take[i - 1]:
            chosen.append(order[i - 1])
            i = prev[i - 1]
        else:
            i -= 1
    return sorted(chosen, key=lambda r: r.start)
