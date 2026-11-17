# Receipt Line Reader

**Problem.** Splitting a bill or logging expenses means retyping receipts. Receipt text is messy: quantities appear as `2 x Latte`, `Latte 2@4.50` or not at all; OCR turns `0` into `O` and `1` into `l`; some printers use a comma for the decimal point. And the printed arithmetic is sometimes simply wrong.

**Solution.** A rule-based parser turns receipt text into items (name, quantity, line total in cents) and totals (subtotal, tax, tip, total), repairs OCR digit confusions only inside amounts, and then checks the arithmetic: do the items sum to the printed subtotal, and does subtotal + tax + tip equal the total?

![demo](docs/demo.png)

**Measured result.** On 8 synthetic receipts (47 items, five different line formats) the parser extracts **100%** of items exactly (name, quantity and amount); a one-pattern baseline (name followed by a dotted price) manages **40%**. Both injected arithmetic errors are caught and no clean receipt is flagged (8/8). The sample receipts were written by the same author as the parser, so this shows the formats are handled, not how it fares on arbitrary receipts.

## Data
`data/receipts.json`: 8 synthetic cafe receipts with ground-truth items, totals and issues, generated for this repo. No real receipts or personal data. Receipt 4's label originally listed one issue; the parser rightly found two (inflated subtotal also breaks subtotal + tax = total), so the label was corrected.

## Architecture
```
static/index.html --POST /parse--> api.py (FastAPI) --> core.parse -> parse_item (qty rules, money repair)
                  --GET /samples, /evaluation-->        core.check (sum and total tests, integer cents)
                                                        data/receipts.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn receiptread.api:app --reload
pytest && ruff check .
docker build -t receiptread . && docker run -p 8000:8000 receiptread
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Integer cents everywhere: sums compare exactly, no float rounding to excuse.
- OCR repair only inside money tokens: turning every `O` into `0` would corrupt item names like "Orange juice".
- Quantity from `N x` or `N@price` only: quantity is not guessed from the price.
- Total keywords matched at line start, longest meaning first ("subtotal" before "total"): the total line must not be read as an item.
- Report issues as codes, not prose: callers (UI, tests) decide how to word them.

## Limitations
English keywords only; one currency format; no multi-line item names, discounts or negative lines; assumes a total is printed on one line; synthetic receipts only. MIT licence.
