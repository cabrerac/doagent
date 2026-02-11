"""Run grid-world validation from a YAML config."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, Tuple

import yaml

from doagent.core import (
    InMemoryParticipationRegistry,
    InMemorySharedData,
    Topology,
    TopologyConfig,
)
from doagent.validation import (
    GridAgentConfig,
    PolicyRegistry,
    RunReporter,
    make_grid_env,
    register_gridworld_policies,
    run_gridworld_validation,
    write_summary,
)


def load_gridworld_config(path: str | Path) -> Dict[str, Any]:
    """Load a grid-world validation config from YAML."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config must be a YAML mapping.")
    return data


def _parse_topology(config: Dict[str, Any]) -> Tuple[TopologyConfig | None, Dict[str, list[str]] | None]:
    scenario = config.get("scenario", {})
    topo_cfg = scenario.get("topology")
    if not topo_cfg:
        return None, None
    mode_raw = str(topo_cfg.get("mode", "centralised")).lower()
    mode = Topology(mode_raw)
    visibility = topo_cfg.get("visibility")
    return TopologyConfig(mode=mode), visibility


def _parse_participation(config: Dict[str, Any]) -> Dict[str, Any]:
    scenario = config.get("scenario", {})
    return scenario.get("participation", {}) or {}


def _parse_render(config: Dict[str, Any]) -> bool:
    scenario = config.get("scenario", {})
    return bool(scenario.get("render", False))


def _parse_render_mode(config: Dict[str, Any]) -> str | None:
    scenario = config.get("scenario", {})
    return scenario.get("render_mode")


def _parse_render_delay(config: Dict[str, Any], render_mode: str | None) -> float:
    scenario = config.get("scenario", {})
    delay = scenario.get("render_delay")
    if delay is not None:
        return float(delay)
    # Default delay for human mode so agents are visible
    return 0.3 if render_mode == "human" else 0.0


def _parse_print_every(config: Dict[str, Any]) -> int:
    scenario = config.get("scenario", {})
    return int(scenario.get("print_every", 0))


def _parse_landmarks_total(config: Dict[str, Any]) -> int | None:
    env_cfg = config.get("scenario", {}).get("env", {})
    val = env_cfg.get("landmarks")
    return int(val) if val is not None else None


def _build_agent_configs(config: Dict[str, Any]) -> list[GridAgentConfig]:
    agents = config.get("agents", [])
    configs: list[GridAgentConfig] = []
    for agent in agents:
        configs.append(
            GridAgentConfig(
                id=agent["id"],
                policy=agent["policy"],
                metadata=agent.get("metadata", {}),
            )
        )
    return configs


def main() -> None:
    _script_dir = Path(__file__).resolve().parent
    default_config = _script_dir / "gridworld_validation_config.yaml"
    config_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else default_config
    )
    config = load_gridworld_config(config_path)

    shared_data = InMemorySharedData()
    participation = InMemoryParticipationRegistry()
    registry = PolicyRegistry()
    register_gridworld_policies(registry)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    agent_ids = [agent["id"] for agent in config.get("agents", [])]

    topology_cfg, visibility = _parse_topology(config)
    participation_cfg = _parse_participation(config)
    energy_model = bool(participation_cfg.get("energy_model", False))
    render = _parse_render(config)
    render_mode = _parse_render_mode(config)
    if render and render_mode is None:
        render_mode = "ansi"
    render_delay = _parse_render_delay(config, render_mode) if render else 0.0
    print_every = _parse_print_every(config)
    landmarks_total = _parse_landmarks_total(config)

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

    reporter = RunReporter(
        label="gridworld",
        print_every=0,
        record_series=True,
        series_every=1,
        record_entropy=True,
        action_space=5,
    )
    summary = run_gridworld_validation(
        shared_data=shared_data,
        env=env,
        registry=registry,
        configs=_build_agent_configs(config),
        rounds=int(run_cfg.get("rounds", 10)),
        seed=int(run_cfg.get("seed", 0)),
        topology=topology_cfg,
        visibility=visibility,
        participation_registry=participation if energy_model else None,
        energy_model=energy_model,
        energy_min=int(participation_cfg.get("energy_min", 6)),
        energy_max=int(participation_cfg.get("energy_max", 12)),
        energy_decay=int(participation_cfg.get("energy_decay", 1)),
        energy_recharge=int(participation_cfg.get("energy_recharge", 1)),
        energy_leave_threshold=int(participation_cfg.get("energy_leave_threshold", 2)),
        render=render,
        render_delay=render_delay,
        print_every=print_every,
        landmarks_total=landmarks_total,
        reporter=reporter,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output") / f"gridworld_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "run": {
            "id": run_cfg.get("id", "gridworld-run"),
            "seed": run_cfg.get("seed"),
            "rounds": run_cfg.get("rounds", 10),
        },
        "runs": {
            "gridworld": reporter.metrics(
                outcomes=summary.outcomes,
                extra={
                    "coverage": summary.coverage,
                    "discovery_round": summary.discovery_round,
                    "contributions": summary.contributions,
                    "total_cells": summary.total_cells,
                    "termination_reason": summary.termination_reason,
                    "landmarks_discovered": summary.landmarks_discovered,
                    "landmarks_total": summary.landmarks_total,
                },
            )
        },
    }
    summary_path = output_dir / "gridworld_validation_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"Outcomes recorded: {summary.outcomes}")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
