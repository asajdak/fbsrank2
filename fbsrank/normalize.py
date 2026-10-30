from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Game


def _get(raw: Dict[str, Any], *keys: str) -> Any:
    """First present key; CFBD has used both camelCase and snake_case."""
    for key in keys:
        if raw.get(key) is not None:
            return raw[key]
    return None


def _classification(raw: Dict[str, Any], side: str) -> str:
    value = _get(raw, f"{side}Classification", f"{side}_classification")
    return str(value).lower() if value else "unknown"


def normalize_game(raw: Dict[str, Any]) -> Optional[Game]:
    """Convert one raw CFBD game, or None if it is not a completed game with a score."""
    home_points = _get(raw, "homePoints", "home_points")
    away_points = _get(raw, "awayPoints", "away_points")
    if not raw.get("completed") or home_points is None or away_points is None:
        return None
    return Game(
        id=int(raw["id"]),
        season=int(raw["season"]),
        week=int(raw["week"]),
        season_type=str(_get(raw, "seasonType", "season_type") or "regular"),
        start_date=str(_get(raw, "startDate", "start_date") or ""),
        home=str(_get(raw, "homeTeam", "home_team")),
        away=str(_get(raw, "awayTeam", "away_team")),
        home_points=int(home_points),
        away_points=int(away_points),
        neutral=bool(_get(raw, "neutralSite", "neutral_site")),
        home_class=_classification(raw, "home"),
        away_class=_classification(raw, "away"),
        home_conf=str(_get(raw, "homeConference", "home_conference") or ""),
        away_conf=str(_get(raw, "awayConference", "away_conference") or ""),
    )


def normalize_season(raw_games: List[Dict[str, Any]]) -> List[Game]:
    """Normalize a season, making `week` one increasing sequence.

    CFBD restarts postseason weeks at 1, so postseason games are shifted to
    continue after the last regular-season week.
    """
    games = [g for g in (normalize_game(r) for r in raw_games) if g is not None]
    last_regular = max((g.week for g in games if g.season_type == "regular"), default=0)
    shifted = [
        Game.from_dict({**g.to_dict(), "week": g.week + last_regular})
        if g.season_type == "postseason"
        else g
        for g in games
    ]
    return sorted(shifted, key=lambda g: (g.week, g.start_date, g.id))


def write_season(season: int, games: List[Game], games_dir: Path) -> Path:
    games_dir.mkdir(parents=True, exist_ok=True)
    path = games_dir / f"{season}.json"
    payload = {"season": season, "games": [g.to_dict() for g in games]}
    path.write_text(json.dumps(payload, indent=1) + "\n")
    return path


def normalize_file(raw_path: Path, games_dir: Path) -> Path:
    raw_games = json.loads(raw_path.read_text())
    games = normalize_season(raw_games)
    season = games[0].season if games else int(raw_path.stem)
    return write_season(season, games, games_dir)
