"""How the federated hub tells leaves who is in.

Leaves only see records whose author is the hub, so after join/leave the hub
must write something they can read. Session asks this hook; the default is a
roster snapshot. Pass another callable as ``topology.on_hub_membership``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Protocol, Sequence


class HubMembershipHook(Protocol):
    """Callable that returns extra participation writes after join/leave."""

    def __call__(
        self,
        event: str,
        agent_id: str,
        members: Sequence[Mapping[str, Any]],
        hub_id: str,
    ) -> Sequence[Mapping[str, Any]]:
        """Return writes. Each item is passed to the participation writer.

        Keys: ``event`` (required); optional ``actor`` (default hub),
        ``members``, ``member_id``, ``capabilities``, ``resource_limits``,
        ``metadata``. Return an empty list to write nothing extra.
        """
        ...


def snapshot_hub_roster(
    event: str,
    agent_id: str,
    members: Sequence[Mapping[str, Any]],
    hub_id: str,
) -> List[Dict[str, Any]]:
    """Default: one hub-authored snapshot of everyone currently in."""
    return [{
        "event": "roster",
        "actor": hub_id,
        "members": [dict(m) for m in members],
    }]


def relay_join_leave_as_hub(
    event: str,
    agent_id: str,
    members: Sequence[Mapping[str, Any]],
    hub_id: str,
) -> List[Dict[str, Any]]:
    """Re-emit the join/leave as a hub-authored record (leaves can see it)."""
    info: Mapping[str, Any] = {}
    for member in members:
        if member.get("agent_id") == agent_id:
            info = member
            break
    write: Dict[str, Any] = {
        "event": event,
        "actor": hub_id,
        "member_id": agent_id,
        "capabilities": list(info.get("capabilities") or []),
        "resource_limits": dict(info.get("resource_limits") or {}),
    }
    if info.get("metadata"):
        write["metadata"] = dict(info["metadata"])
    return [write]
