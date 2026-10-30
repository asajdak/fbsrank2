from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

API_BASE = "https://api.collegefootballdata.com"
SEASON_TYPES = ("regular", "postseason")


def fetch_games(season: int, season_type: str, api_key: str) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode({"year": season, "seasonType": season_type})
    req = urllib.request.Request(
        f"{API_BASE}/games?{query}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def ingest_season(season: int, raw_dir: Path, api_key: str) -> Path:
    """Download all games for a season and save them unmodified to raw_dir."""
    games: List[Dict[str, Any]] = []
    for season_type in SEASON_TYPES:
        games.extend(fetch_games(season, season_type, api_key))
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{season}.json"
    path.write_text(json.dumps(games))
    return path


def api_key_from_env() -> str:
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        raise SystemExit("Set CFBD_API_KEY (free key from https://collegefootballdata.com).")
    return key
