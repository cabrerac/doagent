"""Simple push validation scenario runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ...core.run_config import RunConfig
from ...core.session import Session
from ...interface.shared_data import SharedDataAdapter
from ..policy import PolicyRegistry
from .agents import PushAgentConfig


@dataclass(frozen=True)
class PushRunSummary:
    """Summary of a simple push validation run."""

    rounds: int
    outcomes: int


def run_push_validation(
    *,
    shared_data: SharedDataAdapter,
    env: Any,
    registry: PolicyRegistry,
    configs: list[PushAgentConfig],
    rounds: int,
    seed: int,
    run_config: RunConfig | None = None,
    render: bool = False,
    on_outcome: Callable[[int, Dict[str, Any], Dict[str, float]], None] | None = None,
) -> PushRunSummary:
    """Run the simple push validation scenario for a fixed number of rounds."""
    session = Session(shared_data, run_config)
    wrapped_env = session.wrap_env(env, env_actor="push_env")
    agents = session.create_agents(configs, registry, goal="push_towards_landmark")

    observations = wrapped_env.reset(seed=seed)
    if render:
        wrapped_env.render()

    outcome_count = 0
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        for agent_id, agent in agents.items():
            result = agent.decide(observations.get(agent_id, {}), round_id)
            actions[agent_id] = result["action"]

        step = wrapped_env.step(actions)
        if on_outcome is not None:
            on_outcome(round_id, actions, step["rewards"])
        if render:
            wrapped_env.render()
        observations = step["observations"]
        outcome_count += 1

    return PushRunSummary(rounds=rounds, outcomes=outcome_count)
