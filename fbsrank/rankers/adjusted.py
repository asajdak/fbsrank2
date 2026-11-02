from __future__ import annotations

from typing import Dict, Sequence

from ..models import Game
from .classic import ClassicRanker
from .p4 import default_p4_params, is_p4


class AdjustedClassicRanker(ClassicRanker):
    id = "classic_adjusted"
    name = "FBS Rank Classic (Adjusted)"
    description = (
        "FBS Rank Classic that ignores games against non-FBS teams, with three adjustable credits: the #1 opponent is worth 0.8 instead "
        "of 1 (still falling linearly to nothing at #69), each road win earns a bonus, and each "
        "game against a Power 4 opponent earns a bonus, win or lose."
    )

    def __init__(self, **overrides: object) -> None:
        super().__init__()
        self.params.update(
            {
                "top_opponent_value": 0.8,
                "road_win_bonus": 0.1,
                "p4_opponent_bonus": 0.1,
                **default_p4_params(),
            }
        )
        self.params.update(overrides)

    def rank(self, games: Sequence[Game]) -> Dict[str, float]:
        # Games against FCS (or other non-FBS) teams are dropped; unclassified games are kept.
        keep = ("fbs", "unknown")
        counted = [g for g in games if g.home_class in keep and g.away_class in keep]
        ratings = super().rank(counted)
        # A team whose only games were against non-FBS opponents still needs a rating.
        for g in games:
            ratings.setdefault(g.home, 0.0)
            ratings.setdefault(g.away, 0.0)
        return ratings

    def _opponent_scale(self) -> float:
        return self.params["top_opponent_value"]

    def _game_bonus(self, game: Game, team: str, won: bool) -> float:
        home = team == game.home
        opp, opp_conf = (game.away, game.away_conf) if home else (game.home, game.home_conf)
        bonus = 0.0
        if won and not home and not game.neutral:
            bonus += self.params["road_win_bonus"]
        if is_p4(self.params, opp, opp_conf):
            bonus += self.params["p4_opponent_bonus"]
        return bonus
