# Palette Extractor

**Problem.** Designers, students making slides and developers theming an app all want "the main colours of this picture". Eyedropper-picking is slow and subjective.

**Solution.** Upload an image (or use the bundled sample). The image is shrunk to at most 64x64 pixels and clustered with k-means++, written from scratch. The API returns each palette colour as hex/RGB with its share of the picture, plus the colour error against a simple baseline.

![demo](docs/demo.png)

**Measured result.** On the bundled sample (a noisy synthetic sunset, k=5) k-means gets a mean squared colour error of **200.5** vs **465.1** for uniform binning (four ranges per channel, most-used cells), and it keeps the small sun, which binning loses.

## Architecture
```
static/index.html --POST /palette (multipart image, k)--> api.py (FastAPI)
                                                          --> core: Pillow thumbnail -> k-means++ -> shares + MSE
                                                          static/sample.png (generated for this repo, CC0)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn palettex.api:app --reload
pytest && ruff check .
docker build -t palettex . && docker run -p 8000:8000 palettex
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- k-means++ from scratch (no scikit-learn): small, explainable, and keeps the image tiny.
- Downscale to 64x64 first: request time is bounded, and small colour details barely change the palette.
- Fixed random seed: the same image always gives the same palette, which makes tests exact.
- Upload limit of 5 MB and k between 1 and 12: protects a free-tier server.
- Nothing is saved: images are processed in memory and dropped.

## Limitations
RGB distance is not perceptual (Lab would match human vision better); tiny but important colours can be absorbed into a big cluster at low k; the sample image is synthetic, so real photos will show less clean results. MIT licence.
