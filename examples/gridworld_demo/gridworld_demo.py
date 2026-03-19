"""
Grid-world demo using the DOAgent Session API.
Demonstrates all three DOA principles through the library:
- Shared-data model: agents share knowledge via shared data, library records transparently.
- Decentralisation: topology-filtered record access (centralised, peer-to-peer, federated).
- Openness: user provides environment, policies, and run loop; library provides interfaces.

"""

from __future__ import annotations

from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml

from doagent import Session, RunReporter, make_env
from doagent.analysis import (
    accountability,
    interpretability,
    provenance,
    traceability,
)
from examples.gridworld_demo.env import create_gridworld_env
from examples.gridworld_demo.policies import (
    random_explore_policy,
    frontier_explore_policy,
    auction_frontier_policy,
)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> Dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Scenario-specific helpers
# ---------------------------------------------------------------------------

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
}


# ---------------------------------------------------------------------------
# Run environment with DOAgent Session API
# ---------------------------------------------------------------------------

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
            shared_records = session.visible_records(aid, kind="agent_update")
            shared_map = build_shared_map(shared_records)
            result = agents[aid].decide(observation, round_id, inputs={
                "observation": observation,
                "shared_map": shared_map,
            })
            actions[aid] = result["action"]

        if session.topology_mode == "federated":
            # Hub aggregates agent_update records for federated topology.
            hub_records = session.visible_records(hub_id, kind="agent_update")
            hub_summary = build_shared_map(hub_records)
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


def _make_session_config(
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
    """Build a Session config dict from run parameters. For file/mongo runs with scenario_name, library creates run_id and folders."""
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / "gridworld_demo_config.yaml"
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_config
    config = load_config(config_path)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    participation_cfg = scenario.get("participation", {}) or {}
    # Storage: "file" (default) or "mongo". For mongo, optional "mongo_uri" in scenario (default mongodb://localhost:27017).
    storage_type = str(scenario.get("storage", "file")).lower()
    mongo_uri = scenario.get("mongo_uri") or "mongodb://localhost:27017"

    rounds = int(run_cfg.get("rounds", 10))
    seed = int(run_cfg.get("seed", 0))
    render = bool(scenario.get("render", False))
    render_mode = scenario.get("render_mode")
    if render and render_mode is None:
        render_mode = "ansi"
    render_delay = float(scenario.get("render_delay", 0.3 if render_mode == "human" else 0.0))
    print_every = int(scenario.get("print_every", 0))
    landmarks_total = int(env_cfg["landmarks"]) if "landmarks" in env_cfg else None

    energy_model = bool(participation_cfg.get("energy_model", False))
    energy_min = int(participation_cfg.get("energy_min", 6))
    energy_max = int(participation_cfg.get("energy_max", 12))
    energy_decay = int(participation_cfg.get("energy_decay", 1))
    energy_recharge = int(participation_cfg.get("energy_recharge", 1))
    energy_leave_threshold = int(participation_cfg.get("energy_leave_threshold", 2))

    agent_configs = parse_agent_configs(config)
    agent_ids = [c["id"] for c in agent_configs]
    topology_mode, visibility = parse_topology(config)
    hub_id = "hub"

    env = make_env(
        create_gridworld_env,
        width=int(env_cfg.get("width", 6)),
        height=int(env_cfg.get("height", 6)),
        agent_ids=agent_ids,
        landmarks=int(env_cfg.get("landmarks", 2)),
        observation_radius=int(env_cfg.get("observation_radius", 1)),
        max_cycles=int(env_cfg.get("max_cycles", 25)),
        seed=run_cfg.get("seed"),
        render_mode=render_mode,
    )

    run_kwargs: Dict[str, Any] = dict(
        env=env,
        configs=agent_configs,
        rounds=rounds,
        seed=seed,
        energy_model=energy_model,
        energy_min=energy_min,
        energy_max=energy_max,
        energy_decay=energy_decay,
        energy_recharge=energy_recharge,
        energy_leave_threshold=energy_leave_threshold,
        landmarks_total=landmarks_total,
        render=render,
        render_delay=render_delay,
        print_every=print_every,
    )
    output_base = "output"

    # -- Single file run (library creates run_id, output folder, records/, metadata.json) --
    print("\n=== Grid-world run ===")
    session = Session.from_config(
        _make_session_config(
            shared_data_type=storage_type,
            shared_data_uri=mongo_uri if storage_type == "mongo" else None,
            scenario_name="gridworld",
            output_base=output_base,
            topology_mode=topology_mode,
            visibility=visibility,
            hub_id=hub_id,
            participation=energy_model,
        )
    )
    run_path = Path(session.run_path)
    reporter = RunReporter(
        "gridworld", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    summary = run_with_session(session, **run_kwargs, reporter=reporter)
    reporter.finalize(
        rounds=rounds, seed=seed, outcomes=summary["outcomes"],
        elapsed_seconds=0.0, output_bytes=0, render=render,
        path=str(run_path / "records"),
    )

    # -- Analysis: write_output=True writes to output_base/run_id/analysis/<category>/ --
    run_id = session.run_id
    if run_id:
        print(f"\n=== Analysis (run_id={run_id}) ===")
        effective_id = None
        try:
            effective_id = provenance.render_chain_tree("last", run_id, output_base=output_base, write_output=True)
            print("Provenance: wrote analysis/provenance/ (provenance_tree.png, .pdf)")
        except Exception as e:
            print(f"  Provenance: {e}")
        try:
            G = traceability.build_trace_graph(run_id, output_base=output_base, write_output=True)
            print(f"Traceability: wrote analysis/traceability/ ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
        except Exception as e:
            print(f"  Traceability: {e}")
        try:
            attr = accountability.causal_attribution(run_id, output_base=output_base, write_output=True)
            print(f"Accountability: wrote analysis/accountability/ ({len(attr.get('agents', []))} agents)")
        except Exception as e:
            print(f"  Accountability: {e}")
        try:
            # Use same outcome id as provenance so explanations refer to the same outcome.
            last_id = effective_id or "last"
            units = interpretability.build_atomic_explanations(last_id, run_id, output_base=output_base, write_output=True)
            print(f"Interpretability: wrote analysis/interpretability/ ({len(units)} atomic explanation units)")
        except Exception as e:
            print(f"  Interpretability: {e}")
    print(f"\nRun output: {run_path} (run_id={run_id})")


if __name__ == "__main__":
    main()
