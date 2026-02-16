"""Simple push validation scenario runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ...core.shared_data import new_agent_update_record, new_record, new_trace_record
from ...interface.shared_data import SharedDataAdapter
from ...records import (
    DecisionRequest,
    DecisionResponse,
    INITIAL_STATE_ID,
    new_provenance,
)
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
    render: bool = False,
    on_outcome: Callable[[int, Dict[str, Any], Dict[str, float]], None] | None = None,
) -> PushRunSummary:
    """Run the simple push validation scenario for a fixed number of rounds."""
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
            if "explanation" in response:
                decision["explanation"] = response["explanation"]
            agent_update = new_agent_update_record(
                actor=agent_id,
                local_knowledge={"observation": _serializable(observation)},
                decision=decision,
                provenance=new_provenance(agent=agent_id, sources=[]),
            )
            shared_data.write(agent_update)
            agent_update_ids[agent_id] = agent_update.id

        step = env.step(actions)
        if on_outcome is not None:
            on_outcome(round_id, actions, step.rewards)
        if render:
            env.render()
        observations = step.observations

        outcome_payload = {
            "round": round_id,
            "actions": _serializable(actions),
            "rewards": _serializable(step.rewards),
            "observations": _serializable(step.observations),
        }
        provenance = new_provenance(
            agent="push_env",
            sources=list(agent_update_ids.values()),
            tools=["push_env"],
        )
        outcome_record = new_record(
            actor="push_env",
            kind="outcome",
            payload=outcome_payload,
            provenance=provenance,
        )
        shared_data.write(outcome_record)
        outcome_count += 1

        for agent_id in responses:
            trace = new_trace_record(
                actor=agent_id,
                from_id=prev_outcome_id,
                to_id=outcome_record.id,
                enabled_by_id=agent_update_ids[agent_id],
                relation="enables",
                round_=round_id,
                notes=f"Round {round_id} decision influenced outcome.",
            )
            shared_data.write(trace)

        prev_outcome_id = outcome_record.id

    return PushRunSummary(rounds=rounds, outcomes=outcome_count)
