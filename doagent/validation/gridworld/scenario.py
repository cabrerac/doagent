"""Grid-world validation scenario runner with shared-data communication."""

from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import get_context
import random
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from ...core.participation import ParticipationRecord, ParticipationRegistry
from ...core.shared_data import new_explanation_record, new_record, new_trace_record
from ...core.topology import Topology, TopologyConfig
from ...interface.shared_data import SharedDataAdapter
from ...records import DecisionRequest, DecisionResponse, new_provenance
from ..environment import ValidationEnv
from ..multiprocess_interface import MultiProcessInterface
from ..policy import PolicyRegistry
from ..reporting import RunReporter
from .agents import GridAgentConfig, build_grid_agents


@dataclass(frozen=True)
class GridWorldRunSummary:
    """Summary of a grid-world validation run."""

    rounds: int
    outcomes: int
    coverage: float
    discovery_round: Optional[int]
    contributions: Dict[str, int]
    total_cells: Optional[int]
    termination_reason: str = "rounds_complete"
    landmarks_discovered: int = 0
    landmarks_total: Optional[int] = None


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


def _decide_worker(
    policy_name: str,
    policy_params: Dict[str, Any],
    factories: Dict[str, Any],
    request: DecisionRequest,
) -> DecisionResponse:
    policy = factories[policy_name](policy_params)
    return policy(request)


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
    use_multiprocessing: bool = False,
    mp_context: str = "spawn",
    mp_interface: MultiProcessInterface | None = None,
    participation_registry: ParticipationRegistry | None = None,
    energy_model: bool = False,
    energy_min: int = 6,
    energy_max: int = 12,
    energy_decay: int = 1,
    energy_recharge: int = 1,
    energy_leave_threshold: int = 2,
    render: bool = False,
    render_delay: float = 0.0,
    print_every: int = 0,
    landmarks_total: Optional[int] = None,
    reporter: RunReporter | None = None,
) -> GridWorldRunSummary:
    """Run the grid-world validation scenario for a fixed number of rounds."""
    agents = build_grid_agents(shared_data, registry, configs)
    observations = env.reset(seed=seed)
    topo_mode = topology.mode if topology else Topology.CENTRALISED

    outcome_count = 0
    active_shared = mp_interface if use_multiprocessing else shared_data
    rng = random.Random(seed)
    config_map = {config["id"]: config for config in configs}
    active_agents = set(agents.keys())
    contributions = {agent_id: 0 for agent_id in agents.keys()}
    discovered_cells: set[tuple[int, int]] = set()
    landmarks_discovered: set[tuple[int, int]] = set()
    total_rewards: Dict[str, float] = {}
    total_cells: Optional[int] = None
    discovery_round: Optional[int] = None
    termination_reason = "rounds_complete"
    energy_levels = {
        agent_id: rng.randint(energy_min, energy_max) for agent_id in agents.keys()
    }
    for obs in observations.values():
        width = obs.get("width")
        height = obs.get("height")
        if width and height:
            total_cells = int(width) * int(height)
            break
    for obs in observations.values():
        for cell in obs.get("cells", []):
            x, y = cell.get("x"), cell.get("y")
            if x is None or y is None:
                continue
            coord = (int(x), int(y))
            discovered_cells.add(coord)
            if cell.get("value") == "landmark":
                landmarks_discovered.add(coord)
    if total_cells and len(discovered_cells) >= total_cells:
        discovery_round = 0
    if participation_registry is not None:
        for agent_id in active_agents:
            participation_registry.register(ParticipationRecord(agent_id=agent_id))

    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        responses: Dict[str, DecisionResponse] = {}
        decision_record_ids: Dict[str, Optional[str]] = {}

        if energy_model:
            for agent_id in list(active_agents):
                energy_levels[agent_id] -= energy_decay
                if energy_levels[agent_id] <= 0:
                    active_agents.remove(agent_id)
                    if participation_registry is not None:
                        participation_registry.deregister(agent_id)
            for agent_id in agents.keys():
                if agent_id in active_agents:
                    continue
                energy_levels[agent_id] = min(
                    energy_levels[agent_id] + energy_recharge, energy_max
                )
                if energy_levels[agent_id] > energy_leave_threshold:
                    active_agents.add(agent_id)
                    if participation_registry is not None:
                        participation_registry.register(
                            ParticipationRecord(agent_id=agent_id)
                        )

        active_agent_ids = sorted(active_agents)

        update_payloads: Dict[str, Dict[str, Any]] = {}
        for agent_id in active_agent_ids:
            observation = observations.get(agent_id, {})
            update_payloads[agent_id] = {
                "type": "map_update",
                "round": round_id,
                "agent_id": agent_id,
                "cells": observation.get("cells", []),
            }
        for agent_id, payload in update_payloads.items():
            record = new_record(
                actor=agent_id,
                kind="agent_update",
                payload=payload,
                provenance=new_provenance(agent=agent_id, sources=[]),
            )
            if use_multiprocessing and mp_interface is not None:
                mp_interface.write_record(record)
            else:
                shared_data.write(record)
        if topo_mode == Topology.FEDERATED:
            summary = _collect_shared_map(
                active_shared,
                agent_id=hub_id,
                topology=Topology.CENTRALISED,
                visibility=visibility,
            )
            summary_record = new_record(
                actor=hub_id,
                kind="agent_update",
                payload={"type": "map_summary", "round": round_id, **summary},
                provenance=new_provenance(agent=hub_id, sources=[]),
            )
            if use_multiprocessing and mp_interface is not None:
                mp_interface.write_record(summary_record)
            else:
                shared_data.write(summary_record)

        shared_maps: Dict[str, Dict[str, Any]] = {}
        requests: Dict[str, DecisionRequest] = {}
        for agent_id in active_agent_ids:
            observation = observations.get(agent_id, {})
            shared_map = _collect_shared_map(
                active_shared,
                agent_id=agent_id,
                topology=topo_mode,
                visibility=visibility,
            )
            shared_maps[agent_id] = shared_map
            requests[agent_id] = _build_request(
                agent_id=agent_id,
                observation=observation,
                shared_map=shared_map,
                round_id=round_id,
            )

        if use_multiprocessing and active_agent_ids:
            factories = registry.factories()
            ctx = get_context(mp_context)
            with ctx.Pool(processes=len(active_agent_ids)) as pool:
                tasks = []
                for agent_id in active_agent_ids:
                    policy = config_map[agent_id]["policy"]
                    tasks.append(
                        (
                            policy["name"],
                            policy.get("params", {}),
                            factories,
                            requests[agent_id],
                        )
                    )
                results = pool.starmap(_decide_worker, tasks)
            for agent_id, response in zip(active_agent_ids, results):
                responses[agent_id] = response
                decision_record_ids[agent_id] = _find_decision_record_id(
                    shared_data, response["id"]
                )
                actions[agent_id] = response.get("decision", {}).get("action", 0)
        elif not use_multiprocessing:
            for agent_id in active_agent_ids:
                agent = agents[agent_id]
                request = requests[agent_id]
                response = agent.decide(request)
                responses[agent_id] = response
                decision_record_ids[agent_id] = _find_decision_record_id(
                    shared_data, response["id"]
                )
                actions[agent_id] = response.get("decision", {}).get("action", 0)

        step = env.step(actions)
        observations = step.observations
        if reporter is not None:
            reporter.on_outcome(round_id, actions, step.rewards)
        for agent_id, r in step.rewards.items():
            total_rewards[agent_id] = total_rewards.get(agent_id, 0.0) + r
        for agent_id in active_agent_ids:
            observation = observations.get(agent_id, {})
            for cell in observation.get("cells", []):
                x = cell.get("x")
                y = cell.get("y")
                if x is None or y is None:
                    continue
                coord = (int(x), int(y))
                if coord not in discovered_cells:
                    discovered_cells.add(coord)
                    contributions[agent_id] += 1
                    if cell.get("value") == "landmark":
                        landmarks_discovered.add(coord)
        if total_cells and discovery_round is None:
            if len(discovered_cells) >= total_cells:
                discovery_round = round_id
        if render:
            env.render()
            if render_delay > 0:
                time.sleep(render_delay)

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

        # Terminate early if env signals done, full coverage, or all landmarks found
        if all(step.terminations.values()):
            termination_reason = "max_cycles"
            break
        if total_cells and len(discovered_cells) >= total_cells:
            termination_reason = "full_coverage"
            break
        if landmarks_total is not None and len(landmarks_discovered) >= landmarks_total:
            termination_reason = "all_landmarks_discovered"
            break

        if print_every > 0 and round_id % print_every == 0:
            cov_pct = (
                100.0 * len(discovered_cells) / total_cells
                if total_cells else 0.0
            )
            lm_msg = f"{len(landmarks_discovered)}"
            if landmarks_total is not None:
                lm_msg += f"/{landmarks_total}"
            rewards_str = ", ".join(
                f"{a}={total_rewards.get(a, 0):.0f}"
                for a in sorted(total_rewards.keys())
            )
            print(
                f"[gridworld] round={round_id} "
                f"coverage={cov_pct:.1f}% landmarks={lm_msg} "
                f"active={len(active_agent_ids)} rewards={{{rewards_str}}}"
            )

    coverage = (
        float(len(discovered_cells)) / float(total_cells) if total_cells else 0.0
    )
    summary = GridWorldRunSummary(
        rounds=rounds,
        outcomes=outcome_count,
        coverage=coverage,
        discovery_round=discovery_round,
        contributions=contributions,
        total_cells=total_cells,
        termination_reason=termination_reason,
        landmarks_discovered=len(landmarks_discovered),
        landmarks_total=landmarks_total,
    )
    # Final summary print
    lm_msg = f"{len(landmarks_discovered)}"
    if landmarks_total is not None:
        lm_msg += f"/{landmarks_total}"
    rewards_str = ", ".join(
        f"{a}={total_rewards.get(a, 0):.0f}" for a in sorted(total_rewards.keys())
    )
    print(
        f"[gridworld] FINAL: termination={termination_reason} "
        f"rounds={outcome_count} coverage={coverage*100:.1f}% "
        f"landmarks={lm_msg} rewards={{{rewards_str}}}"
    )
    return summary
