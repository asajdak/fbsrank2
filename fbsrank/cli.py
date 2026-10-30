from __future__ import annotations

import argparse
import datetime
from pathlib import Path
from typing import List, Optional

from . import ingest, normalize, runner

ROOT = Path(__file__).resolve().parent.parent


def current_season() -> int:
    today = datetime.date.today()
    return today.year if today.month >= 8 else today.year - 1


def cmd_ingest(args: argparse.Namespace) -> None:
    key = ingest.api_key_from_env()
    for season in args.season or [current_season()]:
        path = ingest.ingest_season(season, args.raw_dir, key)
        print(f"ingested {path}")


def cmd_normalize(args: argparse.Namespace) -> None:
    seasons = args.season or [current_season()]
    for season in seasons:
        raw = args.raw_dir / f"{season}.json"
        print(f"wrote {normalize.normalize_file(raw, args.games_dir)}")


def cmd_rank(args: argparse.Namespace) -> None:
    runner.run(args.games_dir, args.out_dir, args.ranker, args.season)
    print(f"wrote rankings to {args.out_dir}")


def cmd_update(args: argparse.Namespace) -> None:
    cmd_ingest(args)
    cmd_normalize(args)
    args.season = None  # rank every season on disk, not only the one just fetched
    cmd_rank(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fbsrank")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--games-dir", type=Path, default=ROOT / "data" / "games")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "site" / "data")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, fn, help: str, seasons: bool = True, rankers: bool = False):
        p = sub.add_parser(name, help=help)
        if seasons:
            p.add_argument("--season", type=int, action="append", help="repeatable; default: current season")
        if rankers:
            p.add_argument("--ranker", action="append", help="repeatable; default: all")
        p.set_defaults(fn=fn)

    add("ingest", cmd_ingest, "download raw games from CFBD (needs CFBD_API_KEY)")
    add("normalize", cmd_normalize, "convert raw games to data/games/")
    add("rank", cmd_rank, "run rankers and write site/data/", rankers=True)
    add("update", cmd_update, "ingest + normalize + rank", rankers=True)
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    args.fn(args)
