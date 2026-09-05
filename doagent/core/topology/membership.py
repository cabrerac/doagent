"""Join/leave updates to the peer-to-peer visibility map.

The topology ``visibility`` dict is the graph for agents named in it (as a
key or as a peer). After join/leave, Session asks a membership hook for the
new map.

Default: agents listed in that graph keep (or restore) those links. Only an
agent *not* named there is linked both ways to everyone currently in.
Leave drops the agent from every list.

Users may pass another callable as ``topology.on_membership_change``.
Pass ``mesh_on_membership_change`` to mesh every join, including listed agents.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Protocol, Sequence


class MembershipMapHook(Protocol):
    """Callable that returns a new peer-to-peer visibility map after join/leave."""

    def __call__(
        self,
        event: str,
        agent_id: str,
        members: Sequence[str],
        visibility: Mapping[str, Sequence[str]],
    ) -> Dict[str, List[str]]:
        """Return the updated map.

        Args:
            event: ``"join"`` or ``"leave"``.
            agent_id: Who joined or left.
            members: Registry members *after* the change.
            visibility: Current map (do not mutate; copy if you edit).
        """
        ...


def copy_visibility(visibility: Mapping[str, Sequence[str]]) -> Dict[str, List[str]]:
    """Return a mutable copy of a visibility map."""
    return {key: list(peers) for key, peers in visibility.items()}


def named_in_topology(
    agent_id: str,
    seed: Mapping[str, Sequence[str]],
) -> bool:
    """True if *agent_id* appears as a key or a peer in the starting map."""
    if agent_id in seed:
        return True
    return any(agent_id in peers for peers in seed.values())


def _drop_agent(vis: Dict[str, List[str]], agent_id: str) -> Dict[str, List[str]]:
    vis.pop(agent_id, None)
    for key, peers in vis.items():
        vis[key] = [peer for peer in peers if peer != agent_id]
    return vis


def _restore_seed_agent(
    vis: Dict[str, List[str]],
    agent_id: str,
    seed: Mapping[str, Sequence[str]],
) -> Dict[str, List[str]]:
    vis[agent_id] = list(seed.get(agent_id, []))
    for key, peers in seed.items():
        if agent_id not in peers:
            continue
        current = list(vis.get(key, []))
        if agent_id not in current:
            current.append(agent_id)
        vis[key] = current
    return vis


def mesh_on_membership_change(
    event: str,
    agent_id: str,
    members: Sequence[str],
    visibility: Mapping[str, Sequence[str]],
) -> Dict[str, List[str]]:
    """Mesh every join with everyone currently in. Leave drops the agent.

    Use as ``on_membership_change`` when you want a live full mesh, including
    agents already listed in the topology file.
    """
    vis = copy_visibility(visibility)
    if event == "leave":
        return _drop_agent(vis, agent_id)
    if event == "join":
        others = [member for member in members if member != agent_id]
        existing = vis.get(agent_id, [])
        vis[agent_id] = list(dict.fromkeys([*existing, *others]))
        for other in others:
            peers = list(vis.get(other, []))
            if agent_id not in peers:
                peers.append(agent_id)
            vis[other] = peers
        return vis
    return vis


def make_default_membership_hook(
    seed_visibility: Mapping[str, Sequence[str]],
) -> Callable[..., Dict[str, List[str]]]:
    """Default P2P hook: YAML/graph for named agents. Mesh only strangers."""
    seed = copy_visibility(seed_visibility)

    def hook(
        event: str,
        agent_id: str,
        members: Sequence[str],
        visibility: Mapping[str, Sequence[str]],
    ) -> Dict[str, List[str]]:
        vis = copy_visibility(visibility)
        if event == "leave":
            return _drop_agent(vis, agent_id)
        if event == "join":
            if named_in_topology(agent_id, seed):
                return _restore_seed_agent(vis, agent_id, seed)
            return mesh_on_membership_change("join", agent_id, members, vis)
        return vis

    return hook
