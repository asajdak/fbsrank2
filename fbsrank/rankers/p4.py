from __future__ import annotations

from typing import Any, Dict


def default_p4_params() -> Dict[str, Any]:
    """Power 4 membership: whole conferences, plus independents that count as P4 by name."""
    return {
        "p4_conferences": ["SEC", "Big Ten", "Big 12", "ACC"],
        "p4_teams": ["Notre Dame"],
    }


def is_p4(params: Dict[str, Any], team: str, conference: str) -> bool:
    return conference in params["p4_conferences"] or team in params["p4_teams"]
