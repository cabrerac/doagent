"""Simple push experiment agent configuration types."""

from __future__ import annotations

from typing import Any, Dict, TypedDict


class AgentMetadata(TypedDict, total=False):
    """Optional metadata for agent config. Session injects into policy responses."""

    explanation: str


class PushAgentConfig(TypedDict):
    """Configuration for a simple push experiment agent."""

    id: str
    policy: Dict[str, Any]
    metadata: AgentMetadata
