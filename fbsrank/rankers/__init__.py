"""Registry of ranking algorithms.

To add one: create a module here that subclasses `Ranker`, then add an
instance to `ALL` below.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import Ranker
from .colley import ColleyRanker
from .elo import EloRanker

ALL: List[Ranker] = [EloRanker(), ColleyRanker()]


def select(ids: Optional[List[str]] = None) -> List[Ranker]:
    """All rankers, or only those whose id is in `ids`."""
    by_id: Dict[str, Ranker] = {r.id: r for r in ALL}
    if not ids:
        return list(ALL)
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise SystemExit(f"Unknown ranker(s): {', '.join(unknown)}. Available: {', '.join(by_id)}")
    return [by_id[i] for i in ids]
