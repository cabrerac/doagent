"""Read Werewolf lines from records a player is allowed to see.

lines_for returns the text addressed to one player.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def lines_for(outcomes: Sequence[Any], player_id: str) -> str:
    """Return the game lines addressed to one player.

    Args:
        outcomes: Outcome or observation records the player may read.
        player_id: Player whose lines are required.

    Returns:
        The addressed contents, one per line.
    """
    lines = []
    for record in outcomes:
        payload = record.payload if hasattr(record, "payload") else record
        if not isinstance(payload, Mapping):
            continue
        candidates = []
        observation = payload.get("observation")
        if isinstance(observation, Mapping):
            candidates.extend(observation.get("received_lines") or [])
            candidates.extend(observation.get("game_line") or [])
        observations = payload.get("observations") or {}
        if isinstance(observations, Mapping):
            candidates.extend(observations.get("game_line") or [])
        for entry in candidates:
            if not isinstance(entry, Mapping):
                continue
            recipients = entry.get("recipients") or []
            if player_id in recipients:
                lines.append(str(entry.get("content", "")))
    return "\n".join(lines)
