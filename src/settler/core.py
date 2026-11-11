"""Split shared expenses and settle up with the fewest payments.

Money is kept in integer cents so totals always balance exactly.
"""

from __future__ import annotations

from dataclasses import dataclass


class SettleError(ValueError):
    """Raised for invalid expense input."""


@dataclass(frozen=True)
class Expense:
    payer: str
    cents: int
    split_among: tuple[str, ...]
    label: str = ""


@dataclass(frozen=True)
class Payment:
    frm: str
    to: str
    cents: int


def split_cents(total: int, people: list[str]) -> dict[str, int]:
    """Split total across people; leftover cents go to the first people in order."""
    if total < 0:
        raise SettleError("amount must not be negative")
    if not people or len(set(people)) != len(people):
        raise SettleError("split needs distinct people")
    base, extra = divmod(total, len(people))
    return {p: base + (1 if i < extra else 0) for i, p in enumerate(people)}


def balances(expenses: list[Expense]) -> dict[str, int]:
    """Net balance per person: positive = is owed money, negative = owes money."""
    net: dict[str, int] = {}
    for e in expenses:
        for p in (e.payer, *e.split_among):
            net.setdefault(p, 0)
        net[e.payer] += e.cents
        for p, share in split_cents(e.cents, list(e.split_among)).items():
            net[p] -= share
    return net


def _exact_zero_sum_groups(names: list[str], net: dict[str, int]) -> list[list[str]]:
    """Partition people into the most groups whose balances each sum to zero (bitmask DP).

    A group of k people can settle in k-1 payments, so more groups = fewer payments.
    """
    n = len(names)
    sums = [0] * (1 << n)
    for mask in range(1, 1 << n):
        low = (mask & -mask).bit_length() - 1
        sums[mask] = sums[mask & (mask - 1)] + net[names[low]]
    best = [0] * (1 << n)
    for mask in range(1, 1 << n):
        sub = mask
        top = 0
        while sub:
            if sums[sub] == 0 and sub & (mask & -mask):
                top = max(top, best[mask ^ sub] + 1)
            sub = (sub - 1) & mask
        best[mask] = top if sums[mask] == 0 else max(best[mask & (mask - 1)], 0)
    # Rebuild the partition for the full mask.
    groups: list[list[str]] = []
    mask = (1 << n) - 1
    while mask:
        low_bit = mask & -mask
        chosen = 0
        sub = mask
        while sub:
            if sums[sub] == 0 and sub & low_bit and best[mask ^ sub] + 1 == best[mask]:
                chosen = sub
                break
            sub = (sub - 1) & mask
        if not chosen:  # people left over only if input did not sum to zero
            break
        groups.append([names[i] for i in range(n) if chosen >> i & 1])
        mask ^= chosen
    return groups


def _settle_group(names: list[str], net: dict[str, int]) -> list[Payment]:
    """Greedy settle inside one zero-sum group: largest debtor pays largest creditor."""
    owe = {p: -net[p] for p in names if net[p] < 0}
    due = {p: net[p] for p in names if net[p] > 0}
    out: list[Payment] = []
    while owe and due:
        d = max(owe, key=lambda p: (owe[p], p))
        c = max(due, key=lambda p: (due[p], p))
        amt = min(owe[d], due[c])
        out.append(Payment(d, c, amt))
        owe[d] -= amt
        due[c] -= amt
        if owe[d] == 0:
            del owe[d]
        if due[c] == 0:
            del due[c]
    return out


def settle(net: dict[str, int], exact_limit: int = 14) -> list[Payment]:
    """Fewest payments that bring every balance to zero.

    Exact (optimal) up to `exact_limit` people with non-zero balances; greedy above that.
    """
    if sum(net.values()) != 0:
        raise SettleError("balances must sum to zero")
    names = sorted(p for p, v in net.items() if v != 0)
    if not names:
        return []
    if len(names) > exact_limit:
        return _settle_group(names, net)
    payments: list[Payment] = []
    for group in _exact_zero_sum_groups(names, net):
        payments.extend(_settle_group(group, net))
    return sorted(payments, key=lambda p: (p.frm, p.to))


def naive_payments(expenses: list[Expense]) -> list[Payment]:
    """Baseline: every participant pays the payer their share of every expense."""
    pair: dict[tuple[str, str], int] = {}
    for e in expenses:
        for p, share in split_cents(e.cents, list(e.split_among)).items():
            if p != e.payer and share:
                pair[(p, e.payer)] = pair.get((p, e.payer), 0) + share
    return [Payment(a, b, c) for (a, b), c in sorted(pair.items())]


def apply_payments(net: dict[str, int], payments: list[Payment]) -> dict[str, int]:
    out = dict(net)
    for p in payments:
        out[p.frm] += p.cents
        out[p.to] -= p.cents
    return out
