# Bookshelf Filler

**Problem.** Books in a series must stay in order, but shelf height is wasted when one tall book sits among short ones. Filling each shelf until it is full is quick but not frugal.

**Solution.** Dynamic programming over the ordered books chooses where each shelf ends, so the summed height of all shelves (each as tall as its tallest book) is as small as possible.

![demo](docs/demo.png)

Sample (18 invented books, shelf width 30): **110 cm** of shelf height vs **128 cm** with fill-until-full (18 cm saved). The sample was picked from random draws to show a clear gap; many layouts save less.

## Architecture
```
static/index.html --POST /fill--> api.py (FastAPI) --> core.optimal / greedy
                                                        data/books.json (invented)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn shelffill.api:app --reload
pytest && ruff check .
docker build -t shelffill . && docker run -p 8000:8000 shelffill
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Keep reading order: series are never reshuffled, which also makes the DP one-dimensional.
- DP over the end of the last shelf: O(n·k) and provably optimal; checked against brute force in tests.
- Greedy fill as the baseline: it is what most people actually do.
- Stateless API: no library data is stored.

## Limitations
Shelf height is the tallest book (no adjustable shelves or lying-flat books); one fixed width for all shelves; books are invented. MIT licence.
