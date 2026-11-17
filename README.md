# Password Strength Coach

A password estimator that explains its reasoning: entropy, crack time, patterns and plain advice.

![demo](docs/demo.png)

## Problem
"Must contain a symbol and a digit" rules reward passwords like `Tr0ub4dor&3` and punish long, memorable ones. Users need honest feedback.

## Solution
A FastAPI service and page. It estimates entropy from the character pool, then lowers it for common passwords (including leet-speak variants), keyboard or alphabet runs, repeated characters and dictionary words with predictable tweaks. It converts the result to a crack time for a fast offline attacker (10 billion guesses per second) and gives a 0 to 4 score with warnings.

## Architecture
```
browser (debounced input) -> POST /assess, GET /passphrase -> api.py -> core.py (pool_size, word_aware_bits, has_sequence, assess)
```
Passwords are analysed in memory only and never stored or logged.

## Sample results
| password | bits | verdict |
|---|---|---|
| letmein | 10 | very weak (common) |
| Tr0ub4dor&3 | 31.1 | weak: a word with predictable tweaks |
| qzvmtbhs | 37.6 | weak: 8 random lowercase letters = 8 x log2(26) |
| correct horse battery staple | 61.6 | strong (4 words, not 164 bits as a naive count says) |

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn pwcoach.api:app --port 8000
pytest
docker build -t pwcoach . && docker run -p 8000:8000 pwcoach
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Cost dictionary words as words, not letters: a naive pool estimate rates `Tr0ub4dor&3` far too high.
- Take the lower of the two estimates: the attacker uses whichever method is cheaper.
- Crack time shown in plain words: users act on "6 years", not "61 bits".
- POST body for passwords: keeps them out of URLs and access logs.

## Limitations
- The built-in word list has about 60 words as a stand-in; real crackers use millions, so scores are optimistic.
- Common-password list is a short generic sample, not a breach database.
- Estimates assume a fast hash; a slow hash such as bcrypt makes real attacks far slower.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. No external data; all lists are invented or common knowledge.
