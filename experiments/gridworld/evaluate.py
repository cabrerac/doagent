"""Evaluate one fixed gridworld condition and measure that same execution."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional

from doagent import RunReporter, Session, make_env
from examples.gridworld.env import create_gridworld_env
from examples.gridworld.session import (
    make_session_config,
    parse_agent_configs,
    parse_topology,
    run_with_session,
)
from experiments._shared import EvaluationResult, output_bytes_from_path


def evaluate_gridworld(
    config: Dict[str, Any],
    *,
    storage: str,
    output_base: str = "output",
    topology_mode: Optional[str] = None,
    visibility: Optional[Dict[str, list[str]]] = None,
) -> EvaluationResult:
    """Run and measure one gridworld storage/topology condition exactly once."""
    run_cfg = config.get("run") or {}
    scenario = config.get("scenario") or {}
    env_cfg = scenario.get("env") or {}
    participation = scenario.get("participation") or {}
    rounds = int(run_cfg.get("rounds", 10))
    seed = int(run_cfg.get("seed", 0))
    configured_topology, configured_visibility = parse_topology(config)
    effective_topology = topology_mode or configured_topology
    effective_visibility = (
        visibility if visibility is not None else configured_visibility
    )
    agent_configs = parse_agent_configs(config)
    agent_ids = [item["id"] for item in agent_configs]

    env = make_env(
        create_gridworld_env,
        width=int(env_cfg.get("width", 6)),
        height=int(env_cfg.get("height", 6)),
        agent_ids=agent_ids,
        landmarks=int(env_cfg.get("landmarks", 2)),
        observation_radius=int(env_cfg.get("observation_radius", 1)),
        max_cycles=int(env_cfg.get("max_cycles", rounds)),
        seed=seed,
        render_mode=None,
    )
    session = Session.from_config(
        make_session_config(
            shared_data_type=storage,
            scenario_name="gridworld" if storage == "file" else None,
            output_base=output_base,
            topology_mode=effective_topology,
            visibility=effective_visibility,
            hub_id="hub",
            participation=bool(participation),
        )
    )
    reporter = RunReporter(
        f"{storage}_{effective_topology}",
        print_every=0,
        record_series=True,
        series_every=1,
        record_entropy=True,
        action_space=5,
    )
    started = perf_counter()
    summary = run_with_session(
        session,
        env,
        agent_configs,
        rounds,
        seed,
        energy_model=bool(participation.get("energy_model", False)),
        energy_min=int(participation.get("energy_min", 6)),
        energy_max=int(participation.get("energy_max", 12)),
        energy_decay=int(participation.get("energy_decay", 1)),
        energy_recharge=int(participation.get("energy_recharge", 1)),
        energy_leave_threshold=int(
            participation.get("energy_leave_threshold", 2)
        ),
        landmarks_total=(
            int(env_cfg["landmarks"]) if "landmarks" in env_cfg else None
        ),
        render=False,
        print_every=0,
        reporter=reporter,
    )
    session.close()
    elapsed = perf_counter() - started
    records_path = (
        Path(session.run_path) / "records" if session.run_path else None
    )
    metrics = reporter.metrics(
        outcomes=summary["outcomes"],
        extra=summary,
    )
    return EvaluationResult(
        condition={
            "scenario": "gridworld",
            "storage": storage,
            "topology": effective_topology,
            "seed": seed,
            "rounds": rounds,
        },
        task_metrics=metrics,
        elapsed_seconds=elapsed,
        output_bytes=output_bytes_from_path(records_path),
        run_id=session.run_id,
        run_path=str(session.run_path) if session.run_path else None,
    )
