from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fbsrank import runner
from fbsrank.models import Game
from fbsrank.normalize import normalize_game, normalize_season
from fbsrank.rankers.accumulation import WinAccumulationRanker
from fbsrank.rankers.adjusted import AdjustedClassicRanker
from fbsrank.rankers.classic import ClassicRanker
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


class ClassicTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(ClassicRanker().rank([]), {})

    def test_single_game(self):
        r = ClassicRanker().rank([game("A", "B", 10, 3)])
        self.assertGreater(r["A"], r["B"])

    def test_quality_win_beats_padding(self):
        # A and B are both 1-0 with the same record, but B's win came against the
        # team that beat C in turn; D has only beaten the winless E.
        games = [
            game("X", "C", 10, 0, gid=1),
            game("B", "X", 10, 0, week=2, gid=2),
            game("D", "E", 10, 0, gid=3),
        ]
        r = ClassicRanker().rank(games)
        self.assertGreater(r["B"], r["D"])

    def test_cycle_terminates(self):
        # Three-way round robin is a cycle of equal records.
        games = [
            game("A", "B", 7, 0, gid=1), game("B", "C", 7, 0, gid=2), game("C", "A", 7, 0, gid=3),
        ]
        r = ClassicRanker().rank(games)
        self.assertEqual(set(r), {"A", "B", "C"})

    def test_fcs_opponents_give_no_difficulty_credit(self):
        g = Game(1, 2000, 1, "regular", "2000-09-01", "A", "Q", 10, 0, False, "fbs", "fcs", "", "")
        self.assertAlmostEqual(ClassicRanker().rank([g])["A"], 1.0)


class AdjustedClassicTests(unittest.TestCase):
    def _g(self, **kw):
        base = dict(id=1, season=2000, week=1, season_type="regular", start_date="2000-09-01",
                    home="H", away="V", home_points=0, away_points=10, neutral=False,
                    home_class="fbs", away_class="fbs", home_conf="MAC", away_conf="MAC")
        base.update(kw)
        return Game(**base)

    def _ranker(self, **kw):
        return AdjustedClassicRanker(**{"road_win_bonus": 0.0, "p4_opponent_bonus": 0.0, **kw})

    def test_top_opponent_scaled(self):
        # V (road winner) ranks #1, H #2: H gets 0.8 for playing #1, V gets 0.8 * 67/68.
        ratings = self._ranker().rank([self._g()])
        self.assertAlmostEqual(ratings["H"], 0.8)
        self.assertAlmostEqual(ratings["V"], 1 + 0.8 * 67 / 68)

    def test_fcs_games_are_ignored(self):
        fcs = self._g(id=2, week=2, away="Q", away_class="fcs", home="V", home_points=0, away_points=30)
        r = self._ranker()
        alone = r.rank([self._g()])
        both = r.rank([self._g(), fcs])
        self.assertAlmostEqual(both["V"], alone["V"])
        self.assertEqual(both["Q"], 0.0)

    def test_team_with_only_fcs_games_still_rated(self):
        g = self._g(away="Q", away_class="fcs")
        self.assertEqual(self._ranker().rank([g]), {"H": 0.0, "Q": 0.0})

    def test_road_win_bonus(self):
        r = self._ranker(road_win_bonus=0.3)
        base = 1 + 0.8 * 67 / 68
        self.assertAlmostEqual(r.rank([self._g()])["V"], base + 0.3)
        self.assertAlmostEqual(r.rank([self._g(neutral=True)])["V"], base)
        self.assertAlmostEqual(r.rank([self._g(home_points=10, away_points=0)])["H"], 1 + 0.8 * 67 / 68)

    def test_p4_bonus_applies_regardless_of_result(self):
        r = self._ranker(p4_opponent_bonus=0.2)
        ratings = r.rank([self._g(home_conf="SEC")])  # V visits an SEC team and wins
        self.assertAlmostEqual(ratings["V"], 1 + 0.8 * 67 / 68 + 0.2)
        self.assertAlmostEqual(ratings["H"], 0.8)  # H's opponent is a MAC team: no bonus
        lost = r.rank([self._g(away_conf="SEC")])  # H hosts an SEC team and loses
        self.assertAlmostEqual(lost["H"], 0.8 + 0.2)


class WinAccumulationTests(unittest.TestCase):
    def _g(self, gid, winner, loser, wconf="MAC", lconf="MAC", lclass="fbs", home=True, wclass="fbs"):
        h, a = (winner, loser) if home else (loser, winner)
        hc, ac = (wconf, lconf) if home else (lconf, wconf)
        hcl, acl = (wclass, lclass) if home else (lclass, wclass)
        hp, ap = (10, 0) if home else (0, 10)
        return Game(gid, 2000, gid, "regular", f"2000-09-{gid:02d}", h, a, hp, ap, False, hcl, acl, hc, ac)

    def test_documented_example(self):
        # Me beat O; O beat two P4 teams, a G6 team and an FCS team (and lost to others).
        games = [
            self._g(1, "Me", "O"),
            self._g(2, "O", "P1", lconf="SEC"),
            self._g(3, "O", "P2", lconf="Big Ten"),
            self._g(4, "O", "G1", lconf="Sun Belt"),
            self._g(5, "O", "F1", lclass="fcs"),
        ]
        self.assertEqual(WinAccumulationRanker().rank(games)["Me"], 5.0)

    def test_notre_dame_counts_as_p4_but_other_independents_do_not(self):
        for team, expected in (("Notre Dame", 2.0), ("Army", 1.0), ("UConn", 1.0)):
            games = [self._g(1, "Me", "O"), self._g(2, "O", team, lconf="FBS Independents")]
            self.assertEqual(WinAccumulationRanker().rank(games)["Me"], expected)

    def test_fcs_victim_gives_nothing(self):
        games = [self._g(1, "Me", "F1", lclass="fcs"), self._g(2, "F1", "X", wclass="fcs")]
        self.assertEqual(WinAccumulationRanker().rank(games)["Me"], 0.0)


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
            self.assertEqual({r["id"] for r in index["rankers"]}, {"elo", "colley", "classic", "classic_adjusted", "win_accumulation"})
            weeks = index["seasons"][0]["weeks"]
            self.assertEqual(weeks[-1]["label"], "Postseason")

            for ranker_id in ("elo", "colley", "classic", "classic_adjusted", "win_accumulation"):
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
