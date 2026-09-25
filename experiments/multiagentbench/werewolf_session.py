"""Read Werewolf lines from session outcomes.

lines_for returns the text addressed to one player.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def lines_for(outcomes: Sequence[Any], player_id: str) -> str:
    """Return the game lines addressed to one player.

    Args:
        outcomes: Outcome records from a session.
        player_id: Player whose lines are required.

    Returns:
        The addressed contents, one per line.
    """
    lines = []
    for record in outcomes:
        payload = record.payload if hasattr(record, "payload") else record
        if not isinstance(payload, Mapping):
            continue
        observations = payload.get("observations") or {}
        for entry in observations.get("game_line") or []:
            recipients = entry.get("recipients") or []
            if player_id in recipients:
                lines.append(str(entry.get("content", "")))
    return "\n".join(lines)
