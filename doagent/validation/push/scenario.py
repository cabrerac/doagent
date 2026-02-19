"""Simple push validation scenario runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ...core.record_writer import RecordWriter
from ...core.run_config import RunConfig
from ...interface.shared_data import SharedDataAdapter
from ...records import DecisionRequest, DecisionResponse, INITIAL_STATE_ID
from ..environment import ValidationEnv
from ..policy import PolicyRegistry
from .agents import PushAgentConfig, build_push_agents


@dataclass(frozen=True)
class PushRunSummary:
    """Summary of a simple push validation run."""

    rounds: int
    outcomes: int


def _serializable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _serializable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


def _build_request(
    *,
    agent_id: str,
    observation: Dict[str, Any],
    round_id: int,
) -> DecisionRequest:
    return {
        "id": f"req-{agent_id}-{round_id}-{uuid4()}",
        "actor": agent_id,
        "goal": "push_towards_landmark",
        "context": {"round": round_id},
        "inputs": {"observation": _serializable(observation)},
    }


def run_push_validation(
    *,
    shared_data: SharedDataAdapter,
    env: ValidationEnv,
    registry: PolicyRegistry,
    configs: list[PushAgentConfig],
    rounds: int,
    seed: int,
    run_config: RunConfig | None = None,
    render: bool = False,
    on_outcome: Callable[[int, Dict[str, Any], Dict[str, float]], None] | None = None,
) -> PushRunSummary:
    """Run the simple push validation scenario for a fixed number of rounds."""
    config = run_config or RunConfig()
    record_writer = RecordWriter(shared_data, config)
    agents = build_push_agents(shared_data, registry, configs)
    observations = env.reset(seed=seed)
    if render:
        env.render()

    outcome_count = 0
    prev_outcome_id: str = INITIAL_STATE_ID
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        responses: Dict[str, DecisionResponse] = {}
        agent_update_ids: Dict[str, str] = {}

        for agent_id, agent in agents.items():
            observation = observations.get(agent_id, {})
            request = _build_request(
                agent_id=agent_id,
                observation=observation,
                round_id=round_id,
            )
            response = agent.decide(request, persist=False)
            responses[agent_id] = response
            actions[agent_id] = response.get("decision", {}).get("action", 0)

            decision = {
                "request": dict(request),
                "response": {k: v for k, v in response.items() if k not in ("provenance", "accountability")},
            }
            record_id = record_writer.on_agent_decide(
                agent_id=agent_id,
                local_knowledge={"observation": _serializable(observation)},
                decision=decision,
                response=response,
            )
            agent_update_ids[agent_id] = record_id

        step = env.step(actions)
        if on_outcome is not None:
            on_outcome(round_id, actions, step.rewards)
        if render:
            env.render()
        observations = step.observations

        prev_outcome_id = record_writer.on_outcome_and_traces(
            round_id=round_id,
            actions=actions,
            rewards=step.rewards,
            observations=step.observations,
            agent_update_ids=agent_update_ids,
            prev_outcome_id=prev_outcome_id,
            env_actor="push_env",
            agent_ids=list(responses.keys()),
        )
        outcome_count += 1

    return PushRunSummary(rounds=rounds, outcomes=outcome_count)
