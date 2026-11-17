from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import BracketError, Team, first_round, load_teams, round_robin, seed_order, simulate

app = FastAPI(title="Tournament Bracket Maker")
TEAMS = load_teams()
STATIC = Path(__file__).resolve().parents[2] / "static"


def pick(n: int) -> list[Team]:
    if not 2 <= n <= len(TEAMS):
        raise HTTPException(422, f"n must be between 2 and {len(TEAMS)}")
    return TEAMS[:n]


@lru_cache(maxsize=32)
def sim(n: int, trials: int) -> dict[str, dict[str, float]]:
    return simulate(pick(n), trials)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/teams")
def teams() -> dict[str, object]:
    return {"teams": [{"name": t.name, "rating": t.rating} for t in TEAMS]}


@app.get("/bracket")
def bracket(n: int = 12) -> dict[str, object]:
    ts = pick(n)
    pairs = first_round(ts)
    seeds = {t.name: i + 1 for i, t in enumerate(sorted(ts, key=lambda t: -t.rating))}
    return {"first_round": [[{"name": x.name, "seed": seeds[x.name]} if x else None for x in p] for p in pairs],
            "size": len(pairs) * 2, "seed_order": seed_order(len(pairs) * 2),
            "round_robin": [[[a.name, b.name] for a, b in r] for r in round_robin(ts)]}


@app.get("/simulate")
def simulate_api(n: int = 12, trials: int = 3000) -> dict[str, object]:
    try:
        return {"trials": trials, "chances": sim(n, trials)}
    except BracketError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
