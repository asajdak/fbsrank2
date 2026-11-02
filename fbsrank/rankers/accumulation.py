from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence

from ..models import Game
from .base import Ranker
from .p4 import default_p4_params, is_p4


class WinAccumulationRanker(Ranker):
    id = "win_accumulation"
    name = "Win Accumulation"
    description = (
        "Each win earns points equal to the wins its victim has piled up: 2 for every Power 4 "
        "win the beaten team has, 1 for every other FBS win. Wins over FCS teams count for "
        "nothing, whether earned by the team or by its opponents. A team's score is the total."
    )

    def __init__(self, **overrides: object) -> None:
        self.params = {
            "p4_win_points": 2.0,
            "other_win_points": 1.0,
            **default_p4_params(),
        }
        self.params.update(overrides)

    def rank(self, games: Sequence[Game]) -> Dict[str, float]:
        p = self.params
        fbs: Dict[str, bool] = {}
        conf: Dict[str, str] = {}
        for g in games:
            fbs[g.home], fbs[g.away] = g.home_class == "fbs", g.away_class == "fbs"
            conf[g.home], conf[g.away] = g.home_conf, g.away_conf
        # With no classification data at all, treat everyone as FBS rather than score nothing.
        if not any(fbs.values()):
            fbs = {t: True for t in fbs}

        # Wins over FBS opponents only; ties are ignored.
        victims: Dict[str, List[str]] = defaultdict(list)
        for g in games:
            if g.home_points == g.away_points:
                continue
            winner, loser = (g.home, g.away) if g.home_points > g.away_points else (g.away, g.home)
            if fbs[loser]:
                victims[winner].append(loser)

        def value(win_over: str) -> float:
            return p["p4_win_points"] if is_p4(p, win_over, conf[win_over]) else p["other_win_points"]

        return {
            t: float(sum(value(v) for opp in victims[t] for v in victims[opp])) for t in fbs
        }
