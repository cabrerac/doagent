"""Decide whether a Werewolf night ended the game.

The check uses health.
The published alive list can still name players who died this night.
"""

from __future__ import annotations

from typing import Mapping


def night_side_wiped(health: Mapping[str, int], roles: Mapping[str, str]) -> bool:
    """Return True when every wolf is dead or every non-wolf is dead.

    Args:
        health: Health of each player.
            A value of 1 means the player is alive.
        roles: Role of each player.

    Returns:
        True when one side has no living player.
    """
    living = [player_id for player_id, points in health.items() if points == 1]
    wolves = [player_id for player_id in living if roles.get(player_id) == "wolf"]
    others = [player_id for player_id in living if roles.get(player_id) != "wolf"]
    return not wolves or not others
