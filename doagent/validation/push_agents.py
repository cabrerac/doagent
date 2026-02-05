"""Simple push validation agents and policy assignment helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from ..core.function_agent import FunctionAgent
from ..interface.shared_data import SharedDataAdapter
from ..records import DecisionRequest, DecisionResponse
from .policy import Policy, PolicyConfig, PolicyRegistry


class AgentMetadata(TypedDict, total=False):
    """Optional metadata injected into decision responses."""

    explanation: str
    provenance: Dict[str, Any]
    accountability: Dict[str, Any]


class PushAgentConfig(TypedDict):
    """Configuration for a simple push validation agent."""

    id: str
    policy: PolicyConfig
    metadata: AgentMetadata


def _wrap_policy_with_metadata(
    policy: Policy,
    metadata: Optional[AgentMetadata],
) -> Policy:
    if not metadata:
        return policy

    def decide(request: DecisionRequest) -> DecisionResponse:
        response = dict(policy(request))
        if "explanation" not in response and "explanation" in metadata:
            response["explanation"] = metadata["explanation"]
        if "provenance" not in response and "provenance" in metadata:
            response["provenance"] = metadata["provenance"]
        if "accountability" not in response and "accountability" in metadata:
            response["accountability"] = metadata["accountability"]
        return response

    return decide


def build_push_agents(
    shared_data: SharedDataAdapter,
    registry: PolicyRegistry,
    configs: list[PushAgentConfig],
) -> Dict[str, FunctionAgent]:
    """Build FunctionAgent instances for simple push validation."""
    agents: Dict[str, FunctionAgent] = {}
    for config in configs:
        policy = registry.create(config["policy"])
        decide_fn = _wrap_policy_with_metadata(policy, config.get("metadata"))
        agent = FunctionAgent(config["id"], shared_data, decide_fn)
        agents[config["id"]] = agent
    return agents
