"""Grid-world validation example using the DOAgent Session API.

Demonstrates all three DOA principles through the library:
- Shared-data model: agents share knowledge via shared data, library records transparently.
- Decentralisation: topology-filtered record access (centralised, peer-to-peer, federated).
- Openness: user provides environment, policies, and run loop; library provides interfaces.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml

from doagent import Session, RunConfig
from doagent.core import (
    FileSharedData,
    InMemoryParticipationRegistry,
    InMemorySharedData,
    Topology,
    TopologyConfig,
)
from doagent.records import SimpleRecord
from doagent.validation import (
    NoOpSharedData,
    PolicyRegistry,
    RunReporter,
    measure_baseline,
    output_bytes_from_path,
    write_summary,
)
from doagent.validation.gridworld import (
    GridAgentConfig,
    make_grid_env,
    register_gridworld_policies,
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


def parse_topology(config: Dict[str, Any]) -> Tuple[TopologyConfig, Optional[Dict[str, List[str]]]]:
    topo_cfg = config.get("scenario", {}).get("topology")
    if not topo_cfg:
        return TopologyConfig(), None
    mode = Topology(str(topo_cfg.get("mode", "centralised")).lower())
    visibility = topo_cfg.get("visibility")
    return TopologyConfig(mode=mode), visibility


def parse_agent_configs(config: Dict[str, Any]) -> List[GridAgentConfig]:
    return [
        GridAgentConfig(id=a["id"], policy=a["policy"], metadata=a.get("metadata", {}))
        for a in config.get("agents", [])
    ]


# ---------------------------------------------------------------------------
# Scenario-specific helpers
# ---------------------------------------------------------------------------

def build_shared_map(records: List[SimpleRecord]) -> Dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Session-based run
# ---------------------------------------------------------------------------

def run_with_session(
    shared_data,
    env,
    registry: PolicyRegistry,
    configs: list[GridAgentConfig],
    rounds: int,
    seed: int,
    *,
    topology_cfg: TopologyConfig | None = None,
    visibility: Dict[str, List[str]] | None = None,
    hub_id: str = "hub",
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
    topology_cfg = topology_cfg or TopologyConfig()
    agent_ids = [c["id"] for c in configs]

    # doagent: create Session with topology and wrap env/agents
    session = Session(
        shared_data,
        RunConfig(logging_level=2),
        topology=topology_cfg,
        visibility=visibility,
        hub_id=hub_id,
    )
    wrapped_env = session.wrap_env(env, env_actor="gridworld_env")
    agents = session.create_agents(
        configs, registry, goal="map_discovery", payload_type="map_update",
    )

    participation_registry = InMemoryParticipationRegistry() if energy_model else None
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
    if participation_registry is not None:
        from doagent.core import ParticipationRecord
        for aid in active_agents:
            participation_registry.register(ParticipationRecord(agent_id=aid))

    outcome_count = 0

    for round_id in range(1, rounds + 1):
        if energy_model:
            from doagent.core import ParticipationRecord
            for aid in list(active_agents):
                energy_levels[aid] -= energy_decay
                if energy_levels[aid] <= 0:
                    active_agents.remove(aid)
                    if participation_registry is not None:
                        participation_registry.deregister(aid)
            for aid in agent_ids:
                if aid in active_agents:
                    continue
                energy_levels[aid] = min(energy_levels[aid] + energy_recharge, energy_max)
                if energy_levels[aid] > energy_leave_threshold:
                    active_agents.add(aid)
                    if participation_registry is not None:
                        participation_registry.register(ParticipationRecord(agent_id=aid))

        active_ids = sorted(active_agents)
        actions: Dict[str, Any] = {}

        for aid in active_ids:
            observation = observations.get(aid, {})

            # doagent: topology-filtered record access
            shared_records = session.visible_records(aid, kind="agent_update")
            shared_map = build_shared_map(shared_records)

            # doagent: agent.decide() records agent_update transparently
            result = agents[aid].decide(observation, round_id, inputs={
                "observation": observation,
                "shared_map": shared_map,
            })
            actions[aid] = result["action"]

        # doagent: federated hub aggregation via record_update()
        if topology_cfg.mode == Topology.FEDERATED:
            hub_records = session.visible_records(hub_id, kind="agent_update")
            hub_summary = build_shared_map(hub_records)
            session.record_update(hub_id, hub_summary, payload_type="map_summary")

        # doagent: wrapped_env.step() records outcome + traces transparently
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / "gridworld_validation_config.yaml"
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_config
    config = load_config(config_path)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    participation_cfg = scenario.get("participation", {}) or {}

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
    topology_cfg, visibility = parse_topology(config)
    hub_id = "hub"

    env = make_grid_env(
        width=int(env_cfg.get("width", 6)),
        height=int(env_cfg.get("height", 6)),
        agent_ids=agent_ids,
        landmarks=int(env_cfg.get("landmarks", 2)),
        observation_radius=int(env_cfg.get("observation_radius", 1)),
        max_cycles=int(env_cfg.get("max_cycles", 25)),
        seed=run_cfg.get("seed"),
        render_mode=render_mode,
    )

    registry = PolicyRegistry()
    register_gridworld_policies(registry)

    run_kwargs: Dict[str, Any] = dict(
        env=env,
        registry=registry,
        configs=agent_configs,
        rounds=rounds,
        seed=seed,
        topology_cfg=topology_cfg,
        visibility=visibility,
        hub_id=hub_id,
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

    # -- Baseline run (NoOp adapter — no recording overhead) --
    print("\n=== Baseline run ===")
    baseline_reporter = RunReporter(
        "baseline", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    baseline_metrics = measure_baseline(
        lambda: run_with_session(
            NoOpSharedData(), **run_kwargs, reporter=baseline_reporter,
        )
    )
    baseline_summary = run_with_session(
        NoOpSharedData(), **run_kwargs, reporter=baseline_reporter,
    )

    # -- In-memory run --
    print("\n=== In-memory run ===")
    mem_shared = InMemorySharedData()
    mem_reporter = RunReporter(
        "in_memory", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    mem_summary = run_with_session(
        mem_shared, **run_kwargs, reporter=mem_reporter,
    )

    # doagent: records are accessible for inspection via shared_data
    agent_updates = list(mem_shared.listen("agent_update"))
    traces = list(mem_shared.listen("trace"))
    outcomes = list(mem_shared.listen("outcome"))
    print(f"Records: {len(agent_updates)} agent_updates, {len(outcomes)} outcomes, {len(traces)} traces")

    mem_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=mem_summary["outcomes"],
        elapsed_seconds=0.0, output_bytes=0, render=render,
    )

    # -- File run --
    print("\n=== File run ===")
    records_dir = output_dir / "records"
    file_shared = FileSharedData(records_dir)
    file_reporter = RunReporter(
        "file", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    file_summary = run_with_session(
        file_shared, **run_kwargs, reporter=file_reporter,
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
