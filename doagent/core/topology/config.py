"""Configuration for topology selection."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Topology


@dataclass(frozen=True)
class TopologyConfig:
    """Configuration for coordination topology."""

    mode: Topology = Topology.CENTRALISED
