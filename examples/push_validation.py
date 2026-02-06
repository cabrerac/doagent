"""Simple push validation example."""

from datetime import datetime
import random
from time import perf_counter
from pathlib import Path

from doagent.core import FileSharedData, InMemorySharedData
from doagent.records import new_provenance
from doagent.validation import (
    NoOpSharedData,
    PolicyRegistry,
    PushAgentConfig,
    RunReporter,
    make_push_env,
    measure_baseline,
    run_push_validation,
    write_summary,
)


def register_policies(registry: PolicyRegistry) -> None:
    def _action_from_vector(dx: float, dy: float) -> int:
        if abs(dx) < 1e-6 and abs(dy) < 1e-3:
            return 0
        if abs(dx) >= abs(dy):
            return 2 if dx > 0 else 1
        return 4 if dy > 0 else 3

    def _epsilon_greedy(base_action: int, epsilon: float, rng: random.Random) -> int:
        if rng.random() < epsilon:
            return rng.choice([0, 1, 2, 3, 4])
        return base_action

    def fixed_policy(params):
        action = params.get("action", 0)

        def decide(request):
            return {"decision": {"action": action}}

        return decide

    registry.register("fixed", fixed_policy)

    def heuristic_goal_seek(params):
        epsilon = float(params.get("epsilon", 0.0))
        seed = params.get("seed", 0)
        rng = random.Random(seed)

        def decide(request):
            observation = request.get("inputs", {}).get("observation", [])
            dx, dy = 0.0, 0.0
            if len(observation) >= 4:
                dx, dy = float(observation[2]), float(observation[3])
            base_action = _action_from_vector(dx, dy)
            action = _epsilon_greedy(base_action, epsilon, rng)
            return {"decision": {"action": action}}

        return decide

    registry.register("heuristic_goal_seek", heuristic_goal_seek)

    def heuristic_push_block(params):
        epsilon = float(params.get("epsilon", 0.0))
        seed = params.get("seed", 0)
        rng = random.Random(seed)

        def decide(request):
            observation = request.get("inputs", {}).get("observation", [])
            dx, dy = 0.0, 0.0
            if len(observation) >= 8:
                dx, dy = float(observation[6]), float(observation[7])
            base_action = _action_from_vector(dx, dy)
            action = _epsilon_greedy(base_action, epsilon, rng)
            return {"decision": {"action": action}}

        return decide

    registry.register("heuristic_push_block", heuristic_push_block)


def main() -> None:
    rounds = 100
    seed = 123
    try:
        render_demo = True
        print_every = 10
        record_reward_series = True
        series_every = 1
        record_entropy = True
        action_space = 5
        env_params = {
            "max_cycles": rounds,
            "continuous_actions": False,
            "dynamic_rescaling": False,
        }
        if render_demo:
            env_params["render_mode"] = "human"
        env = make_push_env(
            "pettingzoo:mpe2:simple_push_v3",
            env_params,
        )
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required for this example. "
            "Install with: pip install pettingzoo"
        ) from exc
    registry = PolicyRegistry()
    register_policies(registry)

    configs = [
        PushAgentConfig(
            id="adversary_0",
            policy={
                "name": "heuristic_push_block",
                "params": {"epsilon": 0.2, "seed": 1},
            },
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
            policy={
                "name": "heuristic_goal_seek",
                "params": {"epsilon": 0.2, "seed": 2},
            },
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

    shared_data = InMemorySharedData()
    in_memory_reporter = RunReporter(
        "in_memory",
        print_every=print_every,
        record_series=record_reward_series,
        series_every=series_every,
        record_entropy=record_entropy,
        action_space=action_space,
    )
    in_memory_summary = None

    def in_memory_run() -> None:
        nonlocal in_memory_summary
        in_memory_summary = run_push_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=configs,
            rounds=rounds,
            seed=seed,
            render=render_demo,
            on_outcome=in_memory_reporter.on_outcome,
        )

    in_memory_metrics = measure_baseline(in_memory_run)
    in_memory_reporter.finalize(
        rounds=rounds,
        seed=seed,
        outcomes=in_memory_summary.outcomes if in_memory_summary else 0,
        elapsed_seconds=in_memory_metrics.elapsed_seconds,
        output_bytes=in_memory_metrics.output_bytes,
        render=render_demo,
    )

    baseline_shared = NoOpSharedData()
    baseline_reporter = RunReporter(
        "baseline",
        print_every=print_every,
        record_series=record_reward_series,
        series_every=series_every,
        record_entropy=record_entropy,
        action_space=action_space,
    )
    baseline_summary = None

    def baseline_run() -> None:
        nonlocal baseline_summary
        baseline_summary = run_push_validation(
            shared_data=baseline_shared,
            env=env,
            registry=registry,
            configs=configs,
            rounds=rounds,
            seed=seed,
            render=render_demo,
            on_outcome=baseline_reporter.on_outcome,
        )

    baseline_metrics = measure_baseline(baseline_run)
    baseline_reporter.finalize(
        rounds=rounds,
        seed=seed,
        outcomes=baseline_summary.outcomes if baseline_summary else 0,
        elapsed_seconds=baseline_metrics.elapsed_seconds,
        output_bytes=baseline_metrics.output_bytes,
        render=render_demo,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("./output") / f"push_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "push_records.jsonl"
    file_shared = FileSharedData(file_path)

    file_reporter = RunReporter(
        "file",
        print_every=print_every,
        record_series=record_reward_series,
        series_every=series_every,
        record_entropy=record_entropy,
        action_space=action_space,
    )
    file_summary = None

    def file_run() -> None:
        nonlocal file_summary
        file_summary = run_push_validation(
            shared_data=file_shared,
            env=env,
            registry=registry,
            configs=configs,
            rounds=rounds,
            seed=seed,
            render=render_demo,
            on_outcome=file_reporter.on_outcome,
        )

    file_metrics = measure_baseline(file_run, output_path=file_path)
    file_reporter.finalize(
        rounds=rounds,
        seed=seed,
        outcomes=file_summary.outcomes if file_summary else 0,
        elapsed_seconds=file_metrics.elapsed_seconds,
        output_bytes=file_metrics.output_bytes,
        render=render_demo,
        path=str(file_path),
    )
    summary_payload = {
        "baseline": {
            "elapsed_seconds": baseline_metrics.elapsed_seconds,
            "output_bytes": baseline_metrics.output_bytes,
        },
        "in_memory": {
            "elapsed_seconds": in_memory_metrics.elapsed_seconds,
            "output_bytes": in_memory_metrics.output_bytes,
        },
        "file": {
            "elapsed_seconds": file_metrics.elapsed_seconds,
            "output_bytes": file_metrics.output_bytes,
        },
        "runs": {
            "in_memory": in_memory_reporter.metrics(
                outcomes=in_memory_summary.outcomes if in_memory_summary else 0
            ),
            "baseline": baseline_reporter.metrics(
                outcomes=baseline_summary.outcomes if baseline_summary else 0
            ),
            "file": file_reporter.metrics(
                outcomes=file_summary.outcomes if file_summary else 0
            ),
        },
    }
    summary_path = output_dir / "push_validation_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"Summary written to {summary_path}")
    print(
        "Plot metrics with: "
        f"python -m examples.plot_validation_metrics \"{summary_path}\""
    )


if __name__ == "__main__":
    main()
