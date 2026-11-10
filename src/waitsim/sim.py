"""Discrete-event simulation of a walk-in clinic.

Patients arrive as a (time-varying) Poisson process, queue by priority (urgent first, FIFO within a
class), are served by `servers` staff with random service times, and may give up if they wait too long.
All randomness comes from one seeded generator per replication, so results are reproducible.
"""

from __future__ import annotations

import heapq
import math
import random
import statistics
from dataclasses import dataclass, field

DAY_MIN = 24 * 60.0


@dataclass(frozen=True)
class Config:
    arrivals_per_hour: float = 10.0
    mean_service_min: float = 12.0
    servers: int = 3
    open_hour: int = 8
    close_hour: int = 16
    hourly_profile: tuple[float, ...] = ()  # multipliers per hour of day (24 values) or empty for flat
    urgent_share: float = 0.0  # fraction of arrivals served ahead of routine patients
    mean_patience_min: float = 0.0  # 0 disables walk-outs
    service_cv: float = 1.0  # 1.0 = exponential; <1 more regular; >1 more variable (lognormal)

    def validate(self) -> None:
        if self.arrivals_per_hour <= 0 or self.mean_service_min <= 0:
            raise ValueError("arrival rate and service time must be positive")
        if self.servers < 1 or self.servers > 100:
            raise ValueError("servers must be between 1 and 100")
        if not 0 <= self.open_hour < self.close_hour <= 24:
            raise ValueError("opening hours must satisfy 0 <= open < close <= 24")
        if self.hourly_profile and len(self.hourly_profile) != 24:
            raise ValueError("hourly_profile needs 24 values")
        if self.hourly_profile and min(self.hourly_profile) < 0:
            raise ValueError("hourly_profile values must be non-negative")
        if not 0 <= self.urgent_share <= 1:
            raise ValueError("urgent_share must be within [0, 1]")
        if self.mean_patience_min < 0 or self.service_cv <= 0:
            raise ValueError("patience must be >= 0 and service_cv > 0")


@dataclass
class RunResult:
    waits: list[float] = field(default_factory=list)  # minutes, patients who were served
    urgent_waits: list[float] = field(default_factory=list)
    routine_waits: list[float] = field(default_factory=list)
    abandoned: int = 0
    arrived: int = 0
    busy_minutes: float = 0.0
    last_departure: float = 0.0
    max_queue: int = 0
    wait_hours: list[int] = field(default_factory=list)  # arrival hour of each served patient
    trace: list[tuple[float, float, float, bool, int]] = field(
        default_factory=list
    )  # arrive, start, end, urgent, server


def _service_time(rng: random.Random, mean: float, cv: float) -> float:
    if abs(cv - 1.0) < 1e-9:
        return rng.expovariate(1.0 / mean)
    sigma2 = math.log(1 + cv * cv)
    return rng.lognormvariate(math.log(mean) - sigma2 / 2, math.sqrt(sigma2))


def _arrival_times(cfg: Config, rng: random.Random) -> list[float]:
    """Non-homogeneous Poisson arrivals by thinning, within opening hours (minutes from midnight)."""
    prof = cfg.hourly_profile or (1.0,) * 24
    peak = max(prof) * cfg.arrivals_per_hour / 60.0
    t, out = cfg.open_hour * 60.0, []
    end = cfg.close_hour * 60.0
    if peak <= 0:
        return out
    while True:
        t += rng.expovariate(peak)
        if t >= end:
            return out
        rate = prof[int(t // 60) % 24] * cfg.arrivals_per_hour / 60.0
        if rng.random() < rate / peak:
            out.append(t)


def run_once(cfg: Config, seed: int, trace: bool = False) -> RunResult:
    cfg.validate()
    rng = random.Random(seed)
    res = RunResult()
    arrivals = _arrival_times(cfg, rng)
    res.arrived = len(arrivals)
    patients = [
        (
            t,
            rng.random() < cfg.urgent_share,
            rng.expovariate(1.0 / cfg.mean_patience_min) if cfg.mean_patience_min > 0 else math.inf,
        )
        for t in arrivals
    ]
    # event heap: (time, kind, idx); kind 0 = departure (frees a server first), 1 = arrival
    events: list[tuple[float, int, int]] = [(t, 1, i) for i, (t, _, _) in enumerate(patients)]
    heapq.heapify(events)
    free = cfg.servers
    free_ids = list(range(cfg.servers))
    heapq.heapify(free_ids)
    server_of: dict[int, int] = {}
    queues: tuple[list[int], list[int]] = ([], [])  # (urgent, routine) of patient indices, FIFO
    heads = [0, 0]

    def start_service(i: int, now: float) -> None:
        nonlocal free
        free -= 1
        arrive, urgent, _ = patients[i]
        wait = now - arrive
        res.waits.append(wait)
        (res.urgent_waits if urgent else res.routine_waits).append(wait)
        res.wait_hours.append(int(arrive // 60) % 24)
        dur = _service_time(rng, cfg.mean_service_min, cfg.service_cv)
        sid = heapq.heappop(free_ids)
        server_of[i] = sid
        if trace:
            res.trace.append((arrive, now, now + dur, urgent, sid))
        res.busy_minutes += dur
        heapq.heappush(events, (now + dur, 0, i))

    def next_waiting(now: float) -> int | None:
        for q in (0, 1):
            while heads[q] < len(queues[q]):
                i = queues[q][heads[q]]
                heads[q] += 1
                arrive, _, patience = patients[i]
                if now - arrive > patience:
                    res.abandoned += 1
                    continue
                return i
        return None

    while events:
        now, kind, i = heapq.heappop(events)
        if kind == 0:
            free += 1
            heapq.heappush(free_ids, server_of[i])
            res.last_departure = now
            nxt = next_waiting(now)
            if nxt is not None:
                start_service(nxt, now)
        else:
            if free > 0:
                start_service(i, now)
            else:
                queues[0 if patients[i][1] else 1].append(i)
                res.max_queue = max(res.max_queue, sum(len(q) - h for q, h in zip(queues, heads, strict=True)))
    for q in (0, 1):  # anyone still queued at the end (only possible with abandonment) walked out
        res.abandoned += len(queues[q]) - heads[q]
    return res


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


@dataclass
class Summary:
    replications: int
    patients_per_day: float
    mean_wait_min: float
    mean_wait_ci95: float
    p90_wait_min: float
    p95_wait_min: float
    share_within_target: float
    utilization: float
    abandon_rate: float
    mean_urgent_wait_min: float
    mean_routine_wait_min: float
    max_queue: float
    overtime_min: float
    hourly_wait_min: list[float]  # mean wait by arrival hour (24 values)


def simulate(cfg: Config, replications: int = 30, seed: int = 0, target_min: float = 30.0) -> Summary:
    cfg.validate()
    if not 1 <= replications <= 500:
        raise ValueError("replications must be between 1 and 500")
    runs = [run_once(cfg, seed * 100_003 + r) for r in range(replications)]
    means = [statistics.fmean(r.waits) if r.waits else 0.0 for r in runs]
    all_waits = [w for r in runs for w in r.waits]
    urgent = [w for r in runs for w in r.urgent_waits]
    routine = [w for r in runs for w in r.routine_waits]
    arrived = sum(r.arrived for r in runs)
    hours = (cfg.close_hour - cfg.open_hour) * 60.0
    close = cfg.close_hour * 60.0
    by_hour: list[list[float]] = [[] for _ in range(24)]
    for r in runs:
        for w, h in zip(r.waits, r.wait_hours, strict=True):
            by_hour[h].append(w)
    hourly = [round(statistics.fmean(x), 2) if x else 0.0 for x in by_hour]
    ci = 1.96 * statistics.stdev(means) / math.sqrt(len(means)) if len(means) > 1 else 0.0
    return Summary(
        replications=replications,
        patients_per_day=round(arrived / replications, 1),
        mean_wait_min=round(statistics.fmean(all_waits), 2) if all_waits else 0.0,
        mean_wait_ci95=round(ci, 2),
        p90_wait_min=round(percentile(all_waits, 0.90), 1),
        p95_wait_min=round(percentile(all_waits, 0.95), 1),
        share_within_target=round(sum(w <= target_min for w in all_waits) / len(all_waits), 3) if all_waits else 1.0,
        utilization=round(sum(r.busy_minutes for r in runs) / (replications * cfg.servers * hours), 3),
        abandon_rate=round(sum(r.abandoned for r in runs) / arrived, 3) if arrived else 0.0,
        mean_urgent_wait_min=round(statistics.fmean(urgent), 2) if urgent else 0.0,
        mean_routine_wait_min=round(statistics.fmean(routine), 2) if routine else 0.0,
        max_queue=round(statistics.fmean(r.max_queue for r in runs), 1),
        overtime_min=round(statistics.fmean(max(0.0, r.last_departure - close) for r in runs), 1),
        hourly_wait_min=hourly,
    )
