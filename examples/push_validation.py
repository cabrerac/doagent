"""Simple push validation example."""

from datetime import datetime
from pathlib import Path

from doagent.core import FileSharedData, InMemorySharedData
from doagent.records import new_provenance
from doagent.validation import (
    NoOpSharedData,
    PolicyRegistry,
    PushAgentConfig,
    make_push_env,
    measure_baseline,
    run_push_validation,
    write_summary,
)


def register_policies(registry: PolicyRegistry) -> None:
    def fixed_policy(params):
        action = params.get("action", 0)

        def decide(request):
            return {"decision": {"action": action}}

        return decide

    registry.register("fixed", fixed_policy)


def main() -> None:
    shared_data = InMemorySharedData()
    try:
        render_demo = True
        env_params = {
            "max_cycles": 100,
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
            policy={"name": "fixed", "params": {"action": 2}},
            metadata={
                "explanation": "Hold position (noop) in push task.",
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
            policy={"name": "fixed", "params": {"action": 1}},
            metadata={
                "explanation": "Move left in push task.",
                "provenance": new_provenance(agent="agent_0", sources=[]),
                "accountability": {
                    "owner": "team-b",
                    "policy_id": "policy-001",
                    "responsibility_scope": "simple-push",
                },
            },
        ),
    ]

    def in_memory_run() -> None:
        run_push_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=configs,
            rounds=3,
            seed=123,
            render=False,
        )

    in_memory_metrics = measure_baseline(in_memory_run)
    summary = run_push_validation(
        shared_data=shared_data,
        env=env,
        registry=registry,
        configs=configs,
        rounds=3,
        seed=123,
        render=render_demo,
    )
    print(f"Simple push validation complete. Outcomes: {summary.outcomes}")

    baseline_shared = NoOpSharedData()

    def baseline_run() -> None:
        run_push_validation(
            shared_data=baseline_shared,
            env=env,
            registry=registry,
            configs=configs,
            rounds=3,
            seed=123,
            render=False,
        )

    baseline_metrics = measure_baseline(baseline_run)
    print(
        "Baseline run complete.",
        f"Elapsed: {baseline_metrics.elapsed_seconds:.4f}s,",
        f"Output bytes: {baseline_metrics.output_bytes}",
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("./output") / f"push_run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "push_records.jsonl"
    file_shared = FileSharedData(file_path)

    def file_run() -> None:
        run_push_validation(
            shared_data=file_shared,
            env=env,
            registry=registry,
            configs=configs,
            rounds=3,
            seed=123,
            render=False,
        )

    file_metrics = measure_baseline(file_run, output_path=file_path)
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
    }
    summary_path = output_dir / "push_validation_summary.json"
    write_summary(summary_path, summary_payload)
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
