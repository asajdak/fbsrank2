from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

from ..models import Game
from .base import Ranker


class ColleyRanker(Ranker):
    id = "colley"
    name = "Colley Matrix"
    description = (
        "Solves one linear system using only wins, losses, and strength of schedule. "
        "Margin of victory and home field are ignored, so there is nothing to run up. "
        "Ties are ignored."
    )

    def __init__(self) -> None:
        self.params = {}

    def rank(self, games: Sequence[Game]) -> Dict[str, float]:
        teams = sorted({t for g in games for t in (g.home, g.away)})
        index = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        if n == 0:
            return {}

        # Colley: C r = b, with C = 2I + diag(games played) - opponent counts,
        # and b = 1 + (wins - losses) / 2.
        c = 2.0 * np.eye(n)
        b = np.ones(n)
        for g in games:
            if g.home_points == g.away_points:
                continue
            i, j = index[g.home], index[g.away]
            winner, loser = (i, j) if g.home_points > g.away_points else (j, i)
            c[i, i] += 1
            c[j, j] += 1
            c[i, j] -= 1
            c[j, i] -= 1
            b[winner] += 0.5
            b[loser] -= 0.5

        r = np.linalg.solve(c, b)
        return {t: float(r[i]) for t, i in index.items()}
