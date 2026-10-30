from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import Game
from .rankers import select
from .rankers.base import Ranker


def load_season(path: Path) -> List[Game]:
    payload = json.loads(path.read_text())
    return [Game.from_dict(g) for g in payload["games"]]


def week_label(games: Sequence[Game], week: int) -> str:
    in_week = [g for g in games if g.week == week]
    if in_week and all(g.season_type == "postseason" for g in in_week):
        return "Postseason"
    return f"Week {week}"


def build_rankings(ranker: Ranker, games: Sequence[Game]) -> List[Dict[str, Any]]:
    """Rank every team in `games`, publishing FBS teams only (or all, if unclassified)."""
    ratings = ranker.rank(games)

    stats: Dict[str, Dict[str, Any]] = {}
    for g in games:
        for team, conf, cls, mine, theirs in (
            (g.home, g.home_conf, g.home_class, g.home_points, g.away_points),
            (g.away, g.away_conf, g.away_class, g.away_points, g.home_points),
        ):
            s = stats.setdefault(team, {"w": 0, "l": 0, "t": 0})
            s["conference"], s["classification"] = conf, cls
            s["w" if mine > theirs else "l" if mine < theirs else "t"] += 1

    published = [t for t, s in stats.items() if s["classification"] == "fbs"]
    if not published:
        published = list(stats)

    ordered = sorted(published, key=lambda t: (-ratings[t], t))
    return [
        {
            "rank": i,
            "team": team,
            "rating": round(ratings[team], 4),
            "wins": stats[team]["w"],
            "losses": stats[team]["l"],
            "ties": stats[team]["t"],
            "conference": stats[team]["conference"],
        }
        for i, team in enumerate(ordered, start=1)
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1) + "\n")


def run(
    games_dir: Path,
    out_dir: Path,
    ranker_ids: Optional[List[str]] = None,
    seasons: Optional[List[int]] = None,
) -> None:
    """Rank every season in games_dir with every selected ranker, week by week."""
    rankers = select(ranker_ids)
    season_games = {}
    for path in sorted(games_dir.glob("*.json")):
        games = load_season(path)
        if games and (not seasons or games[0].season in seasons):
            season_games[games[0].season] = games
    if not season_games:
        raise SystemExit(f"No games found in {games_dir}. Run `ingest` and `normalize` first.")

    index_seasons = []
    for season in sorted(season_games, reverse=True):
        games = season_games[season]
        weeks = sorted({g.week for g in games})
        index_seasons.append(
            {"season": season, "weeks": [{"week": w, "label": week_label(games, w)} for w in weeks]}
        )
        for ranker in rankers:
            for week in weeks:
                through = [g for g in games if g.week <= week]
                write_json(
                    out_dir / ranker.id / str(season) / f"week-{week}.json",
                    {
                        "ranker": ranker.id,
                        "season": season,
                        "week": week,
                        "params": ranker.params,
                        "rankings": build_rankings(ranker, through),
                    },
                )

    write_json(
        out_dir / "index.json",
        {
            "rankers": [
                {"id": r.id, "name": r.name, "description": r.description, "params": r.params}
                for r in rankers
            ],
            "seasons": index_seasons,
        },
    )
