from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fbsrank import runner
from fbsrank.models import Game
from fbsrank.normalize import normalize_game, normalize_season
from fbsrank.rankers.colley import ColleyRanker
from fbsrank.rankers.elo import EloRanker

FIXTURES = Path(__file__).parent / "fixtures" / "games"


def game(home, away, hp, ap, week=1, neutral=False, gid=1, cls="fbs", season_type="regular"):
    return Game(
        id=gid, season=2000, week=week, season_type=season_type, start_date=f"2000-09-{week:02d}",
        home=home, away=away, home_points=hp, away_points=ap, neutral=neutral,
        home_class=cls, away_class=cls, home_conf="", away_conf="",
    )


def raw(gid, week, season_type="regular", completed=True, hp=21, ap=14):
    return {
        "id": gid, "season": 2024, "week": week, "seasonType": season_type,
        "startDate": f"2024-09-{week:02d}T00:00:00.000Z", "completed": completed,
        "neutralSite": False, "homeTeam": "A", "awayTeam": "B", "homePoints": hp, "awayPoints": ap,
        "homeClassification": "fbs", "awayClassification": "FCS",
        "homeConference": "X", "awayConference": None,
    }


class ColleyTests(unittest.TestCase):
    def test_single_game_known_solution(self):
        ratings = ColleyRanker().rank([game("A", "B", 10, 3)])
        self.assertAlmostEqual(ratings["A"], 0.625)
        self.assertAlmostEqual(ratings["B"], 0.375)

    def test_ratings_average_one_half(self):
        games = [game("A", "B", 10, 3, gid=1), game("B", "C", 7, 0, gid=2), game("C", "A", 3, 20, gid=3)]
        ratings = ColleyRanker().rank(games)
        self.assertAlmostEqual(sum(ratings.values()) / 3, 0.5)

    def test_empty(self):
        self.assertEqual(ColleyRanker().rank([]), {})


class EloTests(unittest.TestCase):
    def test_winner_gains_loser_loses_zero_sum(self):
        ratings = EloRanker().rank([game("A", "B", 28, 7)])
        self.assertGreater(ratings["A"], 1500)
        self.assertLess(ratings["B"], 1500)
        self.assertAlmostEqual(ratings["A"] + ratings["B"], 3000)

    def test_home_advantage_discounts_home_win_but_not_neutral(self):
        home = EloRanker().rank([game("A", "B", 20, 10)])
        neutral = EloRanker().rank([game("A", "B", 20, 10, neutral=True)])
        self.assertLess(home["A"], neutral["A"])

    def test_tie_between_equal_neutral_teams_changes_nothing(self):
        ratings = EloRanker().rank([game("A", "B", 17, 17, neutral=True)])
        self.assertAlmostEqual(ratings["A"], 1500)

    def test_param_override(self):
        self.assertEqual(EloRanker(k=40).params["k"], 40)


class NormalizeTests(unittest.TestCase):
    def test_drops_incomplete_and_unscored(self):
        self.assertIsNone(normalize_game(raw(1, 1, completed=False)))
        self.assertIsNone(normalize_game({**raw(1, 1), "homePoints": None}))

    def test_fields_and_classification(self):
        g = normalize_game(raw(1, 1))
        self.assertEqual((g.home_class, g.away_class), ("fbs", "fcs"))
        self.assertEqual(g.away_conf, "")

    def test_postseason_weeks_continue_after_regular_season(self):
        games = normalize_season([raw(1, 1), raw(2, 14), raw(3, 1, "postseason"), raw(4, 2, "postseason")])
        self.assertEqual([g.week for g in games], [1, 14, 15, 16])


class RunnerTests(unittest.TestCase):
    def test_fixture_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            runner.run(FIXTURES, out)
            index = json.loads((out / "index.json").read_text())
            self.assertEqual({r["id"] for r in index["rankers"]}, {"elo", "colley"})
            weeks = index["seasons"][0]["weeks"]
            self.assertEqual(weeks[-1]["label"], "Postseason")

            for ranker_id in ("elo", "colley"):
                final = json.loads((out / ranker_id / "2000" / f"week-{weeks[-1]['week']}.json").read_text())
                teams = [r["team"] for r in final["rankings"]]
                self.assertEqual(len(teams), 16)  # FCS teams are rated but not published
                self.assertNotIn("Quarry College", teams)
                self.assertEqual([r["rank"] for r in final["rankings"]], list(range(1, 17)))

    def test_output_is_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            runner.run(FIXTURES, Path(a))
            runner.run(FIXTURES, Path(b))
            for path in Path(a).rglob("*.json"):
                self.assertEqual(path.read_text(), (Path(b) / path.relative_to(a)).read_text())

    def test_unclassified_games_publish_everyone(self):
        games = [game("A", "B", 10, 3, cls="unknown")]
        self.assertEqual(len(runner.build_rankings(EloRanker(), games)), 2)


if __name__ == "__main__":
    unittest.main()
