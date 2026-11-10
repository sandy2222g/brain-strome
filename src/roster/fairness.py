"""Fairness measures: Gini coefficients and max-min spreads over per-person load."""

from __future__ import annotations

from dataclasses import dataclass

from .model import OFF, Grid, Instance

W_WEEKEND, W_UNSOCIAL, W_HOURS = 0.35, 0.35, 0.30


def gini(values: list[float]) -> float:
    """0 = everybody carries the same load, towards 1 = one person carries everything."""
    n = len(values)
    total = sum(values)
    if n == 0 or total <= 0:
        return 0.0
    xs = sorted(values)
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return max(0.0, (2 * cum) / (n * total) - (n + 1) / n)


@dataclass
class PersonStats:
    staff_id: str
    name: str
    shifts: int
    hours: int
    contract: float
    weekends: int
    evenings: int
    nights: int
    unsocial: int
    off_requests: int
    off_granted: int
    avoid_worked: int
    preferred_worked: int

    @property
    def unmet(self) -> int:
        return (self.off_requests - self.off_granted) + self.avoid_worked

    @property
    def granted(self) -> int:
        return self.off_granted + self.preferred_worked


def person_stats(inst: Instance, grid: Grid) -> list[PersonStats]:
    out = []
    for p, s in enumerate(inst.problem.staff):
        row = grid[p]
        shifts = hours = wk = ev = ni = avoid = pref = 0
        for d in range(inst.D):
            k = row[d]
            if k == OFF:
                continue
            shifts += 1
            hours += inst.hours[k]
            wk += inst.weekend[d]
            kind = inst.kinds[k]
            ev += kind == "evening"
            ni += kind == "night"
            avoid += k in inst.avoid[p]
            pref += k in inst.preferred[p]
        reqs = sorted(inst.off_req[p])
        granted = sum(1 for d in reqs if row[d] == OFF)
        out.append(
            PersonStats(
                s.id, s.name, shifts, hours, inst.target[p], wk, ev, ni, ev + ni, len(reqs), granted, avoid, pref
            )
        )
    return out


def load(count: float, contract: float) -> float:
    """Load per 40 contracted hours, so part-timers are judged on their share."""
    return count / max(contract, 8.0) * 40


def fairness_report(stats: list[PersonStats]) -> dict[str, float]:
    wk = [load(s.weekends, s.contract) for s in stats]
    un = [load(s.unsocial, s.contract) for s in stats]
    hr = [s.hours / max(s.contract, 8.0) for s in stats]
    g_w, g_u, g_h = gini(wk), gini(un), gini(hr)
    mean = W_WEEKEND * g_w + W_UNSOCIAL * g_u + W_HOURS * g_h
    return {
        "gini_weekend": round(g_w, 4),
        "gini_unsocial": round(g_u, 4),
        "gini_hours": round(g_h, 4),
        "spread_weekend": round(max(wk) - min(wk), 2) if wk else 0.0,
        "spread_unsocial": round(max(un) - min(un), 2) if un else 0.0,
        "spread_hours_ratio": round(max(hr) - min(hr), 3) if hr else 0.0,
        # A mean Gini of 0.5 would score zero; 0 scores 100.
        "score": round(100 * (1 - min(1.0, mean * 2)), 1),
    }
