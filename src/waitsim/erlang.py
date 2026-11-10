"""Erlang C: closed-form results for an M/M/c queue (the textbook check on the simulator)."""

from __future__ import annotations

import math


def offered_load(arrivals_per_hour: float, mean_service_min: float) -> float:
    """Traffic in Erlangs: average number of servers kept busy."""
    return arrivals_per_hour * mean_service_min / 60.0


def prob_wait(servers: int, load: float) -> float:
    """Erlang C: probability that an arriving patient has to wait (needs load < servers)."""
    if servers < 1:
        raise ValueError("servers must be at least 1")
    if load < 0:
        raise ValueError("load must be non-negative")
    if load >= servers:
        return 1.0
    # numerically stable: iterate the Erlang B recursion, then convert to Erlang C
    b = 1.0
    for k in range(1, servers + 1):
        b = load * b / (k + load * b)
    rho = load / servers
    return b / (1 - rho * (1 - b))


def mean_wait_min(servers: int, arrivals_per_hour: float, mean_service_min: float) -> float:
    """Average time in queue (minutes) for an M/M/c queue; infinity if unstable."""
    load = offered_load(arrivals_per_hour, mean_service_min)
    if load >= servers:
        return math.inf
    c = prob_wait(servers, load)
    return c * mean_service_min / (servers - load)


def service_level(servers: int, arrivals_per_hour: float, mean_service_min: float, target_min: float) -> float:
    """Share of patients who wait no longer than target_min."""
    load = offered_load(arrivals_per_hour, mean_service_min)
    if load >= servers:
        return 0.0
    c = prob_wait(servers, load)
    return 1.0 - c * math.exp(-(servers - load) * target_min / mean_service_min)


def min_servers(arrivals_per_hour: float, mean_service_min: float, target_min: float, level: float = 0.9) -> int:
    """Fewest servers for which `level` of patients wait at most target_min (analytic start point)."""
    c = max(1, math.ceil(offered_load(arrivals_per_hour, mean_service_min)))
    while service_level(c, arrivals_per_hour, mean_service_min, target_min) < level:
        c += 1
        if c > 500:
            raise ValueError("demand is too high to staff")
    return c
