"""Grid-world validation example using the DOAgent Session API.

Demonstrates all three DOA principles through the library:
- Shared-data model: agents share knowledge via shared data, library records transparently.
- Decentralisation: topology-filtered record access (centralised, peer-to-peer, federated).
- Openness: user provides environment, policies, and run loop; library provides interfaces.

Config-driven: no doagent.core or doagent.records imports needed.

Run from the repository root so that the doagent package is on the path:
  python -m examples.validation.gridworld.gridworld_validation [config.yaml] [--record-gif path.gif]
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml

from doagent import Session, make_env
from doagent.validation import (
    RunReporter,
    measure_baseline,
    output_bytes_from_path,
    write_summary,
)
from examples.validation.gridworld.env import create_gridworld_env
from examples.validation.gridworld.policies import (
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
# Session-based run (config-driven)
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
    record_frames: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Run gridworld scenario using the DOAgent Session API. Returns summary dict."""
    agent_ids = [c["id"] for c in configs]

    wrapped_env = session.wrap_env(env, env_actor="gridworld_env")
    agents = session.create_agents(
        configs, goal="map_discovery", payload_type="map_update",
    )

    observations = wrapped_env.reset(seed=seed)
    if render and record_frames is not None:
        frame = env.render()
        if frame is not None:
            record_frames.append(frame)
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
            for aid in agent_ids:
                if aid in active_agents:
                    continue
                energy_levels[aid] = min(energy_levels[aid] + energy_recharge, energy_max)
                if energy_levels[aid] > energy_leave_threshold:
                    active_agents.add(aid)

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
            frame = env.render()
            if record_frames is not None and frame is not None:
                record_frames.append(frame)
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
    topology_mode: str = "centralised",
    visibility: Dict[str, List[str]] | None = None,
    hub_id: str = "hub",
) -> Dict[str, Any]:
    """Build a Session config dict from run parameters."""
    cfg: Dict[str, Any] = {
        "shared_data": {"type": shared_data_type},
        "run_config": {"logging_level": 2},
        "topology": {"mode": topology_mode},
        "policies": GRIDWORLD_POLICIES,
        "hub_id": hub_id,
    }
    if shared_data_path:
        cfg["shared_data"]["path"] = shared_data_path
    if visibility:
        cfg["topology"]["visibility"] = visibility
    return cfg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / "gridworld_validation_config.yaml"
    argv = list(sys.argv[1:])
    record_gif_path: Optional[Path] = None
    if "--record-gif" in argv:
        idx = argv.index("--record-gif")
        argv.pop(idx)
        if idx < len(argv):
            record_gif_path = Path(argv.pop(idx))
        else:
            record_gif_path = Path("output") / "gridworld_demo.gif"
    config_path = Path(argv[0]) if argv else default_config
    config = load_config(config_path)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    participation_cfg = scenario.get("participation", {}) or {}

    rounds = int(run_cfg.get("rounds", 10))
    seed = int(run_cfg.get("seed", 0))
    render = bool(scenario.get("render", False)) or record_gif_path is not None
    render_mode = scenario.get("render_mode")
    if record_gif_path is not None:
        render_mode = "rgb_array"
    elif render and render_mode is None:
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output") / f"gridworld_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    record_frames: List[Any] = [] if record_gif_path is not None else []

    # -- Baseline run (NoOp adapter) --
    print("\n=== Baseline run ===")
    baseline_reporter = RunReporter(
        "baseline", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    noop_cfg = _make_session_config(
        shared_data_type="noop", topology_mode=topology_mode,
        visibility=visibility, hub_id=hub_id,
    )
    baseline_session = Session.from_config(noop_cfg)
    baseline_metrics = measure_baseline(
        lambda: run_with_session(
            baseline_session, **run_kwargs, reporter=baseline_reporter,
        )
    )
    baseline_session2 = Session.from_config(noop_cfg)
    baseline_summary = run_with_session(
        baseline_session2,
        **run_kwargs,
        reporter=baseline_reporter,
        record_frames=record_frames if record_gif_path is not None else None,
    )
    if record_gif_path is not None:
        if record_frames:
            record_gif_path.parent.mkdir(parents=True, exist_ok=True)
            import imageio
            imageio.mimwrite(str(record_gif_path), record_frames, fps=4, loop=0)
            print(f"GIF written to {record_gif_path} ({len(record_frames)} frames)")
        else:
            print("Warning: no frames captured for GIF (ensure pygame and numpy are installed)")
        record_gif_path = None
        record_frames = []

    # -- In-memory run --
    print("\n=== In-memory run ===")
    mem_session = Session.from_config(
        _make_session_config(topology_mode=topology_mode, visibility=visibility, hub_id=hub_id)
    )
    mem_reporter = RunReporter(
        "in_memory", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    mem_summary = run_with_session(
        mem_session, **run_kwargs, reporter=mem_reporter,
    )

    agent_updates = mem_session.inspect("agent_update")
    traces = mem_session.inspect("trace")
    outcomes = mem_session.inspect("outcome")
    print(f"Records: {len(agent_updates)} agent_updates, {len(outcomes)} outcomes, {len(traces)} traces")

    mem_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=mem_summary["outcomes"],
        elapsed_seconds=0.0, output_bytes=0, render=render,
    )

    # -- File run --
    print("\n=== File run ===")
    records_dir = output_dir / "records"
    file_session = Session.from_config(
        _make_session_config(
            shared_data_type="file",
            shared_data_path=str(records_dir),
            topology_mode=topology_mode,
            visibility=visibility,
            hub_id=hub_id,
        )
    )
    file_reporter = RunReporter(
        "file", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    file_summary = run_with_session(
        file_session, **run_kwargs, reporter=file_reporter,
    )

    file_metrics = measure_baseline(lambda: None, output_path=records_dir)
    file_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=file_summary["outcomes"],
        elapsed_seconds=file_metrics.elapsed_seconds,
        output_bytes=output_bytes_from_path(records_dir),
        render=render, path=str(records_dir),
    )

    # -- Combined summary --
    def _run_metrics(label: str, reporter: RunReporter, summary: Dict[str, Any]) -> Dict[str, Any]:
        return reporter.metrics(outcomes=summary["outcomes"], extra=summary)

    summary_payload = {
        "run": {"id": run_cfg.get("id", "gridworld-run"), "seed": seed, "rounds": rounds},
        "runs": {
            "baseline": _run_metrics("baseline", baseline_reporter, baseline_summary),
            "in_memory": _run_metrics("in_memory", mem_reporter, mem_summary),
            "file": _run_metrics("file", file_reporter, file_summary),
        },
        "baseline_elapsed_seconds": baseline_metrics.elapsed_seconds,
    }
    summary_path = output_dir / "gridworld_validation_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"\nSummary written to {summary_path}")


if __name__ == "__main__":
    main()
