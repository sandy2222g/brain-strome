# Check Digit Validator

**Problem.** Card numbers, ISBNs, product barcodes and bank account numbers (IBANs) end in a "check digit" computed from all the others, so a mistyped number is rejected before it causes a failed payment or a wrong delivery. But no check catches every mistake. Which typos does each scheme miss, and by how much?

**Solution.** Four validators written from scratch: Luhn (cards), ISBN-10 (mod 11), ISBN-13 / EAN-13 (weights 1 and 3) and IBAN (mod 97 with letters turned into numbers). On top of that, an experiment: generate thousands of random valid numbers, make one typical typing mistake in each (one digit wrong, two adjacent digits swapped, a doubled pair changed) and count how many are noticed. The page lets you type a number and see it fail when you change a digit.

![demo](docs/demo.png)

**Measured result (4,000 random valid numbers per cell).** One wrong digit: caught 100% by every scheme. Swapped neighbours: Luhn 97.8% (its blind spot is 09 swapped with 90), ISBN-10 100%, ISBN-13 90.7% (misses digits that differ by 5), IBAN 100%. A doubled pair changed (for example 11 to 22): Luhn 93.6%, ISBN-10 89.4%, ISBN-13 88.7%, IBAN 100%. The Luhn figure matches the theoretical 97.8% (88 of 90 ordered pairs of unequal digits).

## Data
No data files. Random valid numbers are generated in code and are made up: they are not anyone's real card, book or account. The documented examples (4111 1111 1111 1111, 0-306-40615-2, 978-0-306-40615-7, GB82 WEST 1234 5698 7654 32, DE89 3704 0044 0532 0130 00) are the well-known public test values from the standards' own documentation. MIT licence.

## Architecture
```
static/index.html --GET /validate?scheme=&value=, /examples, /experiment--> api.py (FastAPI)
   core.{luhn,isbn10,isbn13,iban}_valid   core.random_valid -> core.corrupt -> core.validate
   core.experiment: catch rate for every (scheme, mistake type) pair
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn checkdigit.api:app --reload
pytest && ruff check .
docker build -t checkdigit . && docker run -p 8000:8000 checkdigit
```
Deploy: see [DEPLOY.md](DEPLOY.md). The experiment (about 3 seconds) runs on the first request and is then cached.

## Design decisions
- Measure the detection rates instead of quoting folklore: the experiment reproduces known theory (Luhn 97.8%) and exposes less-known figures such as ISBN-13's 90.7%.
- Generate valid numbers, then corrupt them: that is exactly the question a form designer asks ("if a person mistypes a valid number, do we notice?").
- Test the Luhn blind spot explicitly: a swapped 09 stays valid, and every other swap is caught.
- Strip spaces and dashes before checking: people type numbers in groups, and a validator that rejects "4111 1111" would be unusable.
- IBAN length checked per country for six countries: the mod-97 check alone accepts numbers of the wrong length.

## Limitations
Only detects mistakes, it cannot fix them; no card-brand, country or bank-code rules beyond IBAN length for six countries; a valid check digit does not mean the number exists or belongs to anyone; only digit mistakes are tested, not letters in IBANs; ISBN-13 random numbers start with 978 (so some pairs of digits never swap), which is why 90.7% is above the textbook 88.9%.
