"""Run the three-agent addition example and write attribution gold labels.

From the repository root::

    python -m experiments.attribution.run
    python -m experiments.attribution.run --storage memory
    python -m experiments.attribution.run --observe

The team uses a federated topology: the orchestrator is the hub. Other
agents only see hub-authored records, so after the solver acts the
orchestrator republishes the reported sum. That is ordinary Session
usage, not a special library mode.

Step index (0-based) used in gold.json: 0 assign, 1 solve, 2 check.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from doagent import Session

from experiments.attribution.baselines.protocol import StepCollector, notify
from experiments.attribution.env import ArithmeticEnv
from experiments.attribution.labels import (
    CHECKER,
    ORCHESTRATOR,
    SOLVER,
    gold_record,
)
from experiments.attribution.policies import (
    checker_policy_factory,
    latest_assignment,
    latest_solver_value,
    orchestrator_policy_factory,
    solver_policy_factory,
)
from experiments.attribution.manifest import (
    build_run_manifest,
    write_run_manifest,
)
from experiments.attribution.projections import (
    build_attribution_artifacts,
    write_attribution_artifacts,
)

def load_yaml(path: Path) -> Dict[str, Any]:
    """Load a mapping from a YAML file. Requires PyYAML."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required to load config.yaml") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def build_session(
    storage: str,
    output_base: str,
    logging_level: int = 2,
) -> Session:
    """Create a Session with the three scripted policies registered."""
    config: Dict[str, Any] = {
        "run_config": {"logging_level": logging_level},
        "topology": {"mode": "federated"},
        "hub_id": ORCHESTRATOR,
        "participation": True,
        "policies": {
            "orchestrator": orchestrator_policy_factory,
            "solver": solver_policy_factory,
            "checker": checker_policy_factory,
        },
    }
    if storage == "memory":
        config["shared_data"] = {"type": "memory"}
    elif storage == "file":
        config["shared_data"] = {"type": "file"}
        config["scenario_name"] = "attribution_eval"
        config["output_base"] = output_base
    else:
        raise ValueError(f"Unknown storage {storage!r}")
    return Session.from_config(config)


def run_addition_team(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    *,
    storage: str = "memory",
    output_base: str = "./output",
    collectors: tuple[StepCollector, ...] | list[StepCollector] = (),
    logging_level: int = 2,
    write_eval_artifacts: bool = True,
) -> Dict[str, Any]:
    """Run assign, solve, then check. Return the session, gold labels, and key values.

    Parameters
    ----------
    query:
        ``{"a": int, "b": int}`` — the numbers to add.
    plant:
        Optional ``plant_wrong_sum`` and ``plant_accept_wrong`` (see config.yaml).
    storage:
        ``memory`` or ``file``.
    output_base:
        Root folder for file-backed runs (``output/<run_id>/``).
    collectors:
        Observe-only W/T hooks.
    logging_level:
        Session recording level (0, 1, or 2).
    write_eval_artifacts:
        Write gold, projections, and the manifest. Cost runs turn this off
        so those files stay off the capture clock.
    """
    watchers = tuple(collectors)
    session = build_session(storage, output_base, logging_level=logging_level)
    env = session.wrap_env(ArithmeticEnv(query), env_actor="arithmetic_env")

    session.register_participant(ORCHESTRATOR, capabilities=["plan", "assign"])
    session.register_participant(SOLVER, capabilities=["add"])
    session.register_participant(CHECKER, capabilities=["verify"])

    agents = session.create_agents(
        [
            {"id": ORCHESTRATOR, "policy": {"name": "orchestrator", "params": {"query": query}}},
            {
                "id": SOLVER,
                "policy": {"name": "solver", "params": {"plant_wrong_sum": plant.get("plant_wrong_sum")}},
            },
            {
                "id": CHECKER,
                "policy": {
                    "name": "checker",
                    "params": {"plant_accept_wrong": plant.get("plant_accept_wrong", True)},
                },
            },
        ],
        goal="add-two-numbers",
    )

    observations = env.reset()

    orch_request = {
        "inputs": {"query": query, "observation": observations[ORCHESTRATOR]},
    }
    orch = agents[ORCHESTRATOR].decide(
        observations[ORCHESTRATOR],
        0,
        inputs=orch_request["inputs"],
    )
    notify(
        watchers,
        step=0,
        agent=ORCHESTRATOR,
        request=orch_request,
        response=orch["response"],
    )
    env.step({ORCHESTRATOR: orch["action"]})

    assignment = latest_assignment(session.decision_context(SOLVER, kinds="agent_update"))
    if assignment is None:
        raise RuntimeError("Solver did not see an assignment from the orchestrator.")

    solve_request = {
        "inputs": {"assignment": assignment, "observation": observations[SOLVER]},
    }
    solved = agents[SOLVER].decide(
        observations[SOLVER],
        1,
        inputs=solve_request["inputs"],
    )
    notify(
        watchers,
        step=1,
        agent=SOLVER,
        request=solve_request,
        response=solved["response"],
    )
    env.step({SOLVER: solved["action"]})

    solver_value = solved["action"]["value"]
    session.record_update(
        ORCHESTRATOR,
        {"assignment": assignment, "solver_value": solver_value},
        payload_type="solver_result",
    )

    hub_view = session.decision_context(CHECKER, kinds="agent_update")
    check_assignment = latest_assignment(hub_view)
    check_value = latest_solver_value(hub_view)
    if check_assignment is None or check_value is None:
        raise RuntimeError("Checker did not see the assignment or the solver value.")

    check_request = {
        "inputs": {
            "assignment": check_assignment,
            "solver_value": check_value,
            "observation": observations[CHECKER],
        },
    }
    checked = agents[CHECKER].decide(
        observations[CHECKER],
        2,
        inputs=check_request["inputs"],
    )
    notify(
        watchers,
        step=2,
        agent=CHECKER,
        request=check_request,
        response=checked["response"],
    )
    env.step({CHECKER: checked["action"]})

    gold = gold_record(query, plant)
    gold["run_id"] = session.run_id
    artifacts: Dict[str, Any] = {}
    artifact_paths: Dict[str, str] = {}
    if write_eval_artifacts:
        artifacts = build_attribution_artifacts(session)
        if session.run_path:
            gold_path = Path(session.run_path) / "gold.json"
            gold_path.write_text(json.dumps(gold, indent=2) + "\n", encoding="utf-8")
            gold["gold_path"] = str(gold_path)
            artifact_paths = write_attribution_artifacts(session, session.run_path)
            artifact_paths["manifest"] = write_run_manifest(
                session.run_path,
                build_run_manifest(
                    run_id=session.run_id,
                    storage=storage,
                    query=query,
                    plant=plant,
                    logging_level=logging_level,
                    output_base=output_base,
                ),
            )

    return {
        "session": session,
        "gold": gold,
        "assignment": assignment,
        "solver_value": solver_value,
        "artifacts": artifacts,
        "artifact_paths": artifact_paths,
        "packs": {item.name: item.steps() for item in watchers},
    }


def main(argv: Optional[list[str]] = None) -> None:
    """CLI: load config.yaml, run the team, print gold labels."""
    parser = argparse.ArgumentParser(
        description="Three-agent addition example with a known failure for attribution"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.yaml")),
        help="YAML file with query and optional planted values",
    )
    parser.add_argument("--storage", choices=("file", "memory"), default=None)
    parser.add_argument(
        "--observe",
        action="store_true",
        help="Attach observe-only W and T collectors on this DOAgent run.",
    )
    args = parser.parse_args(argv)

    cfg = load_yaml(Path(args.config))
    storage = args.storage or str(cfg.get("storage", "file"))
    collectors: list[StepCollector] = []
    if args.observe:
        from experiments.attribution.baselines import (
            OutputLogCollector,
            StepIOCollector,
        )

        collectors = [OutputLogCollector(), StepIOCollector()]
    result = run_addition_team(
        cfg["query"],
        cfg.get("plant") or {},
        storage=storage,
        output_base=str(cfg.get("output_base", "./output")),
        collectors=collectors,
    )
    gold = result["gold"]
    print(json.dumps({k: gold[k] for k in gold if k != "gold_path"}, indent=2))
    if gold.get("gold_path"):
        print(f"gold written to {gold['gold_path']}")
    for name, path in result["artifact_paths"].items():
        print(f"{name.upper()} written to {path}")
    if collectors and result.get("session") and result["session"].run_path:
        analysis = Path(result["session"].run_path) / "analysis" / "attribution"
        for collector in collectors:
            written = collector.write(analysis / collector.filename)
            print(f"baseline {collector.name.upper()} written to {written}")


if __name__ == "__main__":
    main()
