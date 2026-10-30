from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Sequence

from ..models import Game


class Ranker(ABC):
    """A ranking algorithm.

    `rank` must be a pure function of the games it is given: no file access,
    no knowledge of weeks, no output formatting. The runner hands it every game
    played through some week and handles sorting, numbering, and output.
    """

    id: str
    name: str
    description: str
    params: Dict[str, Any]

    @abstractmethod
    def rank(self, games: Sequence[Game]) -> Dict[str, float]:
        """Return a rating per team (higher is better) for every team in `games`."""
