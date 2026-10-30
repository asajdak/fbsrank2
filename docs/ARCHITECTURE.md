# Architecture

fbsrank2 is a college football ranking site built as a **batch pipeline that emits static files**. A script downloads game results, several ranking algorithms turn those results into ratings, and the output is written as JSON that a static front end reads. There is no application server and no database in production.

## Why static files instead of a database

The data is tiny (about 130 FBS teams x ~15 weeks x a handful of algorithms is a few hundred KB of JSON). It is written by one batch job and read by anonymous visitors, and nothing needs a live query. A static host (GitHub Pages, Cloudflare Pages, S3 + CloudFront) is cheaper, faster, and has nothing to patch or keep running.

JSON files are preferred over baking numbers into HTML: the pipeline and the presentation stay decoupled, so the site can be redesigned without re-running the analysis, and the files are browser-cacheable.

A database becomes worthwhile if you add user accounts or user-submitted ballots, server-side ad hoc queries (for example "teams in the top 10 of 3+ algorithms"), or much larger data such as play-by-play. Even then you can add a small API later without redoing the pipeline.

## Data flow

```
CFBD API --ingest--> data/raw/{season}.json
                          |
                      normalize
                          v
                data/games/{season}.json          (committed)
                          |
             +------------+------------+
             v                         v
       ranker: elo               ranker: colley   ...   (one module each)
             |                         |
             +-----------+-------------+
                         v
   site/data/{ranker}/{season}/week-{n}.json  +  site/data/index.json
                         |
                static site (site/) fetches the JSON
                         |
                    static host
```

### 1. Ingest (`fbsrank/ingest.py`)

Fetches games from [CollegeFootballData.com](https://collegefootballdata.com) (CFBD), which has a free API key and covers scores, neutral-site flags, conferences, and FBS/FCS classification. The key is read from the `CFBD_API_KEY` environment variable. Raw responses are saved unmodified to `data/raw/` (gitignored), so parsing bugs can be fixed without re-downloading.

Check CFBD's current rate limits before choosing a fetch schedule. The ingester makes two requests per season (regular and postseason).

### 2. Normalize (`fbsrank/normalize.py`)

Converts raw CFBD records to the `Game` schema in `fbsrank/models.py` and writes `data/games/{season}.json`. These files are small and **are committed**, so git history is an audit trail of the inputs.

- Games that are not completed or have no score are dropped.
- Postseason weeks restart at 1 in CFBD. Normalization shifts them to continue after the last regular-season week, so `week` is a single increasing sequence per season.

### 3. Rankers (`fbsrank/rankers/`)

Every algorithm implements one small interface:

```python
class Ranker:
    id: str            # used in file paths and the UI
    name: str
    description: str
    params: dict       # tunables, copied into the output metadata
    def rank(self, games) -> dict[str, float]:   # team -> rating
```

A ranker is a **pure function of the games played so far**. It never reads files, never knows about weeks, and never formats output. This makes results deterministic and lets the runner produce week-by-week history just by calling `rank` with a growing list of games.

To add an algorithm: create a module in `fbsrank/rankers/`, subclass `Ranker`, and add an instance to `ALL` in `fbsrank/rankers/__init__.py`.

Included: **Elo** (chronological, with home-field advantage and a margin-of-victory multiplier) and **Colley** (a linear-system solve using only wins and losses, no margin).

### 4. Runner (`fbsrank/runner.py`)

For each season, ranker, and week it:

1. selects the games with `week <= n`,
2. calls `ranker.rank`,
3. sorts, numbers, and decorates the result with record and conference,
4. writes `site/data/{ranker}/{season}/week-{n}.json`.

It also writes `site/data/index.json`, listing the available rankers (with descriptions and params), seasons, and weeks. The front end is driven entirely by that index, so new rankers and seasons appear without front-end changes.

**FCS policy:** every team that appears in a game is rated (so FBS-vs-FCS results still carry information), but only teams classified `fbs` are published in the rankings. If no game carries classification data, all teams are published.

### 5. Site (`site/`)

Plain HTML, CSS, and JS with no build step. It reads `data/index.json`, lets the visitor pick ranker, season, and week, and renders the table with week-over-week rank movement. When the site outgrows this, a static generator (Astro, Eleventy) can pre-render pages from the same JSON.

### 6. Automation (`.github/workflows/update.yml`)

A scheduled GitHub Actions job runs `python -m fbsrank update` (ingest, normalize, rank), commits any changed `data/games/` files, and deploys `site/` to GitHub Pages. No server to maintain. `site/data/` is generated in CI and is not committed.

## Design rules

- **Rankings are a pure function of the games through week N.** Same input, same output.
- **Raw and normalized data are separate.** Raw is a cache of what the API said; normalized is the source of truth for ranking.
- **Tunables live in `params`** and are written into every output file, so a ranking can be traced to the settings that produced it.
- **Output is deterministic** (no timestamps in per-week files), so commits and diffs only change when the results do.
- **Each season is ranked independently.** There is no carry-over of ratings between seasons yet. Preseason priors would be a natural future ranker option.

## Layout

```
fbsrank/            pipeline package (python -m fbsrank ...)
  models.py         Game dataclass
  ingest.py         CFBD download
  normalize.py      raw -> Game
  runner.py         run rankers, write JSON
  cli.py            command line
  rankers/          one module per algorithm
data/games/         normalized games (committed)
data/raw/           raw API responses (gitignored)
site/               static front end; site/data/ is generated
tests/              unit tests; tests/fixtures/ has a synthetic season
docs/               this file
```
