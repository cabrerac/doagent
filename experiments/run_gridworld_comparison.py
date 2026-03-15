"""Gridworld comparison experiment: baseline (NoOp), in-memory, and file-backed runs.

Run from repository root:
  python -m experiments.run_gridworld_comparison [config.yaml]

Uses the same run loop as examples.gridworld_demo; writes a combined summary to the file run output.
"""

from __future__ import annotations

import sys
from pathlib import Path

from doagent import Session, make_env
from experiments import (
    RunReporter,
    measure_baseline,
    output_bytes_from_path,
    write_summary,
)
from examples.gridworld_demo.gridworld_demo import (
    GRIDWORLD_POLICIES,
    _make_session_config,
    load_config,
    parse_agent_configs,
    parse_topology,
    run_with_session,
)
from examples.gridworld_demo.env import create_gridworld_env


def main() -> None:
    script_dir = Path(__file__).resolve().parent.parent
    default_config = script_dir / "examples" / "gridworld_demo" / "gridworld_demo_config.yaml"
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_config
    config = load_config(config_path)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    rounds = int(run_cfg.get("rounds", 10))
    seed = int(run_cfg.get("seed", 0))
    render = bool(scenario.get("render", False))
    print_every = int(scenario.get("print_every", 0))
    landmarks_total = int(env_cfg["landmarks"]) if "landmarks" in env_cfg else None
    topology_mode, visibility = parse_topology(config)
    hub_id = "hub"
    agent_configs = parse_agent_configs(config)
    agent_ids = [c["id"] for c in agent_configs]

    env = make_env(
        create_gridworld_env,
        width=int(env_cfg.get("width", 6)),
        height=int(env_cfg.get("height", 6)),
        agent_ids=agent_ids,
        landmarks=int(env_cfg.get("landmarks", 2)),
        observation_radius=int(env_cfg.get("observation_radius", 1)),
        max_cycles=int(env_cfg.get("max_cycles", 25)),
        seed=run_cfg.get("seed"),
        render_mode="ansi" if render else None,
    )

    run_kwargs = dict(
        env=env,
        configs=agent_configs,
        rounds=rounds,
        seed=seed,
        energy_model=False,
        landmarks_total=landmarks_total,
        render=render,
        render_delay=0.0,
        print_every=print_every,
    )

    # Baseline (NoOp)
    print("\n=== Baseline run (NoOp) ===")
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
        lambda: run_with_session(baseline_session, **run_kwargs, reporter=baseline_reporter),
    )
    baseline_session2 = Session.from_config(noop_cfg)
    baseline_summary = run_with_session(baseline_session2, **run_kwargs, reporter=baseline_reporter)
    baseline_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=baseline_summary["outcomes"],
        elapsed_seconds=baseline_metrics.elapsed_seconds, output_bytes=0, render=render,
    )

    # In-memory
    print("\n=== In-memory run ===")
    mem_reporter = RunReporter(
        "in_memory", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    mem_session = Session.from_config(
        _make_session_config(topology_mode=topology_mode, visibility=visibility, hub_id=hub_id),
    )
    mem_summary = run_with_session(mem_session, **run_kwargs, reporter=mem_reporter)
    mem_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=mem_summary["outcomes"],
        elapsed_seconds=0.0, output_bytes=0, render=render,
    )

    # File
    print("\n=== File run ===")
    file_session = Session.from_config(
        _make_session_config(
            shared_data_type="file",
            scenario_name="gridworld",
            output_base="output",
            topology_mode=topology_mode,
            visibility=visibility,
            hub_id=hub_id,
        ),
    )
    run_path = Path(file_session.run_path)
    records_dir = run_path / "records"
    file_reporter = RunReporter(
        "file", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    file_summary = run_with_session(file_session, **run_kwargs, reporter=file_reporter)
    file_metrics = measure_baseline(lambda: None, output_path=records_dir)
    file_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=file_summary["outcomes"],
        elapsed_seconds=file_metrics.elapsed_seconds,
        output_bytes=output_bytes_from_path(records_dir),
        render=render, path=str(records_dir),
    )

    def _run_metrics(label: str, reporter: RunReporter, summary: dict) -> dict:
        return reporter.metrics(outcomes=summary["outcomes"], extra=summary)

    summary_payload = {
        "run": {"id": file_session.run_id, "seed": seed, "rounds": rounds},
        "runs": {
            "baseline": _run_metrics("baseline", baseline_reporter, baseline_summary),
            "in_memory": _run_metrics("in_memory", mem_reporter, mem_summary),
            "file": _run_metrics("file", file_reporter, file_summary),
        },
        "baseline_elapsed_seconds": baseline_metrics.elapsed_seconds,
    }
    summary_path = run_path / "gridworld_comparison_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"\nComparison summary written to {summary_path} (run_id={file_session.run_id})")


if __name__ == "__main__":
    main()
