# Town Bridge Finder

**Problem.** When a road closes (flood, roadworks, a collapsed bridge) some towns split in two and others barely notice. Which single roads or junctions is a town *dependent* on, and where would one new road help most?

**Solution.** A town as a graph (places and roads), analysed with Tarjan's low-link depth-first search to find every **bridge** (a road whose closure disconnects the town) and every **articulation point** (a junction whose loss does). Click any road on the map to close it and see which pieces result. A brute-force search over every missing road recommends the best new road to build.

![demo](docs/demo.png)

**Measured result.** The 15-place, 18-road sample town has 6 bridges and 7 critical junctions. Closing Park-Station splits it into 8 and 7 places. The best single new road, Hill-Lighthouse, removes 5 of the 6 weak links by joining the two dead-end branches into one big loop. Tarjan's results match a slow brute-force check (remove each road and each place in turn) on the town and on 400 random graphs.

## Data
`data/town.json`: an invented town (15 places with map coordinates and 18 roads), written for this repo (MIT). Not a real place.

## Architecture
```
static/index.html (SVG map, click a road) --GET /town, /close?a=&b=--> api.py (FastAPI)
   core.tarjan (iterative DFS, low-link)  -> bridges + articulation points
   core.closure (graph without one road)  -> connected pieces
   core.best_new_roads (try every missing road, re-run tarjan) -> top suggestions
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn townbridge.api:app --reload
pytest && ruff check .
docker build -t townbridge . && docker run -p 8000:8000 townbridge
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- One depth-first pass (Tarjan) instead of removing every road and re-counting: O(V + E) rather than O(E x (V + E)).
- Keep the slow brute-force version as a test oracle: an algorithm this subtle needs an independent check, and it caught a tuple-ordering bug in my first draft.
- Iterative DFS with an explicit stack: no recursion-depth limit on long roads.
- Try every missing road for the recommendation: with 15 places there are only about 87 candidates, so the exhaustive answer is cheap and provably best.
- Sorted, normalised edge tuples everywhere: a bridge is the same road whichever end you list first.

## Limitations
Invented town, unweighted (road length and capacity ignored); closing one road at a time (no simultaneous closures); the "best new road" ignores building cost and geography, so it may suggest a road across the sea; the map is drawn from fixed coordinates, with some label overlap; it only looks at connectivity, not detour length.
