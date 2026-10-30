"""Regenerate tests/fixtures/games/2000.json, a synthetic season with fictional teams.

    python tests/make_fixture.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 2000
FBS = {
    "East": ["Albion State", "Bristol Tech", "Calder", "Dunmore", "Eastvale", "Fairmont", "Garrick", "Halloran"],
    "West": ["Ironwood", "Juniper", "Kestrel", "Lakeshore", "Marlow", "Northgate", "Oakridge", "Pinecrest"],
}
FCS = ["Quarry College", "Redfield"]


def main() -> None:
    rng = random.Random(SEED)
    teams = {t: (conf, "fbs") for conf, ts in FBS.items() for t in ts}
    teams.update({t: ("", "fcs") for t in FCS})
    strength = {t: rng.gauss(0, 8) for t in teams}

    games = []

    def play(week: int, season_type: str, home: str, away: str, neutral: bool = False) -> None:
        margin = strength[home] - strength[away] + (0 if neutral else 2.5)
        base = rng.randint(20, 30)
        hp = max(0, round(base + margin / 2 + rng.gauss(0, 7)))
        ap = max(0, round(base - margin / 2 + rng.gauss(0, 7)))
        if hp == ap:
            hp += 3
        games.append({
            "id": 1000 + len(games), "season": 2000, "week": week, "season_type": season_type,
            "start_date": f"2000-{8 + (week - 1) // 4:02d}-{1 + (week - 1) % 4 * 7 + (0 if season_type == 'regular' else 3):02d}T19:00:00.000Z",
            "home": home, "away": away, "home_points": hp, "away_points": ap, "neutral": neutral,
            "home_class": teams[home][1], "away_class": teams[away][1],
            "home_conf": teams[home][0], "away_conf": teams[away][0],
        })

    fbs = [t for t in teams if teams[t][1] == "fbs"]
    for week in range(1, 9):
        order = fbs[:]
        rng.shuffle(order)
        for i in range(0, len(order), 2):
            play(week, "regular", order[i], order[i + 1])
        if week in (1, 2):
            play(week, "regular", rng.choice(fbs), FCS[week - 1])
    top = sorted(fbs, key=lambda t: -strength[t])[:2]
    play(9, "postseason", top[0], top[1], neutral=True)

    out = Path(__file__).parent / "fixtures" / "games" / "2000.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"season": 2000, "games": games}, indent=1) + "\n")
    print(f"wrote {out} ({len(games)} games)")


if __name__ == "__main__":
    main()
