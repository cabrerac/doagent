"""Core implementation of DOAgent."""

from .agent_adapter import StubAgent
from .function_agent import FunctionAgent
from .file_shared_data import FileSharedData

try:
    from .mongo_shared_data import MongoSharedData
except ImportError:
    MongoSharedData = None  # type: ignore[assignment,misc]
from .participation import (
    InMemoryParticipationRegistry,
    ParticipationRecord,
    ParticipationRegistry,
)
from .shared_data import (
    InMemorySharedData,
    new_agent_update_record,
    new_explanation_record,
    new_record,
    new_trace_record,
)
from .record_writer import RecordWriter, StateHashFn, default_state_hash
from .run_config import (
    DEFAULT_LOGGING_LEVEL,
    RunConfig,
    should_include_explanation,
    should_include_provenance_accountability,
    should_write_trace,
)
from .session import Session, SessionAgent, WrappedEnv
from .topology import RoutingDecision, Topology, TopologyConfig, select_routing

__all__ = [
    "StubAgent",
    "FunctionAgent",
    "InMemorySharedData",
    "FileSharedData",
    "MongoSharedData",
    "new_agent_update_record",
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
    "RecordWriter",
    "StateHashFn",
    "default_state_hash",
    "RunConfig",
    "DEFAULT_LOGGING_LEVEL",
    "should_include_explanation",
    "should_include_provenance_accountability",
    "should_write_trace",
    "Session",
    "SessionAgent",
    "WrappedEnv",
]
