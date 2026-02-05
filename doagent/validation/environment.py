"""Environment interface and wrapper for validation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Protocol, Tuple


@dataclass(frozen=True)
class StepResult:
    """Container for a multi-agent environment step."""

    observations: Dict[str, Any]
    rewards: Dict[str, float]
    terminations: Dict[str, bool]
    truncations: Dict[str, bool]
    infos: Dict[str, Dict[str, Any]]


class ValidationEnv(Protocol):
    """Scenario-agnostic environment interface for validation runs."""

    def reset(self, *, seed: int | None = None) -> Dict[str, Any]:
        """Reset the environment and return initial observations."""

    def step(self, actions: Dict[str, Any]) -> StepResult:
        """Advance the environment by one step."""

    def render(self) -> None:
        """Render the environment, if supported."""

    @property
    def agents(self) -> Iterable[str]:
        """Return the active agent ids."""


class ParallelEnvWrapper:
    """Adapter for Gym/MARL-style parallel environments."""

    def __init__(self, env: Any) -> None:
        self._env = env

    @property
    def agents(self) -> Iterable[str]:
        return getattr(self._env, "agents", [])

    def reset(self, *, seed: int | None = None) -> Dict[str, Any]:
        result = self._env.reset(seed=seed)  # type: ignore[call-arg]
        if isinstance(result, tuple) and len(result) == 2:
            observations, _ = result
            return dict(observations)
        return dict(result)

    def step(self, actions: Dict[str, Any]) -> StepResult:
        (
            observations,
            rewards,
            terminations,
            truncations,
            infos,
        ) = self._env.step(actions)
        return StepResult(
            observations=dict(observations),
            rewards=dict(rewards),
            terminations=dict(terminations),
            truncations=dict(truncations),
            infos=dict(infos),
        )

    def render(self) -> None:
        render_fn = getattr(self._env, "render", None)
        if callable(render_fn):
            render_fn()
