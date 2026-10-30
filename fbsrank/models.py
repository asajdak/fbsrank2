from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Game:
    """One completed game, in the normalized schema stored in data/games/."""

    id: int
    season: int
    week: int  # single increasing sequence per season; postseason continues after regular season
    season_type: str  # "regular" or "postseason"
    start_date: str  # ISO 8601, sortable as a string
    home: str
    away: str
    home_points: int
    away_points: int
    neutral: bool
    home_class: str  # "fbs", "fcs", other division, or "unknown"
    away_class: str
    home_conf: str
    away_conf: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Game":
        return cls(**d)
