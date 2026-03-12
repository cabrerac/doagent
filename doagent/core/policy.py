"""Policy interface and registry (used by Session.from_config and experiments)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Protocol, TypedDict

from ..records import DecisionRequest, DecisionResponse


class Policy(Protocol):
    """Scenario-agnostic decision policy callable."""

    def __call__(self, request: DecisionRequest) -> DecisionResponse:
        """Return a DecisionResponse for the given request."""


class PolicyConfig(TypedDict):
    """Configuration for a policy instance."""

    name: str
    params: Dict[str, Any]


class AgentPolicyAssignment(TypedDict):
    """Assignment of a policy to an agent id."""

    id: str
    policy: PolicyConfig


PolicyFactory = Callable[[Dict[str, Any]], Policy]


class PolicyRegistry:
    """Registry for reusable policies mapped to FunctionAgent decision callables."""

    def __init__(self) -> None:
        self._factories: Dict[str, PolicyFactory] = {}

    def register(self, name: str, factory: PolicyFactory) -> None:
        """Register a policy factory by name."""
        if name in self._factories:
            raise ValueError(f"Policy '{name}' is already registered.")
        self._factories[name] = factory

    def create(self, config: PolicyConfig) -> Policy:
        """Create a policy callable from a config."""
        name = config["name"]
        params = config.get("params", {})
        if name not in self._factories:
            raise KeyError(f"Policy '{name}' is not registered.")
        return self._factories[name](params)

    def available(self) -> list[str]:
        """Return registered policy names."""
        return sorted(self._factories.keys())

    def factories(self) -> Dict[str, PolicyFactory]:
        """Return registered factories (for multiprocessing scenarios)."""
        return dict(self._factories)


def build_policy_decide_fn(registry: PolicyRegistry, config: PolicyConfig) -> Policy:
    """Return a decision callable compatible with FunctionAgent."""
    return registry.create(config)
