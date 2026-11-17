# Dither Lab

**Problem.** Printers, e-ink screens, old game consoles and thermal receipt printers can only show black or white. Rounding every pixel to the nearest one throws away all the shading. How do you make a two-colour picture that still *looks* grey from a distance, and how do you compare methods fairly?

**Solution.** Four dithering methods written from scratch in pure Python (no image library): plain threshold, ordered (Bayer 4x4 matrix), Floyd-Steinberg error diffusion and Atkinson. Each is scored by how close the black-and-white picture looks to the original when blurred (5x5 window averages), plus how far overall brightness drifts. Three generated test pictures: a ramp, a shaded sphere and a wave pattern.

![demo](docs/demo.png)

**Measured result.** Look-from-afar error (lower is better): threshold 0.19-0.26, ordered 0.04, **Floyd-Steinberg 0.024-0.026**, Atkinson 0.047-0.069. Floyd-Steinberg wins on all three pictures and keeps overall brightness within 0.01. A useful finding from the build: scoring with 4x4 windows makes ordered dithering look better than Floyd-Steinberg, because the window lines up with the Bayer tile; 5x5 windows at every position remove that bias, and a test pins both results.

## Data
No files. The three test pictures are generated in code (`images()`), 96x96, so there is nothing to license (MIT).

## Architecture
```
static/index.html (canvas) --GET /dither?image=&method=, /images--> api.py (FastAPI)
  --> core.images() (generated greys) --> core.dither(method) -> 0/1 grid
  --> core.blur_error + core.brightness_gap -> table for all four methods
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn dithering.api:app --reload
pytest && ruff check .
docker build -t dithering . && docker run -p 8000:8000 dithering
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Pure Python lists, no Pillow or NumPy: nothing to install, and the algorithms stay readable (about 100 lines).
- Score on blurred windows, not pixel by pixel: dithering deliberately gets every pixel "wrong", what matters is how it looks from a distance.
- Window size 5, every position: a 4-pixel window lines up with the Bayer tile and flatters that method (test `test_measure_choice_can_flatter_a_method`).
- Generated test pictures: a smooth ramp, a curved shape and mixed patterns exercise different weaknesses, and need no image licences.
- Browser draws the pixels on a canvas: the API stays small JSON and the page can show a game-console palette.

## Limitations
Greyscale only (no colour dithering); 96x96 synthetic pictures, not photographs, and no upload; one error metric, which is not the same as what a human prefers (Atkinson scores worse but many people like its crisper look); no serpentine scanning, which removes the directional streaks Floyd-Steinberg can leave.
