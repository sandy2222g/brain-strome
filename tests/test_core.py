import functools
import itertools
import random

import pytest

from settler.core import Expense, SettleError, apply_payments, balances, naive_payments, settle, split_cents


def test_split_cents_sums_exactly():
    s = split_cents(100, ["a", "b", "c"])
    assert sum(s.values()) == 100 and sorted(s.values()) == [33, 33, 34]


def test_split_rejects_bad_input():
    with pytest.raises(SettleError):
        split_cents(10, [])
    with pytest.raises(SettleError):
        split_cents(10, ["a", "a"])
    with pytest.raises(SettleError):
        split_cents(-1, ["a"])


def test_balances_sum_to_zero():
    ex = [Expense("a", 1000, ("a", "b", "c")), Expense("b", 333, ("a", "c"))]
    assert sum(balances(ex).values()) == 0


def test_payer_not_in_split_is_owed_full_amount():
    net = balances([Expense("a", 900, ("b", "c"))])
    assert net == {"a": 900, "b": -450, "c": -450}


def test_settle_clears_all_balances():
    net = {"a": 500, "b": -200, "c": -300}
    assert all(v == 0 for v in apply_payments(net, settle(net)).values())


def test_settle_finds_optimal_pairs():
    # two independent pairs: 2 payments, not the 3 a greedy chain could use
    net = {"a": 10, "b": -10, "c": 7, "d": -7}
    assert len(settle(net)) == 2


def test_settle_requires_zero_sum():
    with pytest.raises(SettleError):
        settle({"a": 5, "b": -3})


def test_empty_and_zero_balances():
    assert settle({"a": 0, "b": 0}) == []


def _brute_min(net):
    names = [p for p, v in net.items() if v]
    best = len(names) - 1 if names else 0
    # minimum payments = n - max number of zero-sum groups
    n = len(names)

    @functools.cache
    def f(mask):
        if not mask:
            return 0
        low = mask & -mask
        res = -(10**9)
        sub = mask
        while sub:
            if sub & low and sum(net[names[i]] for i in range(n) if sub >> i & 1) == 0:
                res = max(res, 1 + f(mask ^ sub))
            sub = (sub - 1) & mask
        return res

    groups = f((1 << n) - 1)
    return n - groups if groups > 0 else best


def test_matches_brute_force_on_random_cases():
    rng = random.Random(7)
    for _ in range(40):
        n = rng.randint(2, 7)
        vals = [rng.randint(-20, 20) for _ in range(n - 1)]
        vals.append(-sum(vals))
        net = {f"p{i}": v for i, v in enumerate(vals)}
        plan = settle(net)
        assert all(v == 0 for v in apply_payments(net, plan).values())
        assert len(plan) == _brute_min(net)


def test_never_more_than_naive():
    rng = random.Random(3)
    people = ["a", "b", "c", "d", "e"]
    for _ in range(25):
        ex = [
            Expense(rng.choice(people), rng.randint(100, 9000), tuple(rng.sample(people, rng.randint(1, 5))))
            for _ in range(12)
        ]
        assert len(settle(balances(ex))) <= max(len(naive_payments(ex)), 1)


def test_greedy_fallback_still_balances():
    net = {f"p{i}": (i + 1) * (1 if i % 2 else -1) for i in range(20)}
    net["z"] = -sum(net.values())
    plan = settle(net, exact_limit=3)
    assert all(v == 0 for v in apply_payments(net, plan).values())


def test_permutation_invariant_count():
    net = {"a": 30, "b": -10, "c": -20, "d": 5, "e": -5}
    counts = {len(settle(dict(p))) for p in itertools.permutations(net.items())}
    assert len(counts) == 1
