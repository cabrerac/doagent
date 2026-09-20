"""Reusable gridworld session functions, separate from the CLI entry point."""

from __future__ import annotations

from pathlib import Path
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from doagent import Session, RunReporter

from examples.gridworld.policies import (
    auction_frontier_policy,
    frontier_explore_policy,
    llm_explore_policy,
    random_explore_policy,
)


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load gridworld YAML only when a configured run is requested."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required to load gridworld config.") from exc
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Config must be a YAML mapping.")
    return data


def parse_topology(config: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, List[str]]]]:
    """Return (mode_string, visibility_dict) from config."""
    topo_cfg = config.get("scenario", {}).get("topology")
    if not topo_cfg:
        return "centralised", None
    mode = str(topo_cfg.get("mode", "centralised")).lower()
    visibility = topo_cfg.get("visibility")
    return mode, visibility


def parse_agent_configs(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Agent configs as plain dicts: id, policy, metadata (Session API contract)."""
    return [
        {"id": a["id"], "policy": a["policy"], "metadata": a.get("metadata", {})}
        for a in config.get("agents", [])
    ]


def build_shared_map(records: List[Any]) -> Dict[str, Any]:
    """Interpret agent_update records into a merged map of discovered cells."""
    cells: Dict[Tuple[int, int], str] = {}
    for record in records:
        local_knowledge = record.payload.get("local_knowledge", {})
        observation = local_knowledge.get("observation", {})
        cell_list = (
            observation.get("cells", [])
            or local_knowledge.get("cells", [])
            or record.payload.get("cells", [])
        )
        for cell in cell_list:
            x, y = cell.get("x"), cell.get("y")
            if x is not None and y is not None:
                cells[(x, y)] = cell.get("value", "unknown")
    return {
        "cells": [{"x": x, "y": y, "value": v} for (x, y), v in cells.items()]
    }


GRIDWORLD_POLICIES = {
    "grid_random": random_explore_policy,
    "grid_frontier": frontier_explore_policy,
    "grid_auction_frontier": auction_frontier_policy,
    "grid_llm": llm_explore_policy,
}


def run_with_session(
    session: Session,
    env: Any,
    configs: list[Dict[str, Any]],
    rounds: int,
    seed: int,
    *,
    energy_model: bool = False,
    energy_min: int = 6,
    energy_max: int = 12,
    energy_decay: int = 1,
    energy_recharge: int = 1,
    energy_leave_threshold: int = 2,
    landmarks_total: int | None = None,
    render: bool = False,
    render_delay: float = 0.0,
    print_every: int = 0,
    reporter: RunReporter | None = None,
) -> Dict[str, Any]:
    """Run gridworld scenario using the DOAgent Session API. Returns summary dict."""
    agent_ids = [c["id"] for c in configs]

    wrapped_env = session.wrap_env(env, env_actor="gridworld_env")
    agents = session.create_agents(
        configs, goal="map_discovery", payload_type="map_update",
    )

    registry = session.participation_registry
    if registry and energy_model:
        for aid in agent_ids:
            session.register_participant(aid, capabilities=["map_discovery"])

    observations = wrapped_env.reset(seed=seed)
    rng = random.Random(seed)

    active_agents = set(agent_ids)
    contributions: Dict[str, int] = {aid: 0 for aid in agent_ids}
    discovered_cells: set[Tuple[int, int]] = set()
    landmarks_discovered: set[Tuple[int, int]] = set()
    total_rewards: Dict[str, float] = {}
    total_cells: Optional[int] = None
    discovery_round: Optional[int] = None
    termination_reason = "rounds_complete"
    energy_levels = {aid: rng.randint(energy_min, energy_max) for aid in agent_ids}

    for obs in observations.values():
        w, h = obs.get("width"), obs.get("height")
        if w and h:
            total_cells = int(w) * int(h)
            break
    for obs in observations.values():
        for cell in obs.get("cells", []):
            x, y = cell.get("x"), cell.get("y")
            if x is not None and y is not None:
                coord = (int(x), int(y))
                discovered_cells.add(coord)
                if cell.get("value") == "landmark":
                    landmarks_discovered.add(coord)
    if total_cells and len(discovered_cells) >= total_cells:
        discovery_round = 0

    outcome_count = 0
    hub_id = session.hub_id

    for round_id in range(1, rounds + 1):
        if energy_model:
            for aid in list(active_agents):
                energy_levels[aid] -= energy_decay
                if energy_levels[aid] <= 0:
                    active_agents.remove(aid)
                    if registry:
                        session.deregister_participant(aid)
            for aid in agent_ids:
                if aid in active_agents:
                    continue
                energy_levels[aid] = min(energy_levels[aid] + energy_recharge, energy_max)
                if energy_levels[aid] > energy_leave_threshold:
                    active_agents.add(aid)
                    if registry:
                        session.register_participant(aid, capabilities=["map_discovery"])

        active_ids = sorted(active_agents)
        actions: Dict[str, Any] = {}

        for aid in active_ids:
            observation = observations.get(aid, {})
            shared_map = session.decision_context(
                aid, kinds="agent_update", summarise=build_shared_map,
            )
            result = agents[aid].decide(observation, round_id, inputs={
                "observation": observation,
                "shared_map": shared_map,
                "participants": session.visible_participants(aid),
            })
            actions[aid] = result["action"]

        if session.topology_mode == "federated":
            hub_summary = session.decision_context(
                hub_id, kinds="agent_update", summarise=build_shared_map,
            )
            session.record_update(hub_id, hub_summary, payload_type="map_summary")

        step = wrapped_env.step(actions)
        observations = step["observations"]

        if reporter is not None:
            reporter.on_outcome(round_id, actions, step["rewards"])
        for aid, r in step["rewards"].items():
            total_rewards[aid] = total_rewards.get(aid, 0.0) + r
        for aid in active_ids:
            obs = observations.get(aid, {})
            for cell in obs.get("cells", []):
                x, y = cell.get("x"), cell.get("y")
                if x is None or y is None:
                    continue
                coord = (int(x), int(y))
                if coord not in discovered_cells:
                    discovered_cells.add(coord)
                    contributions[aid] += 1
                    if cell.get("value") == "landmark":
                        landmarks_discovered.add(coord)
        if total_cells and discovery_round is None and len(discovered_cells) >= total_cells:
            discovery_round = round_id
        if render:
            env.render()
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
        if landmarks_total is not None and len(landmarks_discovered) >= landmarks_total:
            termination_reason = "all_landmarks_discovered"
            break

        if print_every > 0 and round_id % print_every == 0:
            cov = 100.0 * len(discovered_cells) / total_cells if total_cells else 0.0
            lm = f"{len(landmarks_discovered)}"
            if landmarks_total is not None:
                lm += f"/{landmarks_total}"
            rw = ", ".join(f"{a}={total_rewards.get(a, 0):.0f}" for a in sorted(total_rewards))
            print(f"[gridworld] round={round_id} coverage={cov:.1f}% landmarks={lm} active={len(active_ids)} rewards={{{rw}}}")

    coverage = float(len(discovered_cells)) / float(total_cells) if total_cells else 0.0
    lm = f"{len(landmarks_discovered)}"
    if landmarks_total is not None:
        lm += f"/{landmarks_total}"
    rw = ", ".join(f"{a}={total_rewards.get(a, 0):.0f}" for a in sorted(total_rewards))
    print(f"[gridworld] FINAL: termination={termination_reason} rounds={outcome_count} coverage={coverage*100:.1f}% landmarks={lm} rewards={{{rw}}}")

    return {
        "outcomes": outcome_count,
        "coverage": coverage,
        "discovery_round": discovery_round,
        "contributions": contributions,
        "total_cells": total_cells,
        "termination_reason": termination_reason,
        "landmarks_discovered": len(landmarks_discovered),
        "landmarks_total": landmarks_total,
    }


def make_session_config(
    shared_data_type: str = "memory",
    shared_data_path: str | None = None,
    shared_data_uri: str | None = None,
    scenario_name: str | None = None,
    output_base: str = "output",
    topology_mode: str = "centralised",
    visibility: Dict[str, List[str]] | None = None,
    hub_id: str = "hub",
    participation: bool = False,
) -> Dict[str, Any]:
    """Build a Session config dict from run parameters."""
    cfg: Dict[str, Any] = {
        "shared_data": {"type": shared_data_type},
        "run_config": {"logging_level": 2},
        "topology": {"mode": topology_mode},
        "policies": GRIDWORLD_POLICIES,
        "hub_id": hub_id,
    }
    if participation:
        cfg["participation"] = True
    if shared_data_type == "file" and scenario_name:
        cfg["scenario_name"] = scenario_name
        cfg["output_base"] = output_base
    elif shared_data_type == "mongo" and scenario_name:
        cfg["scenario_name"] = scenario_name
        cfg["output_base"] = output_base
        cfg["shared_data"]["uri"] = shared_data_uri or "mongodb://localhost:27017"
    elif shared_data_path:
        cfg["shared_data"]["path"] = shared_data_path
    if visibility:
        cfg["topology"]["visibility"] = visibility
    return cfg
