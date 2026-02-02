"""Internal interface definitions for the DOAgent library."""

from .agent_adapter import AgentAdapter
from .shared_data import SharedDataAdapter
from ..records import SimpleRecord

__all__ = [
    "AgentAdapter",
    "SharedDataAdapter",
    "SimpleRecord",
]
