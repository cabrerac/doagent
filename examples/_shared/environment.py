"""Environment interfaces shared by runnable repository examples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Protocol


@dataclass(frozen=True)
class StepResult:
    """Container for one multi-agent environment step."""

    observations: Dict[str, Any]
    rewards: Dict[str, float]
    terminations: Dict[str, bool]
    truncations: Dict[str, bool]
    infos: Dict[str, Dict[str, Any]]


class ValidationEnv(Protocol):
    """Scenario-agnostic environment interface used by examples."""

    def reset(self, *, seed: int | None = None) -> Dict[str, Any]:
        """Reset the environment and return initial observations."""

    def step(self, actions: Dict[str, Any]) -> StepResult:
        """Advance the environment by one step."""

    def render(self) -> None:
        """Render the environment, if supported."""

    @property
    def agents(self) -> Iterable[str]:
        """Return the active agent identifiers."""


class ParallelEnvWrapper:
    """Adapt a Gym/MARL-style parallel environment to ``ValidationEnv``."""

    def __init__(self, env: Any) -> None:
        self._env = env

    @property
    def agents(self) -> Iterable[str]:
        """Return active agent identifiers from the wrapped environment."""
        return getattr(self._env, "agents", [])

    def reset(self, *, seed: int | None = None) -> Dict[str, Any]:
        """Reset and normalize optional ``(observations, infos)`` results."""
        result = self._env.reset(seed=seed)  # type: ignore[call-arg]
        if isinstance(result, tuple) and len(result) == 2:
            observations, _ = result
            return dict(observations)
        return dict(result)

    def step(self, actions: Dict[str, Any]) -> StepResult:
        """Run one step and normalize mappings into a ``StepResult``."""
        observations, rewards, terminations, truncations, infos = self._env.step(
            actions
        )
        return StepResult(
            observations=dict(observations),
            rewards=dict(rewards),
            terminations=dict(terminations),
            truncations=dict(truncations),
            infos=dict(infos),
        )

    def render(self) -> None:
        """Render the wrapped environment when it supports rendering."""
        render_fn = getattr(self._env, "render", None)
        if callable(render_fn):
            render_fn()
