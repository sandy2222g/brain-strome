# Board Game Dice Odds

**Problem.** "Is rolling with advantage really that much better?" and "how likely is 28 damage from 8d6?" are everyday tabletop questions, usually answered by guesswork or by simulations that are slightly different every time.

**Solution.** Exact probability distributions for dice expressions such as `2d6`, `4d6dl1` (drop lowest), `2d20kh1` (keep highest) and `1d8+3`, computed with exact fractions. A seeded Monte Carlo simulation runs alongside as an independent cross-check, so the page shows both the exact answer and how closely a simulation agrees.

![demo](docs/demo.png)

**Measured result.** Rolling two 20-sided dice and keeping the best gives an average of **13.825** vs **10.5** for one die, and the chance of reaching 15 rises from 30% to **51%**. The simulation agrees with the exact answer to within 0.3 percentage points on every outcome.

## Data
`data/presets.json`: six example rolls with targets. All numbers are computed, not stored; there is no external dataset.

## Architecture
```
static/index.html --GET /odds?expr=&target=--> api.py (FastAPI) --> core.distribution
                  --GET /presets-->                                 (convolution, or multiset enumeration for keep/drop; Fractions)
                                                                    core.monte_carlo (seeded cross-check)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn diceodds.api:app --reload
pytest && ruff check .
docker build -t diceodds . && docker run -p 8000:8000 diceodds
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- `fractions.Fraction`: exact answers like 51/100, no floating-point drift to explain away.
- Convolution for plain sums: one pass per die, far cheaper than enumerating every outcome.
- Multiset enumeration with multinomial weights for keep/drop: 4d6 needs 126 cases rather than 1,296.
- A hard cap on enumeration size: a malicious `20d100kh1` returns an error instead of hanging the server.
- Seeded Monte Carlo cross-check: two independent methods agreeing is the correctness evidence, not a single formula.

## Limitations
No exploding dice, rerolls or multi-step rules; one keep/drop rule per roll; at most 20 dice of up to 100 sides; keep/drop rolls limited by enumeration size. MIT licence.
