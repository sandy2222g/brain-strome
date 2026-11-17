# Huffman Squeeze

Huffman coding built from scratch, with a live comparison against theory (entropy) and zlib.

![demo](docs/demo.png)

## Problem
"Compression" is often a black box. Where does Huffman coding save space, how close is it to the theoretical limit, and where does it lose?

## Solution
A FastAPI service and page. Paste text and see bytes for original, Huffman (including its code table) and zlib, plus bits per character against the Shannon entropy floor and the code for each letter.

## Architecture
```
browser -> POST /analyse, GET /samples -> api.py -> core.py (build_codes, encode, decode, entropy_bits, analyse)
```

## Verified
- Textbook example (frequencies 45/13/12/16/9/5) costs exactly 224 bits.
- Codes are prefix-free; 100 random round trips decode exactly.
- Bits per character is always >= entropy and < entropy + 1 (Huffman's guarantee).
- On the repetitive sample zlib is under half the size of Huffman, because Huffman ignores repeated patterns.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn huffsqueeze.api:app --port 8000
pytest
docker build -t huffsqueeze . && docker run -p 8000:8000 huffsqueeze
```
Deploy: see DEPLOY.md.

## Design decisions
- Heap with an insertion-order tie-breaker: makes the codes deterministic.
- Single-symbol text gets code "0": avoids a zero-length code that cannot be decoded.
- Header cost counted as 2 bytes per symbol: keeps the Huffman byte count honest rather than ignoring the table.
- Bits kept as a string of 0/1: clearer to read and test than packed bytes.

## Limitations
- Codes are for single characters only; no repeat-pattern matching.
- Output is analysed, not written as a real compressed file.
- Input capped at 20,000 characters. Not deployed; needs the owner's Render/HF account.

Licence: MIT. Sample texts are invented or public-domain nursery rhymes.
