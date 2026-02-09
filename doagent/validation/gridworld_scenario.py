"""Grid-world validation scenario runner with shared-data communication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from ..core.shared_data import new_explanation_record, new_record, new_trace_record
from ..core.topology import Topology, TopologyConfig
from ..interface.shared_data import SharedDataAdapter
from ..records import DecisionRequest, DecisionResponse, new_provenance
from .environment import ValidationEnv
from .gridworld_agents import GridAgentConfig, build_grid_agents
from .policy import PolicyRegistry


@dataclass(frozen=True)
class GridWorldRunSummary:
    """Summary of a grid-world validation run."""

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


def _collect_shared_map(
    shared_data: SharedDataAdapter,
    *,
    agent_id: str,
    topology: Topology,
    visibility: Optional[Dict[str, list[str]]] = None,
) -> Dict[str, Any]:
    cells: Dict[tuple[int, int], str] = {}
    for record in shared_data.listen("agent_update"):
        payload = record.payload
        record_type = payload.get("type")
        if record_type not in {"map_update", "map_summary"}:
            continue
        actor = record.actor
        if topology == Topology.PEER_TO_PEER:
            allowed = {agent_id}
            if visibility and agent_id in visibility:
                allowed.update(visibility[agent_id])
            if actor not in allowed:
                continue
        if topology == Topology.FEDERATED and record_type != "map_summary":
            continue
        for cell in payload.get("cells", []):
            coord = (cell.get("x"), cell.get("y"))
            if coord[0] is None or coord[1] is None:
                continue
            cells[(coord[0], coord[1])] = cell.get("value", "unknown")
    return {
        "cells": [
            {"x": x, "y": y, "value": value} for (x, y), value in cells.items()
        ]
    }


def _build_request(
    *,
    agent_id: str,
    observation: Dict[str, Any],
    shared_map: Dict[str, Any],
    round_id: int,
) -> DecisionRequest:
    return {
        "id": f"req-{agent_id}-{round_id}-{uuid4()}",
        "actor": agent_id,
        "goal": "map_discovery",
        "context": {"round": round_id},
        "inputs": {
            "observation": _serializable(observation),
            "shared_map": _serializable(shared_map),
        },
    }


def run_gridworld_validation(
    *,
    shared_data: SharedDataAdapter,
    env: ValidationEnv,
    registry: PolicyRegistry,
    configs: list[GridAgentConfig],
    rounds: int,
    seed: int,
    topology: TopologyConfig | None = None,
    visibility: Optional[Dict[str, list[str]]] = None,
    hub_id: str = "hub",
) -> GridWorldRunSummary:
    """Run the grid-world validation scenario for a fixed number of rounds."""
    agents = build_grid_agents(shared_data, registry, configs)
    observations = env.reset(seed=seed)
    topo_mode = topology.mode if topology else Topology.CENTRALISED

    outcome_count = 0
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        responses: Dict[str, DecisionResponse] = {}
        decision_record_ids: Dict[str, Optional[str]] = {}

        update_payloads: Dict[str, Dict[str, Any]] = {}
        for agent_id in agents.keys():
            observation = observations.get(agent_id, {})
            update_payloads[agent_id] = {
                "type": "map_update",
                "round": round_id,
                "agent_id": agent_id,
                "cells": observation.get("cells", []),
            }
        for agent_id, payload in update_payloads.items():
            shared_data.write(
                new_record(
                    actor=agent_id,
                    kind="agent_update",
                    payload=payload,
                    provenance=new_provenance(agent=agent_id, sources=[]),
                )
            )
        if topo_mode == Topology.FEDERATED:
            summary = _collect_shared_map(
                shared_data,
                agent_id=hub_id,
                topology=Topology.CENTRALISED,
                visibility=visibility,
            )
            shared_data.write(
                new_record(
                    actor=hub_id,
                    kind="agent_update",
                    payload={"type": "map_summary", "round": round_id, **summary},
                    provenance=new_provenance(agent=hub_id, sources=[]),
                )
            )

        for agent_id, agent in agents.items():
            observation = observations.get(agent_id, {})
            shared_map = _collect_shared_map(
                shared_data,
                agent_id=agent_id,
                topology=topo_mode,
                visibility=visibility,
            )
            request = _build_request(
                agent_id=agent_id,
                observation=observation,
                shared_map=shared_map,
                round_id=round_id,
            )
            response = agent.decide(request)
            responses[agent_id] = response
            decision_record_ids[agent_id] = _find_decision_record_id(
                shared_data, response["id"]
            )
            actions[agent_id] = response.get("decision", {}).get("action", 0)

        step = env.step(actions)
        observations = step.observations

        outcome_payload = {
            "round": round_id,
            "actions": _serializable(actions),
            "rewards": _serializable(step.rewards),
            "observations": _serializable(step.observations),
        }
        provenance = new_provenance(
            agent="gridworld_env",
            sources=[rid for rid in decision_record_ids.values() if rid],
            tools=["gridworld_env"],
        )
        outcome_record = new_record(
            actor="gridworld_env",
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

    return GridWorldRunSummary(rounds=rounds, outcomes=outcome_count)
