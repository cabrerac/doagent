"""Evaluate one fixed push condition and measure that same execution."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Dict

from doagent import RunReporter, Session, make_env
from examples.push.env import create_push_env
from examples.push.policies import (
    heuristic_goal_seek,
    heuristic_push_block,
    make_agent_configs,
)
from examples.push.session import run_with_session
from experiments._shared import EvaluationResult, output_bytes_from_path


def evaluate_push(
    *,
    storage: str,
    rounds: int = 100,
    seed: int = 123,
    output_base: str = "output",
) -> EvaluationResult:
    """Run and measure one push storage condition exactly once."""
    env = make_env(
        create_push_env,
        max_cycles=rounds,
        continuous_actions=False,
        dynamic_rescaling=False,
    )
    config: Dict[str, Any] = {
        "shared_data": {"type": storage},
        "run_config": {"logging_level": 2},
        "policies": {
            "heuristic_goal_seek": heuristic_goal_seek,
            "heuristic_push_block": heuristic_push_block,
        },
    }
    if storage == "file":
        config.update(
            {
                "scenario_name": "push",
                "output_base": output_base,
            }
        )
    session = Session.from_config(config)
    reporter = RunReporter(
        storage,
        print_every=0,
        record_series=True,
        series_every=1,
        record_entropy=True,
        action_space=5,
    )
    started = perf_counter()
    outcomes = run_with_session(
        session,
        env,
        make_agent_configs(),
        rounds,
        seed,
        render=False,
        reporter=reporter,
    )
    elapsed = perf_counter() - started
    records_path = (
        Path(session.run_path) / "records" if session.run_path else None
    )
    return EvaluationResult(
        condition={
            "scenario": "push",
            "storage": storage,
            "seed": seed,
            "rounds": rounds,
        },
        task_metrics=reporter.metrics(outcomes=outcomes),
        elapsed_seconds=elapsed,
        output_bytes=output_bytes_from_path(records_path),
        run_id=session.run_id,
        run_path=str(session.run_path) if session.run_path else None,
    )
