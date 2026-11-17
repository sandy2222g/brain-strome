# Message Shrinker

**Problem.** Compression feels like magic. Why can a DNA string shrink to a quarter of its size while a paragraph of random letters barely shrinks at all, and why does a tiny message sometimes get *bigger*?

**Solution.** A from-scratch Huffman coder that builds the code tree, shows the code table, the exact encoded bits (one colour per letter), a byte-for-byte round-trip check, and the size including the code table, next to the theoretical entropy limit and Python's `zlib` for scale.

![demo](docs/demo.png)

**Measured result.** On five sample texts the average Huffman code length always lands within 1 bit of the entropy limit, as theory says (skewed DNA: 1.767 vs 1.757 bits per letter). It reaches **25%** of the original size on skewed DNA vs **43%** for zlib, but loses to zlib on English (68% vs 64%, because the code table costs bits) and on a repeating pattern (14% vs 5%, because zlib exploits repeated phrases). Overall it beats zlib on 2 of 5 samples.

## Data
`data/samples.json`: five short texts written or generated for this repo (an original English paragraph, skewed random DNA, a repeating pattern, uniform random letters, a number list). No third-party text.

## Architecture
```
static/index.html --POST /shrink, /expand; GET /samples--> api.py (FastAPI)
                                                           --> core.build_tree (heap)  -> core.code_table
                                                           --> core.encode / core.decode (prefix-free, exact)
                                                           --> core.shrink (size accounting, entropy, zlib)
                                                           data/samples.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn shrinkmsg.api:app --reload
pytest && ruff check .
docker build -t shrinkmsg . && docker run -p 8000:8000 shrinkmsg
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Heap-based tree with sorted symbols and a counter tie-break: the same text always yields the same codes, so tests can assert exact sizes.
- Decoding needs only the code table: that is what a real file would carry, and the round trip proves the table is enough.
- Table cost counted as one symbol plus one length byte each: shows honestly why tiny messages grow (a 6-character text becomes 119% of its size).
- Single-symbol text gets the code `0`: otherwise the tree would have a zero-bit code and a text of "aaaa" would encode to nothing.
- Entropy and zlib shown beside the result: a compression ratio means little without a bound and a reference.

## Limitations
Per-character codes only, so no repeated-phrase compression; the code table is estimated rather than serialised to a real file format; text limited to 20,000 characters; no bit-packing to bytes. MIT licence.
