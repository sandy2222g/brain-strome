"""Staffing recommendation: smallest team that meets a waiting-time promise, checked by simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from waitsim.erlang import min_servers
from waitsim.sim import Config, Summary, simulate


@dataclass
class Option:
    servers: int
    meets_target: bool
    summary: Summary

    def to_dict(self) -> dict[str, Any]:
        return {"servers": self.servers, "meets_target": self.meets_target, **asdict(self.summary)}


def recommend(
    cfg: Config, target_min: float = 30.0, level: float = 0.9, replications: int = 30, seed: int = 0, extra: int = 2
) -> dict[str, Any]:
    """Promise: `level` of patients wait at most `target_min` minutes.

    Starts from the Erlang C answer for the busiest hour, then confirms with simulation under the
    real conditions (daily profile, urgent patients, walk-outs), moving up or down as needed.
    """
    if not 0 < level < 1:
        raise ValueError("level must be between 0 and 1")
    if target_min <= 0:
        raise ValueError("target must be positive")
    prof = cfg.hourly_profile or (1.0,) * 24
    peak_rate = cfg.arrivals_per_hour * max(prof)
    analytic = min_servers(peak_rate, cfg.mean_service_min, target_min, level)

    cache: dict[int, Option] = {}

    def evaluate(c: int) -> Option:
        if c not in cache:
            s = simulate(replace(cfg, servers=c), replications, seed, target_min)
            cache[c] = Option(c, s.share_within_target >= level, s)
        return cache[c]

    c = max(1, analytic)
    while not evaluate(c).meets_target and c < 100:
        c += 1
    while c > 1 and evaluate(c - 1).meets_target:
        c -= 1
    options = [evaluate(k) for k in range(max(1, c - 2), c + extra + 1)]
    return {
        "recommended_servers": c,
        "analytic_start": analytic,
        "target_min": target_min,
        "level": level,
        "options": [o.to_dict() for o in options],
    }
