"""Coordination hooks based on topology."""

from __future__ import annotations

from dataclasses import dataclass

from .config import TopologyConfig
from .model import Topology


@dataclass(frozen=True)
class RoutingDecision:
    """Routing decision derived from topology."""

    mode: Topology
    description: str


def select_routing(config: TopologyConfig) -> RoutingDecision:
    """Return a routing decision based on topology configuration."""
    if config.mode == Topology.CENTRALISED:
        return RoutingDecision(
            mode=config.mode,
            description="Route all coordination through a central controller.",
        )
    if config.mode == Topology.FEDERATED:
        return RoutingDecision(
            mode=config.mode,
            description="Route coordination within federated controllers.",
        )
    return RoutingDecision(
        mode=config.mode,
        description="Route coordination directly peer-to-peer.",
    )
