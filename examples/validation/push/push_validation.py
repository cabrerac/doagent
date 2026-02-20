"""Push validation example using the DOAgent Session API.

Demonstrates library usage with a PettingZoo environment:
- User creates env, registers policies, defines agent configs.
- Session handles all recording transparently.
- User owns the run loop.

This file IS user code — it shows how any scenario integrates with DOAgent.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
from typing import Any, Dict

from doagent import Session, RunConfig
from doagent.core import FileSharedData, InMemorySharedData
from doagent.records import new_provenance
from doagent.validation import (
    NoOpSharedData,
    PolicyRegistry,
    RunReporter,
    measure_baseline,
    write_summary,
)
from doagent.validation.push import PushAgentConfig, make_push_env


# ---------------------------------------------------------------------------
# User-defined policies (user responsibility)
# ---------------------------------------------------------------------------

def register_policies(registry: PolicyRegistry) -> None:
    def _action_from_vector(dx: float, dy: float) -> int:
        if abs(dx) < 1e-6 and abs(dy) < 1e-3:
            return 0
        if abs(dx) >= abs(dy):
            return 2 if dx > 0 else 1
        return 4 if dy > 0 else 3

    def _epsilon_greedy(base: int, epsilon: float, rng: random.Random) -> int:
        return rng.choice([0, 1, 2, 3, 4]) if rng.random() < epsilon else base

    def fixed_policy(params):
        action = params.get("action", 0)
        def decide(request):
            return {"decision": {"action": action}}
        return decide

    def heuristic_goal_seek(params):
        epsilon = float(params.get("epsilon", 0.0))
        rng = random.Random(params.get("seed", 0))
        def decide(request):
            obs = request.get("inputs", {}).get("observation", [])
            dx, dy = (float(obs[2]), float(obs[3])) if len(obs) >= 4 else (0.0, 0.0)
            return {"decision": {"action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
        return decide

    def heuristic_push_block(params):
        epsilon = float(params.get("epsilon", 0.0))
        rng = random.Random(params.get("seed", 0))
        def decide(request):
            obs = request.get("inputs", {}).get("observation", [])
            dx, dy = (float(obs[6]), float(obs[7])) if len(obs) >= 8 else (0.0, 0.0)
            return {"decision": {"action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
        return decide

    registry.register("fixed", fixed_policy)
    registry.register("heuristic_goal_seek", heuristic_goal_seek)
    registry.register("heuristic_push_block", heuristic_push_block)


# ---------------------------------------------------------------------------
# Agent configs (user responsibility)
# ---------------------------------------------------------------------------

def make_agent_configs() -> list[PushAgentConfig]:
    return [
        PushAgentConfig(
            id="adversary_0",
            policy={"name": "heuristic_push_block", "params": {"epsilon": 0.2, "seed": 1}},
            metadata={
                "explanation": "Heuristic push/block with epsilon-greedy exploration.",
                "provenance": new_provenance(agent="adversary_0", sources=[]),
                "accountability": {
                    "owner": "team-a",
                    "policy_id": "policy-001",
                    "responsibility_scope": "simple-push",
                },
            },
        ),
        PushAgentConfig(
            id="agent_0",
            policy={"name": "heuristic_goal_seek", "params": {"epsilon": 0.2, "seed": 2}},
            metadata={
                "explanation": "Heuristic goal-seek with epsilon-greedy exploration.",
                "provenance": new_provenance(agent="agent_0", sources=[]),
                "accountability": {
                    "owner": "team-b",
                    "policy_id": "policy-001",
                    "responsibility_scope": "simple-push",
                },
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Session-based run (the pattern any user follows)
# ---------------------------------------------------------------------------

def run_with_session(
    shared_data,
    env,
    registry: PolicyRegistry,
    configs: list[PushAgentConfig],
    rounds: int,
    seed: int,
    *,
    render: bool = False,
    reporter: RunReporter | None = None,
) -> int:
    """Run push scenario using the DOAgent Session API. Returns outcome count."""
    session = Session(shared_data, RunConfig(logging_level=2))
    wrapped_env = session.wrap_env(env, env_actor="push_env")
    agents = session.create_agents(
        configs, registry, goal="push_towards_landmark",
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
        env_params = {
            "max_cycles": rounds,
            "continuous_actions": False,
            "dynamic_rescaling": False,
        }
        if render_demo:
            env_params["render_mode"] = "human"
        env = make_push_env("pettingzoo:mpe2:simple_push_v3", env_params)
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required for this example. Install with: pip install pettingzoo"
        ) from exc

    registry = PolicyRegistry()
    register_policies(registry)
    configs = make_agent_configs()

    # -- In-memory run --
    shared_data = InMemorySharedData()
    reporter = RunReporter(
        "in_memory", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )

    def in_memory_run():
        return run_with_session(
            shared_data, env, registry, configs, rounds, seed,
            render=render_demo, reporter=reporter,
        )

    metrics = measure_baseline(in_memory_run)
    outcomes = in_memory_run()

    # OPENNESS: records are accessible for inspection
    agent_updates = list(shared_data.listen("agent_update"))
    traces = list(shared_data.listen("trace"))
    outcome_records = list(shared_data.listen("outcome"))
    print(f"Records: {len(agent_updates)} agent_updates, {len(outcome_records)} outcomes, {len(traces)} traces")

    reporter.finalize(
        rounds=rounds, seed=seed, outcomes=outcomes,
        elapsed_seconds=metrics.elapsed_seconds,
        output_bytes=metrics.output_bytes, render=render_demo,
    )

    # -- File run --
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("./output") / f"push_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "push_records.jsonl"
    file_shared = FileSharedData(file_path)
    file_reporter = RunReporter(
        "file", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    file_outcomes = run_with_session(
        file_shared, env, registry, configs, rounds, seed,
        render=render_demo, reporter=file_reporter,
    )
    file_metrics = measure_baseline(
        lambda: None, output_path=file_path,
    )
    file_reporter.finalize(
        rounds=rounds, seed=seed, outcomes=file_outcomes,
        elapsed_seconds=file_metrics.elapsed_seconds,
        output_bytes=file_metrics.output_bytes, render=render_demo,
        path=str(file_path),
    )

    summary_payload = {
        "runs": {
            "in_memory": reporter.metrics(outcomes=outcomes),
            "file": file_reporter.metrics(outcomes=file_outcomes),
        },
    }
    summary_path = output_dir / "push_validation_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
