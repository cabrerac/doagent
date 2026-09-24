"""Copy Werewolf game state into a truth phase.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def night_phase(shared_memory: Mapping[str, Any]) -> dict[str, Any]:
    """Return the truth phase for the night that just finished.

    Args:
        shared_memory: The environment state after the night phase.

    Returns:
        A phase with one fact per completed night action.
    """
    private = shared_memory["private_state"]
    players = private["players"]
    night_number = shared_memory["public_state"]["days"]
    night_log = private["night_cache"][-1] if private.get("night_cache") else {}
    facts = []
    guard_target = night_log.get("guard_action")
    guard = _role_id(players, "guard")
    if guard_target and guard:
        facts.append(
            {
                "name": f"{guard_target} is protected this night.",
                "holders": [guard],
            }
        )
    wolf_target = (night_log.get("werewolf_action") or {}).get("final_target")
    wolves = _alive(players, "wolf")
    if wolf_target and wolves:
        facts.append(
            {
                "name": f"Final Target: {wolf_target}",
                "holders": wolves,
            }
        )
    seer = _role_id(players, "seer")
    if seer:
        check = players[seer]["status"].get("check_history", {}).get(
            f"Night {night_number}"
        )
        if check:
            target = check["player"]
            facts.append(
                {
                    "name": f"You have checked {target}",
                    "holders": [seer],
                }
            )
    witch = _role_id(players, "witch")
    witch_action = night_log.get("witch_action") or {}
    action = witch_action.get("action")
    target = witch_action.get("target")
    if witch and action == "antidote" and target:
        facts.append(
            {
                "name": f"Witch used antidote to save {target}.",
                "holders": [witch],
            }
        )
    if witch and action == "poison" and target:
        facts.append(
            {
                "name": f"Witch used poison on {target}.",
                "holders": [witch],
            }
        )
    return {
        "phase": f"night-{night_number}",
        "population_size": len(players),
        "facts": facts,
    }


def day_phase(shared_memory: Mapping[str, Any]) -> dict[str, Any]:
    """Return the truth phase for the day that just finished.

    Args:
        shared_memory: The environment state after the day phase.

    Returns:
        A phase whose votes are the banishment choices.
        The votes key is omitted when nobody voted.
    """
    public = shared_memory["public_state"]
    day_number = public["days"]
    cache = public["day_cache"][-1] if public.get("day_cache") else {}
    votes = cache.get("banishment_votes") or {}
    phase: dict[str, Any] = {
        "phase": f"day-{day_number}",
        "population_size": len(shared_memory["private_state"]["players"]),
        "facts": [],
    }
    if votes:
        phase["votes"] = dict(votes)
    return phase


def _role_id(players: Mapping[str, Any], role: str) -> Optional[str]:
    for name, info in players.items():
        if info.get("role") == role:
            return name
    return None


def _alive(players: Mapping[str, Any], role: str) -> list[str]:
    names = []
    for name, info in players.items():
        health = info.get("status", {}).get("health", 0)
        if info.get("role") == role and health == 1:
            names.append(name)
    return names
