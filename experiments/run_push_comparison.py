"""Push comparison experiment: in-memory and file-backed runs.

Run from repository root:
  python -m experiments.run_push_comparison

Uses the same run loop as examples.push_demo; writes a combined summary to the file run output.
"""

from __future__ import annotations

from pathlib import Path

from doagent import Session, make_env
from experiments import RunReporter, measure_baseline, write_summary
from examples.push_demo.env import create_push_env
from examples.push_demo.push_demo import (
    fixed_policy,
    heuristic_goal_seek,
    heuristic_push_block,
    make_agent_configs,
    run_with_session,
)


def main() -> None:
    rounds = 100
    seed = 123
    render_demo = False  # set True if you want a window
    print_every = 10

    try:
        env_params = {
            "max_cycles": rounds,
            "continuous_actions": False,
            "dynamic_rescaling": False,
        }
        if render_demo:
            env_params["render_mode"] = render_demo
        env = make_env(create_push_env, **env_params)
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required. Install with: pip install pettingzoo"
        ) from exc

    configs = make_agent_configs()

    # In-memory run
    print("\n=== In-memory run ===")
    session = Session.from_config({
        "shared_data": {"type": "memory"},
        "run_config": {"logging_level": 2},
        "policies": {
            "fixed": fixed_policy,
            "heuristic_goal_seek": heuristic_goal_seek,
            "heuristic_push_block": heuristic_push_block,
        },
    })
    reporter = RunReporter(
        "in_memory", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    metrics = measure_baseline(
        lambda: run_with_session(session, env, configs, rounds, seed, render=render_demo, reporter=reporter),
    )
    outcomes = run_with_session(session, env, configs, rounds, seed, render=render_demo, reporter=reporter)
    reporter.finalize(
        rounds=rounds, seed=seed, outcomes=outcomes,
        elapsed_seconds=metrics.elapsed_seconds,
        output_bytes=metrics.output_bytes, render=render_demo,
    )

    # File run
    print("\n=== File run ===")
    file_session = Session.from_config({
        "shared_data": {"type": "file"},
        "scenario_name": "push",
        "output_base": "./output",
        "run_config": {"logging_level": 2},
        "policies": {
            "fixed": fixed_policy,
            "heuristic_goal_seek": heuristic_goal_seek,
            "heuristic_push_block": heuristic_push_block,
        },
    })
    run_path = Path(file_session.run_path)
    records_dir = run_path / "records"
    file_reporter = RunReporter(
        "file", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    file_outcomes = run_with_session(
        file_session, env, configs, rounds, seed,
        render=render_demo, reporter=file_reporter,
    )
    file_metrics = measure_baseline(lambda: None, output_path=records_dir)
    file_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=file_outcomes,
        elapsed_seconds=file_metrics.elapsed_seconds,
        output_bytes=file_metrics.output_bytes, render=render_demo,
        path=str(records_dir),
    )

    summary_payload = {
        "runs": {
            "in_memory": reporter.metrics(outcomes=outcomes),
            "file": file_reporter.metrics(outcomes=file_outcomes),
        },
    }
    summary_path = run_path / "push_comparison_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"\nComparison summary written to {summary_path} (run_id={file_session.run_id})")


if __name__ == "__main__":
    main()
