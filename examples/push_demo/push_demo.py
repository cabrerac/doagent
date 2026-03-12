"""Push demo using the DOAgent Session API.

Demonstrates config-driven library usage with a PettingZoo environment.
No doagent.core or doagent.records imports needed.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
from typing import Any, Dict

from doagent import Session, make_env
from experiments import (
    RunReporter,
    measure_baseline,
    write_summary,
)
from examples.push_demo.env import create_push_env


# ---------------------------------------------------------------------------
# Policy factories (callable entry points for config-driven registration)
# ---------------------------------------------------------------------------

def _action_from_vector(dx: float, dy: float) -> int:
    if abs(dx) < 1e-6 and abs(dy) < 1e-3:
        return 0
    if abs(dx) >= abs(dy):
        return 2 if dx > 0 else 1
    return 4 if dy > 0 else 3


def _epsilon_greedy(base: int, epsilon: float, rng: random.Random) -> int:
    return rng.choice([0, 1, 2, 3, 4]) if rng.random() < epsilon else base


def fixed_policy(params: Dict[str, Any]) -> Any:
    action = params.get("action", 0)
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        return {"decision": {"action": action}}
    return decide


def heuristic_goal_seek(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[2]), float(obs[3])) if len(obs) >= 4 else (0.0, 0.0)
        return {"decision": {"action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
    return decide


def heuristic_push_block(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[6]), float(obs[7])) if len(obs) >= 8 else (0.0, 0.0)
        return {"decision": {"action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
    return decide


# ---------------------------------------------------------------------------
# Agent configs
# ---------------------------------------------------------------------------

def make_agent_configs() -> list[Dict[str, Any]]:
    """Agent configs as plain dicts: id, policy, metadata."""
    return [
        {
            "id": "adversary_0",
            "policy": {"name": "heuristic_push_block", "params": {"epsilon": 0.2, "seed": 1}},
            "metadata": {"explanation": "Heuristic push/block with epsilon-greedy exploration."},
        },
        {
            "id": "agent_0",
            "policy": {"name": "heuristic_goal_seek", "params": {"epsilon": 0.2, "seed": 2}},
            "metadata": {"explanation": "Heuristic goal-seek with epsilon-greedy exploration."},
        },
    ]


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
    render: bool = False,
    reporter: RunReporter | None = None,
) -> int:
    """Run push scenario using the DOAgent Session API. Returns outcome count."""
    wrapped_env = session.wrap_env(env, env_actor="push_env")
    agents = session.create_agents(
        configs, goal="push_towards_landmark",
    )

    observations = wrapped_env.reset(seed=seed)
    if render:
        wrapped_env.render()

    outcome_count = 0
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        for agent_id, agent in agents.items():
            result = agent.decide(observations.get(agent_id, {}), round_id)
            actions[agent_id] = result["action"]

        step = wrapped_env.step(actions)
        if reporter is not None:
            reporter.on_outcome(round_id, actions, step["rewards"])
        if render:
            wrapped_env.render()
        observations = step["observations"]
        outcome_count += 1

    return outcome_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rounds = 100
    seed = 123
    render_demo = True
    print_every = 10

    try:
        env_params: Dict[str, Any] = {
            "max_cycles": rounds,
            "continuous_actions": False,
            "dynamic_rescaling": False,
        }
        if render_demo:
            env_params["render_mode"] = render_demo
        env = make_env(create_push_env, **env_params)
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required for this example. Install with: pip install pettingzoo"
        ) from exc

    configs = make_agent_configs()

    # -- In-memory run (config-driven session) --
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

    def in_memory_run():
        return run_with_session(
            session, env, configs, rounds, seed,
            render=render_demo, reporter=reporter,
        )

    metrics = measure_baseline(in_memory_run)
    outcomes = in_memory_run()

    agent_updates = session.inspect("agent_update")
    traces = session.inspect("trace")
    outcome_records = session.inspect("outcome")
    print(f"Records: {len(agent_updates)} agent_updates, {len(outcome_records)} outcomes, {len(traces)} traces")

    reporter.finalize(
        rounds=rounds, seed=seed, outcomes=outcomes,
        elapsed_seconds=metrics.elapsed_seconds,
        output_bytes=metrics.output_bytes, render=render_demo,
    )

    # -- File run (config-driven session) --
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("./output") / f"push_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = str(output_dir / "records")

    file_session = Session.from_config({
        "shared_data": {"type": "file", "path": records_path},
        "run_config": {"logging_level": 2},
        "policies": {
            "fixed": fixed_policy,
            "heuristic_goal_seek": heuristic_goal_seek,
            "heuristic_push_block": heuristic_push_block,
        },
    })
    file_reporter = RunReporter(
        "file", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    file_outcomes = run_with_session(
        file_session, env, configs, rounds, seed,
        render=render_demo, reporter=file_reporter,
    )
    records_dir = output_dir / "records"
    file_metrics = measure_baseline(
        lambda: None, output_path=records_dir,
    )
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
    summary_path = output_dir / "push_demo_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
