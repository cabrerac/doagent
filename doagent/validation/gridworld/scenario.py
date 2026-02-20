"""Grid-world validation scenario runner with shared-data communication."""

from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import get_context
import random
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from ...core.participation import ParticipationRecord, ParticipationRegistry
from ...core.run_config import RunConfig
from ...core.session import Session
from ...core.topology import Topology, TopologyConfig
from ...interface.shared_data import SharedDataAdapter
from ...records import DecisionRequest, DecisionResponse
from ..environment import ValidationEnv
from ..multiprocess_interface import MultiProcessInterface
from ..policy import PolicyRegistry
from ..reporting import RunReporter
from .agents import GridAgentConfig


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
        local_knowledge = payload.get("local_knowledge", {})
        observation = local_knowledge.get("observation", {})
        actor = record.actor
        if topology == Topology.PEER_TO_PEER:
            allowed = {agent_id}
            if visibility and agent_id in visibility:
                allowed.update(visibility[agent_id])
            if actor not in allowed:
                continue
        if topology == Topology.FEDERATED and record_type != "map_summary":
            continue
        cells_source = (
            observation.get("cells", [])
            or local_knowledge.get("cells", [])
            or payload.get("cells", [])
        )
        for cell in cells_source:
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
    run_config: RunConfig | None = None,
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
    agent_write_fn = None
    if use_multiprocessing and mp_interface is not None:
        agent_write_fn = mp_interface.write_record
    session = Session(shared_data, run_config, agent_write_fn=agent_write_fn)
    wrapped_env = session.wrap_env(env, env_actor="gridworld_env")
    agents = session.create_agents(
        configs, registry, goal="map_discovery", payload_type="map_update",
    )

    observations = wrapped_env.reset(seed=seed)
    topo_mode = topology.mode if topology else Topology.CENTRALISED

    outcome_count = 0
    active_shared = mp_interface if use_multiprocessing else shared_data
    rng = random.Random(seed)
    config_map = {cfg["id"]: cfg for cfg in configs}
    agent_ids_all = list(agents.keys())
    active_agents = set(agent_ids_all)
    contributions = {aid: 0 for aid in agent_ids_all}
    discovered_cells: set[tuple[int, int]] = set()
    landmarks_discovered_set: set[tuple[int, int]] = set()
    total_rewards: Dict[str, float] = {}
    total_cells: Optional[int] = None
    discovery_round: Optional[int] = None
    termination_reason = "rounds_complete"
    energy_levels = {
        aid: rng.randint(energy_min, energy_max) for aid in agent_ids_all
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
                landmarks_discovered_set.add(coord)
    if total_cells and len(discovered_cells) >= total_cells:
        discovery_round = 0
    if participation_registry is not None:
        for aid in active_agents:
            participation_registry.register(ParticipationRecord(agent_id=aid))

    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        responses: Dict[str, DecisionResponse] = {}

        if energy_model:
            for aid in list(active_agents):
                energy_levels[aid] -= energy_decay
                if energy_levels[aid] <= 0:
                    active_agents.remove(aid)
                    if participation_registry is not None:
                        participation_registry.deregister(aid)
            for aid in agent_ids_all:
                if aid in active_agents:
                    continue
                energy_levels[aid] = min(
                    energy_levels[aid] + energy_recharge, energy_max
                )
                if energy_levels[aid] > energy_leave_threshold:
                    active_agents.add(aid)
                    if participation_registry is not None:
                        participation_registry.register(
                            ParticipationRecord(agent_id=aid)
                        )

        active_agent_ids = sorted(active_agents)

        shared_maps: Dict[str, Dict[str, Any]] = {}
        for aid in active_agent_ids:
            shared_maps[aid] = _collect_shared_map(
                active_shared,
                agent_id=aid,
                topology=topo_mode,
                visibility=visibility,
            )

        if use_multiprocessing and active_agent_ids:
            requests: Dict[str, DecisionRequest] = {}
            for aid in active_agent_ids:
                requests[aid] = _build_request(
                    agent_id=aid,
                    observation=observations.get(aid, {}),
                    shared_map=shared_maps[aid],
                    round_id=round_id,
                )
            factories = registry.factories()
            ctx = get_context(mp_context)
            with ctx.Pool(processes=len(active_agent_ids)) as pool:
                tasks = []
                for aid in active_agent_ids:
                    policy = config_map[aid]["policy"]
                    tasks.append((
                        policy["name"],
                        policy.get("params", {}),
                        factories,
                        requests[aid],
                    ))
                results = pool.starmap(_decide_worker, tasks)
                for aid, response in zip(active_agent_ids, results):
                    responses[aid] = response
                    actions[aid] = response.get("decision", {}).get("action", 0)
                    obs_for_record = {
                        "cells": observations.get(aid, {}).get("cells", []),
                        "shared_map": shared_maps[aid],
                        "round": round_id,
                    }
                    session.record_decision(
                        aid, obs_for_record, response, round_id,
                        goal="map_discovery", payload_type="map_update",
                    )
        else:
            for aid in active_agent_ids:
                observation = observations.get(aid, {})
                result = agents[aid].decide(observation, round_id, inputs={
                    "observation": observation,
                    "shared_map": shared_maps[aid],
                })
                responses[aid] = result["response"]
                actions[aid] = result["action"]

        if topo_mode == Topology.FEDERATED:
            summary = _collect_shared_map(
                active_shared,
                agent_id=hub_id,
                topology=Topology.CENTRALISED,
                visibility=visibility,
            )
            session.record_update(hub_id, summary, payload_type="map_summary")

        step = wrapped_env.step(actions)
        observations = step["observations"]

        if reporter is not None:
            reporter.on_outcome(round_id, actions, step["rewards"])
        for aid, r in step["rewards"].items():
            total_rewards[aid] = total_rewards.get(aid, 0.0) + r
        for aid in active_agent_ids:
            observation = observations.get(aid, {})
            for cell in observation.get("cells", []):
                x = cell.get("x")
                y = cell.get("y")
                if x is None or y is None:
                    continue
                coord = (int(x), int(y))
                if coord not in discovered_cells:
                    discovered_cells.add(coord)
                    contributions[aid] += 1
                    if cell.get("value") == "landmark":
                        landmarks_discovered_set.add(coord)
        if total_cells and discovery_round is None:
            if len(discovered_cells) >= total_cells:
                discovery_round = round_id
        if render:
            wrapped_env.render()
            if render_delay > 0:
                time.sleep(render_delay)

        outcome_count += 1

        done = step.get("done", {})
        if isinstance(done, dict) and done and all(done.values()):
            termination_reason = "max_cycles"
            break
        if total_cells and len(discovered_cells) >= total_cells:
            termination_reason = "full_coverage"
            break
        if landmarks_total is not None and len(landmarks_discovered_set) >= landmarks_total:
            termination_reason = "all_landmarks_discovered"
            break

        if print_every > 0 and round_id % print_every == 0:
            cov_pct = (
                100.0 * len(discovered_cells) / total_cells
                if total_cells else 0.0
            )
            lm_msg = f"{len(landmarks_discovered_set)}"
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
    result_summary = GridWorldRunSummary(
        rounds=rounds,
        outcomes=outcome_count,
        coverage=coverage,
        discovery_round=discovery_round,
        contributions=contributions,
        total_cells=total_cells,
        termination_reason=termination_reason,
        landmarks_discovered=len(landmarks_discovered_set),
        landmarks_total=landmarks_total,
    )
    lm_msg = f"{len(landmarks_discovered_set)}"
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
    return result_summary
