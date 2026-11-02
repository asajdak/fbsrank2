from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from ..models import Game
from .base import Ranker


class ClassicRanker(Ranker):
    id = "classic"
    name = "FBS Rank Classic"
    description = (
        "Iterative. Teams start sorted by record. Each team then scores 1 point per win plus up "
        "to 1 point per opponent for how highly that opponent ranked in the previous pass "
        "(full credit for #1, falling linearly to nothing at #69), divided by games played. "
        "Teams are re-sorted by that score and the process repeats until the order stops "
        "changing. If the order enters a cycle, the pass where the holder of the best win "
        "ranks highest is used."
    )

    def __init__(self, **overrides: float) -> None:
        self.params = {"cutoff_rank": 69, "max_iterations": 1000}
        self.params.update(overrides)

    def rank(self, games: Sequence[Game]) -> Dict[str, float]:
        if not games:
            return {}

        teams = sorted({t for g in games for t in (g.home, g.away)})
        classes = {}
        for g in games:
            classes[g.home], classes[g.away] = g.home_class, g.away_class
        # Same population the runner publishes: FBS teams, or everyone if none are classified.
        ranked = [t for t in teams if classes[t] == "fbs"] or teams

        wins: Dict[str, float] = defaultdict(float)
        played: Dict[str, int] = defaultdict(int)
        beat: Dict[str, List[str]] = defaultdict(list)  # team -> opponents it defeated
        opponents: Dict[str, List[str]] = defaultdict(list)
        for g in games:
            opponents[g.home].append(g.away)
            opponents[g.away].append(g.home)
            played[g.home] += 1
            played[g.away] += 1
            if g.home_points > g.away_points:
                wins[g.home] += 1
                beat[g.home].append(g.away)
            elif g.away_points > g.home_points:
                wins[g.away] += 1
                beat[g.away].append(g.home)
            else:
                wins[g.home] += 0.5
                wins[g.away] += 0.5

        def order_of(scores: Dict[str, float]) -> Tuple[str, ...]:
            return tuple(sorted(ranked, key=lambda t: (-scores[t], t)))

        # Pass 0: sort by record.
        scores = {t: wins[t] / played[t] for t in teams}
        # Break record ties by number of wins, then name.
        order = tuple(sorted(ranked, key=lambda t: (-scores[t], -wins[t], t)))
        history: List[Tuple[Tuple[str, ...], Dict[str, float]]] = [(order, scores)]
        seen = {order: 0}

        cutoff = self.params["cutoff_rank"]
        for _ in range(self.params["max_iterations"]):
            position = {t: i for i, t in enumerate(order, start=1)}

            def difficulty(opp: str) -> float:
                pos = position.get(opp)
                return 0.0 if pos is None else max(0.0, (cutoff - pos) / (cutoff - 1))

            scores = {
                t: (wins[t] + sum(difficulty(o) for o in opponents[t])) / played[t] for t in teams
            }
            new_order = order_of(scores)
            if new_order == order:
                return scores
            if new_order in seen:
                start = seen[new_order]
                history.append((new_order, scores))
                return self._pick_from_cycle(history[start:-1], beat)
            seen[new_order] = len(history)
            history.append((new_order, scores))
            order = new_order
        return history[-1][1]

    @staticmethod
    def _pick_from_cycle(
        cycle: List[Tuple[Tuple[str, ...], Dict[str, float]]],
        beat: Dict[str, List[str]],
    ) -> Dict[str, float]:
        """Pick the ordering in which the team owning the best win is placed highest.

        Within each ordering, the best win is the victory over the highest-ranked opponent;
        if several teams share it, the one ranked highest counts. Ties between orderings go
        to the earliest pass.
        """

        def best_win_holder_position(order: Tuple[str, ...]) -> int:
            position = {t: i for i, t in enumerate(order)}
            best = (len(order), len(order))  # (opponent position, holder position)
            for team in order:
                for opp in beat.get(team, ()):
                    if opp in position:
                        best = min(best, (position[opp], position[team]))
            return best[1]

        chosen = min(range(len(cycle)), key=lambda i: (best_win_holder_position(cycle[i][0]), i))
        return cycle[chosen][1]
