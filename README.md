# Hall Booking Optimizer

![demo](docs/demo.png)

## Problem
A village hall gets overlapping requests for one Saturday. Accepting them in the order they arrive, or taking as many as possible, can leave a lot of money on the table when one big booking blocks several small ones.

## Solution
Weighted interval scheduling by dynamic programming: sort requests by end time; for each, either skip it or take it with the best set that finishes before it starts. On 11 sample requests:

| Method | Fees | Bookings | Hours used |
|---|---|---|---|
| First come, first served | $480 | 4 | 11.5 |
| Most bookings (earliest finish) | $205 | 4 | 6.5 |
| **Best combination (DP)** | **$655** | 3 | 11 |

The best plan takes yoga, the wedding reception and the charity quiz, and turns away eight requests. A test checks the DP against brute force over all 2,048 subsets.

## Architecture
```
data/requests.json or POST body -> core.build (validate) -> core.best_bookings (DP) / first_come_first_served / earliest_finish
                                -> FastAPI /book -> static/index.html (timeline lanes)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn hallbook.api:app --port 8000
pytest -q && ruff check .
docker build -t hallbook . && docker run -p 8000:8000 hallbook
```
Endpoints: `GET /health`, `GET /sample`, `POST /book`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Dynamic programming over end-sorted requests: optimal in O(n log n) and easy to verify.
- Binary search for the last compatible request: keeps the DP fast for a few hundred requests.
- Back-to-back bookings are allowed: a booking ending at 14:00 and another starting at 14:00 do not overlap.
- Two baselines: first-come is what a volunteer does, earliest-finish is the textbook greedy that maximises count, not money.
- Brute-force check in tests: a small instance lets the DP be proved correct, not just trusted.

## Limitations
- One room, fixed fees, no setup/cleanup gaps, no fairness or regular-customer rules.
- Maximises fees only; it may refuse many small community groups (a weight could value those).
- Requests and fees are invented (MIT).
