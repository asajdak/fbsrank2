from __future__ import annotations

import math
from typing import Dict, Sequence

from ..models import Game
from .base import Ranker


class EloRanker(Ranker):
    id = "elo"
    name = "Elo"
    description = (
        "Games are replayed in date order. Each result moves both teams' ratings toward "
        "the outcome, scaled by margin of victory and adjusted for home-field advantage."
    )

    def __init__(self, **overrides: float) -> None:
        self.params = {
            "k": 20.0,
            "home_advantage": 55.0,
            "initial_fbs": 1500.0,
            "initial_other": 1300.0,
            "margin_of_victory": True,
        }
        self.params.update(overrides)

    def _initial(self, classification: str) -> float:
        key = "initial_fbs" if classification == "fbs" else "initial_other"
        return self.params[key]

    def rank(self, games: Sequence[Game]) -> Dict[str, float]:
        p = self.params
        ratings: Dict[str, float] = {}
        for g in sorted(games, key=lambda g: (g.start_date, g.id)):
            r_home = ratings.setdefault(g.home, self._initial(g.home_class))
            r_away = ratings.setdefault(g.away, self._initial(g.away_class))

            diff = r_home + (0.0 if g.neutral else p["home_advantage"]) - r_away
            expected_home = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

            margin = g.home_points - g.away_points
            actual_home = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5

            multiplier = 1.0
            if p["margin_of_victory"] and margin != 0:
                # Damp blowouts by favorites so big favorites don't inflate.
                winner_diff = diff if margin > 0 else -diff
                multiplier = math.log(abs(margin) + 1) * 2.2 / max(winner_diff * 0.001 + 2.2, 0.1)

            delta = p["k"] * multiplier * (actual_home - expected_home)
            ratings[g.home] = r_home + delta
            ratings[g.away] = r_away - delta
        return ratings
