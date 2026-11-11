# Timetable Builder

![demo](docs/demo.png)

## Problem
Enrolment: each course has several sections, some clash, there is a credit cap, and some courses are mandatory. Signing up in catalogue order often wastes credits, spreads classes across the whole week, or locks out a required course.

## Solution
Exact search. Every course is skipped or taken in one of its sections, and a branch is dropped the moment it clashes or passes the credit cap. Ranking: all required courses present, then most credits, then fewest campus days, then least idle time between classes. On the sample catalogue (8 courses, cap 15):

| | Catalogue order | Timetable Builder |
|---|---|---|
| Credits | 14 | **15** |
| Days on campus | 5 | **3** |
| Idle minutes between classes | 240 | 210 |
| Required courses | **Databases missing** | all in |

## Architecture
```
data/catalog.json or POST body -> core.build_courses (validate) -> core.best_timetable (search) / register_in_order
                               -> FastAPI /build -> static/index.html (Mon-Fri grid)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn timetable.api:app --port 8000
pytest -q && ruff check .
docker build -t timetable . && docker run -p 8000:8000 timetable
```
Endpoints: `GET /health`, `GET /sample`, `POST /build`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Exact search: with at most 12 courses and a few sections each, pruning keeps it fast and the answer cannot be beaten.
- Required courses are a hard rule, not a bonus: a timetable without them is useless, so none is returned.
- Credits before days before idle time: a clear ranking people can reason about.
- Back-to-back classes are not clashes: a class ending at 10:30 and another starting at 10:30 is normal.
- Clear errors for impossible requests: clashing required courses or a cap below the required credits return 422.

## Limitations
- Times are weekly and fixed; no rooms, travel time or waiting lists.
- Capped at 12 courses; larger catalogues need a smarter search.
- Catalogue is invented (MIT).
