"""Grid-world experiment scenario runner.

Uses only the public API: Session is built by the caller via Session.from_config.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Any, Dict, List, Optional

from doagent import Session
from experiments.environment import ValidationEnv
from experiments import RunReporter


@dataclass(frozen=True)
class GridWorldRunSummary:
    """Summary of a grid-world experiment run."""

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


def _build_map_from_records(records: List[Any]) -> Dict[str, Any]:
    """Extract merged cell map from agent_update records."""
    cells: Dict[tuple[int, int], str] = {}
    for record in records:
        payload = getattr(record, "payload", record) if not isinstance(record, dict) else record.get("payload", record)
        record_type = payload.get("type")
        if record_type not in {"map_update", "map_summary"}:
            continue
        local_knowledge = payload.get("local_knowledge", {})
        observation = local_knowledge.get("observation", {})
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


def run_gridworld_validation(
    *,
    session: Session,
    env: ValidationEnv,
    configs: list[Dict[str, Any]],
    rounds: int,
    seed: int,
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
    """Run the grid-world experiment scenario for a fixed number of rounds.

    Caller must provide a Session built with Session.from_config (including policies and topology).
    """
    wrapped_env = session.wrap_env(env, env_actor="gridworld_env")
    agents = session.create_agents(
        configs, goal="map_discovery", payload_type="map_update",
    )

    observations = wrapped_env.reset(seed=seed)
    topo_mode = session.topology_mode

    outcome_count = 0
    rng = random.Random(seed)
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

    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}

        if energy_model:
            for aid in list(active_agents):
                energy_levels[aid] -= energy_decay
                if energy_levels[aid] <= 0:
                    active_agents.remove(aid)
            for aid in agent_ids_all:
                if aid in active_agents:
                    continue
                energy_levels[aid] = min(
                    energy_levels[aid] + energy_recharge, energy_max
                )
                if energy_levels[aid] > energy_leave_threshold:
                    active_agents.add(aid)

        active_agent_ids = sorted(active_agents)

        shared_maps: Dict[str, Dict[str, Any]] = {}
        for aid in active_agent_ids:
            records = session.visible_records(aid, kind="agent_update")
            shared_maps[aid] = _build_map_from_records(list(records))

        for aid in active_agent_ids:
            observation = observations.get(aid, {})
            result = agents[aid].decide(observation, round_id, inputs={
                "observation": observation,
                "shared_map": shared_maps[aid],
            })
            actions[aid] = result["action"]

        if topo_mode == "federated":
            hub_id = getattr(session, "hub_id", "hub")
            hub_records = session.visible_records(hub_id, kind="agent_update")
            hub_summary = _build_map_from_records(list(hub_records))
            session.record_update(hub_id, hub_summary, payload_type="map_summary")

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
