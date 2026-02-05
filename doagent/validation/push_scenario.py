"""Simple push validation scenario runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from ..core.shared_data import new_explanation_record, new_record, new_trace_record
from ..interface.shared_data import SharedDataAdapter
from ..records import DecisionRequest, DecisionResponse, new_provenance
from .environment import ValidationEnv
from .policy import PolicyRegistry
from .push_agents import PushAgentConfig, build_push_agents


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


def _find_decision_record_id(
    shared_data: SharedDataAdapter,
    response_id: str,
) -> Optional[str]:
    for record in shared_data.listen("decision"):
        payload = record.payload
        response = payload.get("response", {})
        if response.get("id") == response_id:
            return record.id
    return None


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
) -> PushRunSummary:
    """Run the simple push validation scenario for a fixed number of rounds."""
    agents = build_push_agents(shared_data, registry, configs)
    observations = env.reset(seed=seed)
    if render:
        env.render()

    outcome_count = 0
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        responses: Dict[str, DecisionResponse] = {}
        decision_record_ids: Dict[str, Optional[str]] = {}

        for agent_id, agent in agents.items():
            observation = observations.get(agent_id, {})
            request = _build_request(
                agent_id=agent_id,
                observation=observation,
                round_id=round_id,
            )
            response = agent.decide(request)
            responses[agent_id] = response
            decision_record_ids[agent_id] = _find_decision_record_id(
                shared_data, response["id"]
            )
            actions[agent_id] = response.get("decision", {}).get("action", 0)

        step = env.step(actions)
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
            sources=[rid for rid in decision_record_ids.values() if rid],
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

        for agent_id, response in responses.items():
            decision_id = decision_record_ids.get(agent_id)
            if decision_id is None:
                continue
            summary = response.get("explanation", "Decision recorded.")
            explanation = new_explanation_record(
                actor=agent_id,
                decision_id=response["id"],
                summary=summary,
            )
            shared_data.write(explanation)

            trace = new_trace_record(
                actor=agent_id,
                from_id=decision_id,
                to_id=outcome_record.id,
                relation="controls",
                notes=f"Round {round_id} decision influenced outcome.",
            )
            shared_data.write(trace)

    return PushRunSummary(rounds=rounds, outcomes=outcome_count)
