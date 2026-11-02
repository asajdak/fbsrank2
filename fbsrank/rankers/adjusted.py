from __future__ import annotations

from ..models import Game
from .classic import ClassicRanker


class AdjustedClassicRanker(ClassicRanker):
    id = "classic_adjusted"
    name = "FBS Rank Classic (Adjusted)"
    description = (
        "FBS Rank Classic with three adjustable credits: the #1 opponent is worth 0.8 instead "
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
                "p4_conferences": ["SEC", "Big Ten", "Big 12", "ACC"],
            }
        )
        self.params.update(overrides)

    def _opponent_scale(self) -> float:
        return self.params["top_opponent_value"]

    def _game_bonus(self, game: Game, team: str, won: bool) -> float:
        home = team == game.home
        opp_conf = game.away_conf if home else game.home_conf
        bonus = 0.0
        if won and not home and not game.neutral:
            bonus += self.params["road_win_bonus"]
        if opp_conf in self.params["p4_conferences"]:
            bonus += self.params["p4_opponent_bonus"]
        return bonus
