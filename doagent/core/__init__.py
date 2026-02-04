"""Core implementation of DOAgent."""

from .agent_adapter import StubAgent
from .function_agent import FunctionAgent
from .file_shared_data import FileSharedData
from .participation import (
    InMemoryParticipationRegistry,
    ParticipationRecord,
    ParticipationRegistry,
)
from .shared_data import (
    InMemorySharedData,
    new_explanation_record,
    new_record,
    new_trace_record,
)
from .topology import RoutingDecision, Topology, TopologyConfig, select_routing

__all__ = [
    "StubAgent",
    "FunctionAgent",
    "InMemorySharedData",
    "FileSharedData",
    "new_record",
    "new_explanation_record",
    "new_trace_record",
    "Topology",
    "TopologyConfig",
    "RoutingDecision",
    "select_routing",
    "ParticipationRecord",
    "ParticipationRegistry",
    "InMemoryParticipationRegistry",
]
