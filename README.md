# Raffle Ticket Reality Check

**Problem.** "Someone has to win" is true, but it hides how rarely it is you, and how much the tickets cost along the way. People rarely see the odds, the payout rate, or the spread of outcomes in one place.

**Solution.** For a pick-k-of-n game the app computes exact hypergeometric odds for every prize tier, the expected return per ticket (the payout rate), and then simulates 1,000 imaginary players who each buy the same number of tickets, showing how many end up ahead and how bad the typical outcome is. A second panel gives the break-even prize for a single-prize raffle.

![demo](docs/demo.png)

**Measured result.** Buying a weekly Lucky Six ticket for 10 years (520 tickets, $1,040) pays back **33 cents per dollar**; **1.5%** of simulated players end up ahead and the typical player is down **$880**. The jackpot is 1 in 8,145,060.

## Data
`data/games.json`: three invented pick-k-of-n games (not real lotteries; prizes tuned to payout rates of 33%, 59% and 61%, in the range real lotteries pay). Nothing is stored beyond these rules; every probability is computed.

## Architecture
```
static/index.html --GET /analyse?game=&tickets=, /raffle, /games--> api.py (FastAPI)
                                                                     --> core.tiers / expected_value  (exact, math.comb)
                                                                     --> core.simulate                (seeded, bisect over the odds table)
                                                                     data/games.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn raffleodds.api:app --reload
pytest && ruff check .
docker build -t raffleodds . && docker run -p 8000:8000 raffleodds
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Exact odds with `math.comb`: no sampling error in the headline numbers.
- Simulation only for the spread of outcomes: the question "how many people end up ahead" has no closed form for 500+ tickets.
- Median shown beside the mean: the mean is dominated by a jackpot almost nobody hits, so it overstates the typical result.
- A cap of 2 million simulated draws per request: a public endpoint cannot be asked to compute forever.
- Seeded random generator: the same inputs always give the same picture, which keeps tests exact.

## Limitations
The simulated mean can differ noticeably from the exact expected value when a rare jackpot dominates (here -$829 simulated vs -$702 exact): that gap is the point, not a bug. No shared jackpots or rollovers, taxes, or multi-draw bonus balls; invented games. MIT licence.
