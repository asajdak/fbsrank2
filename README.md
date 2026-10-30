# fbsrank2

A college football ranking website. A Python pipeline downloads game results, runs several ranking algorithms over them, and writes JSON that a static front end displays. No server or database is needed to host it.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design and the reasoning behind it.

## Quick start

```bash
pip install -e .
```

Try it with the synthetic sample season (fictional teams, no API key needed):

```bash
python -m fbsrank --games-dir tests/fixtures/games rank
python -m http.server 8000 --directory site
```

Then open <http://localhost:8000>.

## Using real data

Get a free API key from [collegefootballdata.com](https://collegefootballdata.com), then:

```bash
export CFBD_API_KEY=your-key
python -m fbsrank update --season 2025      # ingest + normalize + rank
```

Or run the steps separately: `ingest`, `normalize`, `rank`. Each takes `--season` (repeatable; defaults to the current season). `rank` and `update` also take `--ranker` (repeatable) to run a subset of algorithms. Normalized games land in `data/games/` (commit these); rankings land in `site/data/` (generated, gitignored).

## Adding a ranking algorithm

1. Create `fbsrank/rankers/yourname.py` with a `Ranker` subclass whose `rank(games)` returns `{team: rating}`.
2. Add an instance to `ALL` in `fbsrank/rankers/__init__.py`.

It will appear in the site's ranking picker on the next `rank` run. See `fbsrank/rankers/colley.py` for a short example.

## Tests

```bash
python -m unittest discover -s tests -t .
```

`tests/make_fixture.py` regenerates the synthetic sample season.

## Deployment

`.github/workflows/update.yml` refreshes the data on a schedule and deploys `site/` to GitHub Pages. It needs a `CFBD_API_KEY` repository secret and Pages set to deploy from GitHub Actions.
