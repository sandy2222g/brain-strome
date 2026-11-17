from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import MoonError, error_hours, full_moons_in, month_calendar, reference

app = FastAPI(title="Moon Phase Calendar")
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/month")
def month(year: int = 2024, month: int = 1) -> dict[str, object]:
    try:
        days = month_calendar(year, month)
    except MoonError as e:
        raise HTTPException(422, str(e)) from e
    first_weekday = datetime(year, month, 1).weekday()  # Monday = 0
    fulls = [t.strftime("%Y-%m-%d %H:%M") for t in full_moons_in(year) if t.month == month]
    return {"year": year, "month": month, "first_weekday": first_weekday, "days": days, "full_moons": fulls}


@app.get("/accuracy")
def accuracy() -> dict[str, object]:
    rough, good = error_hours(False), error_hours(True)
    def stats(e: list[float]) -> dict[str, float]:
        return {"mean_hours": round(sum(e) / len(e), 2), "worst_hours": round(max(e), 2)}

    return {"count": len(rough), "mean_only": stats(rough), "corrected": stats(good),
            "reference": [t.isoformat() for t in reference()]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
