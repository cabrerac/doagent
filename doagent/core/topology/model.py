"""Topology model for coordination modes."""

from enum import Enum


class Topology(str, Enum):
    """Coordination topology modes."""

    CENTRALISED = "centralised"
    FEDERATED = "federated"
    PEER_TO_PEER = "peer_to_peer"
