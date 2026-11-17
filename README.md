# Mini Spreadsheet

**Problem.** Spreadsheets look simple but hide real computer science: a formula is a program, cells form a dependency graph, and one careless reference can create a loop. Most people use that machinery without ever seeing it.

**Solution.** A small spreadsheet engine written from scratch: a tokenizer and recursive-descent parser for formulas (`+ - * / ^`, parentheses, unary minus, cell references, ranges such as `B2:D2`, and `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `ROUND`, `ABS`), memoised evaluation so every cell is computed once, and cycle detection that marks every cell on a loop with `#CYCLE`. The web page is an editable grid: click a cell to see its formula and the cells it depends on highlighted, edit anything and everything downstream recalculates.

![demo](docs/demo.png)

**Measured result.** The sample monthly budget (48 cells, three levels of dependency) evaluates in one pass with totals checked by hand (spent 3,770, savings 880, savings rate 18.9%). Errors behave like a real spreadsheet: `#DIV/0!`, `#VALUE!`, `#NAME?`, `#SYNTAX` and `#CYCLE` propagate to everything that depends on them. 11 tests cover precedence, associativity, ranges, error propagation and cycles.

## Data
`data/budget.json`: an invented three-month household budget (rent, food, transport, income and totals). No real finances.

## Architecture
```
static/index.html --POST /evaluate; GET /sample--> api.py (FastAPI)
                                                    --> core.tokenize -> core.Parser (recursive descent: expr > term > power > unary > primary)
                                                    --> core.Sheet    (memoised cells, dependency sets, cycle stack, topological order)
                                                    data/budget.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn minisheet.api:app --reload
pytest && ruff check .
docker build -t minisheet . && docker run -p 8000:8000 minisheet
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Recursive descent, one function per precedence level: the grammar is readable straight off the code and a new operator is a few lines.
- Right-associative `^` and Excel-style unary minus (`-2^2` is 4): matching a real spreadsheet beats textbook purity for users who will compare.
- Evaluate on demand with a cache plus a stack of cells being computed: a cell met again while still on the stack is a cycle, no separate graph pass needed.
- The cycle error is re-raised up the stack: without that, only the cell where the loop was noticed would show `#CYCLE` and its neighbours would show wrong numbers.
- Text and blanks are skipped by range functions but break arithmetic: `SUM` over a header row works, `"hello"+1` is a `#VALUE!`.
- Server-side limit of 500 cells and A-Z columns: a public endpoint cannot be fed a huge sheet.

## Limitations
No `IF`, text functions or cross-sheet references; columns A-Z and rows 1-99; no absolute references (`$A$1`) or copy-and-adjust; every edit re-evaluates the whole sheet rather than only the affected cells; floating-point results. MIT licence.
